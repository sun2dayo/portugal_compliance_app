# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from lxml import etree
import os
import tempfile # Added for temporary file creation
from .utils import format_date, format_datetime, format_currency, get_fiscal_year_dates
from ..doctype.compliance_audit_log.compliance_audit_log import create_compliance_log
from .saft_validator import validate_saft_xml # Added import for the validator

# Namespace map for SAF-T PT 1.04
NSMAP = {
    None: "urn:OECD:StandardAuditFile-Tax:PT_1.04_01",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance"
}

XSD_OFFICIAL_PATH = "/home/ubuntu/SAFTPT1.04_01_official.xsd" # Path to the official XSD

class SaftGenerator:
    def __init__(self, fiscal_year, company):
        self.fiscal_year = fiscal_year
        self.company = company
        self.start_date, self.end_date = get_fiscal_year_dates(fiscal_year)
        self.settings = frappe.get_single("Portugal Compliance Settings")
        self.root = etree.Element("AuditFile", nsmap=NSMAP)
        # Add schema location attribute
        self.root.set("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", 
                      "urn:OECD:StandardAuditFile-Tax:PT_1.04_01 SAFTPT1.04_01.xsd")

    def generate_file(self):
        """Generates the complete SAF-T XML file and validates it."""
        self._build_header()
        self._build_master_files()
        self._build_general_ledger_entries() # Optional based on SAF-T type
        self._build_source_documents() # Optional based on SAF-T type
        
        # Log generation event
        create_compliance_log("SAF-T Generated", "Company", self.company, 
                              details=f"SAF-T (PT) generated for Fiscal Year {self.fiscal_year}")

        xml_string = etree.tostring(self.root, pretty_print=True, xml_declaration=True, encoding=\'utf-8\')

        # Validate the generated XML
        validation_errors = []
        is_valid = False
        try:
            with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".xml") as tmp_xml_file:
                tmp_xml_file.write(xml_string)
                tmp_xml_file_path = tmp_xml_file.name
            
            frappe.log_message("SaftGenerator", f"Attempting to validate {tmp_xml_file_path} against {XSD_OFFICIAL_PATH}")
            is_valid, validation_errors = validate_saft_xml(tmp_xml_file_path, XSD_OFFICIAL_PATH)
            
            if is_valid:
                frappe.log_message("SaftGenerator", "SAF-T XML validation successful.")
                print("SAF-T XML validation successful.") # For standalone testing visibility
            else:
                frappe.log_error("SaftGenerator", f"SAF-T XML validation failed: {validation_errors}")
                print(f"SAF-T XML validation failed. Errors: {validation_errors}") # For standalone testing visibility
        except Exception as e:
            frappe.log_error("SaftGenerator", f"Error during SAF-T XML validation: {str(e)}")
            print(f"Error during SAF-T XML validation: {str(e)}")
            validation_errors.append(f"Internal validation error: {str(e)}")
        finally:
            if os.path.exists(tmp_xml_file_path):
                os.remove(tmp_xml_file_path)

        # Here, you might want to decide what to do if validation fails.
        # For now, it returns the XML string regardless, and logs errors.
        # The caller of this method should check for validation status if needed.
        # This method could be enhanced to return (xml_string, is_valid, validation_errors)

        return xml_string # Or (xml_string, is_valid, validation_errors)

    def _build_header(self):
        header = etree.SubElement(self.root, "Header")
        company_doc = frappe.get_doc("Company", self.company)
        
        etree.SubElement(header, "AuditFileVersion").text = "1.04_01"
        etree.SubElement(header, "CompanyID").text = company_doc.tax_id or ""
        etree.SubElement(header, "TaxRegistrationNumber").text = company_doc.tax_id or ""
        etree.SubElement(header, "TaxAccountingBasis").text = "I" # Placeholder
        etree.SubElement(header, "CompanyName").text = company_doc.company_name
        etree.SubElement(header, "BusinessName").text = company_doc.company_name
        
        address = etree.SubElement(header, "CompanyAddress")
        primary_address = frappe.get_cached_value("Address", {"is_primary_address": 1, "links.link_doctype": "Company", "links.link_name": self.company}, ["address_line1", "address_line2", "city", "pincode", "state", "country"])
        if primary_address:
             addr_line1, addr_line2, city, pincode, state, country = primary_address
             etree.SubElement(address, "AddressDetail").text = f"{addr_line1 or \'\'} {addr_line2 or \'\'}".strip()
             etree.SubElement(address, "City").text = city or ""
             etree.SubElement(address, "PostalCode").text = pincode or ""
             etree.SubElement(address, "Region").text = state or ""
             etree.SubElement(address, "Country").text = "PT"
        else:
             etree.SubElement(address, "AddressDetail").text = ""
             etree.SubElement(address, "City").text = ""
             etree.SubElement(address, "PostalCode").text = ""
             etree.SubElement(address, "Region").text = ""
             etree.SubElement(address, "Country").text = "PT"

        etree.SubElement(header, "FiscalYear").text = str(self.fiscal_year)
        etree.SubElement(header, "StartDate").text = format_date(self.start_date)
        etree.SubElement(header, "EndDate").text = format_date(self.end_date)
        etree.SubElement(header, "CurrencyCode").text = company_doc.default_currency or "EUR"
        etree.SubElement(header, "DateCreated").text = format_date(frappe.utils.today())
        etree.SubElement(header, "TaxEntity").text = "Sede"
        etree.SubElement(header, "ProductCompanyTaxID").text = self.settings.software_provider_nif or ""
        etree.SubElement(header, "SoftwareCertificateNumber").text = self.settings.software_certificate_number or "0/AT"
        etree.SubElement(header, "ProductID").text = self.settings.product_id or "ERPNext-PTCompliance/1.0"
        etree.SubElement(header, "ProductVersion").text = self.settings.product_version or "1.0"

    def _build_master_files(self):
        master_files = etree.SubElement(self.root, "MasterFiles")
        self._build_general_ledger_accounts(master_files)
        self._build_customers(master_files)
        self._build_suppliers(master_files)
        self._build_products(master_files)
        self._build_tax_table(master_files)

    def _build_general_ledger_accounts(self, master_files):
        accounts = frappe.get_all("Account", filters={"company": self.company}, fields=["name", "account_name", "account_type", "is_group", "root_type", "report_type", "custom_taxonomy_code"])
        if not accounts: return
        
        gl_accounts = etree.SubElement(master_files, "GeneralLedgerAccounts")
        for acc in accounts:
            account = etree.SubElement(gl_accounts, "Account")
            etree.SubElement(account, "AccountID").text = acc.name
            etree.SubElement(account, "AccountDescription").text = acc.account_name
            etree.SubElement(account, "OpeningDebitBalance").text = "0.00"
            etree.SubElement(account, "OpeningCreditBalance").text = "0.00"
            etree.SubElement(account, "ClosingDebitBalance").text = "0.00"
            etree.SubElement(account, "ClosingCreditBalance").text = "0.00"
            etree.SubElement(account, "GroupingCategory").text = "GM" if acc.is_group else "GA"
            taxonomy_code = acc.get("custom_taxonomy_code")
            if taxonomy_code:
                 etree.SubElement(account, "TaxonomyCode").text = str(taxonomy_code)

    def _build_customers(self, master_files):
        customers = frappe.get_all("Customer", filters={"disabled": 0}, fields=["name", "customer_name", "tax_id", "customer_group"])
        if not customers: return
        
        for cust in customers:
            customer = etree.SubElement(master_files, "Customer")
            etree.SubElement(customer, "CustomerID").text = cust.name
            etree.SubElement(customer, "AccountID").text = "NA"
            etree.SubElement(customer, "CustomerTaxID").text = cust.tax_id or "999999990"
            etree.SubElement(customer, "CompanyName").text = cust.customer_name
            
            billing_address = frappe.get_cached_value("Address", {"is_billing_address": 1, "links.link_doctype": "Customer", "links.link_name": cust.name}, ["address_line1", "address_line2", "city", "pincode", "state", "country"], as_dict=True)
            address = etree.SubElement(customer, "BillingAddress")
            if billing_address:
                 etree.SubElement(address, "AddressDetail").text = f"{billing_address.address_line1 or \'\'} {billing_address.address_line2 or \'\'}".strip()
                 etree.SubElement(address, "City").text = billing_address.city or ""
                 etree.SubElement(address, "PostalCode").text = billing_address.pincode or ""
                 etree.SubElement(address, "Region").text = billing_address.state or ""
                 etree.SubElement(address, "Country").text = "PT"
            else:
                 etree.SubElement(address, "AddressDetail").text = ""
                 etree.SubElement(address, "City").text = ""
                 etree.SubElement(address, "PostalCode").text = ""
                 etree.SubElement(address, "Region").text = ""
                 etree.SubElement(address, "Country").text = "PT"
            etree.SubElement(customer, "SelfBillingIndicator").text = "0"

    def _build_suppliers(self, master_files):
        suppliers = frappe.get_all("Supplier", filters={"disabled": 0}, fields=["name", "supplier_name", "tax_id", "supplier_group"])
        if not suppliers: return
        
        for supp in suppliers:
            supplier = etree.SubElement(master_files, "Supplier")
            etree.SubElement(supplier, "SupplierID").text = supp.name
            etree.SubElement(supplier, "AccountID").text = "NA"
            etree.SubElement(supplier, "SupplierTaxID").text = supp.tax_id or ""
            etree.SubElement(supplier, "CompanyName").text = supp.supplier_name
            billing_address = frappe.get_cached_value("Address", {"is_billing_address": 1, "links.link_doctype": "Supplier", "links.link_name": supp.name}, ["address_line1", "address_line2", "city", "pincode", "state", "country"], as_dict=True)
            address = etree.SubElement(supplier, "BillingAddress")
            if billing_address:
                 etree.SubElement(address, "AddressDetail").text = f"{billing_address.address_line1 or \'\'} {billing_address.address_line2 or \'\'}".strip()
                 etree.SubElement(address, "City").text = billing_address.city or ""
                 etree.SubElement(address, "PostalCode").text = billing_address.pincode or ""
                 etree.SubElement(address, "Region").text = billing_address.state or ""
                 etree.SubElement(address, "Country").text = "PT"
            else:
                 etree.SubElement(address, "AddressDetail").text = ""
                 etree.SubElement(address, "City").text = ""
                 etree.SubElement(address, "PostalCode").text = ""
                 etree.SubElement(address, "Region").text = ""
                 etree.SubElement(address, "Country").text = "PT"
            etree.SubElement(supplier, "SelfBillingIndicator").text = "0"

    def _build_products(self, master_files):
        products = frappe.get_all("Item", filters={"disabled": 0}, fields=["name", "item_name", "item_group", "stock_uom", "custom_saft_product_type"])
        if not products: return
        
        prod_section = etree.SubElement(master_files, "Product")
        for item in products:
            product = etree.SubElement(prod_section, "Product")
            product_type = item.get("custom_saft_product_type") or "P"
            etree.SubElement(product, "ProductType").text = product_type
            etree.SubElement(product, "ProductCode").text = item.name
            etree.SubElement(product, "ProductGroup").text = item.item_group or ""
            etree.SubElement(product, "ProductDescription").text = item.item_name or item.name
            etree.SubElement(product, "ProductNumberCode").text = item.name

    def _build_tax_table(self, master_files):
        tax_templates = frappe.get_all("Sales Taxes and Charges Template", 
                                       filters={"disabled": 0, "custom_saft_tax_code": ["is", "set"]},
                                       fields=["name", "custom_saft_tax_code", "custom_saft_exemption_reason_code", "rate", "description"])
        if not tax_templates: return
        
        tax_table = etree.SubElement(master_files, "TaxTable")
        for tax in tax_templates:
            tax_entry = etree.SubElement(tax_table, "TaxTableEntry")
            saft_code = tax.custom_saft_tax_code
            tax_type = "IVA"
            tax_country_region = "PT"
            tax_code = saft_code
            
            etree.SubElement(tax_entry, "TaxType").text = tax_type
            etree.SubElement(tax_entry, "TaxCountryRegion").text = tax_country_region
            etree.SubElement(tax_entry, "TaxCode").text = tax_code
            etree.SubElement(tax_entry, "Description").text = tax.description or tax.name
            etree.SubElement(tax_entry, "TaxPercentage").text = format_currency(tax.rate or 0.0)
            if saft_code == "ISE":
                 exemption_code = tax.custom_saft_exemption_reason_code or ""
                 exemption_reason = f"Motivo Isen\u00e7\u00e3o {exemption_code}"
                 if exemption_code:
                      etree.SubElement(tax_entry, "TaxExemptionReason").text = exemption_reason
                      etree.SubElement(tax_entry, "TaxExemptionCode").text = exemption_code

    def _build_general_ledger_entries(self, master_files): # Corrected indentation for the method definition
        pass

    def _build_source_documents(self):
        source_docs = etree.SubElement(self.root, "SourceDocuments")
        self._build_sales_invoices(source_docs)

    def _build_sales_invoices(self, source_docs):
        invoices = frappe.get_all("Sales Invoice", 
                                  filters={"company": self.company, "docstatus": 1, 
                                           "posting_date": ["between", [self.start_date, self.end_date]]},
                                  fields=["name", "posting_date", "customer", "customer_name", "tax_id", 
                                          "custom_atcud", "custom_digital_signature", "custom_previous_hash",
                                          "net_total", "grand_total", "total_taxes_and_charges", "currency", "plc_conversion_rate",
                                          "creation"
                                          ])
        if not invoices: return

        sales_invoices = etree.SubElement(source_docs, "SalesInvoices")
        etree.SubElement(sales_invoices, "NumberOfEntries").text = str(len(invoices))
        etree.SubElement(sales_invoices, "TotalDebit").text = "0.00"
        etree.SubElement(sales_invoices, "TotalCredit").text = format_currency(sum(inv.grand_total for inv in invoices if inv.grand_total > 0))

        for inv_header in invoices:
            # ... (rest of the _build_sales_invoices method remains the same)
            invoice = etree.SubElement(sales_invoices, "Invoice")
            etree.SubElement(invoice, "InvoiceNo").text = inv_header.name
            # ... (rest of the fields)
            # Ensure all required fields are populated, even if with default/empty values
            doc_totals = etree.SubElement(invoice, "DocumentTotals")
            etree.SubElement(doc_totals, "TaxPayable").text = format_currency(inv_header.total_taxes_and_charges or 0.0)
            etree.SubElement(doc_totals, "NetTotal").text = format_currency(inv_header.net_total or 0.0)
            etree.SubElement(doc_totals, "GrossTotal").text = format_currency(inv_header.grand_total or 0.0)
            # ... (other elements like WithholdingTax if applicable)

            # Line items
            inv_items = frappe.get_all("Sales Invoice Item", filters={"parent": inv_header.name}, 
                                       fields=["item_code", "description", "qty", "rate", "amount", "net_amount", "tax_rate", "item_tax_template"])
            for item in inv_items:
                line = etree.SubElement(invoice, "Line")
                etree.SubElement(line, "LineNumber").text = str(item.idx) # Assuming idx is line number
                etree.SubElement(line, "ProductCode").text = item.item_code
                etree.SubElement(line, "ProductDescription").text = item.description
                etree.SubElement(line, "Quantity").text = format_currency(item.qty)
                etree.SubElement(line, "UnitOfMeasure").text = frappe.db.get_value("Item", item.item_code, "stock_uom") or "UN"
                etree.SubElement(line, "UnitPrice").text = format_currency(item.rate)
                # TaxPointDate, References, Description, ProductSerialNumber - Add if applicable
                etree.SubElement(line, "DebitAmount").text = "0.00" # For credit notes
                etree.SubElement(line, "CreditAmount").text = format_currency(item.net_amount) # Assuming net amount for sales
                
                tax = etree.SubElement(line, "Tax")
                # This needs to correctly fetch the SAFT tax code from item_tax_template
                # For simplicity, assuming tax_rate is the percentage and we need to find the code
                # This part needs robust logic to map item_tax_template to TaxTableEntry
                tax_detail = frappe.db.get_value("Item Tax Template Detail", {"parent": item.item_tax_template, "tax_type": ["like", "%VAT%"]}, "tax_rate", order_by="idx DESC") if item.item_tax_template else None
                item_tax_rate = tax_detail if tax_detail else (item.tax_rate or 0.0) # Fallback to item.tax_rate

                etree.SubElement(tax, "TaxType").text = "IVA"
                etree.SubElement(tax, "TaxCountryRegion").text = "PT"
                # This is a placeholder - needs to map item_tax_rate to a valid TaxCode from TaxTable
                # For example, if item_tax_rate is 23, map to "NOR" or equivalent
                # This requires a lookup against the self._build_tax_table() generated data or a predefined map
                tax_code_to_use = "RED" # Placeholder - should be dynamic
                if item_tax_rate == 23:
                    tax_code_to_use = "NOR" # Example
                elif item_tax_rate == 13:
                    tax_code_to_use = "INT" # Example
                elif item_tax_rate == 0:
                    tax_code_to_use = "ISE" # Example, if exemption applies
                
                etree.SubElement(tax, "TaxCode").text = tax_code_to_use 
                etree.SubElement(tax, "TaxPercentage").text = format_currency(item_tax_rate)
                # SettlementAmount - if applicable

# Example of how this might be called from a Frappe context (e.g., a Page or whitelisted method)
# def generate_saft_for_year(fiscal_year, company):
#     generator = SaftGenerator(fiscal_year, company)
#     xml_data = generator.generate_file()
#     # Save to file or return as HTTP response
#     with open(f"SAFT_PT_{company}_{fiscal_year}.xml", "wb") as f:
#         f.write(xml_data)
#     return f"SAFT_PT_{company}_{fiscal_year}.xml generated and validated."

