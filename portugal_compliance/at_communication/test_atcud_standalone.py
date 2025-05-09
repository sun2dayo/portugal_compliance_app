from lxml import etree
from lxml.etree import QName
from zeep import Client, Settings, Transport
from zeep.wsse.username import UsernameToken
from zeep.exceptions import Fault
import os
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import base64
import datetime
import json # For pretty printing results
import ssl
import requests # For requests.Session
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager # For custom SSL context in adapter

# --- Constants and Configuration (Directly used for standalone test) ---
# Adjusted to use PEM files, now with the full chain for the certificate
CERT_PEM_PATH = "/home/ubuntu/at_credentials/client_cert_with_chain.pem" # Using combined cert + CA chain
KEY_PEM_PATH = "/home/ubuntu/at_credentials/client_key.pem"

AT_PUBLIC_KEY_PATH = "/home/ubuntu/at_credentials/AT_PublicKey.pem"
WSDL_PATH = "/home/ubuntu/at_credentials/Comunicacao_Series.wsdl" # Local WSDL
ENDPOINT_URL = "https://servicos.portaldasfinancas.gov.pt:422/SeriesWSService" # From WSDL

# Credentials for testing (provided by user)
AT_USERNAME = "518747832/1"
AT_PASSWORD = "t.6qaff8ig2T?Ph"

# --- Helper Functions (Identical to atcud_service.py) ---
def get_at_public_key():
    """Loads the AT's public key from the .pem file."""
    with open(AT_PUBLIC_KEY_PATH, "rb") as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )
    return public_key

def encrypt_password_with_at_public_key(password):
    """Encrypts the password using AT's public key (RSA OAEP SHA1)."""
    public_key = get_at_public_key()
    encrypted_password = public_key.encrypt(
        password.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None
        )
    )
    return base64.b64encode(encrypted_password).decode("utf-8")

class CustomUsernameToken(UsernameToken):
    """Custom UsernameToken to handle AT's specific password encryption and ensure correct nonce type."""
    def __init__(self, username, password=None, password_digest=None, nonce=None, created=None, use_digest=False, **kwargs):
        self._custom_nonce_bytes = nonce if isinstance(nonce, bytes) else os.urandom(16)
        self._custom_created_dt = created if isinstance(created, datetime.datetime) else datetime.datetime.utcnow()
        super().__init__(username, password, password_digest, self._custom_nonce_bytes, self._custom_created_dt, use_digest, **kwargs)
        if password and not use_digest:
            self.encrypted_password_for_at = encrypt_password_with_at_public_key(password)

    def apply(self, envelope, headers):
        wsse_ns = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
        wsu_ns = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
        security_element = etree.Element(QName(wsse_ns, "Security"), nsmap={"wsse": wsse_ns, "wsu": wsu_ns})
        security_element.set(QName("http://schemas.xmlsoap.org/soap/envelope/", "mustUnderstand"), "1")
        timestamp = etree.SubElement(security_element, QName(wsu_ns, "Timestamp"))
        created_str = self._custom_created_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        expires_str = (self._custom_created_dt + datetime.timedelta(seconds=300)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        etree.SubElement(timestamp, QName(wsu_ns, "Created")).text = created_str
        etree.SubElement(timestamp, QName(wsu_ns, "Expires")).text = expires_str
        token = etree.SubElement(security_element, QName(wsse_ns, "UsernameToken"))
        etree.SubElement(token, QName(wsse_ns, "Username")).text = self.username
        password_node = etree.SubElement(token, QName(wsse_ns, "Password"))
        password_node.text = self.encrypted_password_for_at
        password_node.set("Type", "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#PasswordText")
        if self._custom_nonce_bytes:
            nonce_node = etree.SubElement(token, QName(wsse_ns, "Nonce"))
            nonce_node.text = base64.b64encode(self._custom_nonce_bytes).decode("utf-8")
            nonce_node.set("EncodingType", "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary")
        soap_env_ns_uri = envelope.tag[1:].split("}")[0]
        soap_header_qname = QName(soap_env_ns_uri, "Header")
        soap_header_element = envelope.find(soap_header_qname)
        if soap_header_element is None:
            soap_header_element = etree.Element(soap_header_qname)
            soap_body_qname = QName(soap_env_ns_uri, "Body")
            body_el = envelope.find(soap_body_qname)
            if body_el is not None:
                envelope.insert(envelope.index(body_el), soap_header_element)
            else:
                envelope.insert(0, soap_header_element)
        soap_header_element.append(security_element)
        return envelope, headers

class CustomTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        # context.maximum_version = ssl.TLSVersion.TLSv1_2 # To strictly enforce TLS 1.2
        # context.set_ciphers("DEFAULT@SECLEVEL=1") # Example, adjust as needed for broader compatibility
        # Try with a more specific cipher list if default fails, based on s_client output or server requirements
        # Example: context.set_ciphers("ECDHE-RSA-AES256-GCM-SHA384:AES256-GCM-SHA384")
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=context,
            **pool_kwargs
        )

