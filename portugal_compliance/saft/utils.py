# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import re


def format_date(date_obj):
    """Formats date as YYYY-MM-DD."""
    if not date_obj:
        return None
    return formatdate(date_obj, "yyyy-MM-dd")

def format_datetime(datetime_obj):
    """Formats datetime as YYYY-MM-DDThh:mm:ss."""
    if not datetime_obj:
        return None
    # SAF-T PT requires without timezone
    return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")

def get_company_data(company_abbr):
    """Fetches relevant data for the specified company."""
    if not company_abbr:
        company_abbr = frappe.get_doc("Global Defaults").default_company
        if not company_abbr:
            frappe.throw("Default Company not set in Global Defaults.")

    company_doc = frappe.get_doc("Company", company_abbr)

    data = {
        "company_name": company_doc.company_name,
        "abbr": company_doc.abbr,
        "tax_id": company_doc.tax_id, # Ensure this field exists and is correct
        "registration": company_doc.registration_details, # Ensure this holds commercial registration
        "default_currency": company_doc.default_currency,
        "phone": company_doc.phone_no,
        "fax": company_doc.fax,
        "email": company_doc.email,
        "website": company_doc.website,
        "company_address_name": company_doc.company_address # Store address name for later lookup
    }
    return data

def get_fiscal_year_data(fiscal_year_name):
    """Fetches start/end dates and year number for the specified fiscal year."""
    if not fiscal_year_name:
        today = frappe.utils.today()
        fiscal_year_name = frappe.db.get_value("Fiscal Year", {"year_start_date": ("<=", today), "year_end_date": (">=", today)}, "name")
        if not fiscal_year_name:
             frappe.throw("Cannot determine current Fiscal Year.")

    fy_doc = frappe.get_doc("Fiscal Year", fiscal_year_name)
    # Extract the year number (assuming standard naming or a dedicated field)
    year_number = fy_doc.year # Or parse from fy_doc.name if needed
    try:
        year_number = int(year_number)
    except ValueError:
        # Fallback: try parsing from name like '2023-2024', take the first year
        try:
            year_number = int(fy_doc.name.split("-")[0])
        except:
            frappe.throw(f"Could not determine year number for Fiscal Year: {fiscal_year_name}")

    return {
        "name": fy_doc.name,
        "year": year_number,
        "year_start_date": fy_doc.year_start_date,
        "year_end_date": fy_doc.year_end_date
    }

def get_address_detail(address_name=None, party_type=None, party_name=None, is_primary=1, address_type="Billing"):
    """Fetches and formats address details based on address name or party linkage."""
    address_doc = None
    if address_name:
        if frappe.db.exists("Address", address_name):
            address_doc = frappe.get_doc("Address", address_name)
    elif party_type and party_name:
        filters = {
            "links.link_doctype": party_type,
            "links.link_name": party_name,
        }
        if is_primary:
            filters["is_primary_address"] = 1 # Check based on actual field name
        if address_type:
             filters["address_type"] = address_type

        addr_name = frappe.db.get_value("Address", filters, "name")
        if addr_name:
            address_doc = frappe.get_doc("Address", addr_name)
        elif is_primary: # If primary not found, try any linked address
             filters.pop("is_primary_address", None)
             addr_name = frappe.db.get_value("Address", filters, "name")
             if addr_name:
                  address_doc = frappe.get_doc("Address", addr_name)

    if not address_doc:
        return None, None, None, None, None

    # Combine address lines for AddressDetail, handling None values
    addr_line1 = address_doc.address_line1 or ''
    addr_line2 = address_doc.address_line2 or ''
    addr_detail = f"{addr_line1} {addr_line2}".strip()
    city = address_doc.city
    postal_code = address_doc.pincode
    region = address_doc.state # Assuming state holds the region
    country = address_doc.country

    return addr_detail, city, postal_code, region, country

def get_country_code(country_name):
    """Gets the 2-letter ISO 3166-1 alpha-2 country code."""
    if not country_name:
        return None
    # Frappe stores country name, SAF-T needs code
    code = frappe.db.get_value("Country", {"name": country_name}, "code")
    return code.upper() if code else None

def get_party_account(party_name, party_type, company):
    """Find the default receivable/payable account for the party in the given company."""
    account_field = "default_receivable_account" if party_type == "Customer" else "default_payable_account"
    default_account = frappe.db.get_value(party_type, party_name, account_field)
    if default_account:
        return default_account

    # Fallback: Check linked Party Account for the specific company
    linked_account = frappe.db.get_value("Party Account", {
        "parent": party_name,
        "parenttype": party_type,
        "company": company
    }, "account")
    return linked_account

def format_currency(value, decimals=2):
    """Formats a float/Decimal value to a string with fixed decimal places for SAF-T."""
    if value is None:
        zero_str = '0' * decimals
        return f"0.{zero_str}"
    try:
        # Ensure it's treated as a number, round appropriately
        num_value = float(value)
        format_spec = f":.{decimals}f"
        return f"{num_value:{format_spec}}"
    except (ValueError, TypeError):
        zero_str = '0' * decimals
        return f"0.{zero_str}"


# ... (keep existing utility functions: format_date, format_datetime, etc.) ...

