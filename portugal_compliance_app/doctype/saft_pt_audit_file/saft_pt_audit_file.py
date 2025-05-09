# Copyright (c) 2024, Your Company Name and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class SAFTPTAuditFile(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        company: DF.Link | None
        end_date: DF.Date | None
        error_message: DF.SmallText | None
        file_attachment: DF.Attach | None
        file_name: DF.Data | None
        fiscal_year: DF.Link | None
        generation_date: DF.Datetime | None
        start_date: DF.Date | None
        status: DF.Literal["Pending", "Generated", "Generation Failed", "Validated", "Validation Failed"]
        user: DF.Link | None
        version: DF.Data | None
    # end: auto-generated types
    pass

