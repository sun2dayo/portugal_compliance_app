```python
import xml.etree.ElementTree as ET

# Mock data (replace with actual data generation if needed for a full test)
company_data = {
    "tax_id": "501234567",
    "company_name": "Test Company Ltd.",
    "address_detail": "Rua Principal 123",
    "city": "Lisboa",
    "postal_code": "1000-001",
    "region": "Lisboa",
    "country": "PT",
    "default_currency": "EUR"
}

fiscal_year = 2023

# --- MasterFiles --- 
# GeneralLedgerAccounts
accounts = [
    {"AccountID": "111", "AccountDescription": "Cash", "OpeningDebitBalance": "1000", "ClosingDebitBalance": "1500", "GroupingCategory": "ASSET", "GroupingCode": "1", "TaxonomyCode": "1.1.1"},
    {"AccountID": "211", "AccountDescription": "Accounts Payable", "OpeningCreditBalance": "500", "ClosingCreditBalance": "800", "GroupingCategory": "LIABILITY", "GroupingCode": "2", "TaxonomyCode": "2.1.1"}
]

# Customers
customers = [
    {"CustomerID": "CUST001", "AccountID": "1211", "CustomerTaxID": "501111111", "CompanyName": "Cliente Exemplo 1", 
     "BillingAddress": {"AddressDetail": "Av. da Liberdade, 1", "City": "Lisboa", "PostalCode": "1250-140", "Region": "Lisboa", "Country": "PT"},
     "SelfBillingIndicator": "0"}
]

# Suppliers
suppliers = [
    {"SupplierID": "SUP001", "AccountID": "2211", "SupplierTaxID": "502222222", "CompanyName": "Fornecedor Exemplo 1",
     "BillingAddress": {"AddressDetail": "Rua das Flores, 10", "City": "Porto", "PostalCode": "4000-001", "Region": "Norte", "Country": "PT"},
     "SelfBillingIndicator": "0"}
]

# Products
products = [
    {"ProductType": "P", "ProductCode": "PROD001", "ProductGroup": "Eletrónicos", "ProductDescription": "Smartphone XPTO", "ProductNumberCode": "12345678"}
]

# TaxTable
tax_table_entries = [
    {"TaxType": "IVA", "TaxCountryRegion": "PT", "TaxCode": "NOR", "Description": "Normal VAT rate", "TaxPercentage": "23.00"},
    {"TaxType": "IVA", "TaxCountryRegion": "PT", "TaxCode": "RED", "Description": "Reduced VAT rate", "TaxPercentage": "6.00"}
]

# --- GeneralLedgerEntries --- 
# Journals and Transactions
journals = [
    {"JournalID": "J001", "Description": "Sales Journal", "Transactions": [
        {"TransactionID": "T001", "Period": "1", "TransactionDate": "2023-01-15", "SourceID": "User001", "Description": "Sale of goods", "DocArchivalNo": "SAFT/FT A/1", "TransactionType": "N", "GLPostingDate": "2023-01-15", "CustomerID": "CUST001", "Lines": [
            {"RecordID": "1", "AccountID": "1211", "SourceDocumentID": "FT A/1", "SystemEntryDate": "2023-01-15T10:00:00", "Description": "Debit from sale", "DebitAmount": "123.00"},
            {"RecordID": "2", "AccountID": "711", "SourceDocumentID": "FT A/1", "SystemEntryDate": "2023-01-15T10:00:00", "Description": "Credit from sale", "CreditAmount": "100.00"},
            {"RecordID": "3", "AccountID": "24331", "SourceDocumentID": "FT A/1", "SystemEntryDate": "2023-01-15T10:00:00", "Description": "VAT on sale", "CreditAmount": "23.00"}
        ]}
    ]}
]

# --- SourceDocuments --- 
# SalesInvoices
sales_invoices = [
    {
        "InvoiceNo": "FT A/1", "ATCUD": "ATCUD:XYZ123-1", "DocumentStatus": {"InvoiceStatus": "N", "InvoiceStatusDate": "2023-01-15T10:05:00", "SourceID": "User001", "SourceBilling": "P"},
        "Hash": "HASHDOCCORRENTE1", "HashControl": "1", "Period": "1", "InvoiceDate": "2023-01-15", "InvoiceType": "FT",
        "SpecialRegimes": {"SelfBillingIndicator": "0", "CashVATSchemeIndicator": "0", "ThirdPartiesBillingIndicator": "0"},
        "SourceID": "User001", "SystemEntryDate": "2023-01-15T10:00:00", "CustomerID": "CUST001",
        "Lines": [
            {"LineNumber": "1", "ProductCode": "PROD001", "ProductDescription": "Smartphone XPTO", "Quantity": "1.00", "UnitOfMeasure": "UN", "UnitPrice": "100.00", "TaxPointDate": "2023-01-15", "Description": "Smartphone XPTO", "CreditAmount": "100.00",
             "Tax": {"TaxType": "IVA", "TaxCountryRegion": "PT", "TaxCode": "NOR", "TaxPercentage": "23.00"}}
        ],
        "DocumentTotals": {"TaxPayable": "23.00", "NetTotal": "100.00", "GrossTotal": "123.00"}
    }
]

# MovementOfGoods (Simplified - assuming similar structure for demonstration)
movement_of_goods = [] # Populate if needed

# WorkingDocuments (Simplified - assuming similar structure for demonstration)
working_documents = [] # Populate if needed

# Payments (Simplified - assuming similar structure for demonstration)
payments = [] # Populate if needed

# --- XML Generation --- 

def create_xml_element(parent, tag, text=None, attributes=None):
    element = ET.SubElement(parent, tag)
    if text:
        element.text = str(text)
    if attributes:
        for k, v in attributes.items():
            element.set(k, str(v))
    return element

# Root element
root = ET.Element("AuditFile", nsmap=NSMAP)
root.set("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", "urn:OECD:StandardAuditFile-Tax:PT_1.04_01 saftpt1.04_01.xsd")

# Header
header_xml = create_xml_element(root, "Header")
create_xml_element(header_xml, "AuditFileVersion", "1.04_01")
create_xml_element(header_xml, "CompanyID", company_data["tax_id"])
create_xml_element(header_xml, "TaxRegistrationNumber", company_data["tax_id"])
create_xml_element(header_xml, "TaxAccountingBasis", "I") # Assuming Integrated
create_xml_element(header_xml, "CompanyName", company_data["company_name"])
create_xml_element(header_xml, "BusinessName", company_data["company_name"])
company_address_xml = create_xml_element(header_xml, "CompanyAddress")
create_xml_element(company_address_xml, "AddressDetail", company_data["address_detail"])
create_xml_element(company_address_xml, "City", company_data["city"])
create_xml_element(company_address_xml, "PostalCode", company_data["postal_code"])
create_xml_element(company_address_xml, "Region", company_data["region"])
create_xml_element(company_address_xml, "Country", company_data["country"])
create_xml_element(header_xml, "FiscalYear", str(fiscal_year))
create_xml_element(header_xml, "StartDate", f"{fiscal_year}-01-01")
create_xml_element(header_xml, "EndDate", f"{fiscal_year}-12-31")
create_xml_element(header_xml, "CurrencyCode", company_data["default_currency"])
create_xml_element(header_xml, "DateCreated", datetime.now().strftime("%Y-%m-%d"))
create_xml_element(header_xml, "TaxEntity", "Sede")
create_xml_element(header_xml, "ProductCompanyTaxID", "500000000") # Example NIF
create_xml_element(header_xml, "SoftwareCertificateNumber", "0000/AT") # Example Cert Number
create_xml_element(header_xml, "ProductID", "MyERP_PT_Compliance")
create_xml_element(header_xml, "ProductVersion", "1.0")

# MasterFiles
master_files_xml = create_xml_element(root, "MasterFiles")

# GeneralLedgerAccounts
gl_accounts_xml = create_xml_element(master_files_xml, "GeneralLedgerAccounts")
for acc in accounts:
    acc_xml = create_xml_element(gl_accounts_xml, "Account")
    create_xml_element(acc_xml, "AccountID", acc["AccountID"])
    create_xml_element(acc_xml, "AccountDescription", acc["AccountDescription"])
    create_xml_element(acc_xml, "OpeningDebitBalance", acc.get("OpeningDebitBalance", "0.00"))
    create_xml_element(acc_xml, "OpeningCreditBalance", acc.get("OpeningCreditBalance", "0.00"))
    create_xml_element(acc_xml, "ClosingDebitBalance", acc.get("ClosingDebitBalance", "0.00"))
    create_xml_element(acc_xml, "ClosingCreditBalance", acc.get("ClosingCreditBalance", "0.00"))
    create_xml_element(acc_xml, "GroupingCategory", acc["GroupingCategory"])
    create_xml_element(acc_xml, "GroupingCode", acc["GroupingCode"])
    if "TaxonomyCode" in acc: # Optional
        create_xml_element(acc_xml, "TaxonomyCode", acc["TaxonomyCode"])

# Customers
for cust in customers:
    customer_xml = create_xml_element(master_files_xml, "Customer")
    create_xml_element(customer_xml, "CustomerID", cust["CustomerID"])
    create_xml_element(customer_xml, "AccountID", cust["AccountID"])
    create_xml_element(customer_xml, "CustomerTaxID", cust["CustomerTaxID"])
    create_xml_element(customer_xml, "CompanyName", cust["CompanyName"])
    billing_address_xml = create_xml_element(customer_xml, "BillingAddress")
    create_xml_element(billing_address_xml, "AddressDetail", cust["BillingAddress"]["AddressDetail"])
    create_xml_element(billing_address_xml, "City", cust["BillingAddress"]["City"])
    create_xml_element(billing_address_xml, "PostalCode", cust["BillingAddress"]["PostalCode"])
    create_xml_element(billing_address_xml, "Region", cust["BillingAddress"]["Region"])
    create_xml_element(billing_address_xml, "Country", cust["BillingAddress"]["Country"])
    create_xml_element(customer_xml, "SelfBillingIndicator", cust["SelfBillingIndicator"])

# Suppliers
for supp in suppliers:
    supplier_xml = create_xml_element(master_files_xml, "Supplier")
    create_xml_element(supplier_xml, "SupplierID", supp["SupplierID"])
    create_xml_element(supplier_xml, "AccountID", supp["AccountID"])
    create_xml_element(supplier_xml, "SupplierTaxID", supp["SupplierTaxID"])
    create_xml_element(supplier_xml, "CompanyName", supp["CompanyName"])
    billing_address_xml = create_xml_element(supplier_xml, "BillingAddress")
    create_xml_element(billing_address_xml, "AddressDetail", supp["BillingAddress"]["AddressDetail"])
    create_xml_element(billing_address_xml, "City", supp["BillingAddress"]["City"])
    create_xml_element(billing_address_xml, "PostalCode", supp["BillingAddress"]["PostalCode"])
    create_xml_element(billing_address_xml, "Region", supp["BillingAddress"]["Region"])
    create_xml_element(billing_address_xml, "Country", supp["BillingAddress"]["Country"])
    create_xml_element(supplier_xml, "SelfBillingIndicator", supp["SelfBillingIndicator"])

# Products
for prod in products:
    product_xml = create_xml_element(master_files_xml, "Product")
    create_xml_element(product_xml, "ProductType", prod["ProductType"])
    create_xml_element(product_xml, "ProductCode", prod["ProductCode"])
    create_xml_element(product_xml, "ProductGroup", prod["ProductGroup"])
    create_xml_element(product_xml, "ProductDescription", prod["ProductDescription"])
    create_xml_element(product_xml, "ProductNumberCode", prod["ProductNumberCode"])

# TaxTable
tax_table_xml = create_xml_element(master_files_xml, "TaxTable")
for tax_entry_data in tax_table_entries:
    tax_entry_xml = create_xml_element(tax_table_xml, "TaxTableEntry")
    create_xml_element(tax_entry_xml, "TaxType", tax_entry_data["TaxType"])
    create_xml_element(tax_entry_xml, "TaxCountryRegion", tax_entry_data["TaxCountryRegion"])
    create_xml_element(tax_entry_xml, "TaxCode", tax_entry_data["TaxCode"])
    create_xml_element(tax_entry_xml, "Description", tax_entry_data["Description"])
    create_xml_element(tax_entry_xml, "TaxPercentage", tax_entry_data["TaxPercentage"])

# GeneralLedgerEntries
gl_entries_xml = create_xml_element(root, "GeneralLedgerEntries")
create_xml_element(gl_entries_xml, "NumberOfEntries", str(sum(len(j["Transactions"]) for j in journals)))
create_xml_element(gl_entries_xml, "TotalDebit", format_currency(sum(l["DebitAmount"] for j in journals for t in j["Transactions"] for l in t["Lines"] if "DebitAmount" in l)))
create_xml_element(gl_entries_xml, "TotalCredit", format_currency(sum(l["CreditAmount"] for j in journals for t in j["Transactions"] for l in t["Lines"] if "CreditAmount" in l)))

for journal_data in journals:
    journal_xml = create_xml_element(gl_entries_xml, "Journal")
    create_xml_element(journal_xml, "JournalID", journal_data["JournalID"])
    create_xml_element(journal_xml, "Description", journal_data["Description"])
    for transaction_data in journal_data["Transactions"]:
        transaction_xml = create_xml_element(journal_xml, "Transaction")
        create_xml_element(transaction_xml, "TransactionID", transaction_data["TransactionID"])
        create_xml_element(transaction_xml, "Period", transaction_data["Period"])
        create_xml_element(transaction_xml, "TransactionDate", transaction_data["TransactionDate"])
        create_xml_element(transaction_xml, "SourceID", transaction_data["SourceID"])
        create_xml_element(transaction_xml, "Description", transaction_data["Description"])
        create_xml_element(transaction_xml, "DocArchivalNo", transaction_data["DocArchivalNo"])
        create_xml_element(transaction_xml, "TransactionType", transaction_data["TransactionType"])
        create_xml_element(transaction_xml, "GLPostingDate", transaction_data["GLPostingDate"])
        if "CustomerID" in transaction_data:
             create_xml_element(transaction_xml, "CustomerID", transaction_data["CustomerID"])
        # SupplierID can be added similarly if needed
        lines_xml = create_xml_element(transaction_xml, "Lines")
        for line_data in transaction_data["Lines"]:
            line_xml = create_xml_element(lines_xml, "Line")
            create_xml_element(line_xml, "RecordID", line_data["RecordID"])
            create_xml_element(line_xml, "AccountID", line_data["AccountID"])
            create_xml_element(line_xml, "SourceDocumentID", line_data["SourceDocumentID"])
            create_xml_element(line_xml, "SystemEntryDate", line_data["SystemEntryDate"])
            create_xml_element(line_xml, "Description", line_data["Description"])
            if "DebitAmount" in line_data:
                create_xml_element(line_xml, "DebitAmount", line_data["DebitAmount"])
            if "CreditAmount" in line_data:
                create_xml_element(line_xml, "CreditAmount", line_data["CreditAmount"])

# SourceDocuments
source_documents_xml = create_xml_element(root, "SourceDocuments")

# SalesInvoices
sales_invoices_xml = create_xml_element(source_documents_xml, "SalesInvoices")
create_xml_element(sales_invoices_xml, "NumberOfEntries", str(len(sales_invoices)))
create_xml_element(sales_invoices_xml, "TotalCredit", format_currency(sum(inv["DocumentTotals"]["GrossTotal"] for inv in sales_invoices)))
create_xml_element(sales_invoices_xml, "TotalDebit", "0.00") # Assuming no debit notes in this section

for inv_data in sales_invoices:
    invoice_xml = create_xml_element(sales_invoices_xml, "Invoice")
    create_xml_element(invoice_xml, "InvoiceNo", inv_data["InvoiceNo"])
    create_xml_element(invoice_xml, "ATCUD", inv_data["ATCUD"])
    doc_status_xml = create_xml_element(invoice_xml, "DocumentStatus")
    create_xml_element(doc_status_xml, "InvoiceStatus", inv_data["DocumentStatus"]["InvoiceStatus"])
    create_xml_element(doc_status_xml, "InvoiceStatusDate", inv_data["DocumentStatus"]["InvoiceStatusDate"])
    create_xml_element(doc_status_xml, "SourceID", inv_data["DocumentStatus"]["SourceID"])
    create_xml_element(doc_status_xml, "SourceBilling", inv_data["DocumentStatus"]["SourceBilling"])
    create_xml_element(invoice_xml, "Hash", inv_data["Hash"])
    create_xml_element(invoice_xml, "HashControl", inv_data["HashControl"])
    create_xml_element(invoice_xml, "Period", inv_data["Period"])
    create_xml_element(invoice_xml, "InvoiceDate", inv_data["InvoiceDate"])
    create_xml_element(invoice_xml, "InvoiceType", inv_data["InvoiceType"])
    special_regimes_xml = create_xml_element(invoice_xml, "SpecialRegimes")
    create_xml_element(special_regimes_xml, "SelfBillingIndicator", inv_data["SpecialRegimes"]["SelfBillingIndicator"])
    create_xml_element(special_regimes_xml, "CashVATSchemeIndicator", inv_data["SpecialRegimes"]["CashVATSchemeIndicator"])
    create_xml_element(special_regimes_xml, "ThirdPartiesBillingIndicator", inv_data["SpecialRegimes"]["ThirdPartiesBillingIndicator"])
    create_xml_element(invoice_xml, "SourceID", inv_data["SourceID"])
    create_xml_element(invoice_xml, "SystemEntryDate", inv_data["SystemEntryDate"])
    create_xml_element(invoice_xml, "CustomerID", inv_data["CustomerID"])

    for line_data in inv_data["Lines"]:
        line_xml = create_xml_element(invoice_xml, "Line")
        create_xml_element(line_xml, "LineNumber", line_data["LineNumber"])
        create_xml_element(line_xml, "ProductCode", line_data["ProductCode"])
        create_xml_element(line_xml, "ProductDescription", line_data["ProductDescription"])
        create_xml_element(line_xml, "Quantity", line_data["Quantity"])
        create_xml_element(line_xml, "UnitOfMeasure", line_data["UnitOfMeasure"])
        create_xml_element(line_xml, "UnitPrice", line_data["UnitPrice"])
        create_xml_element(line_xml, "TaxPointDate", line_data["TaxPointDate"])
        create_xml_element(line_xml, "Description", line_data["Description"])
        create_xml_element(line_xml, "CreditAmount", line_data["CreditAmount"])
        tax_xml = create_xml_element(line_xml, "Tax")
        create_xml_element(tax_xml, "TaxType", line_data["Tax"]["TaxType"])
        create_xml_element(tax_xml, "TaxCountryRegion", line_data["Tax"]["TaxCountryRegion"])
        create_xml_element(tax_xml, "TaxCode", line_data["Tax"]["TaxCode"])
        create_xml_element(tax_xml, "TaxPercentage", line_data["Tax"]["TaxPercentage"])

    doc_totals_xml = create_xml_element(invoice_xml, "DocumentTotals")
    create_xml_element(doc_totals_xml, "TaxPayable", inv_data["DocumentTotals"]["TaxPayable"])
    create_xml_element(doc_totals_xml, "NetTotal", inv_data["DocumentTotals"]["NetTotal"])
    create_xml_element(doc_totals_xml, "GrossTotal", inv_data["DocumentTotals"]["GrossTotal"])

# MovementOfGoods, WorkingDocuments, Payments would follow a similar structure if data is available
# For this example, they are empty as per the provided simplified data structure.
# If these sections are mandatory even if empty, add empty tags.
if not movement_of_goods:
    create_xml_element(source_documents_xml, "MovementOfGoods") # Add empty tag if schema requires it
if not working_documents:
    create_xml_element(source_documents_xml, "WorkingDocuments")
if not payments:
    create_xml_element(source_documents_xml, "Payments")

# Output the XML to a file
tree = ET.ElementTree(root)
ET.indent(tree, space="  ", level=0) # For pretty printing, requires Python 3.9+
output_file = "/home/ubuntu/saft_pt_output.xml"

try:
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"SAF-T XML file generated: {output_file}")
except TypeError: # Older Python versions might not support indent directly with write
    # Fallback for older versions (might not be perfectly formatted but structurally correct)
    # This part might need adjustment based on the specific Python version if indent is not available.
    # For now, assuming a modern enough Python that supports it or that rough output is acceptable for testing.
    rough_string = ET.tostring(root, encoding='utf-8', method='xml')
    with open(output_file, "wb") as f:
        f.write(rough_string)
    print(f"SAF-T XML file generated (basic formatting): {output_file}")



