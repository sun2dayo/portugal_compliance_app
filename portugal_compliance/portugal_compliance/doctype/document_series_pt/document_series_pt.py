# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import requests # For AT communication
import json

class DocumentSeriesPT(Document):
	def validate(self):
		# TODO: Add validation logic, e.g., ensure start_number is positive
		pass

	def before_save(self):
		# Ensure series code is uppercase or follows a specific format if needed
		# self.series_code = self.series_code.upper()
		pass

	@frappe.whitelist()
	def communicate_series_to_at(self):
		"""Communicates the document series details to the AT webservice."""
		# Check permissions
			 if not frappe.has_permission(self.doctype, "write"):
				 frappe.throw(_("Not permitted to communicate series"), frappe.PermissionError)

		 settings = frappe.get_single("Portugal Compliance Settings")
		 at_username = settings.at_username
		 at_password = settings.get_password("at_password")

		 if not at_username or not at_password:
			 frappe.throw(_("AT communication credentials not set in Portugal Compliance Settings."))

		 # TODO: Replace with actual AT webservice endpoint and payload structure
		 at_endpoint = "https://servicos.portaldasfinancas.gov.pt/seriestws/communicateSeries" # Placeholder URL

		 payload = {
			 "series": self.series_code,
			 "class": self.document_type, # Assuming document_type holds the AT class code (e.g., "FT")
			 "type": "N", # Assuming 'N' for Normal type, adjust as needed
			 "num": self.start_number,
			 "date": frappe.get_doc("Fiscal Year", self.fiscal_year).year_start_date.strftime("%Y-%m-%d"),
			 "seq": "", # Optional sequence number if multiple series communicated at once
			 "just": "" # Justification if needed
		 }

		 headers = {
			 "Content-Type": "application/json" # Or SOAPAction if it's SOAP
			 # Add Authentication headers (e.g., Basic Auth, OAuth)
			 # "Authorization": "Basic " + base64.b64encode(f"{at_username}:{at_password}".encode()).decode()
		 }

		 try:
			 # This is a placeholder request. Actual implementation needs correct endpoint, method, auth, and payload.
			 response = requests.post(at_endpoint, json=payload, headers=headers, auth=(at_username, at_password), timeout=30)
			 response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)

			 response_data = response.json() # Assuming JSON response

			 # TODO: Parse the actual response structure from AT
			 if response_data.get("result") == "success" and response_data.get("validationCode"):
				 self.at_validation_code = response_data["validationCode"]
				 self.communication_status = "Communicated"
				 self.last_communicated_on = frappe.utils.now_datetime()
				 self.save()
				 frappe.msgprint(_("Series {0} communicated successfully. Validation Code: {1}").format(self.series_code, self.at_validation_code), indicator="green")
			 else:
				 self.communication_status = "Error"
				 self.save()
				 error_msg = response_data.get("error_message", "Unknown error from AT.")
				 frappe.throw(_("Failed to communicate series to AT: {0}").format(error_msg))

		 except requests.exceptions.RequestException as e:
			 self.communication_status = "Error"
			 self.save()
			 frappe.log_error(frappe.get_traceback(), "AT Series Communication Error")
			 frappe.throw(_("Error communicating with AT webservice: {0}").format(str(e)))
		 except Exception as e:
			 self.communication_status = "Error"
			 self.save()
			 frappe.log_error(frappe.get_traceback(), "AT Series Communication Error")
			 frappe.throw(_("An unexpected error occurred during AT communication: {0}").format(str(e)))

# Helper function to get validation code for a given series and document type
# This might be called by documents (e.g., Sales Invoice) before generating ATCUD
@frappe.whitelist()
def get_series_validation_code(series_code, document_type, fiscal_year):
    # Add caching later if needed
    validation_code = frappe.db.get_value("Document Series PT", 
                                        {"series_code": series_code, 
                                         "document_type": document_type, 
                                         "fiscal_year": fiscal_year, 
                                         "communication_status": "Communicated"}, 
                                        "at_validation_code")
    if not validation_code:
        # Optionally, try to communicate it automatically here, or raise an error
        frappe.throw(_("Series {0} for document type {1} and fiscal year {2} has not been successfully communicated to AT.").format(series_code, document_type, fiscal_year))
    return validation_code

