# Change-Order Extraction Pipeline

Turns messy construction change-order PDFs or plain text into **validated JSON with a
confidence score, supporting evidence and validation issues for every field**, and tells you
which fields a human should check.

```jsonc
"change_amount": {
  "value": -32400.0,
  "confidence": 0.93,
  "evidence": "Credit for deleted work: ($32,400.00)",
  "issues": []
}
```

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env            # add GROQ_API_KEY (default model: openai/gpt-oss-120b)
python make_samples.py          # builds 5 synthetic samples + expected JSON
python pipeline.py samples      # extract all samples -> output/*.json
python pipeline.py some.pdf     # one file
python eval.py                  # field accuracy + confidence check vs samples/expected
```

## Approach

```
PDF / text -> read -> select relevant chunks -> LLM (x2) -> validate -> score -> JSON
```

| Step | File | What it does |
|---|---|---|
| Read | `pdf_reader.py` | pdfplumber with `layout=True` to keep label/value columns aligned. Scanned PDFs (no text layer) raise an explicit "OCR needed" error instead of returning garbage. |
| Select | `chunker.py` | Short docs pass through. Long docs (>12k chars) are split into overlapping chunks and the highest keyword/dollar-density chunks are kept. |
| Extract | `extract.py` | One LLM call returns `{value, evidence, confidence}` per field plus line items. Prompt rules: evidence must be a verbatim quote, never guess or calculate, "unsigned" (false) differs from "no mention" (null). Called twice (temperature 0.0 and 0.3). |
| Validate | `validate.py` | Deterministic code, not the LLM, normalizes values: `$12,500.00` -> `12500.0`, `(3,200)` -> `-3200.0`, dates -> ISO. Then cross-checks (below). |
| Score | `confidence.py` | Per-field confidence from four signals (below). Fields under 0.70 go to `needs_review`. |

### Design decisions

1. **The LLM copies, code computes.** The model is told to return values exactly as written.
   Parsing, sign handling and arithmetic are done in plain Python, so a language model never
   has to do maths or reformat dates.
2. **Abstain rather than guess.** Missing or ambiguous fields come back `null` with low
   confidence and land in `needs_review`. A silent wrong value is worse than a flagged blank.
3. **Confidence is built mostly from signals the model cannot fake.**

   | Signal | Weight | Meaning |
   |---|---|---|
   | Grounding | 0.40 | Is the quoted evidence really in the source (fuzzy match)? Money fields must also have the number itself appear in the text. |
   | Agreement | 0.25 | Do two independent runs give the same normalized value? |
   | Self-reported | 0.20 | The model's own confidence (deliberately the smallest-but-one weight). |
   | Validation | 0.15 | No failed cross-check. Any field with an issue is **capped at 0.60**. |

4. **Cross-field validation catches errors a single field cannot show.**
   - `original (+ previous) + this change == new contract sum`
   - line item `qty * unit_price == total`, and `sum(line items) == change amount`
   - owner / contractor / project name must not collapse to the same string
   - ambiguous dates (`04/03/2026`) are parsed as MM/DD, flagged, and sent to review
   - final pydantic schema check

## Results

`python eval.py` over 6 documents x 11 scored fields (free-text description is not scored):
5 synthetic samples covering a clean PDF, a credit with an ambiguous date, OCR-style noise
(`0RDER`, non-standard labels), an email-style text file and a draft with missing values, plus
one PDF imitating the AIA G701 form layout (AI-generated, not a scan of a real project).

| Run | Accuracy | Avg conf. correct | Avg conf. wrong | Wrong but confident (>=0.7) |
|---|---|---|---|---|
| 1 | 65/66 (98%) | 0.96 | 0.30 | 0 |
| 2 | 64/66 (97%) | 0.95 | 0.53 | 1 |
| 3 | 66/66 (100%) | 0.95 | n/a | 0 |

What the runs showed:
- Wrong answers consistently scored lower than right ones, so the confidence ordering is useful.
- **Results vary between runs** (LLM sampling), so I report the range, not the best run.
- Run 1's miss: sample3 labels the base amount "Prev. contract sum" instead of "original".
  The model abstained (`null`, 0.30) rather than guessing, which is the intended behaviour. I then
  added a prompt rule for this label variant, which is why run 3 passes.
- Run 2's miss was the dangerous kind: an email calls the project "Lakeside School gym" in the
  subject and "Lakeside School Gym Renovation" in the body; the model picked the short form at 0.75.

**Honest caveat:** six documents, mostly synthetic, and I tuned the prompt and validators while
looking at these same files. 97-100% is a sanity check for the pipeline, not a benchmark of real-world accuracy.

## Failure modes

Known and not fixed unless stated.

**Input**

| Failure | Behaviour |
|---|---|
| Scanned / image-only PDF | Stops with "OCR needed". No OCR step built. |
| Ambiguous date (`04/03/2026`) | Assumes MM/DD, flags it, caps confidence at 0.60 so it gets reviewed. |
| Multi-column layouts | Value can be read from the wrong column (e.g. checkbox text `OWNER X` taken as a name). Prompt rules and the distinct-parties check reduce this, not eliminate it. |
| Long documents | Keyword chunk selection could drop the page that holds the totals. Only applies above 12k chars, untested. |
| Unseen label wording | "Prev. contract sum", "Revised sum", etc. Handled for the cases I saw; new variants will tend to return `null` and be flagged. |

**Checks that are weaker than they look**

| Failure | Detail |
|---|---|
| Number grounding is a substring test | A small number such as `5` days appears in almost any document, so small values get little real protection from this check. |
| Line items | In the AIA-style test the model returned no line items although the PDF lists three priced rows summing exactly to the change amount, so that cross-check never ran. |
| Same entity, several spellings | Seen in eval (project name above). Confidence was not low enough to trigger review. A "prefer the fullest name in the body" rule would help. |

**Confidence**

| Failure | Detail |
|---|---|
| `signed` is over-trusted | Printed names under a signature block scored 1.0 as "signed". Printed names are not signatures. Fix: cap confidence unless there is `/s/`, an explicit "signed", or a signature image. |
| Weights are hand-set | 0.20 / 0.40 / 0.25 / 0.15 were chosen by reasoning, not fitted. With 66 data points they cannot be calibrated. |
| Agreement is not independence | Both runs use the same model and share blind spots, so agreeing does not prove correctness. |

**Practical**

| Failure | Detail |
|---|---|
| Cost / latency | Two LLM calls per document. Fine here, wasteful at volume. |
| Free-tier rate limits | `eval.py` sleeps 15 s between files. |
| Sample realism | Synthetic text is cleaner than real scans and faxes. |

## What I would do next

1. Cap `signed` confidence unless there is real signature evidence.
2. Require line-item extraction on itemized documents so the sum check always runs.
3. Add OCR (e.g. Tesseract, or a vision model) for scanned inputs.
4. Replace the second same-model run with a different model for a more independent agreement signal.
5. Build 30-50 real, hand-labelled change orders, then fit and calibrate the confidence weights
   (reliability curve) instead of hand-setting them.
6. Add unit tests for `validate.py` (money, dates, cross-checks), which run without an API key.

## Layout

```
pipeline.py     orchestration, CLI        extract.py     prompt + LLM call
pdf_reader.py   PDF/text input            validate.py    normalisation + cross-checks
chunker.py      long-document selection   confidence.py  per-field scoring
schema.py       pydantic model, fields    eval.py        accuracy + calibration check
make_samples.py synthetic sample builder  samples/       inputs + expected/ ground truth
```
