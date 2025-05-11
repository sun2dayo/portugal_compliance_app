# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from lxml import etree
from .utils import format_date, format_datetime, format_currency, get_fiscal_year_data # Assuming utils.py exists and is correct
from ..doctype.compliance_audit_log.compliance_audit_log import create_compliance_log # Assuming this doctype exists

# SAF-T Namespace map
NSMAP = {
    None: "urn:OECD:StandardAuditFile-Tax:PT_1.04_01",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance"
}

class SaftGenerator:
    def __init__(self, fiscal_year, company):
        self.fiscal_year_name = fiscal_year # Assuming fiscal_year is the name, e.g., "2023"
        self.company = company
        
        # Get fiscal year start and end dates using the correct utility function
        fy_data = get_fiscal_year_data(self.fiscal_year_name)
        if not fy_data or not fy_data.get("year_start_date") or not fy_data.get("year_end_date"):
            frappe.throw(_(f"Could not retrieve start and end dates for fiscal year: {self.fiscal_year_name}"))
        self.start_date = fy_data["year_start_date"]
        self.end_date = fy_data["year_end_date"]
        self.actual_fiscal_year_for_saft = fy_data.get("year") # The numeric year for SAF-T header

        self.settings = frappe.get_single("Portugal Compliance Settings")
        self.root = etree.Element("AuditFile", nsmap=NSMAP)
        self.root.set("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", 
                      "urn:OECD:StandardAuditFile-Tax:PT_1.04_01 saftpt1.04_01.xsd")

    def generate_file_content(self):
        """Builds all SAF-T XML sections and returns the full XML string"""
        self._build_header()
        self._build_master_files()
        self._build_general_ledger_entries()
        self._build_source_documents()
        
        xml_string = etree.tostring(self.root, pretty_print=True, xml_declaration=True, encoding='utf-8') # Corrected encoding argument
        create_compliance_log("SAF-T Generated", "Company", self.company, 
                              details=f"SAF-T (PT) XML content generated for Fiscal Year {self.fiscal_year_name}")
        return xml_string

    def _add_element(self, parent, tag, text=None):
        """Helper to create and add an element, handling None text."""
        element = etree.SubElement(parent, tag)
        if text is not None:
            element.text = str(text)
        return element

    def _build_header(self):
        header = self._add_element(self.root, "Header")
        company_doc = frappe.get_doc("Company", self.company)
        
        self._add_element(header, "AuditFileVersion", "1.04_01")
        self._add_element(header, "CompanyID", company_doc.tax_id or frappe.throw(_("Company Tax ID not set")))
        self._add_element(header, "TaxRegistrationNumber", company_doc.tax_id)
        self._add_element(header, "TaxAccountingBasis", self.settings.get("tax_accounting_basis", "I"))
        self._add_element(header, "CompanyName", company_doc.company_name or frappe.throw(_("Company Name not set")))
        self._add_element(header, "BusinessName", company_doc.company_name)
        
        address_node = self._add_element(header, "CompanyAddress")
        # Assuming primary_address_doc is fetched correctly as before
        # For brevity, direct assignment is shown here. In practice, fetch as before.
        primary_address_doc = frappe.get_value("Address", {
            "is_primary_address": 1,
            "links.link_doctype": "Company",
            "links.link_name": self.company
        }, ["address_line1", "address_line2", "city", "pincode", "state", "country"], as_dict=True)

        if primary_address_doc:
            self._add_element(address_node, "AddressDetail", f"{primary_address_doc.get('address_line1', '')} {primary_address_doc.get('address_line2', '')}".strip() or "Unknown")
            self._add_element(address_node, "City", primary_address_doc.get('city', '') or "Unknown")
            self._add_element(address_node, "PostalCode", primary_address_doc.get('pincode', '') or "0000-000")
            self._add_element(address_node, "Region", primary_address_doc.get('state', '') or "Unknown") # Assuming state is region
            self._add_element(address_node, "Country", "PT")
        else:
            # Fallback if address not found (should ideally not happen in production)
            self._add_element(address_node, "AddressDetail", "Unknown")
            self._add_element(address_node, "City", "Unknown")
            self._add_element(address_node, "PostalCode", "0000-000")
            self._add_element(address_node, "Region", "Unknown")
            self._add_element(address_node, "Country", "PT")

        self._add_element(header, "FiscalYear", str(self.actual_fiscal_year_for_saft))
        self._add_element(header, "StartDate", format_date(self.start_date))
        self._add_element(header, "EndDate", format_date(self.end_date))
        self._add_element(header, "CurrencyCode", company_doc.default_currency or "EUR")
        self._add_element(header, "DateCreated", format_date(frappe.utils.today()))
        self._add_element(header, "TaxEntity", self.settings.tax_entity or "Sede")
        self._add_element(header, "ProductCompanyTaxID", self.settings.software_provider_nif or frappe.throw(_("Software Provider NIF not set in settings")))
        self._add_element(header, "SoftwareCertificateNumber", self.settings.software_certificate_number or "0/AT")
        self._add_element(header, "ProductID", self.settings.product_id or "ERPNextPortugalCompliance")
        self._add_element(header, "ProductVersion", self.settings.product_version or "1.0")
        if company_doc.phone: self._add_element(header, "Telephone", company_doc.phone)
        # Fax, Email, Website can be added similarly if available and required

    def _build_master_files(self):
        master_files = self._add_element(self.root, "MasterFiles")
        self._build_general_ledger_accounts(master_files)
        self._build_customers(master_files)
        self._build_suppliers(master_files)
        self._build_products(master_files)
        self._build_tax_table(master_files)

    def _build_general_ledger_accounts(self, master_files):
        accounts_node = self._add_element(master_files, "GeneralLedgerAccounts")
        # Placeholder for actual data retrieval
        # Example: self._add_element(accounts_node, "Account") 
        # ... add AccountID, AccountDescription etc. ...
        pass

    def _build_customers(self, master_files):
        customers_data = frappe.get_all("Customer", filters={"disabled": 0, "company": self.company}, 
                                      fields=["name", "customer_name", "tax_id"])
        if not customers_data: return

        for cust_data in customers_data:
            customer_node = self._add_element(master_files, "Customer")
            self._add_element(customer_node, "CustomerID", cust_data.name)
            self._add_element(customer_node, "AccountID", frappe.get_cached_value("Company", self.company, "default_receivable_account") or "NA")
            self._add_element(customer_node, "CustomerTaxID", cust_data.tax_id or "999999990")
            self._add_element(customer_node, "CompanyName", cust_data.customer_name or cust_data.name)
            
            billing_address_node = self._add_element(customer_node, "BillingAddress")
            # Simplified address handling for brevity in this example
            # In a real scenario, fetch address details as done in _build_header
            addr = frappe.get_value("Address", {"links.link_doctype": "Customer", "links.link_name": cust_data.name, "is_billing_address":1}, 
                                      ["address_line1", "city", "pincode", "state"], as_dict=True)
            if addr:
                self._add_element(billing_address_node, "AddressDetail", addr.address_line1 or "Unknown")
                self._add_element(billing_address_node, "City", addr.city or "Unknown")
                self._add_element(billing_address_node, "PostalCode", addr.pincode or "0000-000")
                self._add_element(billing_address_node, "Region", addr.state or "Unknown")
            else:
                self._add_element(billing_address_node, "AddressDetail", "Not Specified")
                self._add_element(billing_address_node, "City", "Not Specified")
                self._add_element(billing_address_node, "PostalCode", "Not Specified")
                self._add_element(billing_address_node, "Region", "Not Specified")
            self._add_element(billing_address_node, "Country", "PT")
            self._add_element(customer_node, "SelfBillingIndicator", "0")

    def _build_suppliers(self, master_files):
        # Placeholder for actual data retrieval
        pass

    def _build_products(self, master_files):
        products_data = frappe.get_all("Item", filters={"disabled": 0, "has_variants": 0}, 
                                     fields=["name", "item_name", "item_group", "custom_pt_product_type", "custom_product_commodity_code"])
        if not products_data: return

        for item_data in products_data:
            product_node = self._add_element(master_files, "Product")
            self._add_element(product_node, "ProductType", item_data.custom_pt_product_type or "P")
            self._add_element(product_node, "ProductCode", item_data.name)
            self._add_element(product_node, "ProductDescription", item_data.item_name or item_data.name)
            self._add_element(product_node, "ProductNumberCode", item_data.custom_product_commodity_code or item_data.name)
            if item_data.item_group: self._add_element(product_node, "ProductGroup", item_data.item_group)

    def _build_tax_table(self, master_files):
        tax_table_node = self._add_element(master_files, "TaxTable")
        # Placeholder for actual data retrieval
        # Example: Add a default VAT entry
        tax_entry = self._add_element(tax_table_node, "TaxTableEntry")
        self._add_element(tax_entry, "TaxType", "IVA")
        self._add_element(tax_entry, "TaxCountryRegion", "PT")
        self._add_element(tax_entry, "TaxCode", "NOR") # Normal Rate
        self._add_element(tax_entry, "Description", "Taxa Normal de IVA")
        self._add_element(tax_entry, "TaxPercentage", "23.00")
        pass

    def _build_source_documents(self):
        source_docs = self._add_element(self.root, "SourceDocuments")
        self._build_sales_invoices(source_docs)
        # Placeholders for other document types if needed
        # self._build_movement_of_goods(source_docs)
        # self._build_working_documents(source_docs)
        # self._build_payments(source_docs)

    def _build_sales_invoices(self, source_docs):
        invoices_data = frappe.get_all("Sales Invoice", 
            filters={"company": self.company, "docstatus": 1, 
                     "posting_date": ["between", [self.start_date, self.end_date]]},
            fields=["name", "posting_date", "customer", "custom_atcud", 
                    "custom_document_hash", "custom_qr_code_content",
                    "net_total", "grand_total", "total_taxes_and_charges", "currency", 
                    "creation", "modified", "modified_by", "owner", "custom_pt_invoice_type" 
                    ])

        if not invoices_data: return

        sales_invoices_node = self._add_element(source_docs, "SalesInvoices")
        self._add_element(sales_invoices_node, "NumberOfEntries", str(len(invoices_data)))
        
        total_credit = sum(inv.grand_total for inv in invoices_data if inv.grand_total and inv.grand_total > 0)
        self._add_element(sales_invoices_node, "TotalCredit", format_currency(total_credit))
        self._add_element(sales_invoices_node, "TotalDebit", "0.00")

        for inv_header in invoices_data:
            inv_doc = frappe.get_doc("Sales Invoice", inv_header.name) # Fetch full doc for items
            invoice_node = self._add_element(sales_invoices_node, "Invoice")
            self._add_element(invoice_node, "InvoiceNo", inv_doc.name)
            if inv_doc.custom_atcud: self._add_element(invoice_node, "ATCUD", inv_doc.custom_atcud)
            
            doc_status_node = self._add_element(invoice_node, "DocumentStatus")
            invoice_status_val = "N"
            if inv_doc.status == "Cancelled": invoice_status_val = "A"
            self._add_element(doc_status_node, "InvoiceStatus", invoice_status_val)
            self._add_element(doc_status_node, "InvoiceStatusDate", format_datetime(inv_doc.modified))
            self._add_element(doc_status_node, "SourceID", inv_doc.modified_by or inv_doc.owner)
            self._add_element(doc_status_node, "SourceBilling", "P")

            self._add_element(invoice_node, "Hash", inv_doc.custom_document_hash or "0") 
            self._add_element(invoice_node, "HashControl", "1") 
            if inv_doc.posting_date: self._add_element(invoice_node, "Period", str(inv_doc.posting_date.month))
            self._add_element(invoice_node, "InvoiceDate", format_date(inv_doc.posting_date))
            self._add_element(invoice_node, "InvoiceType", inv_doc.custom_pt_invoice_type or "FT")
            
            special_regimes_node = self._add_element(invoice_node, "SpecialRegimes")
            self._add_element(special_regimes_node, "SelfBillingIndicator", "0")
            self._add_element(special_regimes_node, "CashVATSchemeIndicator", "0")
            self._add_element(special_regimes_node, "ThirdPartiesBillingIndicator", "0")

            self._add_element(invoice_node, "SourceID", inv_doc.owner)
            self._add_element(invoice_node, "SystemEntryDate", format_datetime(inv_doc.creation))
            self._add_element(invoice_node, "CustomerID", inv_doc.customer)
            
            for item in inv_doc.items:
                line_node = self._add_element(invoice_node, "Line")
                self._add_element(line_node, "LineNumber", str(item.idx))
                self._add_element(line_node, "ProductCode", item.item_code)
                self._add_element(line_node, "ProductDescription", item.description or item.item_name)
                self._add_element(line_node, "Quantity", format_currency(item.qty, no_symbol=True))
                self._add_element(line_node, "UnitOfMeasure", item.uom or "UN")
                self._add_element(line_node, "UnitPrice", format_currency(item.rate, no_symbol=True))
                self._add_element(line_node, "TaxPointDate", format_date(inv_doc.posting_date))
                self._add_element(line_node, "Description", item.description or item.item_name)
                self._add_element(line_node, "CreditAmount", format_currency(item.net_amount, no_symbol=True) if item.net_amount else "0.00")
                
                tax_node = self._add_element(line_node, "Tax")
                # This needs to be dynamic based on actual taxes applied to the line item.
                # For now, using placeholder values as before.
                self._add_element(tax_node, "TaxType", "IVA") 
                self._add_element(tax_node, "TaxCountryRegion", "PT") 
                self._add_element(tax_node, "TaxCode", "NOR") 
                self._add_element(tax_node, "TaxPercentage", "23.00")

            doc_totals_node = self._add_element(invoice_node, "DocumentTotals")
            self._add_element(doc_totals_node, "TaxPayable", format_currency(inv_doc.total_taxes_and_charges))
            self._add_element(doc_totals_node, "NetTotal", format_currency(inv_doc.net_total))
            self._add_element(doc_totals_node, "GrossTotal", format_currency(inv_doc.grand_total))

    def _build_movement_of_goods(self, source_docs):
        # Placeholder for actual implementation
        pass

    def _build_working_documents(self, source_docs):
        # Placeholder for actual implementation
        pass

    def _build_payments(self, source_docs):
        # Placeholder for actual implementation
        pass

    def _build_general_ledger_entries(self):
        # Placeholder for actual implementation
        pass

# Example usage (for testing, would be called from a UI or background job)
# if __name__ == "__main__":
#     # This is for local testing only, not part of Frappe app execution
#     # Mock frappe and other dependencies if running standalone
#     frappe.get_single = lambda doctype: frappe.settings if doctype == "Portugal Compliance Settings" else None
#     frappe.get_doc = lambda doctype, name: frappe.company_data.get(name) if doctype == "Company" else None # Simplified mock
#     frappe.get_all = lambda doctype, filters, fields, order_by, limit_page_length: [] # Simplified mock

#     generator = SaftGenerator(fiscal_year="2023", company="Test Company")
#     xml_content = generator.generate_file_content()
#     # print(xml_content.decode("utf-8")) # Print XML to console for verification
#     with open("saft_output.xml", "wb") as f:
#         f.write(xml_content)
#     print("SAF-T XML generated as saft_output.xml")

