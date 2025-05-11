# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import json
from .signing import sign_document
# Removed direct import of generate_atcud_and_qr, will call helper
from .doctype.compliance_audit_log.compliance_audit_log import create_compliance_log

# Mapping from ERPNext DocType to AT Document Type Code (defined in Document Series PT)
# This needs careful review and expansion based on specific ERPNext usage in Portugal
DOCTYPE_TO_AT_CODE = {
    "Sales Invoice": "FT",        # Fatura
    "Sales Invoice Return": "NC", # Nota de Cr\u00e9dito (assuming this doctype is used)
    "Delivery Note": "GT",        # Guia de Transporte (needs verification if used for this purpose)
    # Add other mappings based on how ERPNext doctypes are used:
    # "Purchase Invoice": "", # Not typically certified/signed by the receiver
    # "Receipt": "RC", # Recibo - If using Payment Entry or Journal Entry? Needs specific doctype
    # "Pro Forma Invoice": "PF", # Pro-Forma
    # "Quotation": "OR", # Or\u00e7amento
    # Add mappings for simplified invoices (FS), invoice-receipts (FR), debit notes (ND), etc.
    # if specific doctypes or configurations are used for them.
}

# --- Event Handlers --- #

def handle_before_save(doc, method):
    """Handles logic before document save (both new and updates)."""
    if doc.docstatus == 0: # Only run for drafts
        if doc.is_new():
            create_compliance_log("Create", doc.doctype, doc.name, details="Document created in draft state.")
        
        # Generate ATCUD and QR Code content (if applicable and not already done)
        _ensure_atcud_and_qr_content(doc, method)

def handle_on_submit(doc, method):
    """Handles logic on document submission."""
    # Ensure ATCUD/QR content is generated before signing
    _ensure_atcud_and_qr_content(doc, method, force_qr_rebuild=True) # Rebuild QR content with final data
    
    # Sign the document (this also updates QR code content hash)
    sign_document(doc, method)
    
    # Log the submission event
    create_compliance_log("Submit", doc.doctype, doc.name, details=f"Document submitted. Hash: {doc.custom_document_hash}")

def handle_on_cancel(doc, method):
    """Handles logic on document cancellation."""
    # Log the cancellation event
    create_compliance_log("Cancel", doc.doctype, doc.name, details="Document cancelled.")
    # Update QR code status field (E) if needed - Requires modifying QR string logic
    # Potentially update SAF-T status if applicable

def handle_validate_submitted(doc, method):
    """Handles validation attempts on already submitted documents to ensure inviolability."""
    if not doc.is_new() and doc.docstatus == 1:
        db_doc = frappe.get_doc(doc.doctype, doc.name)
        critical_fields = [
            "posting_date", "company", "customer", "grand_total", "net_total", 
            "total_taxes_and_charges", "naming_series", "currency", "plc_conversion_rate"
            # Add other fields deemed critical by AT regulations
        ]
        changed_fields = []
        for field in critical_fields:
            # Handle potential type differences (e.g., float vs Decimal)
            current_val = doc.get(field)
            db_val = db_doc.get(field)
            if type(current_val) != type(db_val):
                 # Attempt type conversion for comparison if safe (e.g., float to Decimal)
                 try:
                     if isinstance(current_val, float) and isinstance(db_val, (int, float)):
                         db_val = float(db_val)
                     elif isinstance(db_val, float) and isinstance(current_val, (int, float)):
                         current_val = float(current_val)
                     # Add other safe conversions if needed
                 except: pass # Ignore conversion errors, comparison will likely fail
            
            if current_val != db_val:
                changed_fields.append(field)

        # Basic check on items table changes (more detailed check recommended)
        if len(doc.get("items", [])) != len(db_doc.get("items", [])):
             changed_fields.append("items (count)")
        else:
            # Compare key item fields if count matches
            item_critical_fields = ["item_code", "qty", "uom", "rate", "amount", "net_rate", "net_amount", "item_tax_template"]
            for i, item in enumerate(doc.get("items", [])):
                db_item = db_doc.get("items", [])[i]
                for field in item_critical_fields:
                    if item.get(field) != db_item.get(field):
                        changed_fields.append(f"items[{i}].{field}")
                        break # Move to next item if change found
                if f"items[{i}].{field}" in changed_fields: break # Move to next check if change found

        if changed_fields:
            changed_fields_str = ", ".join(changed_fields)
            details = f"Attempt to modify submitted document. Changed fields: {changed_fields_str}"
            create_compliance_log("Update Attempt (Submitted)", doc.doctype, doc.name, details=details)
            frappe.throw(_("Submitted documents compliant with Portuguese regulations cannot be modified. Please cancel and create a new one if changes are needed."))

