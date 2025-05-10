import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def execute():
	# Define custom fields to be added
	custom_fields = [
		# Account
		{
			"doctype": "Account",
			"fieldname": "custom_taxonomy_code",
			"label": "Taxonomy Code (SAF-T PT)",
			"fieldtype": "Link",
			"options": "Taxonomy Code",
			"insert_after": "account_type",
			"description": "SNC Taxonomy Code for SAF-T reporting."
		},
		# Item
		{
			"doctype": "Item",
			"fieldname": "custom_saft_product_type",
			"label": "Product Type (SAF-T PT)",
			"fieldtype": "Select",
			"options": "\nP\nS\nO\nI\nE", # P-Product, S-Service, O-Other, I-Investments, E-Expenses
			"insert_after": "item_group",
			"default": "P",
			"description": "Product type according to SAF-T PT specification."
		},
		# Sales Taxes and Charges Template
		{
			"doctype": "Sales Taxes and Charges Template",
			"fieldname": "custom_saft_tax_code",
			"label": "Tax Code (SAF-T PT)",
			"fieldtype": "Select",
			"options": "\nNOR\nISE\nRED\nINT\nOUT", # NOR-Normal, ISE-Exempt, RED-Reduced, INT-Intermediate, OUT-Other
			"insert_after": "account_head",
			"default": "NOR",
			"description": "VAT Tax Code according to SAF-T PT specification."
		},
		{
			"doctype": "Sales Taxes and Charges Template",
			"fieldname": "custom_saft_exemption_reason",
			"label": "Exemption Reason (SAF-T PT)",
			"fieldtype": "Data",
			"insert_after": "custom_saft_tax_code",
			"description": "Reason for VAT exemption (e.g., M01-M99). Required if Tax Code is ISE."
		},
	]

	# Add fields for documents requiring ATCUD, QR Code, Hashing, Signature
	documents_to_patch = ["Sales Invoice", "Delivery Note"] # Add other relevant doctypes like 'Credit Note' if needed
	for doc in documents_to_patch:
		custom_fields.extend([
			{
				"doctype": doc,
				"fieldname": "custom_atcud",
				"label": "ATCUD",
				"fieldtype": "Data",
				"insert_after": "naming_series",
				"read_only": 1,
				"print_hide": 0,
				"no_copy": 1,
				"allow_on_submit": 1,
				"description": "Unique Document Code (ATCUD) assigned by Tax Authority."
			},
			{
				"doctype": doc,
				"fieldname": "custom_qr_code_content",
				"label": "QR Code Content",
				"fieldtype": "Small Text",
				"insert_after": "custom_atcud",
				"read_only": 1,
				"print_hide": 1,
				"no_copy": 1,
				"allow_on_submit": 1,
				"description": "Raw content used to generate the QR Code."
			},
			{
				"doctype": doc,
				"fieldname": "custom_previous_hash",
				"label": "Previous Document Hash",
				"fieldtype": "Small Text",
				"insert_after": "custom_qr_code_content",
				"read_only": 1,
				"print_hide": 1,
				"no_copy": 1,
				"allow_on_submit": 1,
				"description": "Hash of the previously submitted document in the same series."
			},
			{
				"doctype": doc,
				"fieldname": "custom_document_hash",
				"label": "Document Hash",
				"fieldtype": "Small Text",
				"insert_after": "custom_previous_hash",
				"read_only": 1,
				"print_hide": 1,
				"no_copy": 1,
				"allow_on_submit": 1,
				"description": "Hash of this document's key fields."
			},
			{
				"doctype": doc,
				"fieldname": "custom_digital_signature",
				"label": "Digital Signature",
				"fieldtype": "Text",
				"insert_after": "custom_document_hash",
				"read_only": 1,
				"print_hide": 1,
				"no_copy": 1,
				"allow_on_submit": 1,
				"description": "Digital signature of the document."
			}
		])

	# Create the custom fields
	for field_def in custom_fields:
		doctype = field_def["doctype"]
		fieldname = field_def["fieldname"]
		if not frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fieldname}):
			try:
				create_custom_field(doctype, field_def)
				frappe.db.commit() # Commit after each field creation
				frappe.log_error(f"Created custom field {fieldname} on {doctype}", "Portugal Compliance Patch")
			except Exception as e:
				frappe.log_error(f"Failed to create custom field {fieldname} on {doctype}: {e}", "Portugal Compliance Patch")
		else:
			frappe.log_error(f"Custom field {fieldname} on {doctype} already exists.", "Portugal Compliance Patch")

	frappe.clear_cache(doctype=doctype)