def get_soap_client(username, password):
    """Initializes and returns the Zeep SOAP client with WS-Security and custom TLS settings."""
    settings = Settings(strict=False, xml_huge_tree=True, force_https=False)
    session = requests.Session()
    session.mount("https://", CustomTLSAdapter())
    transport = Transport(timeout=60, session=session)
    transport.client_cert = (CERT_PEM_PATH, KEY_PEM_PATH)
    current_nonce_bytes = os.urandom(16)
    current_created_dt = datetime.datetime.utcnow()
    wsse = CustomUsernameToken(username, password, nonce=current_nonce_bytes, created=current_created_dt)
    client = Client(WSDL_PATH, settings=settings, transport=transport, wsse=wsse)
    service = client.bind("SeriesWSService", "SeriesWSPort")
    service._binding_options["address"] = ENDPOINT_URL
    return service

# --- Standalone Test Function ---
def test_register_serie_standalone(serie_data):
    """Registers a new document series with AT - Standalone version."""
    client_service = get_soap_client(AT_USERNAME, AT_PASSWORD)
    request_data = {
        "serie": serie_data["serie"],
        "tipoSerie": serie_data["tipo_serie"],
        "classeDoc": serie_data["classe_doc"],
        "tipoDoc": serie_data["tipo_doc"],
        "numPrimDocSerie": int(serie_data["num_prim_doc_serie"]),
        "dataInicioPrevUtiliz": serie_data["data_inicio_prev_utiliz"],
        "numCertSWFatur": int(serie_data["num_cert_sw_fatur"])
    }
    if "meio_processamento" in serie_data and serie_data["meio_processamento"]:
        request_data["meioProcessamento"] = serie_data["meio_processamento"]

    try:
        print(f"Sending request to AT: {request_data}")
        response = client_service.registarSerie(**request_data)
        print(f"Received response from AT: {response}")
        if response and hasattr(response, "InfoSerie") and response.InfoSerie and hasattr(response.InfoSerie, "codValidacaoSerie") and response.InfoSerie.codValidacaoSerie:
            atcud = response.InfoSerie.codValidacaoSerie
            return {"status": "success", "atcud": atcud, "response_raw": str(response)}
        elif response and hasattr(response, "listaErros") and response.listaErros and response.listaErros.Erro:
            errors = [{"code": err.codErro, "message": err.msgErro} for err in response.listaErros.Erro]
            print(f"ERROR: AT Series Registration Error - {errors}")
            return {"status": "error", "errors": errors, "response_raw": str(response)}
        else:
            print(f"ERROR: AT Series Registration Unexpected Response - {response}")
            return {"status": "error", "message": "Unexpected response structure from AT.", "response_raw": str(response)}
    except Fault as f:
        print(f"ERROR: AT Series Registration SOAP Fault - {f}")
        return {"status": "error", "message": f"SOAP Fault: {str(f)}", "details": str(f.detail) if f.detail else None}
    except Exception as e:
        print(f"ERROR: AT Series Registration Exception - {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Generic Exception: {str(e)}"}

if __name__ == "__main__":
    print("--- Starting Standalone Test for AT Series Registration ---")
    test_data = {
        "serie": "TESTMANUS08", # Incremented series for testing
        "tipo_serie": "N",
        "classe_doc": "FT",
        "tipo_doc": "FT",
        "num_prim_doc_serie": 1,
        "data_inicio_prev_utiliz": datetime.date(2025, 7, 1),
        "num_cert_sw_fatur": 0,
        "meio_processamento": "ERPNext Manus Standalone Test v1"
    }
    print(f"Test Data: {test_data}")
    result = test_register_serie_standalone(test_data)
    print("--- Test Result ---")
    print(json.dumps(result, indent=4, default=str))
    print("--- Standalone Test Finished ---")

