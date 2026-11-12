import io
from typing import Optional
import docx
import openpyxl

def extract_text_from_docx(file_bytes: bytes) -> str:
    """DOCX faylidan matnlarni ajratib olish."""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        
        # Jadvallarni ham o'qish
        table_texts = []
        for table in doc.tables:
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_data:
                    table_texts.append(" | ".join(row_data))
                    
        full_text = "\n".join(paragraphs)
        if table_texts:
            full_text += "\n\n--- Jadvallar ---\n" + "\n".join(table_texts)
        return full_text
    except Exception as e:
        return f"[DOCX faylini o'qishda xatolik: {e}]"

def extract_text_from_excel(file_bytes: bytes) -> str:
    """Excel (XLSX) faylidan varaqlar va kataklar matnini ajratib olish."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        sheets_data = []
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            sheet_lines = [f"=== Varaq: {sheet_name} ==="]
            for row in sheet.iter_rows(values_only=True):
                non_empty = [str(val).strip() for val in row if val is not None and str(val).strip()]
                if non_empty:
                    sheet_lines.append(" | ".join(non_empty))
            if len(sheet_lines) > 1:
                sheets_data.append("\n".join(sheet_lines))
        return "\n\n".join(sheets_data)
    except Exception as e:
        return f"[Excel faylini o'qishda xatolik: {e}]"
