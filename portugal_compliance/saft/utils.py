# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.utils import formatdate, now_datetime, cstr

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
    addr_detail = f"{address_doc.address_line1 or \'\'} {address_doc.address_line2 or \'\'}".strip()
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
        return f"0.{'0' * decimals}"
    try:
        # Ensure it's treated as a number, round appropriately
        num_value = float(value)
        return f"{num_value:.{decimals}f}"
    except (ValueError, TypeError):
        return f"0.{'0' * decimals}"


# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import re

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
    """Extracts the sequential number from a document name based on its series prefix."""
    if not doc_name or not series_prefix:
        return None
    try:
        # Basic assumption: prefix ends with non-digit, followed by digits
        # Example: FT/2025/A/00001 -> prefix = FT/2025/A/
        # More robust: Use Naming Series format if available
        match = re.match(f"^{re.escape(series_prefix)}(\d+)$".replace('\\.', '.'), doc_name) # Allow '.' in prefix
        if match:
            return int(match.group(1))
        else:
            # Fallback: try splitting by '/' and taking the last part if it's numeric
            parts = doc_name.split('/')
            if parts and parts[-1].isdigit():
                return int(parts[-1])
            else:
                frappe.log_error("Could not extract sequential number", f"Name: {doc_name}, Prefix: {series_prefix}")
                return None
    except Exception as e:
        frappe.log_error(f"Error extracting sequential number: {e}", f"Name: {doc_name}, Prefix: {series_prefix}")
        return None

# ... (keep other existing utility functions) ...

