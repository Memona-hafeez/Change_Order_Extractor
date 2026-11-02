from pathlib import Path
import pdfplumber


def read_input(path):
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        pages = []
        with pdfplumber.open(p) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text(layout=True) or "")
        text = "\n".join(pages).strip()
        if len(text) < 30:
            raise ValueError(f"{p.name}: no text layer (scanned PDF?). OCR needed.")
        return text
    return p.read_text(encoding="utf-8", errors="ignore")