# --- Helper Functions --- #

import qrcode
import os
from io import BytesIO
from frappe.utils.file_manager import save_file
from portugal_compliance.saft.utils import get_atcud, get_sequential_number_from_name, format_currency, format_date

def _ensure_atcud_and_qr_content(doc, method, force_qr_rebuild=False):
    """Generates ATCUD and QR Code content if applicable and not already present or forced."""
    # Only run for relevant doctypes and if status allows (draft or forced rebuild on submit)
    if doc.doctype not in DOCTYPE_TO_AT_CODE or (doc.docstatus != 0 and not force_qr_rebuild):
        return

    doc_type_at_code = DOCTYPE_TO_AT_CODE.get(doc.doctype)
    if not doc_type_at_code or not doc.naming_series:
        return

    # Generate ATCUD if not present
    if not doc.custom_atcud or doc.custom_atcud == "ErrorGeneratingATCUD":
        sequential_number = get_sequential_number_from_name(doc.name, doc.naming_series)
        # Handle case where sequential number might not be available yet
        if sequential_number is None:
             if not doc.is_new(): # If name exists but number extraction failed
                  frappe.log_warning(f"Could not extract sequential number for ATCUD on {doc.name}", "ATCUD Generation")
             # Cannot generate ATCUD yet if number is missing
             doc.custom_atcud = "ErrorGeneratingATCUD" # Mark as error
             # Do not proceed to QR code generation without ATCUD
             return 
        else:    
            atcud = get_atcud(doc.naming_series, doc_type_at_code, doc.posting_date, sequential_number)
            if atcud:
                doc.custom_atcud = atcud
            else:
                doc.custom_atcud = "ErrorGeneratingATCUD"

    # Generate/Rebuild QR Code Content if ATCUD is valid or rebuild is forced
    if (doc.custom_atcud and doc.custom_atcud != "ErrorGeneratingATCUD") and (not doc.custom_qr_code_content or force_qr_rebuild):
        try:
            qr_content = _build_qr_code_string(doc)
            doc.custom_qr_code_content = qr_content
        except Exception as e:
             frappe.log_error(f"Error building QR code string for {doc.name}: {e}", "QR Code Generation")
             doc.custom_qr_code_content = "ErrorBuildingQRContent"

