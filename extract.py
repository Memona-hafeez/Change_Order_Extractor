import os
import json
import time
from dotenv import load_dotenv
from groq import Groq
from schema import FIELDS, FIELD_HELP
from chunker import select_relevant

load_dotenv()
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
client = Groq(api_key=os.environ["GROQ_API_KEY"])

field_lines = "\n".join(f'- "{f}": {FIELD_HELP[f]}' for f in FIELDS)

SYSTEM = f"""You are an information extraction engine for construction change orders.
Return ONLY one valid JSON object (JSON, no markdown, no commentary).

For EACH field below return an object: {{"value": ..., "evidence": "...", "confidence": 0.0-1.0}}
- "evidence" must be an EXACT copy of the shortest snippet from the document that supports the value. Never paraphrase it.
- If the document does not state the field, use {{"value": null, "evidence": null, "confidence": 0}}.
- NEVER guess and NEVER calculate values that are not written in the document.
- "confidence" is your honest certainty. Lower it if the text is ambiguous, garbled or has several candidate values.

Layout notes:
- The text comes from a PDF; labels and values can be on separate lines or in different columns. A value usually sits directly below or beside its label.
- "owner" and "contractor" must be company or person names, never a project or building name. If the owner's name appears only in a signature block (e.g. "OWNER (Firm name)" followed by a name), use that.
- Checkbox labels such as "OWNER X" are not names.
- "signed" is true only if the document shows signatures, "/s/", or signer names with dates in the signature area. In that case quote one signer line as evidence.
- "signed" is false ONLY if the document visibly shows an unsigned or blank signature line, or says it is unsigned. If the document says nothing about signatures or approval, "signed" must be null (not false).
- "description_of_change": include ALL listed change items, joined with "; ".

Fields:
{field_lines}

Also return "line_items": a list of objects with keys description, quantity, unit_price, total
(copied as written; empty list if the document has no itemized lines).
"""


def call_llm(text, temperature=0.0, retries=5):
    text = select_relevant(text)
    user = f'DOCUMENT:\n"""\n{text}\n"""'
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": user}],
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            wait = 10 * (attempt + 1)
            print(f"  LLM error ({e}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError("LLM failed after retries")