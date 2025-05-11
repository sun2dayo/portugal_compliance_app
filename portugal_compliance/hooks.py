# -*- coding: utf-8 -*-
app_name = "portugal_compliance"
app_title = "Portugal Compliance"
app_publisher = "Manus Team & User"
app_description = "Compliance with Portuguese fiscal regulations for ERPNext."
app_email = "user@example.com" # Placeholder, user should update
app_license = "MIT"

# Includes in <head> (CSS) 
# ---------------------------

# app_include_css = "/assets/portugal_compliance/css/portugal_compliance.css"
# app_include_js = "/assets/portugal_compliance/js/portugal_compliance.js"

# Fixtures
# ---------
fixtures = [
    "Client Script",
    "Custom Field",
    "Workspace",
    # For DocType data, use this format if you have specific records to export from these DocTypes
    # Ensure that the corresponding JSON files (e.g., document_series_pt.json) exist in the fixtures folder
    {"doctype": "Serie de Documento Fiscal", "filters": []}, # Exports all records if filters are empty
    {"doctype": "Portugal Compliance Settings", "filters": []} # Exports all records if filters are empty
    # If you only want to export the DocType structure itself (fields, permissions), 
    # that is usually handled by Frappe automatically or via specific export commands, not typically via fixtures for the structure.
    # "Property Setter" # Add if property_setter.json exists and is needed
]

# DocType Class
# ---------------_-
# override_doctype_class = {
# "ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------_-
# Hook on document methods and events

doc_events = {
    "Sales Invoice": {
        "on_submit": "portugal_compliance.utils.fiscal_signature.sign_document_and_generate_qr",
        "validate": [
            "portugal_compliance.utils.fiscal_validations.validate_sales_invoice_fields",
            "portugal_compliance.utils.fiscal_validations.prevent_modification_of_certified_fields"
        ],
        "on_cancel": "portugal_compliance.utils.fiscal_cancellation.prevent_direct_cancellation_of_fiscal_document"
    },
    "Journal Entry": { # Assuming Journal Entry is used for Credit Notes that can cancel Sales Invoices
        "on_submit": "portugal_compliance.utils.fiscal_cancellation.process_fiscal_cancellation_via_rectifying_document",
    },
    "Customer": {
        "validate": "portugal_compliance.utils.fiscal_validations.validate_customer_nif"
    },
    "Supplier": {
        "validate": "portugal_compliance.utils.fiscal_validations.validate_supplier_nif"
    }
}

# Scheduled Tasks
# ---------------_-

# scheduler_events = {
# "all": [
# "portugal_compliance.tasks.all"
# ],
# "daily": [
# "portugal_compliance.tasks.daily"
# ],
# "hourly": [
# "portugal_compliance.tasks.hourly"
# ],
# "weekly": [
# "portugal_compliance.tasks.weekly"
# ],
# "monthly": [
# "portugal_compliance.tasks.monthly"
# ]
# }

# Testing
# -------_-

# before_tests = "portugal_compliance.install.before_tests"

# Overriding Methods
# ---------------------
# 
# override_whitelisted_methods = {
# "frappe.desk.doctype.event.event.get_events": "portugal_compliance.event.get_events"
# }
# 
# override_doctype_dashboards = {
# "Task": "portugal_compliance.task.get_dashboard_data"
# }

# exempt Escalation Routes from Unauthorized exception
# -----------------------------------------------------
# exempt_exception_from_auth = [
# "portugal_compliance.custom_exceptions.CustomException"
# ]

# Home Pages
# -----------

# home_page = "login"

# Generators
# -----------

# Jinja Filters
# -------------
# jinja = {
# "methods": "portugal_compliance.utils.jinja_methods",
# "filters": "portugal_compliance.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "portugal_compliance.install.before_install"
# after_install = "portugal_compliance.install.after_install"

# Desk Notifications (beta)
# ---------------------------
# desk_notification_handlers = [
# "portugal_compliance.utils.notifications.handler"
# ]

# App Includes
# -------------

# required_apps = []

# DocType List
# -------------
doctype_list = [
    "Serie de Documento Fiscal",
    "Certificado Digital Qualificado",
    "Portugal Compliance Settings"
]

# Page List
# ---------
page_list = [
    "saft_pt_generator"
]

# Report List
# -----------
# report_list = [
# {
# "doctype": "Sales Invoice",
# "name": "PT Sales Invoice Report",
# "is_standard": "No"
# }
# ]

# Module Def
# -----------

modules = [
    {
        "module_name": "Portugal Compliance",
        "label": "Portugal Compliance",
        "category": "Compliance", 
        "type": "module",
        "description": "Funcionalidades para conformidade fiscal em Portugal.",
        "color": "#FFD700", 
        "icon": "octicon octicon-law", 
        "app": "portugal_compliance",
        "link": "list/DocType?module=Portugal Compliance"
    }
]

# Workflow List
# -------------

# workflow_list = [
# "PT Sales Invoice Workflow"
# ]

# User Data Protection
# ---------------------

# user_data_fields = [
# {
# "doctype": "User",
# "filter_by": "email",
# "redact_fields": [" Alguns campos sensíveis "],
# "label": "User Personal Data"
# }
# ]

# Portal Pages
# -------------

# portal_pages = [
# "pt-compliance-portal"
# ]

