import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from google import genai
from google.genai import types
from config import GEMINI_API_KEY
from file_parser import extract_text_from_docx, extract_text_from_excel

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """
Siz Telegram uchun yaratilgan ko'p tarmoqli (multimodal) va internetdan ma'lumot qidiruvchi sun'iy intellekt yordamchisisiz.
Qat'iy qoidalar:
1. Siz FAQAT VA FAQAT O'ZBEK TILIDA muloqot qilasiz.
2. Agar foydalanuvchi boshqa tilda yozsa, hech qanday tarjimasiz qat'iy ravishda faqat:
"Men ushbu tilda gaplasha olmayman. Iltimos, faqat o'zbek tilida muloqot qiling." deb javob bering.
3. Internetdan qidirish (Google Search):
- So'nggi yangiliklar, ob-havo, valyuta kurslari, yangi faktlar va dolzarb ma'lumotlar so'ralganda internet qidiruvidan faol foydalaning va eng yangi ma'lumotlarni taqdim eting.
4. Telegram formati:
- Javoblarni Telegram uchun chiroyli va qulay formatda taqdim eting.
- Ketma-ket keraksiz belgilar, ortiqcha yulduzchalar (***), panjaralar (###) ishlatmang.
- Qalin matn uchun faqat **matn** ishlating, ro'yxatlar uchun • yoki raqamlardan foydalaning.
5. Kontekstni (xotirani) inobatga oling.
"""

# Zaxira modellar ketma-ketligi (birontasi limitga uchrasa, darhol keyingisiga o'tadi)
MODELS_TO_TRY = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash"
]

