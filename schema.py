from typing import List, Optional
from pydantic import BaseModel

TEXT_FIELDS = ["project_name", "change_order_number", "date",
               "contractor", "owner", "description_of_change"]
MONEY_FIELDS = ["original_contract_sum", "previous_changes_total",
                "change_amount", "new_contract_sum"]
OTHER_FIELDS = ["schedule_change_days", "signed"]
FIELDS = TEXT_FIELDS + MONEY_FIELDS + OTHER_FIELDS

FIELD_HELP = {
    "project_name": "name of the project/job",
    "change_order_number": "the change order number exactly as written (e.g. 'CO-012', '003')",
    "date": "date of the change order, copied EXACTLY as written",
    "contractor": "contractor / general contractor / GC company name",
    "owner": "owner / client company name",
    "description_of_change": "one or two sentence summary of the change, copied from the text",
    "original_contract_sum": "original contract sum/amount BEFORE any change orders, copied as written including $ and ( )",
    "previous_changes_total": "net total of PREVIOUS/prior approved change orders, copied as written",
    "change_amount": "amount of THIS change order only. Credits/deductions must keep their sign or parentheses, copied as written",
    "new_contract_sum": "new/revised/adjusted contract sum AFTER this change order, copied as written",
    "schedule_change_days": "integer number of days added to schedule (negative if schedule is reduced, 0 if no impact)",
    "signed": "true if the document shows it was signed/approved, false if explicitly unsigned/blank, null if unclear",
}


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None


class ChangeOrder(BaseModel):
    project_name: Optional[str] = None
    change_order_number: Optional[str] = None
    date: Optional[str] = None
    contractor: Optional[str] = None
    owner: Optional[str] = None
    description_of_change: Optional[str] = None
    original_contract_sum: Optional[float] = None
    previous_changes_total: Optional[float] = None
    change_amount: Optional[float] = None
    new_contract_sum: Optional[float] = None
    schedule_change_days: Optional[int] = None
    signed: Optional[bool] = None
    line_items: List[LineItem] = []