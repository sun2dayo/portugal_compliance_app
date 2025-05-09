# Copyright (c) 2024, Your Company Name and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class PortugalComplianceSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        at_password: DF.Password | None
        at_username: DF.Data | None
        at_webservice_url_saft: DF.Data | None
        at_webservice_url_series: DF.Data | None
        certificate_password: DF.Password | None
        certificate_pfx_path: DF.Data | None
        client_chain_pem_path: DF.Data | None
        client_key_pem_path: DF.Data | None
        company_nif: DF.Data | None
        saft_product_company_tax_id: DF.Data | None
        saft_product_version: DF.Data | None
        saft_software_validation_number: DF.Data | None
        software_producer_nif: DF.Data | None
    # end: auto-generated types
    pass

