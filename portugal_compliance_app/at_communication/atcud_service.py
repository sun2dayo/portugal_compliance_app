import frappe
from frappe.utils import cint, cstr, now_datetime, get_datetime
from lxml import etree
from lxml.etree import QName # Added from standalone
from zeep import Client, Settings, Transport
from zeep.wsse.username import UsernameToken
from zeep.exceptions import Fault
import os
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import base64
import datetime
import json # Added from standalone for potential debugging

# --- Constants and Configuration ---
def get_portugal_compliance_settings():
    """Get settings from Portugal Compliance Settings DocType."""
    settings = frappe.get_single("Portugal Compliance Settings")
    return settings

def get_portugal_compliance_paths():
    """Get secure paths to certificates and WSDL from Portugal Compliance Settings."""
    settings = get_portugal_compliance_settings()
    usar_personalizado = settings.usar_wsdl_personalizado

    wsdl_path = (
        settings.wsdl_path
        if usar_personalizado
        else frappe.get_app_path("portugal_compliance", "wsdl", "Comunicacao_Series.wsdl")
    )

    # Paths for PEM certificate chain and private key
    # These fields (client_chain_pem_path, client_key_pem_path) would need to be added to 
    # the "Portugal Compliance Settings" DocType in ERPNext.
    client_chain_pem_path = settings.get("client_chain_pem_path", "/tmp/client_chain.pem") # Default for testing if not set
    client_key_pem_path = settings.get("client_key_pem_path", "/tmp/client_key.pem")     # Default for testing if not set

    return {
        "client_chain_pem_path": client_chain_pem_path,
        "client_key_pem_path": client_key_pem_path,
        "at_public_key_path": settings.at_public_key_path,
        "endpoint_url": settings.endpoint_url,
        "wsdl_path": wsdl_path
    }

# --- Helper Functions (largely from standalone, adapted for Frappe) ---

def get_at_public_key(paths):
    """Loads the AT's public key from the .cer file specified in paths."""
    # paths = get_portugal_compliance_paths() # Called by the caller now
    with open(paths["at_public_key_path"], "rb") as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )
    return public_key

def encrypt_password_with_at_public_key(password, paths):
    """Encrypts the password using AT's public key (RSA OAEP)."""
    public_key = get_at_public_key(paths)
    encrypted_password = public_key.encrypt(
        password.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None
        )
    )
    return base64.b64encode(encrypted_password).decode("utf-8")

