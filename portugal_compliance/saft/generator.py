# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from lxml import etree
from .utils import format_date, format_datetime, format_currency, get_fiscal_year_dates
from ..doctype.compliance_audit_log.compliance_audit_log import create_compliance_log
from .validator import validate_saft_xml

# SAF-T Namespace map
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
        self.root.set("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", 
                      "urn:OECD:StandardAuditFile-Tax:PT_1.04_01 SAFTPT1.04_01.xsd")

    def generate_file(self):
        """Builds all SAF-T XML sections and returns the full XML string"""
        self._build_header()
        self._build_master_files()
        self._build_general_ledger_entries()
        self._build_source_documents()
        create_compliance_log("SAF-T Generated", "Company", self.company, 
                              details=f"SAF-T (PT) generated for Fiscal Year {self.fiscal_year}")
        return etree.tostring(self.root, pretty_print=True, xml_declaration=True, encoding='utf-8')

    def _build_header(self):
        """Build SAF-T <Header> block with company metadata"""
        header = etree.SubElement(self.root, "Header")
        company_doc = frappe.get_doc("Company", self.company)
        
        etree.SubElement(header, "AuditFileVersion").text = "1.04_01"
        etree.SubElement(header, "CompanyID").text = company_doc.tax_id or ""
        etree.SubElement(header, "TaxRegistrationNumber").text = company_doc.tax_id or ""
        etree.SubElement(header, "TaxAccountingBasis").text = "I"
        etree.SubElement(header, "CompanyName").text = company_doc.company_name
        etree.SubElement(header, "BusinessName").text = company_doc.company_name
        
        # Load and format the company’s main address
        address = etree.SubElement(header, "CompanyAddress")
        primary_address = frappe.get_cached_value("Address", {
            "is_primary_address": 1,
            "links.link_doctype": "Company",
            "links.link_name": self.company
        }, ["address_line1", "address_line2", "city", "pincode", "state", "country"])

        if primary_address:
            line1, line2, city, pincode, state, _ = primary_address
            etree.SubElement(address, "AddressDetail").text = f"{line1 or ''} {line2 or ''}".strip()
            etree.SubElement(address, "City").text = city or ""
            etree.SubElement(address, "PostalCode").text = pincode or ""
            etree.SubElement(address, "Region").text = state or ""
            etree.SubElement(address, "Country").text = "PT"
        else:
            for tag in ["AddressDetail", "City", "PostalCode", "Region", "Country"]:
                etree.SubElement(address, tag).text = ""

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
        """Builds the MasterFiles section of SAF-T XML"""
        master_files = etree.SubElement(self.root, "MasterFiles")
        self._build_general_ledger_accounts(master_files)
        self._build_customers(master_files)
        self._build_suppliers(master_files)
        self._build_products(master_files)
        self._build_tax_table(master_files)

    def _build_customers(self, master_files):
        """Adds Customer records with billing address and NIF"""
        customers = frappe.get_all("Customer", filters={"disabled": 0}, fields=["name", "customer_name", "tax_id"])
        if not customers:
            return

        for cust in customers:
            customer = etree.SubElement(master_files, "Customer")
            etree.SubElement(customer, "CustomerID").text = cust.name
            etree.SubElement(customer, "AccountID").text = "NA"
            etree.SubElement(customer, "CustomerTaxID").text = cust.tax_id or "999999990"
            etree.SubElement(customer, "CompanyName").text = cust.customer_name

            # Billing address
            billing_address = frappe.get_cached_value("Address", {
                "is_billing_address": 1,
                "links.link_doctype": "Customer",
                "links.link_name": cust.name
            }, ["address_line1", "address_line2", "city", "pincode", "state", "country"], as_dict=True)

            address = etree.SubElement(customer, "BillingAddress")
            if billing_address:
                etree.SubElement(address, "AddressDetail").text = f"{billing_address.address_line1 or ''} {billing_address.address_line2 or ''}".strip()
                etree.SubElement(address, "City").text = billing_address.city or ""
                etree.SubElement(address, "PostalCode").text = billing_address.pincode or ""
                etree.SubElement(address, "Region").text = billing_address.state or ""
                etree.SubElement(address, "Country").text = "PT"
            else:
                for tag in ["AddressDetail", "City", "PostalCode", "Region", "Country"]:
                    etree.SubElement(address, tag).text = ""

            etree.SubElement(customer, "SelfBillingIndicator").text = "0"

    def _build_suppliers(self, master_files):
        """Adds Supplier records with billing address and NIF"""
        suppliers = frappe.get_all("Supplier", filters={"disabled": 0}, fields=["name", "supplier_name", "tax_id"])
        if not suppliers:
            return

        for supp in suppliers:
            supplier = etree.SubElement(master_files, "Supplier")
            etree.SubElement(supplier, "SupplierID").text = supp.name
            etree.SubElement(supplier, "AccountID").text = "NA"
            etree.SubElement(supplier, "SupplierTaxID").text = supp.tax_id or ""
            etree.SubElement(supplier, "CompanyName").text = supp.supplier_name

            billing_address = frappe.get_cached_value("Address", {
                "is_billing_address": 1,
                "links.link_doctype": "Supplier",
                "links.link_name": supp.name
            }, ["address_line1", "address_line2", "city", "pincode", "state", "country"], as_dict=True)

            address = etree.SubElement(supplier, "BillingAddress")
            if billing_address:
                etree.SubElement(address, "AddressDetail").text = f"{billing_address.address_line1 or ''} {billing_address.address_line2 or ''}".strip()
                etree.SubElement(address, "City").text = billing_address.city or ""
                etree.SubElement(address, "PostalCode").text = billing_address.pincode or ""
                etree.SubElement(address, "Region").text = billing_address.state or ""
                etree.SubElement(address, "Country").text = "PT"
            else:
                for tag in ["AddressDetail", "City", "PostalCode", "Region", "Country"]:
                    etree.SubElement(address, tag).text = ""

            etree.SubElement(supplier, "SelfBillingIndicator").text = "0"

    def _build_products(self, master_files):
        """Adds products (items) with type, group, and codes"""
        products = frappe.get_all("Item", filters={"disabled": 0}, fields=["name", "item_name", "item_group", "stock_uom", "custom_saft_product_type"])
        if not products:
            return

        for item in products:
            product = etree.SubElement(master_files, "Product")
            product_type = item.custom_saft_product_type or "P"
            etree.SubElement(product, "ProductType").text = product_type
            etree.SubElement(product, "ProductCode").text = item.name
            etree.SubElement(product, "ProductGroup").text = item.item_group or ""
            etree.SubElement(product, "ProductDescription").text = item.item_name or item.name
            etree.SubElement(product, "ProductNumberCode").text = item.name

    def _build_tax_table(self, master_files):
        """Builds TaxTable entries with VAT codes and exemption reasons"""
        tax_templates = frappe.get_all("Sales Taxes and Charges Template", filters={"disabled": 0, "custom_saft_tax_code": ["is", "set"]},
            fields=["name", "custom_saft_tax_code", "custom_saft_exemption_reason_code", "rate", "description"])
        if not tax_templates:
            return

        tax_table = etree.SubElement(master_files, "TaxTable")
        for tax in tax_templates:
            entry = etree.SubElement(tax_table, "TaxTableEntry")
            etree.SubElement(entry, "TaxType").text = "IVA"
            etree.SubElement(entry, "TaxCountryRegion").text = "PT"
            etree.SubElement(entry, "TaxCode").text = tax.custom_saft_tax_code
            etree.SubElement(entry, "Description").text = tax.description or tax.name
            etree.SubElement(entry, "TaxPercentage").text = format_currency(tax.rate)

            if tax.custom_saft_tax_code == "ISE" and tax.custom_saft_exemption_reason_code:
                etree.SubElement(entry, "TaxExemptionReason").text = f"Exemption {tax.custom_saft_exemption_reason_code}"
                etree.SubElement(entry, "TaxExemptionCode").text = tax.custom_saft_exemption_reason_code

    def _build_source_documents(self):
        """Builds the SourceDocuments block (invoices, payments, etc.)"""
        source_docs = etree.SubElement(self.root, "SourceDocuments")
        self._build_sales_invoices(source_docs)
        self._build_working_documents(source_docs)
        self._build_movement_of_goods(source_docs)
        self._build_payments(source_docs)

    def _build_sales_invoices(self, source_docs):
        """Lists submitted Sales Invoices with digital signature and taxes"""
        invoices = frappe.get_all("Sales Invoice", 
            filters={"company": self.company, "docstatus": 1, "posting_date": ["between", [self.start_date, self.end_date]]},
            fields=["name", "posting_date", "customer", "customer_name", "tax_id", 
                    "custom_atcud", "custom_digital_signature", "custom_previous_hash",
                    "net_total", "grand_total", "total_taxes_and_charges", "currency", "plc_conversion_rate", "creation"])

        if not invoices:
            return

        invoices_section = etree.SubElement(source_docs, "SalesInvoices")
        etree.SubElement(invoices_section, "NumberOfEntries").text = str(len(invoices))
        total_credit = sum(inv.grand_total for inv in invoices if inv.grand_total > 0)
        etree.SubElement(invoices_section, "TotalCredit").text = format_currency(total_credit)
        etree.SubElement(invoices_section, "TotalDebit").text = "0.00"  # Only if credit notes

        for inv_data in invoices:
            inv = frappe.get_doc("Sales Invoice", inv_data.name)
            invoice = etree.SubElement(invoices_section, "Invoice")
            etree.SubElement(invoice, "InvoiceNo").text = inv.name

            doc_status = etree.SubElement(invoice, "DocumentStatus")
            etree.SubElement(doc_status, "InvoiceStatus").text = "N"
            etree.SubElement(doc_status, "InvoiceStatusDate").text = format_datetime(inv.modified)
            etree.SubElement(doc_status, "SourceID").text = inv.modified_by or ""
            etree.SubElement(doc_status, "SourceBilling").text = "P"

            etree.SubElement(invoice, "Hash").text = inv.custom_digital_signature or "0"
            etree.SubElement(invoice, "HashControl").text = "1"
            etree.SubElement(invoice, "Period").text = str(inv.posting_date.month)
            etree.SubElement(invoice, "InvoiceDate").text = format_date(inv.posting_date)
            etree.SubElement(invoice, "InvoiceType").text = "FT"

            regimes = etree.SubElement(invoice, "SpecialRegimes")
            etree.SubElement(regimes, "SelfBillingIndicator").text = "0"
            etree.SubElement(regimes, "CashVATSchemeIndicator").text = "0"
            etree.SubElement(regimes, "ThirdPartiesBillingIndicator").text = "0"

            etree.SubElement(invoice, "SourceID").text = inv.owner or ""
            etree.SubElement(invoice, "SystemEntryDate").text = format_datetime(inv.creation)
            etree.SubElement(invoice, "CustomerID").text = inv.customer

            for item in inv.items:
                line = etree.SubElement(invoice, "Line")
                etree.SubElement(line, "LineNumber").text = str(item.idx)
                etree.SubElement(line, "ProductCode").text = item.item_code
                etree.SubElement(line, "ProductDescription").text = item.description
                etree.SubElement(line, "Quantity").text = format_currency(item.qty)
                etree.SubElement(line, "UnitOfMeasure").text = item.uom or ""
                etree.SubElement(line, "UnitPrice").text = format_currency(item.rate)
                etree.SubElement(line, "TaxPointDate").text = format_date(inv.posting_date)
                etree.SubElement(line, "Description").text = item.description
                etree.SubElement(line, "CreditAmount").text = format_currency(item.net_amount)
                etree.SubElement(line, "DebitAmount").text = "0.00"

                tax = etree.SubElement(line, "Tax")
                etree.SubElement(tax, "TaxType").text = "IVA"
                etree.SubElement(tax, "TaxCountryRegion").text = "PT"
                etree.SubElement(tax, "TaxCode").text = "NOR"
                etree.SubElement(tax, "TaxPercentage").text = "23.00"  # Replace with dynamic logic if needed

            totals = etree.SubElement(invoice, "DocumentTotals")
            etree.SubElement(totals, "TaxPayable").text = format_currency(inv.total_taxes_and_charges)
            etree.SubElement(totals, "NetTotal").text = format_currency(inv.net_total)
            etree.SubElement(totals, "GrossTotal").text = format_currency(inv.grand_total)

    def _build_general_ledger_entries(self):
        """Adds all accounting journal entries (GL Entry)"""
        entries = frappe.get_all("GL Entry", filters={
            "company": self.company,
            "posting_date": ["between", [self.start_date, self.end_date]],
            "is_cancelled": 0
        }, fields=["name", "posting_date", "voucher_type", "voucher_no", "account", "debit", "credit", "remarks", "modified", "modified_by"],
           order_by="posting_date, name")

        if not entries:
            return

        gle = etree.SubElement(self.root, "GeneralLedgerEntries")
        etree.SubElement(gle, "NumberOfEntries").text = str(len(entries))
        etree.SubElement(gle, "TotalDebit").text = format_currency(sum(e.debit for e in entries))
        etree.SubElement(gle, "TotalCredit").text = format_currency(sum(e.credit for e in entries))

        journal = etree.SubElement(gle, "Journal")
        grouped = {}
        for e in entries:
            grouped.setdefault(e.voucher_no, []).append(e)

        for txn_id, lines in grouped.items():
            txn_node = etree.SubElement(journal, "Transaction")
            first_line = lines[0]
            etree.SubElement(txn_node, "TransactionID").text = txn_id
            etree.SubElement(txn_node, "Period").text = str(first_line.posting_date.month)
            etree.SubElement(txn_node, "TransactionDate").text = format_date(first_line.posting_date)
            etree.SubElement(txn_node, "Description").text = first_line.remarks or first_line.voucher_type
            etree.SubElement(txn_node, "SourceID").text = first_line.modified_by or ""
            etree.SubElement(txn_node, "SystemEntryDate").text = format_datetime(first_line.modified)

            for line in lines:
                if line.debit > 0:
                    node = etree.SubElement(txn_node, "DebitLine")
                    etree.SubElement(node, "DebitAmount").text = format_currency(line.debit)
                else:
                    node = etree.SubElement(txn_node, "CreditLine")
                    etree.SubElement(node, "CreditAmount").text = format_currency(line.credit)

                etree.SubElement(node, "RecordID").text = line.name
                etree.SubElement(node, "AccountID").text = line.account
                etree.SubElement(node, "SourceDocumentID").text = line.voucher_type

    def _build_working_documents(self, source_docs):
        """Creates placeholder or full block for Working Documents (e.g., drafts, proformas)"""
        # Placeholder implementation (optional for some companies)
        working_docs = etree.SubElement(source_docs, "WorkingDocuments")
        etree.SubElement(working_docs, "NumberOfEntries").text = "0"
        etree.SubElement(working_docs, "TotalDebit").text = "0.00"
        etree.SubElement(working_docs, "TotalCredit").text = "0.00"

        # You can expand this by including Quotation, Proforma, or Draft types if needed

    def _build_payments(self, source_docs):
        """Creates Payments block for payment receipts or settlement notes"""
        payments = frappe.get_all("Payment Entry", filters={
            "company": self.company,
            "docstatus": 1,
            "posting_date": ["between", [self.start_date, self.end_date]],
            "payment_type": "Receive"
        }, fields=["name", "party", "party_type", "paid_amount", "posting_date", "paid_to", "remarks", "modified", "owner"])

        payments_node = etree.SubElement(source_docs, "Payments")
        etree.SubElement(payments_node, "NumberOfEntries").text = str(len(payments))
        etree.SubElement(payments_node, "TotalDebit").text = "0.00"
        etree.SubElement(payments_node, "TotalCredit").text = format_currency(sum(p.paid_amount for p in payments))

        for pay in payments:
            pay_node = etree.SubElement(payments_node, "Payment")
            etree.SubElement(pay_node, "PaymentRefNo").text = pay.name
            etree.SubElement(pay_node, "Period").text = str(pay.posting_date.month)
            etree.SubElement(pay_node, "TransactionDate").text = format_date(pay.posting_date)
            etree.SubElement(pay_node, "PaymentType").text = "RC"  # RC = Receipt
            etree.SubElement(pay_node, "Description").text = pay.remarks or "Receipt"
            etree.SubElement(pay_node, "SystemID").text = pay.name
            etree.SubElement(pay_node, "SourceID").text = pay.owner or ""
            etree.SubElement(pay_node, "SystemEntryDate").text = format_datetime(pay.modified)
            etree.SubElement(pay_node, "CustomerID").text = pay.party if pay.party_type == "Customer" else ""

            lines = etree.SubElement(pay_node, "Line")
            etree.SubElement(lines, "RecordID").text = pay.name
            etree.SubElement(lines, "CreditAmount").text = format_currency(pay.paid_amount)
            etree.SubElement(lines, "TaxType").text = "IVA"
            etree.SubElement(lines, "TaxCountryRegion").text = "PT"
            etree.SubElement(lines, "TaxCode").text = "NOR"
            etree.SubElement(lines, "TaxPercentage").text = "0.00"  # Assuming exempt
            etree.SubElement(lines, "SettlementAmount").text = format_currency(pay.paid_amount)

    def _build_movement_of_goods(self, source_docs):
        """Creates placeholder block for transport documents (Guia de Transporte)"""
        # If your company issues 'Delivery Note' or 'Shipping Documents', you can add them here
        movement = etree.SubElement(source_docs, "MovementOfGoods")
        etree.SubElement(movement, "NumberOfMovementLines").text = "0"
        etree.SubElement(movement, "TotalQuantityIssued").text = "0.00"
        # Optional: iterate over Stock Entry or Delivery Note if applicable
        
    # Keep this at the very bottom of generator.py

       @frappe.whitelist()
    def generate_saft_pt_file(fiscal_year, start_date=None, end_date=None):
        import base64
        from frappe.utils.file_manager import save_file
        from .generator import SaftGenerator
        from .utils import run_saft_precheck
        from .validator import validate_saft_xml  # <--- certifique-se que está importado!

        try:
            company = frappe.defaults.get_user_default("Company")
            if not company:
                frappe.throw("Default company is not defined.")

            # Pre-validation before SAF-T generation
            precheck = run_saft_precheck(company)
            if precheck["status"] != "OK":
                frappe.throw(_("SAF-T precheck failed. Please fix issues before generating."))

            # Generate SAF-T
            generator = SaftGenerator(fiscal_year=fiscal_year, company=company)
            if start_date and end_date:
                generator.start_date = start_date
                generator.end_date = end_date

            xml_content = generator.generate_file()

            # Validate XML against official XSD
            xsd_path = frappe.get_app_path("portugal_compliance", "xsd", "SAFTPT1.04_01.xsd")
            validate_saft_xml(xml_content, xsd_path)

            # Save and return file
            file_name = f"SAFT_PT_{company}_{fiscal_year}.xml"
            save_file(file_name, xml_content, "Company", company, is_private=1)
            encoded = base64.b64encode(xml_content).decode("utf-8")

            return {
                "filename": file_name,
                "filecontent": encoded
            }

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Error generating SAF-T")
            frappe.throw("Error generating SAF-T file. Check logs for details.")


