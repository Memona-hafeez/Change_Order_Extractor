import re
from datetime import datetime
from pydantic import ValidationError
from schema import MONEY_FIELDS, ChangeOrder

DATE_FORMATS = ["%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%B %d %Y",
                "%b %d %Y", "%d %B %Y", "%d %b %Y",
                "%Y-%b-%d", "%d-%b-%Y"]


def parse_money(v):
    """'$12,500.00' -> 12500.0 ; '(3,200)' -> -3200.0"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    neg = (s.startswith("(") and s.endswith(")")) or s.startswith("-") \
        or s.startswith("−") or "credit" in s.lower()
    digits = re.sub(r"[^\d.]", "", s)
    if not digits or digits == "." or digits.count(".") > 1:
        return None
    val = float(digits)
    return -val if neg else val


def parse_date(v):
    """Returns (iso_date or None, is_ambiguous)."""
    if not v:
        return None, False
    s = str(v).strip()
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s, f).date().isoformat(), False
        except ValueError:
            pass
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", s)
    if m:
        a, b, y = map(int, m.groups())
        ambiguous = a <= 12 and b <= 12 and a != b
        try:
            return datetime(y, a, b).date().isoformat(), ambiguous  # assume MM/DD
        except ValueError:
            try:
                return datetime(y, b, a).date().isoformat(), False  # DD/MM
            except ValueError:
                return None, False
    return None, False


def to_int(v):
    m = re.search(r"-?\d+(\.\d+)?", str(v).replace(",", ""))
    return int(round(float(m.group()))) if m else None


def to_bool(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "yes", "signed"):
        return True
    if s in ("false", "no", "unsigned"):
        return False
    return None


def close(a, b):
    return abs(a - b) <= 0.01


def canon(field, v):
    """Canonical form, used to compare values across runs and in eval."""
    if v is None or v == "":
        return None
    if field in MONEY_FIELDS:
        return parse_money(v)
    if field == "date":
        return parse_date(v)[0]
    if field == "schedule_change_days":
        return to_int(v)
    if field == "signed":
        return to_bool(v)
    if field == "change_order_number":
        digits = re.sub(r"\D", "", str(v)).lstrip("0")
        return digits or str(v).strip().lower()
    s = re.sub(r"[^a-z0-9 ]", "", str(v).lower())
    return re.sub(r"\s+", " ", s).strip()


def validate(raw, line_items):
    """raw: field -> raw LLM value. Returns (clean_dict, line_items, issues)."""
    issues = {}

    def add(field, msg):
        issues.setdefault(field, []).append(msg)

    clean = {}
    for f in MONEY_FIELDS:
        clean[f] = parse_money(raw.get(f))
        if raw.get(f) not in (None, "") and clean[f] is None:
            add(f, "could not parse amount")

    iso, amb = parse_date(raw.get("date"))
    clean["date"] = iso
    if raw.get("date") and iso is None:
        add("date", "unrecognized date format")
    if amb:
        add("date", "ambiguous day/month order; assumed MM/DD/YYYY")

    clean["schedule_change_days"] = (
        to_int(raw["schedule_change_days"])
        if raw.get("schedule_change_days") is not None else None)
    clean["signed"] = to_bool(raw["signed"]) if raw.get("signed") is not None else None

    for f in ["project_name", "change_order_number", "contractor",
              "owner", "description_of_change"]:
        v = raw.get(f)
        clean[f] = str(v).strip() if v not in (None, "") else None

    items = []
    if isinstance(line_items, list):
        for it in line_items:
            if isinstance(it, dict):
                items.append({
                    "description": it.get("description"),
                    "quantity": parse_money(it.get("quantity")),
                    "unit_price": parse_money(it.get("unit_price")),
                    "total": parse_money(it.get("total")),
                })

    # ---- cross checks: arithmetic ----
    o, c, n = (clean["original_contract_sum"], clean["change_amount"],
               clean["new_contract_sum"])
    p = clean["previous_changes_total"] or 0.0
    if None not in (o, c, n):
        if not (close(o + c, n) or close(o + p + c, n)):
            msg = "original + change != new contract sum"
            for f in ("original_contract_sum", "change_amount", "new_contract_sum"):
                add(f, msg)

    for i in items:
        q, u, t = i["quantity"], i["unit_price"], i["total"]
        if None not in (q, u, t) and not close(q * u, t):
            add("line_items", f"qty*price != total for '{i['description']}'")
    totals = [i["total"] for i in items if i["total"] is not None]
    if totals and c is not None and not close(sum(totals), c):
        add("change_amount", "sum of line items != change amount")

    # ---- cross-field: parties must differ from each other ----
    pn, ow, ct = (clean.get(k) for k in ("project_name", "owner", "contractor"))
    for f1, v1, f2, v2 in [("owner", ow, "contractor", ct),
                           ("owner", ow, "project_name", pn),
                           ("contractor", ct, "project_name", pn)]:
        if v1 and v2 and canon(f1, v1) == canon(f2, v2):
            add(f1, f"same value as {f2}")
            add(f2, f"same value as {f1}")

    # ---- final schema validation ----
    try:
        out = ChangeOrder(**clean, line_items=items).model_dump()
        items = out.pop("line_items")
        clean = out
    except ValidationError as e:
        add("_document", f"schema error: {e.errors()[0]['msg']}")

    return clean, items, issues