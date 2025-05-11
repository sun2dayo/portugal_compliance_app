# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import json
import hashlib

class ComplianceAuditLog(Document):
	# This DocType is primarily for storing logs, no complex logic needed here
	# We might add validation later if we implement log hashing/chaining
	pass

@frappe.whitelist()
def create_compliance_log(event_type, reference_doctype, reference_name, details=""):
    """Creates a new entry in the Compliance Audit Log."""
    try:
        log_entry = frappe.new_doc("Compliance Audit Log")
        log_entry.timestamp = frappe.utils.now_datetime()
        log_entry.user = frappe.session.user
        log_entry.event_type = event_type
        log_entry.reference_doctype = reference_doctype
        log_entry.reference_name = reference_name
        log_entry.details = details
        
        # Optional: Implement log hashing later for extra integrity
        # log_entry.log_hash = calculate_log_hash(log_entry)
        
        log_entry.flags.ignore_permissions = True # Ensure log can be created by system/hooks
        log_entry.insert(ignore_permissions=True)
        # Do not commit here, let the calling transaction handle it
        # frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Failed to create compliance audit log: {e}", "Compliance Audit Log")
        # Decide if the original operation should fail if logging fails
        # frappe.throw(_("Failed to record audit log entry. Operation aborted."))

# Placeholder for potential future log hashing
# def calculate_log_hash(log_doc):
#     data_to_hash = f"{log_doc.timestamp}{log_doc.user}{log_doc.event_type}{log_doc.reference_doctype}{log_doc.reference_name}{log_doc.details}"
#     # Add previous log hash if chaining logs
#     # previous_log_hash = get_previous_log_hash()
#     # data_to_hash += previous_log_hash
#     hash_obj = hashlib.sha256(data_to_hash.encode("utf-8"))
#     return hash_obj.hexdigest()

# def get_previous_log_hash():
#     # Logic to get the hash of the most recent log entry
#     last_log = frappe.db.get_value("Compliance Audit Log", filters={}, fieldname="log_hash", order_by="timestamp desc")
#     return last_log or "0"

