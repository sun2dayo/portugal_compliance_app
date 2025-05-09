# Copyright (c) 2024, Your Company Name and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class DocumentSeriesPT(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        at_communication_status: DF.Literal["Not Communicated", "Pending Communication", "Communicated Successfully", "Communication Failed"]
        atcud_code: DF.Data | None
        current_number: DF.Int
        document_type: DF.Literal["", "Sales Invoice", "Credit Note", "Simplified Invoice", "Receipt", "Transport Document"]
        is_active: DF.Check
        last_at_response: DF.SmallText | None
        prefix: DF.Data | None
        series_id: DF.Data
    # end: auto-generated types
    pass

