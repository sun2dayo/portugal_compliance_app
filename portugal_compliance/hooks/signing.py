# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import hashlib
import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from portugal_compliance.saft.utils import format_date, get_sequential_number_from_name # Removed format_currency

# Placeholder for the initial hash value for the first document in a series
# As per Despacho 8632/2014, point 4.1.1, this should be "0"
INITIAL_HASH = "0"

def sign_document(doc, method):
    """Hook triggered on_submit. Calculates hash, retrieves previous hash, signs the document data, stores results, and finalizes QR code content."""
    # Ensure document is submitted and not already signed
    if doc.docstatus != 1 or doc.custom_digital_signature:
        return

    if not doc.naming_series or not doc.name:
        frappe.log_error("Missing naming series or name for signing", doc.doctype)
        frappe.throw(_("Cannot sign document without Naming Series or Name."))
        return

    # 1. Get Previous Hash
    previous_hash = get_previous_document_hash(doc)
    doc.custom_previous_hash = previous_hash

    # 2. Construct Data String for Hashing/Signing
    # Format based on Despacho n.\u00ba 8632/2014, point 4.1:
    # DataDeEmissao;DataHoraDeEmissao;IdentificadorUnicoDoc;ValorTotal;HashAnterior
    # Using posting_date for DataDeEmissao and creation for DataHoraDeEmissao
    # Using grand_total formatted to two decimal places with '.' separator for ValorTotal
    try:
        emission_date = format_date(doc.posting_date)
        # Use creation timestamp as emission timestamp
        emission_datetime_obj = doc.creation
        emission_datetime = emission_datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")
        doc_identifier = doc.name
        total_value = "{:.2f}".format(doc.grand_total or 0.0) # Ensure 2 decimal places, use 0.0 if None

        data_string = f"{emission_date};{emission_datetime};{doc_identifier};{total_value}"
        data_bytes = data_string.encode("utf-8")

    except Exception as e:
        frappe.log_error(f"Error constructing data string for signing {doc.name}: {e}", "Digital Signature")
        frappe.throw(_("Error preparing data for digital signature."))

    # 3. Calculate Current Document Hash (for next document)
    # Using SHA-256 as per modern standards. Verify if SHA-1 is required by specific AT version.
    try:
        current_hash_obj = hashlib.sha256()
        current_hash_obj.update(data_bytes) # Hash the core data string (without previous hash)
        current_hash = base64.b64encode(current_hash_obj.digest()).decode("utf-8")
        doc.custom_document_hash = current_hash
    except Exception as e:
        frappe.log_error(f"Error calculating document hash for {doc.name}: {e}", "Digital Signature")
        frappe.throw(_("Error calculating document hash."))

    # 4. Construct Data String for Signing (includes previous hash)
    signing_string = f"{data_string};{previous_hash}"
    signing_bytes = signing_string.encode("utf-8")

    # 5. Load Private Key
    settings = frappe.get_single("Portugal Compliance Settings")
    key_path = settings.private_key_path
    key_password = settings.get_password("private_key_password")

    if not key_path or not os.path.exists(key_path):
        frappe.throw(_("Private key path not configured or file not found in Portugal Compliance Settings."))

    try:
        with open(key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=key_password.encode("utf-8") if key_password else None,
                backend=default_backend()
            )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Private Key Load Error")
        frappe.throw(_("Failed to load private key: {0}").format(str(e)))

    # 6. Sign the Data
    try:
        # Using RSA with SHA-256 and PKCS1v15 padding.
        # Verify exact algorithm (SHA1/SHA256) and padding required by AT.
        signature = private_key.sign(
            signing_bytes,
            padding.PKCS1v15(),
            hashes.SHA256() # Or hashes.SHA1() if required
        )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Document Signing Error")
        frappe.throw(_("Failed to sign document: {0}").format(str(e)))

    # 7. Encode Signature and Store
    signature_b64 = base64.b64encode(signature).decode("utf-8")
    doc.custom_digital_signature = signature_b64

    # 8. Update QR Code Content with Signature Hash (First 4 Chars)
    # WARNING: The exact source for the 'Q' field (first 4 chars) needs confirmation from official AT technical specs.
    # This implementation assumes it's the first 4 chars of the Base64 encoded signature itself.
    if doc.custom_qr_code_content:
        sig_hash_chars = signature_b64[:4]
        qr_parts = doc.custom_qr_code_content.split("*")
        updated_qr_parts = []
        q_field_updated = False
        for part in qr_parts:
            if part.startswith("Q:"):
                updated_qr_parts.append(f"Q:{sig_hash_chars}")
                q_field_updated = True
            else:
                updated_qr_parts.append(part)
        if q_field_updated:
            doc.custom_qr_code_content = "*".join(updated_qr_parts)
        else:
            frappe.log_warning(f"Q field placeholder not found in QR code content for {doc.name}", "Digital Signature")

    # Save the updated fields (hash, previous hash, signature, potentially QR content)
    # Use db_set to avoid triggering save hooks again
    frappe.db.set_value(doc.doctype, doc.name, {
        "custom_previous_hash": doc.custom_previous_hash,
        "custom_document_hash": doc.custom_document_hash,
        "custom_digital_signature": doc.custom_digital_signature,
        "custom_qr_code_content": doc.custom_qr_code_content
    })

def get_previous_document_hash(doc):
    """Finds the hash of the previous submitted document in the same series and type."""
    sequential_number = get_sequential_number_from_name(doc.name, doc.naming_series)
    if sequential_number is None or sequential_number <= 1:
        # First document in the series (or error getting number)
        return INITIAL_HASH

    # Find the previous document by looking for the highest submitted document
    # with the same series and a name numerically smaller than the current one.
    # This is more robust than reconstructing the name.
    previous_doc = frappe.db.sql("""
        SELECT name, custom_document_hash
        FROM `tab{doctype}`
        WHERE naming_series = %s
          AND name < %s
          AND docstatus = 1
        ORDER BY name DESC
        LIMIT 1
    """.format(doctype=doc.doctype), (doc.naming_series, doc.name), as_dict=True)

    if not previous_doc:
        # Could be the first submitted document even if number > 1 (e.g., drafts existed)
        # Or if previous docs were cancelled (docstatus=2)
        # Check if ANY previous submitted doc exists in the series
        any_previous = frappe.db.exists(doc.doctype, {
            "naming_series": doc.naming_series,
            "name": ("<", doc.name),
            "docstatus": 1
        })
        if not any_previous:
             # Truly the first submitted document in the series
             return INITIAL_HASH
        else:
             # Gap in sequence or previous was cancelled. This might be an issue for AT.
             # Log warning, but proceed cautiously. Returning INITIAL_HASH might break chain.
             # Strict compliance might require preventing submission or using last valid hash.
             frappe.log_warning(f"Could not find immediately preceding submitted document for {doc.name}. Chain might be broken.", "Hash Chaining")
             # For now, return INITIAL_HASH, but this needs review based on AT rules for gaps.
             return INITIAL_HASH

    previous_hash = previous_doc[0].custom_document_hash

    if not previous_hash:
        # Previous doc exists but has no hash? Should not happen for submitted docs.
        frappe.log_error(f"Hash not found for previous document {previous_doc[0].name}", "Hash Chaining")
        frappe.throw(_("Hash not found for the previous document ({0}). Cannot continue signing.").format(previous_doc[0].name))

    return previous_hash

