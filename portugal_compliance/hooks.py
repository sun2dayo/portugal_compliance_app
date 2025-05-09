# hooks.py for Portugal Compliance App

app_name = "portugal_compliance_app"
app_title = "Portugal Compliance"
app_publisher = "Your Company Name"
app_description = "Compliance with Portuguese fiscal regulations (ATCUD, SAFT-PT, Digital Signatures)."
app_email = "your.email@example.com"
app_license = "MIT"
app_logo_url = "/assets/portugal_compliance_app/images/logo.png"  # Placeholder

# Frappe/ERPNext version compatibility (adjust as needed)
# frappe_compatibility = "^15.0.0"
# erpnext_compatibility = "^15.0.0"

required_apps = ["erpnext"] # Assuming ERPNext is a dependency

# Document Events
# Example: Trigger actions on Sales Invoice submission or cancellation
doc_events = {
    # "Sales Invoice": {
    #     "on_submit": "portugal_compliance_app.portugal_compliance.modules.signing.sign_document_on_submit",
    #     "before_save": "portugal_compliance_app.portugal_compliance.modules.at_communication.validate_atcud_on_save",
    #     "on_cancel": "portugal_compliance_app.portugal_compliance.modules.at_communication.handle_cancelled_document_series",
    # },
    # "Company": {
    #     "on_update": "portugal_compliance_app.portugal_compliance.doctype.portugal_compliance_settings.update_settings_on_company_change"
    # }
}

# Fixtures: Data to be loaded on app installation/update
# List of fixtures to be exported/imported.
# Fixtures are JSON files that represent data records.
fixtures = [
    "custom_field",         # Loads from portugal_compliance/fixtures/custom_field.json
    "property_setter",      # Loads from portugal_compliance/fixtures/property_setter.json
    # The following are examples of other ways to define fixtures or specific DocTypes to export
    # {"dt": "Custom Field", "filters": [["module", "=", "Portugal Compliance"]]}, # Example for custom fields with filters
    # {"dt": "Property Setter", "filters": [["module", "=", "Portugal Compliance"]]}, # Example for property setters with filters
    # "Portugal Chart of Accounts", # Example for a custom fixture for a DocType (e.g. if you have a DocType named this)
    # "Taxonomy Code",              # Example for a custom fixture for a DocType
    # "Document Series PT"          # Example for a custom fixture for a DocType
]

# Client-side scripts
# doctype_js = {
#     "Sales Invoice": "public/js/sales_invoice_pt.js",
#     "Purchase Invoice": "public/js/purchase_invoice_pt.js"
# }
# doctype_list_js = {
#     "Sales Invoice": "public/js/sales_invoice_list_pt.js"
# }

# Scheduled Tasks
# scheduler_events = {
#     "cron": {
#         "*/15 * * * *": [
#             "portugal_compliance_app.portugal_compliance.tasks.sync_document_series_with_at"
#         ]
#     },
#     "daily": [
#         "portugal_compliance_app.portugal_compliance.tasks.daily_compliance_check"
#     ]
# }

# Override Doctype Class
# override_doctype_class = {
#     "Sales Invoice": "portugal_compliance_app.overrides.extended_sales_invoice.ExtendedSalesInvoice"
# }

# Desk Notifications
# on_session_creation = "portugal_compliance_app.utils.setup_compliance_notifications"

# App includes (for JS and CSS)
# app_include_js = "/assets/portugal_compliance_app/js/main.js"
# app_include_css = "/assets/portugal_compliance_app/css/main.css"

# Workspace / Desktop Page
# workspace_name = "Portugal Compliance"
# workspace_link = "portugal_compliance_app.portugal_compliance.config.desktop.get_data"

# User Permissions
# on_session_creation = [
#     "portugal_compliance_app.permissions.setup_user_permissions"
# ]

# Patches
# patch_handlers = {
#     "portugal_compliance_app.patches.v1_0.fix_data_migration": "execute_patch"
# }

# Standard Hooks for custom reports, pages, etc.
# report_override_path = "portugal_compliance_app.reports"
# page_override_path = "portugal_compliance_app.pages"

# If you have commands that should be available in `bench`
# commands = [
#     "portugal_compliance_app.commands.setup_at_credentials"
# ]

# Translation
# get_translated_dict = {
#     "pt": "portugal_compliance_app.translations.pt"
# }

# Add to apps screen
add_to_apps_screen = 1

