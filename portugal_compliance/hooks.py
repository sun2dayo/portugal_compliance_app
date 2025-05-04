# -*- coding: utf-8 -*-
from __future__ import unicode_literals
# Ensure __init__ is loaded correctly
try:
    from . import __version__ as app_version
except ImportError:
    app_version = "0.0.1" # Fallback

app_name = "portugal_compliance"
app_title = "Portugal Compliance" # Simple ASCII title
app_publisher = "Manus AI Agent"
app_description = "Portuguese Fiscal Compliance App (SAF-T, ATCUD, QR Code, Signature)" # Simplified description
app_email = "noreply@example.com"
app_license = "mit"

# Minimal hooks for base testing

doctype_js = {}
doctype_list_js = {}
doctype_tree_js = {}
doctype_calendar_js = {}

# Temporarily comment out fixtures, doc_events, jinja for isolation
# fixtures = ["Print Format", "Compliance Audit Log"]

# doc_events = {
#     "Sales Invoice": {
#         "before_save": "portugal_compliance.hooks.doc_events.handle_before_save",
#         "on_submit": "portugal_compliance.hooks.doc_events.handle_on_submit",
#         "on_cancel": "portugal_compliance.hooks.doc_events.handle_on_cancel",
#         "validate": "portugal_compliance.hooks.doc_events.handle_validate_submitted"
#     },
#     "Delivery Note": {
#         "before_save": "portugal_compliance.hooks.doc_events.handle_before_save",
#         "on_submit": "portugal_compliance.hooks.doc_events.handle_on_submit",
#         "on_cancel": "portugal_compliance.hooks.doc_events.handle_on_cancel",
#         "validate": "portugal_compliance.hooks.doc_events.handle_validate_submitted"
#     },
#     "Sales Invoice Return": { # Assuming Credit Note uses this doctype
#         "before_save": "portugal_compliance.hooks.doc_events.handle_before_save",
#         "on_submit": "portugal_compliance.hooks.doc_events.handle_on_submit",
#         "on_cancel": "portugal_compliance.hooks.doc_events.handle_on_cancel",
#         "validate": "portugal_compliance.hooks.doc_events.handle_validate_submitted"
#     },
#     # Add other relevant document types here
#     "Document Series PT": {
#         # Log successful communication (triggered from within the doctype method)
#     }
# }

# jinja = {
#     "methods": [
#         "portugal_compliance.hooks.print_utils.get_qr_code_base64"
#     ],
# #    "filters": "portugal_compliance.utils.jinja_filters"
# }

# Other hooks remain commented or default
# scheduler_events = { ... }
# Includes in <head> = { ... }
# Home Pages = { ... }
# Generators = { ... }
# Installation / Uninstallation = { ... }

