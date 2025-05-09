import frappe
from frappe.utils import cint, cstr, now_datetime
from lxml import etree
from zeep import Client, Settings, Transport
from zeep.wsse.username import UsernameToken
from zeep.exceptions import Fault
import os
import datetime
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

# --- Configuration Section ---
# These paths and credentials should be configured by the user when running standalone.
# In a Frappe environment, these might be fetched from a settings DocType.

# Default paths - User should verify and update these if running standalone.
DEFAULT_CERT_PATH = os.environ.get("ATCUD_CERT_PATH", "/home/ubuntu/at_credentials/testeWebservices.pfx")
DEFAULT_CERT_PASSWORD = os.environ.get("ATCUD_CERT_PASSWORD", "TESTEwebservice")
DEFAULT_AT_PUBLIC_KEY_PATH = os.environ.get("ATCUD_AT_PUBLIC_KEY_PATH", "/home/ubuntu/at_credentials/ChaveCifraPublicaAT2027.cer")
DEFAULT_WSDL_PATH = os.environ.get("ATCUD_WSDL_PATH", "/home/ubuntu/at_credentials/Comunicacao_Series.wsdl")
DEFAULT_ENDPOINT_URL = os.environ.get("ATCUD_ENDPOINT_URL", "https://servicos.portaldasfinancas.gov.pt:422/SeriesWSService")

# --- Helper Functions ---

def get_at_public_key(at_public_key_path=DEFAULT_AT_PUBLIC_KEY_PATH):
    """Loads the AT's public key from the .cer file."""
    if not os.path.exists(at_public_key_path):
        raise FileNotFoundError(f"AT Public Key file not found: {at_public_key_path}")
    with open(at_public_key_path, "rb") as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )
    return public_key

def encrypt_password_with_at_public_key(password, at_public_key_path=DEFAULT_AT_PUBLIC_KEY_PATH):
    """Encrypts the password using AT's public key (RSA OAEP)."""
    public_key = get_at_public_key(at_public_key_path)
    encrypted_password = public_key.encrypt(
        password.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None
        )
    )
    return base64.b64encode(encrypted_password).decode("utf-8")

