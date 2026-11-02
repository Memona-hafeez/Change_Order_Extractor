import json
import time
from pathlib import Path
from difflib import SequenceMatcher
from pipeline import process
from validate import canon
from schema import FIELDS

SKIP = {"description_of_change"}  # free text, not scored
EVAL_FIELDS = [f for f in FIELDS if f not in SKIP]


def match(f, exp, got):
    e, g = canon(f, exp), canon(f, got)
    if e is None or g is None:
        return e == g
    if isinstance(e, str):
        return SequenceMatcher(None, e, g).ratio() >= 0.85
    if isinstance(e, float):
        return abs(e - g) < 0.01
    return e == g


correct = {f: 0 for f in EVAL_FIELDS}
total = {f: 0 for f in EVAL_FIELDS}
conf_ok, conf_bad, dangerous = [], [], []

files = sorted(p for p in Path("samples").glob("*") if p.suffix in (".pdf", ".txt"))
for p in files:
    exp_path = Path("samples/expected") / f"{p.stem}.json"
    if not exp_path.exists():
        print(f"SKIP {p.name}: no expected JSON in samples/expected/")
        continue
    exp = json.loads(exp_path.read_text())
    print("Evaluating", p.name)
    try:
        res = process(p)
    except Exception as e:
        print(f"  FAILED: {e}")
        continue
    for f in EVAL_FIELDS:
        got = res["fields"][f]
        ok = match(f, exp.get(f), got["value"])
        total[f] += 1
        correct[f] += ok
        (conf_ok if ok else conf_bad).append(got["confidence"])
        if not ok:
            print(f"  WRONG {f}: got {got['value']!r}, expected {exp.get(f)!r}, conf {got['confidence']}")
            if got["confidence"] >= 0.7:
                dangerous.append((p.name, f, got["value"], exp.get(f), got["confidence"]))
    time.sleep(15)  # free-tier rate limits (8000 tokens/min)

print("\n=== Field accuracy ===")
for f in EVAL_FIELDS:
    print(f"{f:26s} {correct[f]}/{total[f]}")
all_c, all_t = sum(correct.values()), sum(total.values())
if all_t:
    print(f"\nOVERALL: {all_c}/{all_t} = {all_c / all_t:.0%}")
avg = lambda xs: round(sum(xs) / len(xs), 2) if xs else "n/a"
print(f"Avg confidence when correct: {avg(conf_ok)} | when wrong: {avg(conf_bad)}")
print("\nWrong but confident (>=0.7), the dangerous cases:")
for d in dangerous:
    print("  ", d)
if not dangerous:
    print("   none")