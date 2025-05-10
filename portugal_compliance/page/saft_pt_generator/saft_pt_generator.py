# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_fiscal_years():
    """Returns a list of fiscal years for the SAF-T generator filter."""
    # Check permissions
    if not frappe.has_permission("Account", "export"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    return frappe.db.get_all(
        "Fiscal Year",
        fields=["name", "year_start_date", "year_end_date"],
        order_by="year_start_date desc"
    )