def get_atcud(doc_series_code, doc_type_at_code, doc_posting_date, doc_sequential_number):
    """Constructs the ATCUD string for a given document."""
    if not doc_series_code or not doc_type_at_code or not doc_posting_date or doc_sequential_number is None:
        frappe.log_error("Missing data for ATCUD generation", f"Series: {doc_series_code}, Type: {doc_type_at_code}, Date: {doc_posting_date}, Number: {doc_sequential_number}")
        return None # Or raise error

    # Determine the fiscal year based on the document's posting date
    fiscal_year = frappe.db.get_value("Fiscal Year", {
        "year_start_date": ("<=", doc_posting_date),
        "year_end_date": (">=", doc_posting_date)
    }, "name")

    if not fiscal_year:
        frappe.log_error("Could not determine Fiscal Year for ATCUD", f"Date: {doc_posting_date}")
        return None # Or raise error

    # Get the validation code from the communicated series
    validation_code = frappe.db.get_value("Document Series PT", {
        "series_code": doc_series_code,
        "document_type": doc_type_at_code,
        "fiscal_year": fiscal_year,
        "communication_status": "Communicated"
    }, "at_validation_code")

    if not validation_code:
        # Log the error, but might still proceed without ATCUD depending on requirements
        frappe.log_error("AT Validation Code not found for ATCUD", f"Series: {doc_series_code}, Type: {doc_type_at_code}, FY: {fiscal_year}")
        # Depending on strictness, could return None or raise an error
        # frappe.throw(_("Series {0} for document type {1} and fiscal year {2} has not been successfully communicated to AT.").format(doc_series_code, doc_type_at_code, fiscal_year))
        return "ValidationCodeNotFound"

    # Construct ATCUD: ValidationCode-SequentialNumber
    atcud = f"{validation_code}-{doc_sequential_number}"
    return atcud

def get_sequential_number_from_name(doc_name, series_prefix):
    """
    Extracts the sequential number from a document name using its naming series prefix.
    Ensures the result is a string to preserve leading zeros (needed for ATCUD).
    """
    if not doc_name or not series_prefix:
        return None

    try:
        # Escape series prefix for regex pattern
        escaped_prefix = re.escape(series_prefix)
        pattern_string = f"^{escaped_prefix}(\\d+)$"
        match = re.match(pattern_string, doc_name)

        if match:
            return match.group(1)  # return as string (with leading zeros)

        # Fallback: try to extract numeric tail after last dash or slash
        number_match = re.search(r"(\d+)$", doc_name)
        if number_match:
            return number_match.group(1)

        frappe.log_error("Could not extract sequential number", f"Name: {doc_name}, Prefix: {series_prefix}")
        return None

    except Exception as e:
        frappe.log_error(f"Error extracting sequential number: {e}", f"Name: {doc_name}, Prefix: {series_prefix}")
        return None


def validate_taxonomy_codes(accounts=None):
    """
    Checks if all accounts have a custom taxonomy code mapped.
    Returns a list of accounts missing the mapping.
    """
    if not accounts:
        accounts = frappe.get_all("Account", filters={"disabled": 0}, fields=["name", "custom_taxonomy_code"])

    missing = [acc.name for acc in accounts if not acc.custom_taxonomy_code]
    if missing:
        frappe.log_error("\n".join(missing), "Accounts missing taxonomy codes")
    return missing


def validate_customer_tax_id():
    """
    Validates that all active customers have a proper NIF (tax_id).
    Returns list of invalid customer names.
    """
    customers = frappe.get_all("Customer", filters={"disabled": 0}, fields=["name", "tax_id"])
    invalids = []

    for cust in customers:
        tax_id = cust.tax_id or ""
        # Accept 9 digits or default consumer code
        if not tax_id.isdigit() or len(tax_id) != 9:
            invalids.append(cust.name)
        elif tax_id == "000000000":
            invalids.append(cust.name)

    if invalids:
        frappe.log_error("\n".join(invalids), "Customers with invalid NIF")
    return invalids


def get_invoice_reference_data(credit_note_doc):
    """
    Extracts reference data for a credit note: links it to the original invoice.
    Assumes credit note includes a link via 'return_against' or similar custom field.
    """
    if not credit_note_doc or not credit_note_doc.get("return_against"):
        return None

    ref_invoice = frappe.get_doc("Sales Invoice", credit_note_doc.return_against)
    return {
        "InvoiceNo": ref_invoice.name,
        "InvoiceDate": ref_invoice.posting_date,
        "ATCUD": ref_invoice.get("custom_atcud"),
        "Hash": ref_invoice.get("custom_digital_signature")
    }

def run_saft_precheck(company):
    """
    Runs a full precheck of SAF-T requirements for a given company.
    Includes validations for:
      - Taxonomy codes on accounts
      - Valid NIFs on customers
      - Series settings (ATCUD) (optional: add later)
    Returns a dictionary with results and any problems found.
    """
    from frappe.utils import get_url

    summary = {
        "company": company,
        "taxonomy_issues": [],
        "customer_nif_issues": [],
        "status": "OK"
    }

    # Validate account taxonomy codes
    accounts = frappe.get_all("Account", filters={"company": company}, fields=["name", "custom_taxonomy_code"])
    missing_taxonomies = validate_taxonomy_codes(accounts)
    if missing_taxonomies:
        summary["taxonomy_issues"] = missing_taxonomies
        summary["status"] = "WARNING"

    # Validate customer NIFs
    bad_nifs = validate_customer_tax_id()
    if bad_nifs:
        summary["customer_nif_issues"] = bad_nifs
        summary["status"] = "WARNING"

    # Optional: Check if ATCUD series are communicated
    # (future enhancement — link to Document Series PT table)

    if summary["status"] == "WARNING":
        frappe.msgprint({
            "title": _("SAF-T Precheck Warnings"),
            "message": _("Some issues were found. Please review before generating SAF-T."),
            "indicator": "orange"
        })
    else:
        frappe.msgprint({
            "title": _("SAF-T Precheck Complete"),
            "message": _("All checks passed successfully."),
            "indicator": "green"
        })

    return summary

# ... (keep other existing utility functions) ...


