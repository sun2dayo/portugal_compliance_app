# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from lxml import etree
import os
from .utils import format_date, format_datetime, format_currency, get_fiscal_year_dates
from ..doctype.compliance_audit_log.compliance_audit_log import create_compliance_log

# Namespace map for SAF-T PT 1.04
NSMAP = {
    None: "urn:OECD:StandardAuditFile-Tax:PT_1.04_01",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance"
}

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
        """Generates the complete SAF-T XML file."""
        self._build_header()
        self._build_master_files()
        self._build_general_ledger_entries() # Optional based on SAF-T type
        self._build_source_documents() # Optional based on SAF-T type
        
        # Log generation event
        create_compliance_log("SAF-T Generated", "Company", self.company, 
                              details=f"SAF-T (PT) generated for Fiscal Year {self.fiscal_year}")

        # Return XML string
        return etree.tostring(self.root, pretty_print=True, xml_declaration=True, encoding=\'utf-8\')

    def _build_header(self):
        header = etree.SubElement(self.root, "Header")
        company_doc = frappe.get_doc("Company", self.company)
        
        etree.SubElement(header, "AuditFileVersion").text = "1.04_01"
        etree.SubElement(header, "CompanyID").text = company_doc.tax_id or "" # Assuming NIF is Tax ID
        etree.SubElement(header, "TaxRegistrationNumber").text = company_doc.tax_id or ""
        # Determine TaxAccountingBasis based on app/settings (e.g., "I" for integrated)
        # This might need refinement based on actual deployment context
        etree.SubElement(header, "TaxAccountingBasis").text = "I" # Placeholder
        etree.SubElement(header, "CompanyName").text = company_doc.company_name
        etree.SubElement(header, "BusinessName").text = company_doc.company_name # Or a specific field if exists
        
        address = etree.SubElement(header, "CompanyAddress")
        # Assuming primary address is used
        primary_address = frappe.get_cached_value("Address", {"is_primary_address": 1, "links.link_doctype": "Company", "links.link_name": self.company}, ["address_line1", "address_line2", "city", "pincode", "state", "country"])
        if primary_address:
             addr_line1, addr_line2, city, pincode, state, country = primary_address
             etree.SubElement(address, "AddressDetail").text = f"{addr_line1 or \'\'} {addr_line2 or \'\'}".strip()
             etree.SubElement(address, "City").text = city or ""
             etree.SubElement(address, "PostalCode").text = pincode or ""
             etree.SubElement(address, "Region").text = state or ""
             etree.SubElement(address, "Country").text = "PT" # Hardcoded for SAF-T PT
        else:
             # Add empty elements if no primary address found
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
        etree.SubElement(header, "TaxEntity").text = "Sede" # Assuming global/HQ generation
        etree.SubElement(header, "ProductCompanyTaxID").text = self.settings.software_provider_nif or ""
        etree.SubElement(header, "SoftwareCertificateNumber").text = self.settings.software_certificate_number or "0/AT"
        etree.SubElement(header, "ProductID").text = self.settings.product_id or "ERPNext-PTCompliance/1.0"
        etree.SubElement(header, "ProductVersion").text = self.settings.product_version or "1.0"
        # HeaderComment, Telephone, Fax, Email, Website - Add if available

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
            etree.SubElement(account, "OpeningDebitBalance").text = "0.00" # TODO: Get opening balances
            etree.SubElement(account, "OpeningCreditBalance").text = "0.00" # TODO: Get opening balances
            etree.SubElement(account, "ClosingDebitBalance").text = "0.00" # TODO: Get closing balances
            etree.SubElement(account, "ClosingCreditBalance").text = "0.00" # TODO: Get closing balances
            etree.SubElement(account, "GroupingCategory").text = "GM" if acc.is_group else "GA" # GM=Group, GA=Account
            # Use custom_taxonomy_code if available
            taxonomy_code = acc.get("custom_taxonomy_code")
            if taxonomy_code:
                 etree.SubElement(account, "TaxonomyCode").text = str(taxonomy_code) # Ensure it's string
            # SelfBillingIndicator - not applicable here

    def _build_customers(self, master_files):
        customers = frappe.get_all("Customer", filters={"disabled": 0}, fields=["name", "customer_name", "tax_id", "customer_group"])
        if not customers: return
        
        for cust in customers:
            customer = etree.SubElement(master_files, "Customer")
            etree.SubElement(customer, "CustomerID").text = cust.name
            etree.SubElement(customer, "AccountID").text = "NA" # Default if no specific GL account link
            # TODO: Find linked GL account if applicable
            etree.SubElement(customer, "CustomerTaxID").text = cust.tax_id or "999999990" # Use default for consumers
            etree.SubElement(customer, "CompanyName").text = cust.customer_name
            
            # Get billing address
            billing_address = frappe.get_cached_value("Address", {"is_billing_address": 1, "links.link_doctype": "Customer", "links.link_name": cust.name}, ["address_line1", "address_line2", "city", "pincode", "state", "country"], as_dict=True)
            address = etree.SubElement(customer, "BillingAddress")
            if billing_address:
                 etree.SubElement(address, "AddressDetail").text = f"{billing_address.address_line1 or \'\'} {billing_address.address_line2 or \'\'}".strip()
                 etree.SubElement(address, "City").text = billing_address.city or ""
                 etree.SubElement(address, "PostalCode").text = billing_address.pincode or ""
                 etree.SubElement(address, "Region").text = billing_address.state or ""
                 etree.SubElement(address, "Country").text = "PT" # Default, needs check
            else: # Add empty elements if no address
                 etree.SubElement(address, "AddressDetail").text = ""
                 etree.SubElement(address, "City").text = ""
                 etree.SubElement(address, "PostalCode").text = ""
                 etree.SubElement(address, "Region").text = ""
                 etree.SubElement(address, "Country").text = "PT"
            
            # Shipping Address - similar logic if needed
            # etree.SubElement(customer, "ShipToAddress") ...
            
            etree.SubElement(customer, "SelfBillingIndicator").text = "0" # Assuming no self-billing by default

    def _build_suppliers(self, master_files):
        suppliers = frappe.get_all("Supplier", filters={"disabled": 0}, fields=["name", "supplier_name", "tax_id", "supplier_group"])
        if not suppliers: return
        
        for supp in suppliers:
            supplier = etree.SubElement(master_files, "Supplier")
            etree.SubElement(supplier, "SupplierID").text = supp.name
            etree.SubElement(supplier, "AccountID").text = "NA" # Default
            # TODO: Find linked GL account
            etree.SubElement(supplier, "SupplierTaxID").text = supp.tax_id or ""
            etree.SubElement(supplier, "CompanyName").text = supp.supplier_name
            # Billing Address - similar logic to Customer
            # Get billing address
            billing_address = frappe.get_cached_value("Address", {"is_billing_address": 1, "links.link_doctype": "Supplier", "links.link_name": supp.name}, ["address_line1", "address_line2", "city", "pincode", "state", "country"], as_dict=True)
            address = etree.SubElement(supplier, "BillingAddress")
            if billing_address:
                 etree.SubElement(address, "AddressDetail").text = f"{billing_address.address_line1 or \'\'} {billing_address.address_line2 or \'\'}".strip()
                 etree.SubElement(address, "City").text = billing_address.city or ""
                 etree.SubElement(address, "PostalCode").text = billing_address.pincode or ""
                 etree.SubElement(address, "Region").text = billing_address.state or ""
                 etree.SubElement(address, "Country").text = "PT" # Default, needs check
            else: # Add empty elements if no address
                 etree.SubElement(address, "AddressDetail").text = ""
                 etree.SubElement(address, "City").text = ""
                 etree.SubElement(address, "PostalCode").text = ""
                 etree.SubElement(address, "Region").text = ""
                 etree.SubElement(address, "Country").text = "PT"
            
            etree.SubElement(supplier, "SelfBillingIndicator").text = "0" # Assuming no self-billing by default

    def _build_products(self, master_files):
        products = frappe.get_all("Item", filters={"disabled": 0}, fields=["name", "item_name", "item_group", "stock_uom", "custom_saft_product_type"])
        if not products: return
        
        prod_section = etree.SubElement(master_files, "Product")
        for item in products:
            product = etree.SubElement(prod_section, "Product")
            # Use custom_saft_product_type if available, default to 'P'
            product_type = item.get("custom_saft_product_type") or "P"
            etree.SubElement(product, "ProductType").text = product_type
            etree.SubElement(product, "ProductCode").text = item.name
            etree.SubElement(product, "ProductGroup").text = item.item_group or ""
            etree.SubElement(product, "ProductDescription").text = item.item_name or item.name
            etree.SubElement(product, "ProductNumberCode").text = item.name # Or barcode if available
            # CustomsDetails, UNNumber - Add if applicable

    def _build_tax_table(self, master_files):
        # Get relevant tax templates used in the period (more complex query needed ideally)
        # Simpler: Get all tax templates with PT compliance fields
        tax_templates = frappe.get_all("Sales Taxes and Charges Template", 
                                       filters={"disabled": 0, "custom_saft_tax_code": ["is", "set"]},
                                       fields=["name", "custom_saft_tax_code", "custom_saft_exemption_reason_code", "rate", "description"])
        if not tax_templates: return
        
        tax_table = etree.SubElement(master_files, "TaxTable")
        for tax in tax_templates:
            tax_entry = etree.SubElement(tax_table, "TaxTableEntry")
            # Map custom_saft_tax_code to TaxType and TaxCode
            saft_code = tax.custom_saft_tax_code
            tax_type = "IVA"
            tax_country_region = "PT"
            tax_code = saft_code # Use the custom code directly
            
            etree.SubElement(tax_entry, "TaxType").text = tax_type
            etree.SubElement(tax_entry, "TaxCountryRegion").text = tax_country_region
            etree.SubElement(tax_entry, "TaxCode").text = tax_code
            etree.SubElement(tax_entry, "Description").text = tax.description or tax.name
            etree.SubElement(tax_entry, "TaxPercentage").text = format_currency(tax.rate or 0.0)
            # Add TaxExemptionReason and TaxExemptionCode if ISE
            if saft_code == "ISE":
                 exemption_code = tax.custom_saft_exemption_reason_code or ""
                 # TODO: Map exemption_code to official reason text if possible/needed
                 exemption_reason = f"Motivo Isen\u00e7\u00e3o {exemption_code}" # Placeholder text
                 if exemption_code:
                      etree.SubElement(tax_entry, "TaxExemptionReason").text = exemption_reason
                      etree.SubElement(tax_entry, "TaxExemptionCode").text = exemption_code

    def _build_general_ledger_entries(self, master_files):
        # Optional: Implement if generating SAF-T for Accounting
        # Query General Ledger Entry table for the period
        # Structure: GeneralLedgerEntries -> NumberOfEntries, TotalDebit, TotalCredit -> Journal -> Transaction -> ...
        pass

    def _build_source_documents(self):
        source_docs = etree.SubElement(self.root, "SourceDocuments")
        self._build_sales_invoices(source_docs)
        # self._build_movement_of_goods(source_docs) # Optional
        # self._build_working_documents(source_docs) # Optional
        # self._build_payments(source_docs) # Optional

    def _build_sales_invoices(self, source_docs):
        invoices = frappe.get_all("Sales Invoice", 
                                  filters={"company": self.company, "docstatus": 1, 
                                           "posting_date": ["between", [self.start_date, self.end_date]]},
                                  fields=["name", "posting_date", "customer", "customer_name", "tax_id", 
                                          "custom_atcud", "custom_digital_signature", "custom_previous_hash",
                                          "net_total", "grand_total", "total_taxes_and_charges", "currency", "plc_conversion_rate",
                                          "creation" # Needed for hash string
                                          ])
        if not invoices: return

        sales_invoices = etree.SubElement(source_docs, "SalesInvoices")
        # TODO: Calculate NumberOfEntries, TotalDebit, TotalCredit for the period
        etree.SubElement(sales_invoices, "NumberOfEntries").text = str(len(invoices))
        etree.SubElement(sales_invoices, "TotalDebit").text = "0.00" # Should be sum of Credit Notes
        etree.SubElement(sales_invoices, "TotalCredit").text = format_currency(sum(inv.grand_total for inv in invoices if inv.grand_total > 0)) # Sum of positive invoices

        for inv_header in invoices:
            # Get full document to access items and taxes
            inv = frappe.get_doc("Sales Invoice", inv_header.name)
            
            invoice = etree.SubElement(sales_invoices, "Invoice")
            etree.SubElement(invoice, "InvoiceNo").text = inv.name
            # DocumentStatus
            doc_status_node = etree.SubElement(invoice, "DocumentStatus")
            invoice_status = "N" # Normal
            if inv.docstatus == 2: invoice_status = "A" # Cancelled
            # TODO: Add logic for F=Final (if applicable), S=SelfBilling, R=Corrected
            etree.SubElement(doc_status_node, "InvoiceStatus").text = invoice_status
            etree.SubElement(doc_status_node, "InvoiceStatusDate").text = format_datetime(inv.modified) # Use modified as status date
            etree.SubElement(doc_status_node, "SourceID").text = inv.modified_by or ""
            etree.SubElement(doc_status_node, "SourceBilling").text = "P" # P=Produced in system
            
            etree.SubElement(invoice, "Hash").text = inv.custom_digital_signature or "0" # Signature
            etree.SubElement(invoice, "HashControl").text = "1" # Version of the key (needs config)
            etree.SubElement(invoice, "Period").text = str(inv.posting_date.month) # Or based on fiscal period
            etree.SubElement(invoice, "InvoiceDate").text = format_date(inv.posting_date)
            # Map DocType to InvoiceType
            invoice_type = "FT" # Default
            if inv.doctype == "Sales Invoice Return": invoice_type = "NC"
            # Add more mappings
            etree.SubElement(invoice, "InvoiceType").text = invoice_type
            # SpecialRegimes
            special_regimes = etree.SubElement(invoice, "SpecialRegimes")
            etree.SubElement(special_regimes, "SelfBillingIndicator").text = "0"
            etree.SubElement(special_regimes, "CashVATSchemeIndicator").text = "0"
            etree.SubElement(special_regimes, "ThirdPartiesBillingIndicator").text = "0"
            
            etree.SubElement(invoice, "SourceID").text = inv.owner or ""
            etree.SubElement(invoice, "SystemEntryDate").text = format_datetime(inv.creation)
            etree.SubElement(invoice, "CustomerID").text = inv.customer
            # ShipTo / ShipFrom Addresses if applicable
            
            # Lines
            for item in inv.items:
                line = etree.SubElement(invoice, "Line")
                etree.SubElement(line, "LineNumber").text = str(item.idx)
                etree.SubElement(line, "ProductCode").text = item.item_code
                etree.SubElement(line, "ProductDescription").text = item.description
                etree.SubElement(line, "Quantity").text = format_currency(item.qty)
                etree.SubElement(line, "UnitOfMeasure").text = item.uom or ""
                etree.SubElement(line, "UnitPrice").text = format_currency(item.rate)
                # TaxPointDate - usually same as invoice date
                etree.SubElement(line, "TaxPointDate").text = format_date(inv.posting_date)
                # References - Add if Credit Note references original invoice
                # Description
                etree.SubElement(line, "Description").text = item.description # Redundant?
                etree.SubElement(line, "DebitAmount").text = "0.00" # For Credit Notes
                etree.SubElement(line, "CreditAmount").text = format_currency(item.net_amount) # For Invoices
                if invoice_type == "NC": # Swap for Credit Notes
                     line.find("DebitAmount").text = format_currency(item.net_amount)
                     line.find("CreditAmount").text = "0.00"
                
                # Tax details for the line
                tax = etree.SubElement(line, "Tax")
                # Find the relevant tax template for this item/line
                # This requires linking item tax template to Sales Taxes and Charges Template
                # Simplified: Assume first tax rate applies or use average if multiple?
                # Needs robust logic based on ERPNext tax calculation
                tax_rate = item.get("tax_rate") or 0.0 # Placeholder
                tax_template_name = item.item_tax_template or ""
                saft_tax_code = "NOR" # Default
                exemption_reason = "" 
                exemption_code = ""
                if tax_template_name:
                     tax_template_doc = frappe.get_cached_value("Item Tax Template", tax_template_name, ["*"], as_dict=True)
                     if tax_template_doc and tax_template_doc.get("tax_type"): # Assuming tax_type links to Sales Taxes and Charges Template
                          charge_template = frappe.get_cached_value("Sales Taxes and Charges Template", tax_template_doc.tax_type, ["custom_saft_tax_code", "custom_saft_exemption_reason_code", "rate"], as_dict=True)
                          if charge_template:
                               saft_tax_code = charge_template.custom_saft_tax_code or "NOR"
                               tax_rate = charge_template.rate or 0.0
                               if saft_tax_code == "ISE":
                                    exemption_code = charge_template.custom_saft_exemption_reason_code or ""
                                    # TODO: Map code to reason text
                                    exemption_reason = f"Motivo Isen\u00e7\u00e3o {exemption_code}" if exemption_code else "Isento"
                                    
                etree.SubElement(tax, "TaxType").text = "IVA"
                etree.SubElement(tax, "TaxCountryRegion").text = "PT"
                etree.SubElement(tax, "TaxCode").text = saft_tax_code
                etree.SubElement(tax, "TaxPercentage").text = format_currency(tax_rate)
                if saft_tax_code == "ISE" and exemption_code:
                     etree.SubElement(line, "TaxExemptionReason").text = exemption_reason
                     etree.SubElement(line, "TaxExemptionCode").text = exemption_code
                # SettlementAmount - Add if applicable

            # Document Totals
            totals = etree.SubElement(invoice, "DocumentTotals")
            etree.SubElement(totals, "TaxPayable").text = format_currency(inv.total_taxes_and_charges) # Total VAT
            etree.SubElement(totals, "NetTotal").text = format_currency(inv.net_total)
            etree.SubElement(totals, "GrossTotal").text = format_currency(inv.grand_total)
            # Settlement, Payment - Add if applicable

# --- Add other document types: MovementOfGoods, WorkingDocuments, Payments --- #

# Example Usage (called from a page or report):
# generator = SaftGenerator(fiscal_year=2024, company="My Company")
# xml_content = generator.generate_file()
# with open("saft_pt_output.xml", "wb") as f:
#     f.write(xml_content)