def _build_qr_code_string(doc):
    """Constructs the string content for the QR code based on AT specifications."""
    fields = []
    company_nif = frappe.db.get_value("Company", doc.company, "tax_id") or ""
    customer_nif = doc.tax_id or "999999990"
    customer_country = "PT" # Needs logic for non-PT customers based on address/country
    doc_type_at = DOCTYPE_TO_AT_CODE.get(doc.doctype, "")
    # Determine document status (E field)
    doc_status = "N" # Normal
    if doc.docstatus == 2: # Cancelled
        doc_status = "A"
    # Add logic for other statuses if needed (e.g., Self-billed 'S', Corrected 'R')
    
    doc_date = format_date(doc.posting_date) if doc.posting_date else ""
    atcud = doc.custom_atcud or ""
    fiscal_space = "PT"

    # --- VAT Breakdown (Fields I1 to I9) --- #
    vat_breakdown = {
        "ISE": {"base": 0.0, "tax": 0.0}, # I1
        "RED": {"base": 0.0, "tax": 0.0}, # I2, I3
        "INT": {"base": 0.0, "tax": 0.0}, # I4, I5
        "NOR": {"base": 0.0, "tax": 0.0}, # I6, I7
        "OUT": {"base": 0.0, "tax": 0.0}  # I8, I9 (Other rates/taxes)
    }
    total_vat_amount = 0.0

    # Iterate through taxes applied to the document
    for tax in doc.get("taxes", []):
        # Get the SAF-T tax code from the tax template
        tax_template_name = tax.charge_type + " - " + tax.account_head.split(" - ")[0] # Heuristic name
        saft_tax_code = frappe.db.get_value("Sales Taxes and Charges Template", tax_template_name, "custom_saft_tax_code")
        
        if saft_tax_code in vat_breakdown:
            vat_breakdown[saft_tax_code]["base"] += tax.tax_amount_after_discount_amount # Base amount for this tax
            vat_breakdown[saft_tax_code]["tax"] += tax.tax_amount # Tax amount itself
            total_vat_amount += tax.tax_amount
        else:
            # If tax code is not standard VAT, add to 'OUT'
            vat_breakdown["OUT"]["base"] += tax.tax_amount_after_discount_amount
            vat_breakdown["OUT"]["tax"] += tax.tax_amount
            total_vat_amount += tax.tax_amount
            
    # --- Stamp Duty (Field N) --- #
    stamp_duty = 0.0
    # TODO: Add logic to identify and sum Stamp Duty if applicable from doc.taxes

    # --- Total Impostos (Field O) --- #
    # Should be sum of all VAT and Stamp Duty
    total_impostos = total_vat_amount + stamp_duty

    # --- Valor Total (Field P) --- #
    valor_total = doc.grand_total or 0.0

    # --- Signature Hash (Field Q) --- #
    # Placeholder 'AAAA' initially, updated by sign_document on submit
    hash_chars = "AAAA"
    if doc.custom_digital_signature: # If already signed, use actual chars
         hash_chars = doc.custom_digital_signature[:4]

    # --- Software Certificate (Field R) --- #
    cert_no = frappe.get_single("Portugal Compliance Settings").software_certificate_number or "0/AT"

    # --- Assemble QR String --- #
    fields.append(f"A:{company_nif}")
    fields.append(f"B:{customer_nif}")
    fields.append(f"C:{customer_country}")
    fields.append(f"D:{doc_type_at}")
    fields.append(f"E:{doc_status}")
    fields.append(f"F:{doc_date}")
    fields.append(f"G:{atcud}")
    fields.append(f"H:{fiscal_space}")
    fields.append(f"I1:{format_currency(vat_breakdown['ISE']['base'])}") # Base Isenta
    fields.append(f"I2:{format_currency(vat_breakdown['RED']['base'])}") # Base Reduzida
    fields.append(f"I3:{format_currency(vat_breakdown['RED']['tax'])}")  # IVA Reduzida
    fields.append(f"I4:{format_currency(vat_breakdown['INT']['base'])}") # Base Interm\u00e9dia
    fields.append(f"I5:{format_currency(vat_breakdown['INT']['tax'])}")  # IVA Interm\u00e9dia
    fields.append(f"I6:{format_currency(vat_breakdown['NOR']['base'])}") # Base Normal
    fields.append(f"I7:{format_currency(vat_breakdown['NOR']['tax'])}")  # IVA Normal
    fields.append(f"I8:{format_currency(vat_breakdown['OUT']['base'])}") # Base Outras Taxas
    fields.append(f"I9:{format_currency(vat_breakdown['OUT']['tax'])}")  # IVA Outras Taxas
    fields.append(f"N:{format_currency(stamp_duty)}") # Imposto Selo
    fields.append(f"O:{format_currency(total_impostos)}") # Total Impostos
    fields.append(f"P:{format_currency(valor_total)}") # Valor Total
    fields.append(f"Q:{hash_chars}") # Hash Assinatura (4 chars)
    fields.append(f"R:{cert_no}") # No Certificado Software

    return "*".join(fields)

# Utility function needed by _build_qr_code_string
def format_currency(value):
    """Formats currency to two decimal places with dot separator."""
    if value is None: return "0.00"
    # Ensure value is float or Decimal before formatting
    try:
        float_value = float(value)
        return "{:.2f}".format(float_value)
    except (ValueError, TypeError):
        return "0.00"

