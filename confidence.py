import re
from difflib import SequenceMatcher
from schema import MONEY_FIELDS

W_SELF, W_GROUND, W_AGREE, W_VALID = 0.20, 0.40, 0.25, 0.15
REVIEW_THRESHOLD = 0.70


def _norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def evidence_score(evidence, source):
    """1.0 if the quoted evidence exists in the document verbatim."""
    if not evidence:
        return 0.0
    e, s = _norm(evidence), _norm(source)
    if e in s:
        return 1.0
    m = SequenceMatcher(None, e, s, autojunk=False).find_longest_match(0, len(e), 0, len(s))
    return round(m.size / len(e), 2)


def number_in_text(value, source):
    """Anti-hallucination: does this number actually appear in the document?"""
    flat = source.replace(",", "")
    v = abs(value)
    return f"{v:.2f}" in flat or f"{v:.0f}" in flat


def field_confidence(field, value, evidence, self_conf, agreement, has_issue, source):
    if value is None:
        # Model says "not present": trust more if both runs agree
        return 0.8 if agreement else 0.3
    ground = evidence_score(evidence, source)
    if field in MONEY_FIELDS:
        ground = 0.5 * ground + 0.5 * (1.0 if number_in_text(value, source) else 0.0)
    score = (W_SELF * self_conf + W_GROUND * ground
             + W_AGREE * (1.0 if agreement else 0.0)
             + W_VALID * (0.0 if has_issue else 1.0))
    if has_issue:
        score = min(score, 0.60)  # validation failure => always goes to human review
    return round(max(0.0, min(1.0, score)), 2)