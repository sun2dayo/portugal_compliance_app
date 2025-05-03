# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from portugal_compliance import __version__ as app_version
except ImportError:
    app_version = "0.0.1"

app_name = "portugal_compliance"
app_title = "portugal_compliance"
app_publisher = "Manus AI Agent"
app_description = "Portuguese Fiscal Compliance App"
app_email = "noreply@example.com"
app_license = "mit"

doctype_js = {}
doctype_list_js = {}
doctype_tree_js = {}
doctype_calendar_js = {}

fixtures = ["Print Format", "Compliance Audit Log"]

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
    "Sales Invoice Return": {
        "before_save": "portugal_compliance.hooks.doc_events.handle_before_save",
        "on_submit": "portugal_compliance.hooks.doc_events.handle_on_submit",
        "on_cancel": "portugal_compliance.hooks.doc_events.handle_on_cancel",
        "validate": "portugal_compliance.hooks.doc_events.handle_validate_submitted"
    },
    "Document Series PT": {}
}

jinja = {
    "methods": [
        "portugal_compliance.hooks.print_utils.get_qr_code_base64"
    ]
}

