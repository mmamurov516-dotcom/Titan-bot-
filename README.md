# Titan Gemini AI Telegram Bot 🤖🇺🇿

Google Gemini sun'iy intellekti bilan ishlovchi, ko'p tarmoqli (multimodal), aqlli xotira va administrator paneliga ega zamonaviy Telegram bot.

---

## 🌟 Bot imkoniyatlari:
1. **O'zbek tili:** Faqat va faqat o'zbek tilida mukammal, ravon muloqot olib boradi.
2. **Aqlli xotira (Memory):** So'nggi 20-50 ta suhbat xabarini eslab qoladi va kontekst asosida muloqot qiladi.
3. **Internetdan qidiruv (Google Search):** Yangiliklar, ob-havo, kurslar va so'nggi faktlarni internetdan real vaqtda topib beradi.
4. **Multimodal tahlil:**
   - 🖼 **Rasmlar:** Rasmni ko'rib, batafsil tahlil qiladi.
   - 📄 **Hujjatlar (2 MB gacha):** PDF, Word (`.docx`), Excel (`.xlsx`, `.csv`), matnli fayllarni o'qib savollarga javob beradi.
   - 🎙 **Ovozli xabarlar (20 MB gacha):** Ovozli yozuvni aniq transkripsiya qiladi, undagi savolga javob qaytaradi va `.txt` fayl sifatida taqdim etadi.
5. **👑 Admin Panel:**
   - Umumiy statistika (foydalanuvchilar soni, faollik).
   - Foydalanuvchilar ro'yxati.
   - Jonli suhbatlar monitoringi (odamlar nima savol berayotgani va AI javoblarini ko'rib turish).
   - Barcha a'zolarga xabar tarqatish (Broadcast).
6. **Serverga moslashuv (Render 24/7):** Ichki health-check veb-serveri orqali Render va boshqa bulutli serverlarda to'xtovsiz ishlaydi.

---

## 🚀 Render.com serverida 24/7 ishga tushirish yo'riqnomasi

### 1-qadam: GitHub ga yuklash
Loyihangiz papkasida terminal orqali quyidagi buyruqlarni bajaring:
```bash
git init
git add .
git commit -m "feat: Titan Bot full release"
git branch -M main
git remote add origin https://github.com/mmamurov516-dotcom/Titan-bot-.git
git push -u origin main
```

### 2-qadam: Render.com da Web Service yaratish
1. [Render.com](https://render.com) saytiga kiring va **GitHub hisobingiz orqali** ro'yxatdan o'ting.
2. Bosh sahifada **New +** tugmasini bosing va **Web Service** ni tanlang.
3. GitHub dagi `mmamurov516-dotcom/Titan-bot-` repozitoriyasini tanlang va **Connect** tugmasini bosing.
4. Sozlamalarni quyidagicha to'ldiring:
   - **Name:** `titan-gemini-bot`
   - **Region:** Frankfurt (Germaniya) yoki istalgan yaqin server
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Instance Type:** `Free`

### 3-qadam: Maxfiy o'zgaruvchilarni (Environment Variables) kiritish
O'sha sahifaning pastrog'idagi **Environment Variables** bo'limiga quyidagi 3 ta parametrni qo'shing:
- `BOT_TOKEN` = `sizning_telegram_bot_tokeningiz`
- `GEMINI_API_KEY` = `sizning_gemini_api_kalitingiz`
- `ADMIN_ID` = `8675462900`

So'ng **Deploy Web Service** (yoki **Create Web Service**) tugmasini bosing.
Render loyihangizni bir necha daqiqada yuklab, ishga tushiradi. Loglarda `Render health-check server 8080-portda ishga tushdi` va `Run polling for bot @t1tann_bot` yozuvlari chiqadi.

---

## ⏰ 24/7 to'xtovsiz ishlashini ta'minlash (Cron-job sozlash)
Render bepul tarifida 15 daqiqa murojaat bo'lmasa, server uxlab qolishi mumkin. Buni oldini olish va bot 24/7 uyg'oq turishi uchun:

1. Render dashboardida xizmatingizning URL manzilini nusxalang:  
   *(masalan: `https://titan-gemini-bot.onrender.com`)*
2. Bepul [cron-job.org](https://cron-job.org) saytiga kiring va hisob yarating.
3. **Create Cronjob** tugmasini bosing:
   - **Title:** `Titan Bot Ping`
   - **URL:** Render bergan URL manzilingiz (masalan: `https://titan-gemini-bot.onrender.com/health`)
   - **Execution schedule:** `Every 10 minutes` (Har 10 daqiqada)
4. **Create** tugmasini bosing.

🎉 **Bo'ldi!** Endi `cron-job.org` har 10 daqiqada botingiz serveriga so'rov yuborib turadi va Render serveri hech qachon uxlamasdan **24/7 rejimda to'xtovsiz** ishlaydi!
