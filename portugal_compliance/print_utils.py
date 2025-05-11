# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import qrcode
import base64
from io import BytesIO

@frappe.whitelist()
def get_qr_code_base64(doctype, docname):
    """Generates QR code for a document and returns its base64 representation."""
    # Permission check (optional, depends on context)
    # if not frappe.has_permission(doctype, "read", docname):
    #     frappe.throw(_("Not permitted to read document"), frappe.PermissionError)

    qr_content = frappe.db.get_value(doctype, docname, "custom_qr_code_content")

    if not qr_content:
        # Return a placeholder or empty string if no content
        frappe.log_warning(f"QR Code content not found for {doctype} {docname}", "QR Code Generation")
        return ""

    try:
        qr = qrcode.QRCode(
            version=None, # Auto-detect size
            error_correction=qrcode.constants.ERROR_CORRECT_M, # Medium error correction
            box_size=4, # Smaller box size for print formats
            border=2, # Smaller border
        )
        qr.add_data(qr_content)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Save image to buffer
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Encode as base64
        base64_encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{base64_encoded}"

    except Exception as e:
        frappe.log_error(f"Failed to generate QR Code base64 for {doctype} {docname}: {e}", "QR Code Generation")
        return "" # Return empty string on error

