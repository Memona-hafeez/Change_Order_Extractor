import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

S1 = """CHANGE ORDER NO. 003
Project: Riverside Medical Center - Phase 2
Date: March 14, 2026
Owner: Riverside Health Partners LLC
Contractor: Apex Builders Inc.

Description of Change:
Add two additional electrical outlets in each patient room on Level 3.

Original Contract Sum: $1,250,000.00
Net change by previous Change Orders: $0.00
This Change Order: $12,500.00
New Contract Sum: $1,262,500.00

Contract time change: 5 days

Line items:
Outlets - 40 ea @ 125.00 = 5,000.00
Wiring labor - 100 hr @ 75.00 = 7,500.00

Approved by: John Smith, Owner Rep.  Signed: /s/ John Smith"""

S2 = """CO # 7
Job: Maple Street Townhomes
Date: 04/03/2026
Owner: Maple Dev Group
Contractor: Brightline Construction

Reason: Owner deleted the rooftop deck from scope.
Original contract: $840,000
Credit for deleted work: ($32,400.00)
Revised contract total: $807,600
Schedule: decrease of 3 days
Signature: ____________ (unsigned)"""

S3 = """CHANGE 0RDER   No: CO-012
Proj:  Harbor View Warehouse
Dated 2026-01-22
Owner : Harbor Logistics Co
GC : Steelman Contractors LLC
Scope: Install additional fire suppression sprinkler heads in Zone B per fire marshal request.
Prev. contract sum   $2,100,000.00
Prior approved COs   $45,000.00
THIS CO   $18,750.00
Adjusted contract sum   $2,163,750.00
Time extension: 10 calendar days
Approved: Maria Lopez, Steelman (signed)"""

S4 = """Subject: CO 21 - Lakeside School gym
Hi team, attaching CO 21 for Lakeside School Gym Renovation dated June 5 2026.
Owner is Lakeside School District, contractor Tri-County Builders.
We are adding a secondary scoreboard wiring run. Cost is $4,300.
Contract was 615,000 and now becomes 619,300. No time impact.
Not yet signed by the district."""

S5 = """Change Order Request (DRAFT - NOT FINAL)
Project: Oak Ridge Library
Amount: TBD pending pricing from subcontractor"""

N = None
SAMPLES = [
    ("sample1_clean", "pdf", S1, dict(
        project_name="Riverside Medical Center - Phase 2", change_order_number="3",
        date="2026-03-14", contractor="Apex Builders Inc.",
        owner="Riverside Health Partners LLC", original_contract_sum=1250000,
        previous_changes_total=0, change_amount=12500, new_contract_sum=1262500,
        schedule_change_days=5, signed=True)),
    ("sample2_credit_ambiguous_date", "pdf", S2, dict(
        project_name="Maple Street Townhomes", change_order_number="7",
        date="2026-04-03", contractor="Brightline Construction",
        owner="Maple Dev Group", original_contract_sum=840000,
        previous_changes_total=N, change_amount=-32400, new_contract_sum=807600,
        schedule_change_days=-3, signed=False)),
    ("sample3_messy_ocr", "pdf", S3, dict(
        project_name="Harbor View Warehouse", change_order_number="12",
        date="2026-01-22", contractor="Steelman Contractors LLC",
        owner="Harbor Logistics Co", original_contract_sum=2100000,
        previous_changes_total=45000, change_amount=18750, new_contract_sum=2163750,
        schedule_change_days=10, signed=True)),
    ("sample4_email_text", "txt", S4, dict(
        project_name="Lakeside School Gym Renovation", change_order_number="21",
        date="2026-06-05", contractor="Tri-County Builders",
        owner="Lakeside School District", original_contract_sum=615000,
        previous_changes_total=N, change_amount=4300, new_contract_sum=619300,
        schedule_change_days=0, signed=False)),
    ("sample5_draft_missing", "txt", S5, dict(
        project_name="Oak Ridge Library", change_order_number=N, date=N,
        contractor=N, owner=N, original_contract_sum=N, previous_changes_total=N,
        change_amount=N, new_contract_sum=N, schedule_change_days=N, signed=N)),
]


def write_pdf(path, text):
    c = canvas.Canvas(str(path), pagesize=letter)
    y = 750
    for line in text.split("\n"):
        c.drawString(50, y, line)
        y -= 16
        if y < 50:
            c.showPage()
            y = 750
    c.save()


Path("samples/expected").mkdir(parents=True, exist_ok=True)
for stem, ext, text, expected in SAMPLES:
    path = Path("samples") / f"{stem}.{ext}"
    if ext == "pdf":
        write_pdf(path, text)
    else:
        path.write_text(text, encoding="utf-8")
    (Path("samples/expected") / f"{stem}.json").write_text(json.dumps(expected, indent=2))
    print("created", path)