# Using CustomUsernameToken from the standalone script (it's more debugged)
class CustomUsernameToken(UsernameToken):
    def __init__(self, username, password=None, password_digest=None, nonce=None, created=None, use_digest=False, **kwargs):
        self._custom_nonce = nonce # Store the binary nonce
        # The actual password encryption will be done using a passed-in 'paths' dictionary
        # to resolve AT_PUBLIC_KEY_PATH within the Frappe context.
        self.raw_password = password # Store raw password for encryption within apply or by caller
        self.paths_for_encryption = kwargs.pop('paths_for_encryption', None)
        super().__init__(username, password, password_digest, nonce, created, use_digest, **kwargs)
        # Defer encryption to apply or ensure it's done before passing to super if needed by zeep's UsernameToken
        if self.raw_password and not use_digest and self.paths_for_encryption:
             self.encrypted_password_for_at = encrypt_password_with_at_public_key(self.raw_password, self.paths_for_encryption)
        else:
            self.encrypted_password_for_at = self.raw_password # Or handle error if paths not provided

    def apply(self, envelope, headers):
        wsse_ns = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
        wsu_ns = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"

        security_header = etree.Element(QName(wsse_ns, "Security"), nsmap={"wsse": wsse_ns, "wsu": wsu_ns})
        security_header.set(QName("http://schemas.xmlsoap.org/soap/envelope/", "mustUnderstand"), "1")

        timestamp = etree.SubElement(security_header, QName(wsu_ns, "Timestamp"))
        current_time = self.created
        if not isinstance(current_time, datetime.datetime):
            current_time = datetime.datetime.utcnow() # Fallback if created is not a datetime object
        
        created_str = current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        expires_str = (current_time + datetime.timedelta(seconds=300)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        etree.SubElement(timestamp, QName(wsu_ns, "Created")).text = created_str
        etree.SubElement(timestamp, QName(wsu_ns, "Expires")).text = expires_str

        token = etree.SubElement(security_header, QName(wsse_ns, "UsernameToken"))
        etree.SubElement(token, QName(wsse_ns, "Username")).text = self.username
        
        password_node = etree.SubElement(token, QName(wsse_ns, "Password"))
        # Use the pre-encrypted password
        password_node.text = self.encrypted_password_for_at 
        password_node.set("Type", "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#PasswordText")

        if self._custom_nonce: # self._custom_nonce should be binary
            nonce_node = etree.SubElement(token, QName(wsse_ns, "Nonce"))
            nonce_node.text = base64.b64encode(self._custom_nonce).decode("utf-8")
            nonce_node.set("EncodingType", "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary")
        
        # Critical change from standalone for Zeep compatibility with dict headers
        headers["Security"] = etree.tostring(security_header).decode("utf-8")
        return envelope, headers

def get_soap_client(username, password):
    """Initializes and returns the Zeep SOAP client with WS-Security."""
    paths = get_portugal_compliance_paths()

    settings = Settings(strict=False, xml_huge_tree=True, force_https=False) # force_https=False for local WSDL if used
    transport = Transport(timeout=60) # Increased timeout from standalone
    
    # Use PEM certificate chain and private key paths
    transport.client_cert = (paths["client_chain_pem_path"], paths["client_key_pem_path"])

    current_nonce_bytes = os.urandom(16) # Binary nonce
    # Pass paths for encryption context to CustomUsernameToken
    wsse = CustomUsernameToken(username, password, nonce=current_nonce_bytes, created=datetime.datetime.utcnow(), paths_for_encryption=paths)

    client = Client(paths["wsdl_path"], settings=settings, transport=transport, wsse=wsse)
    service = client.bind("SeriesWSService", "SeriesWSPort")
    service._binding_options["address"] = paths["endpoint_url"]

    return service # Return the service proxy directly


# --- API Functions (to be called from ERPNext hooks or UI) ---

@frappe.whitelist()
def register_serie_at(serie_details_json):
    """Registers a new document series with AT.
       serie_details_json: A JSON string containing series data.
       Expected keys: serie, tipo_serie, classe_doc, tipo_doc, 
                      num_prim_doc_serie, data_inicio_prev_utiliz, 
                      num_cert_sw_fatur, [meio_processamento]
    """
    try:
        serie_data = json.loads(serie_details_json)
    except json.JSONDecodeError as e:
        frappe.log_error(title="ATCUD Registration JSON Error", message=str(e))
        frappe.throw(f"Invalid JSON format for series details: {e}")
        return # Should not reach here due to throw

    # Fetch username/password from ERPNext settings
    settings = get_portugal_compliance_settings()
    at_username = settings.at_subuser_username
    at_password = settings.get_password("at_subuser_password") # Use get_password for encrypted fields

    if not at_username or not at_password:
        frappe.throw("AT Subuser credentials not configured in Portugal Compliance Settings.")

    client_service = get_soap_client(at_username, at_password)

    # Prepare request data, ensuring correct types
    try:
        request_data = {
            "serie": cstr(serie_data["serie"]),
            "tipoSerie": cstr(serie_data["tipo_serie"]),
            "classeDoc": cstr(serie_data["classe_doc"]),
            "tipoDoc": cstr(serie_data["tipo_doc"]),
            "numPrimDocSerie": cint(serie_data["num_prim_doc_serie"]),
            # Ensure dataInicioPrevUtiliz is a date object for the SOAP call if WSDL expects date
            # Zeep usually handles Python date/datetime to XSD date/dateTime conversion.
            "dataInicioPrevUtiliz": get_datetime(serie_data["data_inicio_prev_utiliz"]).date(), 
            "numCertSWFatur": cint(serie_data["num_cert_sw_fatur"])
        }
        if "meio_processamento" in serie_data and serie_data["meio_processamento"]:
            request_data["meioProcessamento"] = cstr(serie_data["meio_processamento"])
    except KeyError as e:
        frappe.throw(f"Missing key in series details: {e}")
        return
    except Exception as e: # Catch other potential errors during data prep
        frappe.log_error(title="ATCUD Data Preparation Error", message=str(e))
        frappe.throw(f"Error preparing data for AT communication: {e}")
        return

    try:
        frappe.log_info(f"Sending ATCUD request to AT: {request_data}", "ATCUD Communication")
        response = client_service.registarSerie(**request_data)
        frappe.log_info(f"Received ATCUD response from AT: {response}", "ATCUD Communication")

        if response and hasattr(response, "InfoSerie") and response.InfoSerie and hasattr(response.InfoSerie, "codValidacaoSerie") and response.InfoSerie.codValidacaoSerie:
            atcud = response.InfoSerie.codValidacaoSerie
            # Log success and ATCUD
            frappe.msgprint(f"Série {serie_data['serie']} registada com sucesso. ATCUD: {atcud}")
            return {"status": "success", "atcud": atcud, "response_raw": str(response)}
        elif response and hasattr(response, "listaErros") and response.listaErros and response.listaErros.Erro:
            errors = [{"code": err.codErro, "message": err.msgErro} for err in response.listaErros.Erro]
            frappe.log_error(title="AT Series Registration Error", message=str(errors))
            # Present a more user-friendly error
            error_messages = "\n".join([f"- {err.msgErro} (Código: {err.codErro})" for err in response.listaErros.Erro])
            frappe.throw(title="Erro ao Registar Série na AT", msg=f"Ocorreram os seguintes erros:\n{error_messages}")
            return {"status": "error", "errors": errors, "response_raw": str(response)} # Should not reach due to throw
        else:
            frappe.log_error(title="AT Series Registration Unexpected Response", message=str(response))
            frappe.throw("Resposta inesperada da AT ao registar série.")
            return {"status": "error", "message": "Unexpected response structure from AT.", "response_raw": str(response)} # Should not reach
    except Fault as f:
        frappe.log_error(title="AT Series Registration SOAP Fault", message=f"{f.message}\nDetail: {f.detail}")
        frappe.throw(f"Erro de comunicação SOAP com a AT: {f.message}")
        return {"status": "error", "message": f"SOAP Fault: {f.message}", "details": str(f.detail) if f.detail else None} # Should not reach
    except Exception as e:
        frappe.log_error(title="AT Series Registration Exception", message=frappe.get_traceback())
        frappe.throw(f"Erro durante a comunicação com a AT: {e}")
        return {"status": "error", "message": f"Generic Exception: {e}"} # Should not reach

# Placeholder for other functions from user's original atcud_service.py if needed
# def consult_series_at(serie_code): ...
# def finalize_serie_at(serie_code): ...

if __name__ == "__main__":
    # This part is for direct testing outside Frappe, similar to test_atcud_standalone.py
    # It requires manual setup of paths and credentials if not running in Frappe context.
    print("--- Starting Standalone-Style Test for AT Series Registration (within atcud_service.py) ---")
    
    # Mock frappe for local testing if needed, or ensure settings are accessible
    # For this example, we'll use hardcoded paths similar to the original standalone
    # THIS IS FOR LOCAL TESTING ONLY. In Frappe, paths come from settings.
    class MockFrappeDB:
        def get_single_value(self, doctype, fieldname, cache=None):
            if doctype == "Portugal Compliance Settings":
                if fieldname == "client_chain_pem_path": return "/tmp/client_chain.pem"
                if fieldname == "client_key_pem_path": return "/tmp/client_key.pem"
                if fieldname == "at_public_key_path": return "/home/ubuntu/at_credentials/AT_PublicKey.pem" # Adjust if different
                if fieldname == "endpoint_url": return "https://servicos.portaldasfinancas.gov.pt:422/SeriesWSService"
                if fieldname == "wsdl_path": return "/home/ubuntu/at_credentials/Comunicacao_Series.wsdl" # Adjust if different
                if fieldname == "at_subuser_username": return "518747832/1" # Test username
            return None
        def get_password(self, doctype, fieldname, dn=None, raise_exception=True):
             if doctype == "Portugal Compliance Settings" and fieldname == "at_subuser_password":
                return "t.6qaff8ig2T?Ph" # Test password
             return None

    class MockFrappe:
        def __init__(self):
            self.db = MockFrappeDB()
            self.app_path = "/tmp"
        def get_app_path(self, app_name, *args):
            return os.path.join(self.app_path, *args)
        def get_single(self, doctype):
            # Simplified mock for get_single
            if doctype == "Portugal Compliance Settings":
                mock_settings = {
                    "usar_wsdl_personalizado": False, # Or True based on your test case
                    "wsdl_path": "/home/ubuntu/at_credentials/Comunicacao_Series.wsdl",
                    "client_chain_pem_path": "/tmp/client_chain.pem",
                    "client_key_pem_path": "/tmp/client_key.pem",
                    "at_public_key_path": "/home/ubuntu/at_credentials/AT_PublicKey.pem",
                    "endpoint_url": "https://servicos.portaldasfinancas.gov.pt:422/SeriesWSService",
                    "at_subuser_username": "518747832/1",
                    "get_password": lambda field: "t.6qaff8ig2T?Ph" if field == "at_subuser_password" else None
                }
                # Make it behave somewhat like a Doc object for attribute access
                class MockSettingsDoc:
                    def __init__(self, data):
                        self.__dict__.update(data)
                    def get(self, key, default=None):
                        return self.__dict__.get(key, default)
                    def get_password(self, fieldname):
                         return self.__dict__.get('get_password')(fieldname)
                return MockSettingsDoc(mock_settings)
            return None
        def whitelist(self, fn):
            return fn # Decorator passthrough
        def log_error(self, message, title="Error"):
            print(f"LOG ERROR ({title}): {message}")
        def log_info(self, message, title="Info"):
            print(f"LOG INFO ({title}): {message}")
        def throw(self, msg, title="Error"):
            print(f"THROW ({title}): {msg}")
            raise Exception(msg)
        def msgprint(self, msg):
            print(f"MSGPRINT: {msg}")

    # Replace frappe with mock for local testing
    # frappe = MockFrappe() # Uncomment to run __main__ locally

    if hasattr(frappe, 'db') and isinstance(frappe.db, MockFrappeDB): # Check if mock is active
        print("Running with MOCKED Frappe environment for local test.")
        test_serie_data = {
            "serie": "TESTMANUS04",
            "tipo_serie": "N",
            "classe_doc": "FT",
            "tipo_doc": "FT",
            "num_prim_doc_serie": 1,
            "data_inicio_prev_utiliz": "2025-08-01",
            "num_cert_sw_fatur": 0, # Using 0 as per standalone
            "meio_processamento": "ERPNext Manus App Test v1"
        }
        result = register_serie_at(json.dumps(test_serie_data))
        print("--- Test Result (within atcud_service.py) ---")
        print(json.dumps(result, indent=4, default=str))
    else:
        print("This script is intended to be used within the Frappe framework or with a local mock.")
    print("--- Standalone-Style Test Finished (within atcud_service.py) ---")

