import sys
import json
from pathlib import Path
from schema import FIELDS
from pdf_reader import read_input
from extract import call_llm
from validate import validate, canon
from confidence import field_confidence, REVIEW_THRESHOLD


def _node(run, f):
    n = run.get(f)
    return n if isinstance(n, dict) else {"value": n, "evidence": None, "confidence": 0.5}


def _num(x, default=0.5):
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return default


def process(path):
    text = read_input(path)
    run1 = call_llm(text, temperature=0.0)
    run2 = call_llm(text, temperature=0.3)   # second opinion for agreement check

    raw = {f: _node(run1, f).get("value") for f in FIELDS}
    clean, items, issues = validate(raw, run1.get("line_items") or [])

    fields = {}
    for f in FIELDS:
        n1, n2 = _node(run1, f), _node(run2, f)
        agreement = canon(f, n1.get("value")) == canon(f, n2.get("value"))
        conf = field_confidence(
            f, clean.get(f), n1.get("evidence"), _num(n1.get("confidence")),
            agreement, f in issues, text)
        fields[f] = {"value": clean.get(f), "confidence": conf,
                     "evidence": n1.get("evidence"), "issues": issues.get(f, [])}

    return {
        "source_file": Path(path).name,
        "fields": fields,
        "line_items": items,
        "document_issues": issues.get("line_items", []) + issues.get("_document", []),
        "needs_review": [f for f, d in fields.items() if d["confidence"] < REVIEW_THRESHOLD],
    }


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "samples")
    files = sorted(p for p in ([target] if target.is_file() else target.glob("*"))
                   if p.suffix.lower() in (".pdf", ".txt"))
    Path("output").mkdir(exist_ok=True)
    for f in files:
        print(f"Processing {f.name} ...")
        result = process(f)
        (Path("output") / f"{f.stem}.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))