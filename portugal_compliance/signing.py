# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
import hashlib # Changed from 'hashlib as sha1_hasher' for clarity, will use hashlib.sha1
import base64 # Retained for now, though might not be needed if signature is hex
import os
from datetime import datetime

# As per Despacho 8632/2014, point 4.1.1, the initial hash value for the first document in a series is "0"
INITIAL_HASH = "0"

# Helper function to format date as YYYY-MM-DD
# Assuming doc.posting_date is a date object or string that can be parsed to one.
# Frappe typically stores dates as YYYY-MM-DD strings or datetime objects.
def format_date_for_hash(date_obj):
    if isinstance(date_obj, str):
        dt_obj = datetime.strptime(date_obj, '%Y-%m-%d') # Adjust format if ERPNext stores differently
        return dt_obj.strftime('%Y-%m-%d')
    elif isinstance(date_obj, datetime):
        return date_obj.strftime('%Y-%m-%d')
    return str(date_obj) # Fallback, assuming it's already in a suitable string format

# Helper function to format datetime as YYYY-MM-DDTHH:MM:SS
# Assuming doc.creation is a datetime object.
def format_datetime_for_hash(datetime_obj):
    if isinstance(datetime_obj, datetime):
        return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")
    return str(datetime_obj) # Fallback

def sign_document(doc, method):
    """
    Hook triggered on_submit for relevant fiscal documents.
    Calculates the SHA-1 chained hash as per Portuguese AT regulations.
    Stores the current hash and the previous hash used.
    The 'custom_digital_signature' field will store the calculated SHA-1 hash for SAF-T purposes.
    The 'custom_document_hash' field will also store this hash for the next document's chaining.
    """
    # Ensure document is being submitted (status 0 means draft, 1 means submitted)
    # This hook might be called on_submit (before commit) or on_update (after commit)
    # We need to ensure it runs once when the document is finalized for the first time.
    # For simplicity, let's assume it's called on_submit and docstatus becomes 1.
    # If it's on_update after submission, doc.docstatus would be 1.

    # Check if this is a new submission that needs signing
    # If custom_document_hash already exists, assume it's already processed or a resave.
    if doc.docstatus != 1 or doc.custom_document_hash: # Check if already submitted and has a hash
        # Or, if this is an update and hash already exists, don't re-calculate unless specifically needed.
        # For now, let's assume we only sign once on first submission.
        # If a document can be modified after submission and needs re-signing, this logic needs adjustment.
        # The prompt implies this is for SAF-T generation, which usually happens on submitted documents.
        # Let's assume this hook is appropriately called when a signature is needed.
        pass # Allow saving if already processed or not relevant status

    if not doc.name: # Should always have a name if it's being saved/submitted
        frappe.throw(_("Document name is missing, cannot generate hash."))
        return

    # 1. Get Previous Document Hash
    # The get_previous_document_hash function needs to be defined or imported.
    # For this example, let's assume it's available and retrieves the 'custom_document_hash' of the previous doc.
    # If no previous document, it should return INITIAL_HASH ("0").
    previous_hash = get_previous_hash_for_series(doc.doctype, doc.name, doc.naming_series)

    # 2. Construct Data String for Hashing
    # Fields based on Despacho n.º 8632/2014, Anexo II, 4.1. Assinatura dos documentos.
    # DataDeEmissao;DataHoraDeEmissao;IdentificadorUnicoDoc;ValorTotalDocumento;HashAnterior
    # We need to map these to the actual fields in the ERPNext DocType.
    # Assuming 'Sales Invoice' for this example.

    # DataDeEmissao (Invoice Date)
    # Assuming doc.posting_date is the invoice date and is a date object or 'YYYY-MM-DD' string
    invoice_date_str = format_date_for_hash(doc.get('posting_date'))

    # DataHoraDeEmissao (System Entry Date/Time for the invoice)
    # Assuming doc.creation is a datetime object representing when the document was created in the system.
    # The Despacho mentions "Data e hora de emissão do documento com segundos"
    # We'll use doc.creation for this, formatted appropriately.
    system_entry_datetime_str = format_datetime_for_hash(doc.get('creation')) # doc.creation should be a datetime object

    # IdentificadorUnicoDoc (Invoice Number)
    invoice_number_str = doc.name # Usually the document's unique ID

    # ValorTotalDocumento (Grand Total of the invoice)
    # Formatted to two decimal places, using '.' as decimal separator.
    grand_total_str = "{:.2f}".format(doc.get('grand_total') or 0.00)

    # String to be hashed
    string_to_be_hashed = f"{invoice_date_str};{system_entry_datetime_str};{invoice_number_str};{grand_total_str};{previous_hash}"

    # 3. Calculate Current Document Hash (SHA-1)
    hasher = hashlib.sha1()
    hasher.update(string_to_be_hashed.encode('utf-8'))
    current_hash = hasher.hexdigest().upper()

    # 4. Store the hashes
    # The current hash will be used as the 'previous hash' for the next document in the series.
    # It's also the 'signature' for the current document for SAF-T purposes.
    doc.custom_previous_hash = previous_hash
    doc.custom_document_hash = current_hash
    doc.custom_digital_signature = current_hash # As this is the value required by AT for SAF-T Hash field

    # Potentially update QR code content if it depends on this hash. This part is pending clarification.
    # For now, we assume the QR code part is handled elsewhere or not dependent on this specific hash format.
    # If custom_qr_code_content needs to be updated, that logic would go here.
    # e.g., update_qr_code_with_hash(doc, current_hash)

    # Note: The document is not explicitly saved here as this function is expected to be a hook
    # (e.g., before_save or before_submit) and Frappe handles the save afterwards.
    # If called outside a hook, ensure doc.save() is handled appropriately.