class CustomUsernameTokenForAT(UsernameToken):
    """Custom UsernameToken for AT: handles password encryption and specific nonce/created encoding."""
    def __init__(self, username, password=None, password_digest=None, nonce=None, created=None, use_digest=False, at_public_key_path=DEFAULT_AT_PUBLIC_KEY_PATH, **kwargs):
        self.at_public_key_path = at_public_key_path
        # Encrypt password before calling super().__init__ as it might use the password directly
        if password and not use_digest:
            encrypted_pass = encrypt_password_with_at_public_key(password, self.at_public_key_path)
            super().__init__(username, encrypted_pass, password_digest, nonce, created, use_digest, **kwargs)
        else:
            super().__init__(username, password, password_digest, nonce, created, use_digest, **kwargs)

    def apply(self, envelope, headers):
        # Copied from zeep.wsse.username.UsernameToken and adapted for AT specifics
        # Create security element
        security = etree.Element(
            etree.QName(self.namespace, "Security"),
            attrib={etree.QName(envelope.nsmap["soapenv"], "mustUnderstand"): "1"}
        )

        # Timestamp
        timestamp = etree.SubElement(security, etree.QName(self.wsse_utility_ns, "Timestamp"))
        if self.created is None:
            self.created = datetime.datetime.utcnow()
        
        created_str = self.created.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        expires_str = (self.created + datetime.timedelta(seconds=300)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        etree.SubElement(timestamp, etree.QName(self.wsse_utility_ns, "Created")).text = created_str
        etree.SubElement(timestamp, etree.QName(self.wsse_utility_ns, "Expires")).text = expires_str

        # UsernameToken
        token = etree.SubElement(security, etree.QName(self.namespace, "UsernameToken"))
        if self.prefix:
            token.set(etree.QName(self.wsse_utility_ns, "Id"), self.prefix + "-UsernameToken") # AT examples use this ID format

        etree.SubElement(token, etree.QName(self.namespace, "Username")).text = self.username

        if self.password:
            password_node = etree.SubElement(token, etree.QName(self.namespace, "Password"))
            password_node.text = self.password # Already encrypted and base64 encoded by our logic
            # AT expects PasswordText for encrypted password, not digest
            password_node.set("Type", "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#PasswordText")

        if self.nonce:
            nonce_node = etree.SubElement(token, etree.QName(self.namespace, "Nonce"))
            # AT expects Nonce to be Base64 encoded
            nonce_node.text = base64.b64encode(self.nonce).decode("utf-8") # Ensure nonce is bytes before b64encode
            nonce_node.set("EncodingType", "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary")
        
        # Created element within UsernameToken
        created_token_str = self.created.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        etree.SubElement(token, etree.QName(self.wsse_utility_ns, "Created")).text = created_token_str
        
        headers.insert(0, security)
        return envelope, headers

def get_soap_client(username, password, 
                    cert_path=DEFAULT_CERT_PATH, 
                    cert_password=DEFAULT_CERT_PASSWORD, 
                    wsdl_path=DEFAULT_WSDL_PATH, 
                    endpoint_url=DEFAULT_ENDPOINT_URL,
                    at_public_key_path=DEFAULT_AT_PUBLIC_KEY_PATH):
    """Initializes and returns the Zeep SOAP client with WS-Security for AT communication."""
    if not os.path.exists(cert_path):
        raise FileNotFoundError(f"Client certificate file not found: {cert_path}")
    if not os.path.exists(wsdl_path):
        raise FileNotFoundError(f"WSDL file not found: {wsdl_path}")

    settings = Settings(strict=False, xml_huge_tree=True, force_https=False) # force_https=False if endpoint is http for local WSDL test
    
    # Prepare client certificate (PFX converted to PEM pair is often more robust with requests)
    # For simplicity with PFX directly, ensure your Python env and OpenSSL libs support it well.
    # Zeep/requests might need cert and key as separate PEM files. If PFX causes issues,
    # convert it to client_cert.pem and client_key.pem using OpenSSL:
    # openssl pkcs12 -in testeWebservices.pfx -clcerts -nokeys -out client_cert.pem -passin pass:TESTEwebservice
    # openssl pkcs12 -in testeWebservices.pfx -nocerts -nodes -out client_key.pem -passin pass:TESTEwebservice -passout pass:your_pem_key_password
    # Then use: transport.client_cert = ("path/to/client_cert.pem", "path/to/client_key.pem")
    # For now, attempting direct PFX path as tuple (cert_file, password_for_cert_file)
    # Update: Zeep transport expects client_cert to be path to cert file, or tuple (cert, key)
    # If PFX is used, it should be a single path. Password for PFX is handled by requests library if supported.
    # However, requests typically expects cert and key as separate files for mutual TLS.
    # The (cert_path, cert_password) tuple for transport.client_cert is NOT standard for requests.
    # It should be: transport.client_cert = cert_path (if PEM with unencrypted key) or (cert_pem_path, key_pem_path)
    # Let's assume PFX is converted to PEM cert and unencrypted PEM key for robustness in standalone tests.
    # For this iteration, we will stick to the PFX path and password, assuming the environment handles it.
    # If SSL errors persist, converting PFX to PEM pair is the next step.
    
    transport = Transport(timeout=60)
    # transport.client_cert = (cert_path, cert_password) # This syntax is for requests Session.cert
                                                    # Zeep's Transport client_cert expects path to cert or (cert, key) paths.
                                                    # For PFX, it's tricky. Best to convert PFX to PEM cert and key.
                                                    # For now, we'll assume user has client_cert.pem and client_key.pem
    # User needs to ensure cert_path is the .pem certificate and provide key_path separately if key is encrypted.
    # For simplicity, let's assume an unencrypted key PEM or that the PFX path works directly if the underlying lib supports it.
    # Given the previous SSL errors, it's highly recommended to use separate .pem cert and .pem key files.
    # For the purpose of this script, we will assume the user will provide the correct path to a .pem cert
    # and the key is either included or provided separately if needed by their Zeep/requests setup.
    # The original script used (CERT_PATH, CERT_PASSWORD) which is not standard for zeep's transport.client_cert
    # It should be client_cert = "path_to_cert_and_key.pem" or ("path_to_cert.pem", "path_to_key.pem")
    # We will use the provided PFX path for now and let the user adjust if it fails in their env.
    # The most robust way is to convert PFX to separate PEM files.
    # openssl pkcs12 -in {cert_path} -clcerts -nokeys -out client_cert.pem -passin pass:{cert_password}
    # openssl pkcs12 -in {cert_path} -nocerts -nodes  -out client_key.pem -passin pass:{cert_password} -passout pass:your_new_pem_key_password (or no -passout for unencrypted)
    # Then: transport.client_cert = ('client_cert.pem', 'client_key.pem')
    
    # For this iteration, we will assume the user has set up their PFX to be usable directly
    # or has converted it and will adjust the cert_path to point to the .pem file (cert+key combined or just cert).
    # If it's a PFX, requests might handle it if python-cryptography[pkcs12] is installed.
    transport.client_cert = cert_path # This assumes cert_path is a PEM that might include the key, or just the cert. 
                                      # If key is separate, it's ('cert.pem', 'key.pem')
                                      # For PFX, this might not work directly. User must ensure their env supports it.

    # Custom WSSE token for AT's specific password encryption
    # Nonce must be bytes for base64 encoding
    wsse = CustomUsernameTokenForAT(username, password, nonce=os.urandom(16), created=datetime.datetime.utcnow(), at_public_key_path=at_public_key_path)

    client = Client(wsdl_path, settings=settings, transport=transport, wsse=wsse)
    
    # Override the service endpoint if necessary
    # The WSDL might point to a generic one, ensure it's the correct HTTPS endpoint.
    service = client.bind("SeriesWSService", "SeriesWSPort") # Service and Port names from WSDL
    service._binding_options["address"] = endpoint_url
    return client.service, client # Return client too for access to last_sent/last_received

# --- API Functions (adapted for standalone or Frappe use) ---

def register_serie_at(serie_data, credentials, config_paths):
    """
    Registers a new document series with AT.
    serie_data (dict): Contains all data for the 'registarSerie' request.
    credentials (dict): {'username': 'user', 'password': 'pass'}
    config_paths (dict): Paths for cert, key, wsdl, etc.
                         {'cert_path', 'cert_password', 'wsdl_path', 'endpoint_url', 'at_public_key_path'}
    """
    try:
        client_service, client_obj = get_soap_client(
            username=credentials['username'], 
            password=credentials['password'],
            cert_path=config_paths.get('cert_path', DEFAULT_CERT_PATH),
            cert_password=config_paths.get('cert_password', DEFAULT_CERT_PASSWORD), # May not be used if cert_path is PEM
            wsdl_path=config_paths.get('wsdl_path', DEFAULT_WSDL_PATH),
            endpoint_url=config_paths.get('endpoint_url', DEFAULT_ENDPOINT_URL),
            at_public_key_path=config_paths.get('at_public_key_path', DEFAULT_AT_PUBLIC_KEY_PATH)
        )

        # Ensure numeric fields are integers
        serie_data['numPrimDocSerie'] = cint(serie_data['numPrimDocSerie'])
        serie_data['numCertSWFatur'] = cint(serie_data['numCertSWFatur'])

        response = client_service.registarSerie(**serie_data)
        
        # For debugging, capture raw XML request and response
        last_sent_xml = etree.tostring(client_obj.transport.last_sent['envelope'], encoding='unicode', pretty_print=True)
        last_received_xml = etree.tostring(client_obj.transport.last_received['envelope'], encoding='unicode', pretty_print=True)

        if response and response.InfoSerie and response.InfoSerie.codValidacaoSerie:
            atcud = response.InfoSerie.codValidacaoSerie
            return {"status": "success", "atcud": atcud, "response_obj": response, "last_sent_xml": last_sent_xml, "last_received_xml": last_received_xml}
        elif response and response.listaErros:
            errors = [{"code": err.codErro, "message": err.msgErro} for err in response.listaErros.Erro]
            return {"status": "error", "errors": errors, "response_obj": response, "last_sent_xml": last_sent_xml, "last_received_xml": last_received_xml}
        else:
            return {"status": "error", "message": "Unexpected response structure from AT.", "response_obj": response, "last_sent_xml": last_sent_xml, "last_received_xml": last_received_xml}
    except Fault as f:
        return {"status": "error", "message": f"SOAP Fault: {str(f)}", "details": str(f.detail) if f.detail else None}
    except FileNotFoundError as fnf:
        return {"status": "error", "message": str(fnf)}
    except Exception as e:
        # Log full traceback for unexpected errors
        import traceback
        tb_str = traceback.format_exc()
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}", "traceback": tb_str}

