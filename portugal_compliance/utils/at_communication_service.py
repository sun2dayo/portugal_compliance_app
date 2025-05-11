# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from zeep import Client, Settings, Transport
from zeep.exceptions import Fault
from zeep.wsse.username import UsernameToken
import os

# Import for Compliance Audit Log
from ..doctype.compliance_audit_log.compliance_audit_log import create_compliance_log

class ATCommunicationService:
    def __init__(self):
        self.settings_doc = frappe.get_single("Portugal Compliance Settings")
        self.series_wsdl_url = self.settings_doc.at_series_communication_endpoint
        self.username = self.settings_doc.at_username
        self.password = self.settings_doc.get_password("at_password")
        self.http_proxy = self.settings_doc.http_proxy
        self.https_proxy = self.settings_doc.https_proxy

        if not self.series_wsdl_url or not self.username or not self.password:
            msg = _("AT Communication credentials or Series WSDL endpoint not configured in Portugal Compliance Settings.")
            frappe.throw(msg)
            create_compliance_log("Error", "Portugal Compliance Settings", self.settings_doc.name, details=msg)

        # Configure proxies if set
        proxies = {}
        if self.http_proxy:
            proxies["http"] = self.http_proxy
        if self.https_proxy:
            proxies["https"] = self.https_proxy
        
        transport = Transport(proxies=proxies) if proxies else Transport()
        
        # Zeep settings - consider strict=False if WSDL has minor issues, but strict=True is safer
        zeep_settings = Settings(strict=True, xml_huge_tree=True)
        
        # WSSE UsernameToken for authentication
        wsse = UsernameToken(self.username, self.password, use_digest=False) # AT typically uses plain password over HTTPS

        try:
            self.series_client = Client(self.series_wsdl_url, wsse=wsse, transport=transport, settings=zeep_settings)
            # You might need to specify the service and port if the WSDL has multiple
            # self.series_service = self.series_client.service.YourSeriesServiceNameSoap11 # Adjust as per WSDL
        except Exception as e:
            msg = _("Failed to initialize AT Series Communication client: {0}").format(e)
            frappe.log_error(frappe.get_traceback(), "AT Communication Service Init")
            create_compliance_log("Error", "Portugal Compliance Settings", self.settings_doc.name, details=msg)
            frappe.throw(msg)

    def register_series(self, series_data):
        """
        Communicates a new document series to AT.
        series_data should be a dictionary matching the expected input structure of the AT webservice.
        Example series_data structure (needs to be confirmed with actual WSDL):
        {
            "serie": "A",
            "tipoDoc": "FT",
            "numInicial": "1",
            "numFinal": "999999",
            "dataInicioPrevistaUtil": "2025-01-01",
            "meioProcessamento": "PF" # Programa de Faturação
            # ... other fields as required by AT
        }
        Returns the validation code from AT or raises an exception.
        """
        try:
            # The method name (e.g., "RegistaSerie") and parameter names must match the WSDL
            # response = self.series_service.RegistaSerie(**series_data) # Adjust method and parameters
            
            # Placeholder for actual call - replace with correct method and parameters from WSDL
            # This is a MOCK response structure, replace with actual structure from AT
            # response = self.series_client.service.RegistaSerie(
            #     serie=series_data.get("serie"),
            #     tipoDoc=series_data.get("tipoDoc"),
            #     numInicial=series_data.get("numInicial"),
            #     numFinal=series_data.get("numFinal"),
            #     dataInicioPrevistaUtil=series_data.get("dataInicioPrevistaUtil"),
            #     meioProcessamento=series_data.get("meioProcessamento")
            # )

            # --- MOCK IMPLEMENTATION --- 
            # This section needs to be replaced with the actual SOAP call using self.series_client.service
            # For now, simulate a successful response for development purposes
            frappe.log_info(f"MOCK AT Series Registration Call for: {series_data}", "AT Communication")
            if series_data.get("serie") == "FAIL": # For testing error handling
                raise Fault(message="Simulated AT Error: Invalid Series Data", code="Client.ValidationError")
            
            mock_validation_code = f"MOCK_VALID_{frappe.generate_hash(length=8).upper()}"
            response_message = f"Serie {series_data.get('serie')} comunicada com sucesso."
            # --- END MOCK IMPLEMENTATION ---

            # Assuming response has attributes like 'codValidacao' and 'mensagem'
            # validation_code = response.codValidacao
            # message = response.mensagem
            validation_code = mock_validation_code # MOCK
            message = response_message # MOCK

            create_compliance_log(
                "AT Series Communication", 
                "Document Series PT", 
                series_data.get("serie"), # Assuming series_code is part of series_data or passed differently
                details=f"Series registration successful. Validation Code: {validation_code}. Message: {message}"
            )
            return validation_code, message

        except Fault as f:
            error_details = f"SOAP Fault during series registration for {series_data.get('serie')}: {f.message} (Code: {f.code})"
            frappe.log_error(error_details, "AT Communication Service")
            create_compliance_log(
                "AT Series Communication Error", 
                "Document Series PT", 
                series_data.get("serie"),
                details=error_details
            )
            frappe.throw(_("AT Communication Error: {0}").format(f.message))
        except Exception as e:
            error_details = f"Error during series registration for {series_data.get('serie')}: {e}"
            frappe.log_error(frappe.get_traceback(), "AT Communication Service")
            create_compliance_log(
                "AT Series Communication Error", 
                "Document Series PT", 
                series_data.get("serie"),
                details=error_details
            )
            frappe.throw(_("An unexpected error occurred during AT series communication: {0}").format(e))

    # Add other methods for AnulaSerie, ConsultaSerie as needed, following a similar pattern.

# Whitelisted function to be called from client-side scripts (e.g., from Document Series PT doctype)
@frappe.whitelist()
def communicate_serie_to_at(doc_series_name):
    try:
        series_doc = frappe.get_doc("Document Series PT", doc_series_name)
        
        # Prepare data for AT webservice from series_doc
        # This mapping needs to be precise according to AT requirements
        series_data_for_at = {
            "serie": series_doc.name, # Assuming series name is the code
            "tipoDoc": series_doc.document_type_at_code, # Ensure this field exists and is correct
            "numInicial": str(series_doc.starting_no),
            "numFinal": str(series_doc.ending_no), # This might not be required by AT, or might be a large default
            "dataInicioPrevistaUtil": series_doc.valid_from.strftime("%Y-%m-%d"), # Ensure field exists
            "meioProcessamento": "PF" # Programa de Faturação (Software)
            # Add any other required fields from series_doc
        }

        at_service = ATCommunicationService()
        validation_code, message = at_service.register_series(series_data_for_at)

        # Update Document Series PT with validation code and status
        series_doc.custom_at_validation_code = validation_code
        series_doc.custom_series_status_at = "Comunicada"
        series_doc.save(ignore_permissions=True) # Save with system permissions

        frappe.msgprint(_("Series {0} communicated successfully to AT. Validation Code: {1}").format(doc_series_name, validation_code))
        return {"status": "success", "validation_code": validation_code, "message": message}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Communicate Series to AT API")
        # Update status in Document Series PT to reflect error
        try:
            series_doc = frappe.get_doc("Document Series PT", doc_series_name)
            series_doc.custom_series_status_at = "Erro na Comunicação"
            series_doc.save(ignore_permissions=True)
        except Exception as e_save:
            frappe.log_error(f"Failed to update series status after communication error: {e_save}", "Communicate Series to AT API")
            
        frappe.throw(_("Failed to communicate series to AT: {0}").format(e))