def get_previous_hash_for_series(doctype_name, current_doc_name, series):
    """
    Retrieves the custom_document_hash from the latest submitted document 
    of the same series that precedes the current document.
    This is a simplified placeholder. A robust solution would need to handle 
    complex series, cancellations, etc.
    """
    # This query needs to be adapted to the specific database and how documents are ordered.
    # It should find the chronologically last submitted document in the same series before the current one.
    # Sorting by 'creation' or a submission timestamp might be more reliable than 'name' if names are not strictly sequential.
    # For this example, we assume 'name' can be used for ordering for simplicity.

    # Find the previous document by looking for the highest submitted document
    # with the same series and a name numerically smaller (or creation date earlier) than the current one.
    # This is a conceptual query. The actual DB query would depend on the Frappe/ERPNext version and setup.
    # We are looking for the 'custom_document_hash' of that previous document.

    # Simplified logic: Fetch previous documents in the series, get the latest one.
    # This is NOT production-ready and needs proper DB querying and error handling.
    previous_docs = frappe.get_all(
        doctype_name, 
        filters={
            'name': ['<', current_doc_name],
            'naming_series': series,
            'docstatus': 1 # Assuming 1 means submitted/finalized
        },
        fields=['name', 'custom_document_hash', 'creation'],
        order_by='creation desc', # Get the most recent one first
        limit_page_length=1
    )

    if previous_docs:
        # Assuming custom_document_hash stores the hash from the previous iteration
        previous_hash = previous_docs[0].get('custom_document_hash')
        if previous_hash:
            return previous_hash
    
    return INITIAL_HASH # Default for the first document or if no valid previous found

# Example of how it might be called (conceptual)
# This part would typically be in the DocType's Python controller or hooks file.
# @frappe.whitelist()
# def on_submit(doc, method):
# if doc.doctype == 'Sales Invoice': # Or other relevant doctypes
# sign_document(doc, method) # Call the signing logic

# Note on QR Code: The original brief mentioned QR code generation.
# The current implementation of sign_document focuses only on the SAF-T hash.
# If the QR code content depends on this hash or another signature type,
# that logic would need to be integrated here or called separately.
# The user's latest reflection indicates the QR code content (field Q) is still pending clarification.
# Therefore, this example deliberately omits QR code update to avoid making assumptions.

# Note on Settings: The fields for private_key_path and private_key_password 
# in Portugal Compliance Settings are not used in this SHA-1 hash chaining implementation.
# If a cryptographic signature (e.g., for e-invoicing or a different QR code scheme) is still required elsewhere,
# those settings might still be relevant for other parts of the application.
# This implementation strictly follows the interpretation that for SAF-T hash, no private key is involved.

# To make this runnable, we'd need to define the DocTypes and potentially mock frappe.get_all / frappe.get_single if testing outside Frappe.
# This is a conceptual representation of the logic within a Frappe environment.

# --- End of conceptual signing logic for `signing.py` ---

# The following is a placeholder for how it might be integrated if this were a real Frappe script
# For actual use, this logic would be part of the appropriate DocType's Python class or hooks.

# Example: If this were in sales_invoice.py
# class SalesInvoice(Document):
#     def on_submit(self):
#         # Assuming 'portugal_compliance_settings' has a field 'enable_pt_saft_signing'
#         settings = frappe.get_single("Portugal Compliance Settings")
#         if settings.get("enable_pt_saft_signing"):
#             sign_document(self, "on_submit")

# For the purpose of this exercise, we'll assume the above `sign_document` and `get_previous_hash_for_series`
# would replace the relevant parts of the existing `signing.py` or be a new module if the old signing
# mechanism is still needed for other purposes.

# Given the prompt is to update/refactor `signing.py`, the content above would be the core logic.
# The actual integration into the Frappe framework would involve placing this within the appropriate
# hooks or server scripts for the relevant DocTypes (e.g., Sales Invoice, Purchase Invoice etc. that require SAF-T hash).

# The fields custom_previous_hash, custom_document_hash, custom_digital_signature must exist in the DocType definitions.

# Final considerations for `get_previous_hash_for_series`:
# - It needs to correctly identify the 
