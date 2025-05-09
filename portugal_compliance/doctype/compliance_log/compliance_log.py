# Copyright (c) 2024, Your Company Name and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class ComplianceLog(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        details: DF.Text | None
        event_type: DF.Data | None
        log_type: DF.Literal["", "System", "AT Communication", "Signing", "SAF-T Generation", "Validation"]
        reference_doctype: DF.Link | None
        reference_document: DF.DynamicLink | None
        request_data: DF.Code | None
        response_data: DF.Code | None
        status: DF.Literal["", "Info", "Success", "Warning", "Error", "Critical"]
        summary: DF.Data
        timestamp: DF.Datetime
        user: DF.Link | None
    # end: auto-generated types
    pass

