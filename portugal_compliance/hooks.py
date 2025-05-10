# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from . import __version__ as app_version
except ImportError:
    app_version = "1.0.1"

app_name = "portugal_compliance"
app_title = "Portugal Compliance"
app_publisher = "NovaDX - Octávio Daio"
app_description = "Portuguese Fiscal Compliance App (SAF-T, ATCUD, QR Code, Signature)"
app_email = "app@novadx.eu"
app_license = "GPL-3.0"
required_apps = ["erpnext"]

fixtures = [
    "Print Format",
    {
        "dt": "Workspace",
        "filters": [
            ["name", "in", ["Portugal Compliance"]]
        ]
    },
    {
        "dt": "Custom Field",
        "filters": [
            ["name", "in", [
                "Sales Invoice-custom_atcud",
                "Sales Invoice-custom_qr_code",
                "Sales Invoice-custom_digital_signature",
                "Sales Invoice-custom_previous_hash"
            ]]
        ]
    },
    {
        "dt": "Client Script",
        "filters": [
            ["dt", "=", "Document Series PT"]
        ]
    },
    {
        "dt": "DocType",
        "filters": [["name", "in", [
            "Portugal Compliance Settings",
            "Compliance Audit Log",
            "Taxonomy Code",
            "Document Series PT"
        ]]]
    },
    {
        "dt": "Portugal Compliance Settings"
    },
    {
        "dt": "Document Series PT"
    }
]


# Doc Events for compliance hooks
doc_events = {
    "Sales Invoice": {
        "before_save": "portugal_compliance.doc_events.handle_before_save",
        "on_submit": "portugal_compliance.doc_events.handle_on_submit",
        "on_cancel": "portugal_compliance.doc_events.handle_on_cancel",
        "validate": "portugal_compliance.doc_events.handle_validate_submitted"
    },
    "Delivery Note": {
        "before_save": "portugal_compliance.doc_events.handle_before_save",
        "on_submit": "portugal_compliance.doc_events.handle_on_submit",
        "on_cancel": "portugal_compliance.doc_events.handle_on_cancel",
        "validate": "portugal_compliance.doc_events.handle_validate_submitted"
    },
    "Sales Invoice Return": {
        "before_save": "portugal_compliance.doc_events.handle_before_save",
        "on_submit": "portugal_compliance.doc_events.handle_on_submit",
        "on_cancel": "portugal_compliance.doc_events.handle_on_cancel",
        "validate": "portugal_compliance.doc_events.handle_validate_submitted"
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
        "portugal_compliance.print_utils.get_qr_code_base64"
    ],
#    "filters": "portugal_compliance.utils.jinja_filters"
}

# Installation / Uninstallation = { ... }


