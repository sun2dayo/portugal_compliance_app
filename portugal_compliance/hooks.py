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

# Hooks for ATCUD, QR Code generation, Signing, and Audit Logging
doctype_js = {}
doctype_list_js = {}
doctype_tree_js = {}
doctype_calendar_js = {}

fixtures = ["Print Format", "Compliance Audit Log"] # Add DocType to fixtures if needed for export

# Define hooks to trigger compliance features
doc_events = {
    "Sales Invoice": {
        "before_save": "portugal_compliance.hooks.doc_events.handle_before_save",
        "on_submit": "portugal_compliance.hooks.doc_events.handle_on_submit",
        "on_cancel": "portugal_compliance.hooks.doc_events.handle_on_cancel",
        "validate": "portugal_compliance.hooks.doc_events.handle_validate_submitted"
    },
    "Delivery Note": {
        "before_save": "portugal_compliance.hooks.doc_events.handle_before_save",
        "on_submit": "portugal_compliance.hooks.doc_events.handle_on_submit",
        "on_cancel": "portugal_compliance.hooks.doc_events.handle_on_cancel",
        "validate": "portugal_compliance.hooks.doc_events.handle_validate_submitted"
    },
    "Sales Invoice Return": { # Assuming Credit Note uses this doctype
        "before_save": "portugal_compliance.hooks.doc_events.handle_before_save",
        "on_submit": "portugal_compliance.hooks.doc_events.handle_on_submit",
        "on_cancel": "portugal_compliance.hooks.doc_events.handle_on_cancel",
        "validate": "portugal_compliance.hooks.doc_events.handle_validate_submitted"
    },
    # Add other relevant document types here
    "Document Series PT": {
        # Log successful communication (triggered from within the doctype method)
    }
}

# Hook for SAF-T Generation (triggered from the page/report script)
# We'll add logging within the generator script itself.

# scheduler_events = { ... }

# Includes in <head> = { ... }

# Home Pages = { ... }

# Generators = { ... }

# Jinja
jinja = {
    "methods": [
        "portugal_compliance.hooks.print_utils.get_qr_code_base64"
    ],
#    "filters": "portugal_compliance.utils.jinja_filters"
}

# Installation / Uninstallation = { ... }

