import re

KEYWORDS = [
    "change order", "contract sum", "contract amount", "original contract",
    "new contract", "revised contract", "adjusted contract", "net change",
    "previous", "this change", "days", "contract time", "owner", "contractor",
    "project", "date", "approved", "signed", "signature", "description",
]


def split_chunks(text, size=1500, overlap=200):
    chunks, i = [], 0
    while i < len(text):
        chunks.append((i, text[i:i + size]))
        i += size - overlap
    return chunks


def score(chunk):
    low = chunk.lower()
    s = sum(low.count(k) for k in KEYWORDS)
    s += 2 * len(re.findall(r"\$\s?[\d,]+", chunk))
    return s


def select_relevant(text, max_chars=12000):
    """Short doc: return as is. Long doc: keep top-scoring chunks in original order."""
    if len(text) <= max_chars:
        return text
    chunks = split_chunks(text)
    ranked = sorted(chunks, key=lambda c: score(c[1]), reverse=True)
    chosen, total = [], 0
    for pos, ch in ranked:
        if total + len(ch) > max_chars:
            break
        chosen.append((pos, ch))
        total += len(ch)
    chosen.sort(key=lambda c: c[0])
    return "\n...\n".join(ch for _, ch in chosen)