class GeminiService:
    def __init__(self):
        if not GEMINI_API_KEY:
            self.client = None
            return

        self.client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Internet qidiruvi ulangan asosiy konfiguratsiya
        self.search_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.7,
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
        
        # Zaxira (qidiruvsiz) konfiguratsiya
        self.plain_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.7,
        )

    def _sync_generate(self, contents: list, use_search: bool = True, custom_config: Optional[types.GenerateContentConfig] = None) -> str:
        """Modellarni avtomatik rotatsiya qilib xatosiz javob olish."""
        configs_to_try = []
        if custom_config:
            configs_to_try = [custom_config]
        elif use_search:
            # Avval internet qidiruvi bilan, agar bo'lmasa qidiruvsiz sinash
            configs_to_try = [self.search_config, self.plain_config]
        else:
            configs_to_try = [self.plain_config]

        for cfg in configs_to_try:
            for model_name in MODELS_TO_TRY:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=cfg
                    )
                    if response and response.text:
                        return response.text
                except Exception as e:
                    logger.warning(f"Model {model_name} (search={use_search}) limit yoki xato berdi: {e}. Keyingi modelga o'tilmoqda.")
                    continue

        return "Kechirasiz, ayni paytda serverlar yuqori yuklanishda. Iltimos, bir necha daqiqadan so'ng qayta urinib ko'ring."

    def _build_history_contents(self, history: List[Dict[str, str]]) -> list:
        contents = []
        for item in history:
            role = "user" if item["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=item["content"])]
                )
            )
        return contents

    async def get_response(self, history: List[Dict[str, str]], current_message: str) -> str:
        """Matnli xabar va internetdan qidiruv."""
        if not self.client:
            return "⚠️ Gemini API kaliti kiritilmagan!"

        try:
            contents = self._build_history_contents(history)
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=current_message)]
                )
            )
            return await asyncio.to_thread(self._sync_generate, contents, True)
        except Exception as e:
            logger.error(f"Gemini matn xatosi: {e}")
            return "Kechirasiz, javob tayyorlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."

    async def analyze_image(self, image_bytes: bytes, mime_type: str, caption: str, history: List[Dict[str, str]]) -> str:
        """Rasmlarni tahlil qilish."""
        if not self.client:
            return "⚠️ Gemini API kaliti kiritilmagan!"

        try:
            prompt_text = caption if caption else "Ushbu rasmni batafsil tahlil qiling va nimalar tasvirlanganini o'zbek tilida tushuntirib bering."
            contents = self._build_history_contents(history)
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        types.Part.from_text(text=prompt_text)
                    ]
                )
            )
            return await asyncio.to_thread(self._sync_generate, contents, False)
        except Exception as e:
            logger.error(f"Gemini rasm xatosi: {e}")
            return "Kechirasiz, rasmni ko'rishda xatolik yuz berdi."

    async def analyze_document(self, doc_bytes: bytes, filename: str, mime_type: str, caption: str, history: List[Dict[str, str]]) -> str:
        """Hujjatlarni tahlil qilish."""
        if not self.client:
            return "⚠️ Gemini API kaliti kiritilmagan!"

        try:
            fname_lower = filename.lower()
            prompt = caption if caption else f"Ushbu '{filename}' nomli hujjat mazmunini o'zbek tilida tahlil qiling."
            contents = self._build_history_contents(history)

            if fname_lower.endswith(".docx") or fname_lower.endswith(".doc"):
                doc_text = extract_text_from_docx(doc_bytes)
                combined = f"Hujjat: {filename}\nMatn:\n{doc_text}\n\nSavol: {prompt}"
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=combined)]))
            elif fname_lower.endswith(".xlsx") or fname_lower.endswith(".xls") or fname_lower.endswith(".csv"):
                excel_text = doc_bytes.decode("utf-8", errors="ignore") if fname_lower.endswith(".csv") else extract_text_from_excel(doc_bytes)
                combined = f"Excel: {filename}\nJadval:\n{excel_text}\n\nSavol: {prompt}"
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=combined)]))
            elif fname_lower.endswith(".pdf") or "pdf" in mime_type:
                pdf_part = types.Part.from_bytes(data=doc_bytes, mime_type="application/pdf")
                contents.append(types.Content(role="user", parts=[pdf_part, types.Part.from_text(text=f"Fayl: {filename}\n{prompt}")]))
            else:
                text_content = doc_bytes.decode("utf-8", errors="ignore")
                combined = f"Fayl: {filename}\nMatn:\n{text_content}\n\nSavol: {prompt}"
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=combined)]))

            return await asyncio.to_thread(self._sync_generate, contents, False)
        except Exception as e:
            logger.error(f"Gemini hujjat xatosi: {e}")
            return "Kechirasiz, hujjatni o'qishda xatolik yuz berdi."

    async def transcribe_and_answer(self, audio_bytes: bytes, mime_type: str) -> Tuple[str, str]:
        """
        Ovozli xabarni o'zbek tilida aniq transkripsiya qilish VA undagi savolga javob qaytarish.
        Qaytaradi: (transkripsiya_matni, suniy_intellekt_javobi)
        """
        if not self.client:
            return ("API kalit yo'q", "⚠️ Gemini API kaliti kiritilmagan!")

        try:
            instruction = """
Siz audio tahlilchi va sun'iy intellekt yordamchisisiz.
Ushbu audio yozuv O'ZBEK TILIDA gapirilgan.
Sizning 2 ta vazifangiz bor:
1. Audioda aytilgan barcha gaplarni diqqat bilan eshiting va to'liq o'zbek lotin imlosida xatosiz transkripsiya qiling.
2. Agar audioda savol, topshiriq yoki murojaat bo'lsa, unga to'laqonli, ravon o'zbek tilida javob bering.

Javobingizni QAT'IY ravishda quyidagi ikki bo'limda bering:
---TRANSKRIPSIYA---
(audiodagi aniq so'zlar)
---JAVOB---
(savolga yoki murojaatga sun'iy intellekt javobi)
"""
            cfg = types.GenerateContentConfig(
                system_instruction=instruction,
                temperature=0.3
            )

            clean_mime = mime_type if mime_type else "audio/ogg"
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime),
                        types.Part.from_text(text="Iltimos, ushbu audioni transkripsiya qiling va undagi savolga javob bering.")
                    ]
                )
            ]

            full_res = await asyncio.to_thread(self._sync_generate, contents, False, cfg)
            
            # Matnni ajratib olish
            transcription = ""
            answer = ""
            if "---TRANSKRIPSIYA---" in full_res and "---JAVOB---" in full_res:
                parts = full_res.split("---JAVOB---")
                transcription = parts[0].replace("---TRANSKRIPSIYA---", "").strip()
                answer = parts[1].strip()
            else:
                transcription = full_res.strip()
                answer = "Ovozli xabar qabul qilindi va muvaffaqiyatli transkripsiya qilindi."

            return (transcription, answer)
        except Exception as e:
            logger.error(f"Gemini audio xatosi: {e}")
            return ("Transkripsiyada xatolik", "Kechirasiz, audio yozuvni qayta ishlashda xatolik yuz berdi.")
