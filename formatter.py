import html
import re

def markdown_to_telegram_html(text: str) -> str:
    """
    Gemini qaytargan matnni Telegram HTML formatiga xavfsiz va chiroyli o'tkazish.
    Ortiqcha yulduzchalar (***), panjaralar (###) va g'alati belgilarni to'g'rilaydi.
    """
    if not text:
        return ""

    # 1. Ko'p qatorli kod bloklarini saqlash (```python ... ```)
    code_blocks = []
    def save_code_block(match):
        code_blocks.append(match.group(1))
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"

    text = re.sub(r'```(?:[a-zA-Z0-9_-]+)?\n?(.*?)```', save_code_block, text, flags=re.DOTALL)

    # 2. Bir qatorli kodlarni saqlash (`...`)
    inline_codes = []
    def save_inline_code(match):
        inline_codes.append(match.group(1))
        return f"__INLINE_CODE_{len(inline_codes)-1}__"

    text = re.sub(r'`([^`]+)`', save_inline_code, text)

    # 3. HTML maxsus belgilarini escape qilish (lekin qo'shtirnoq va apostrofni buzmaymiz, chunki o'zbek tilida tutuq belgisi ko'p)
    text = html.escape(text, quote=False)

    # 4. Sarlavhalarni to'g'rilash (### Sarlavha -> <b>Sarlavha</b>)
    text = re.sub(r'^#{1,6}\s*(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)

    # 5. Qalin va kursiv (3 ta yulduzcha: ***matn*** -> <b><i>matn</i></b>)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)

    # 6. Qalin matn (2 ta yulduzcha: **matn** -> <b>matn</b>)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # 7. Kursiv matn (1 ta yulduzcha yoki _pastki chiziq_)
    text = re.sub(r'(?<!\w)\*([^\*\n]+?)\*(?!\w)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!\w)_([^_ \n]+?)_(?!\w)', r'<i>\1</i>', text)

    # 8. Ro'yxat belgilarini tartibga keltirish (* band -> • band)
    text = re.sub(r'^\s*[\*\-]\s+', '• ', text, flags=re.MULTILINE)

    # 9. Adashib qolgan ortiqcha yulduzchalarni tozalash (masalan ****)
    text = re.sub(r'\*{2,}', '', text)

    # 10. Saqlangan inline kodlarni qaytarish
    for idx, code in enumerate(inline_codes):
        safe_code = html.escape(code, quote=False)
        text = text.replace(f"__INLINE_CODE_{idx}__", f"<code>{safe_code}</code>")

    # 11. Saqlangan kod bloklarini qaytarish
    for idx, code in enumerate(code_blocks):
        safe_code = html.escape(code, quote=False)
        text = text.replace(f"__CODE_BLOCK_{idx}__", f"<pre><code>{safe_code}</code></pre>")

    return text.strip()

def strip_all_markdown(text: str) -> str:
    """Xatolik yuz berganda barcha formatlash belgilarini butunlay tozalab tashlash."""
    text = re.sub(r'\*{1,}', '', text)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'^\s*[\*\-]\s+', '• ', text, flags=re.MULTILINE)
    return text.strip()