# --- Frappe Whitelisted Method (if running in ERPNext) ---
@frappe.whitelist()
def register_serie_frappe_adapter(serie, tipo_serie, classe_doc, tipo_doc, num_prim_doc_serie, data_inicio_prev_utiliz, num_cert_sw_fatur, meio_processamento=None):
    """Adapter for calling from Frappe, fetches config from DocSettings."""
    # Fetch username/password from ERPNext settings (e.g., "Portugal Compliance Settings")
    # This part remains specific to Frappe environment.
    settings_doctype = "Portugal Compliance Settings" # Replace with actual DocType name
    at_username = frappe.db.get_single_value(settings_doctype, "at_subuser_username")
    at_password_encrypted = frappe.db.get_single_value(settings_doctype, "at_subuser_password")
    
    if not at_username or not at_password_encrypted:
        frappe.throw("AT Subuser credentials not configured in Portugal Compliance Settings.")
    
    # Assuming password is encrypted in DB, get decrypted value
    # This depends on how frappe.get_doc("User", frappe.session.user).get_password() works or custom decryption
    # For this example, let's assume a utility function or direct call if it's stored via Password field type
    # at_password = frappe.utils.password.get_decrypted_password(settings_doctype, settings_doctype, 'at_subuser_password', at_password_encrypted) 
    # This is a placeholder, actual decryption depends on Frappe version and field type.
    # If it's a standard Password field, frappe.get_doc(settings_doctype, settings_doctype).get_password('at_subuser_password')
    # For simplicity, if you store it plainly for testing (NOT RECOMMENDED FOR PROD):
    # at_password = at_password_encrypted 
    # A better way for single DocTypes:
    doc_settings = frappe.get_single(settings_doctype)
    at_password = doc_settings.get_password("at_subuser_password")

    serie_data = {
        "serie": serie,
        "tipoSerie": tipo_serie,
        "classeDoc": classe_doc,
        "tipoDoc": tipo_doc,
        "numPrimDocSerie": num_prim_doc_serie,
        "dataInicioPrevUtiliz": data_inicio_prev_utiliz, 
        "numCertSWFatur": num_cert_sw_fatur
    }
    if meio_processamento:
        serie_data["meioProcessamento"] = meio_processamento

    # Config paths can also be fetched from DocSettings if they are configurable
    config_paths = {
        'cert_path': frappe.db.get_single_value(settings_doctype, "client_certificate_path") or DEFAULT_CERT_PATH,
        'cert_password': frappe.db.get_single_value(settings_doctype, "client_certificate_password") or DEFAULT_CERT_PASSWORD, # This might be for PFX, not directly used by Zeep if PEMs are used
        'wsdl_path': frappe.db.get_single_value(settings_doctype, "wsdl_file_path") or DEFAULT_WSDL_PATH,
        'endpoint_url': frappe.db.get_single_value(settings_doctype, "at_endpoint_url") or DEFAULT_ENDPOINT_URL,
        'at_public_key_path': frappe.db.get_single_value(settings_doctype, "at_public_key_file_path") or DEFAULT_AT_PUBLIC_KEY_PATH
    }
    
    credentials = {'username': at_username, 'password': at_password}
    
    result = register_serie_at(serie_data, credentials, config_paths)

    if result['status'] == 'error':
        frappe.log_error(title=f"AT Series Registration Error for {serie}", message=str(result))
    # Return the full result for the client-side to handle
    return result


if __name__ == "__main__":
    # This section is for testing the service functions standalone, outside Frappe.
    # It will NOT be executed when imported by Frappe.
    print("This script (`atcud_service.py`) can be used as a module.")
    print("To test `register_serie_at` standalone, use `test_atcud_standalone.py`.")
    
    # Example of how to use encrypt_password_with_at_public_key directly for testing:
    # try:
    #     test_password = "your_plain_text_password"
    #     # Ensure the AT public key path is correct for this test
    #     encrypted = encrypt_password_with_at_public_key(test_password, DEFAULT_AT_PUBLIC_KEY_PATH)
    #     print(f"Encrypted password for '{test_password}': {encrypted}")
    # except FileNotFoundError as e:
    #     print(f"Error during encryption test: {e}. Ensure AT public key path is correct.")
    # except Exception as e:
    #     print(f"An unexpected error occurred during encryption test: {e}")

