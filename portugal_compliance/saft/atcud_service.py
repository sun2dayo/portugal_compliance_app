import frappe
from frappe.utils import cint, cstr, now_datetime
from lxml import etree
from zeep import Client, Settings, Transport
from zeep.wsse.username import UsernameToken
from zeep.exceptions import Fault
import os
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import base64
import datetime

# --- Constants and Configuration ---
# These should ideally be configurable via ERPNext settings
def get_portugal_compliance_paths():
    """Get secure paths to certificates and WSDL from Portugal Compliance Settings."""
    usar_personalizado = frappe.db.get_single_value("Portugal Compliance Settings", "usar_wsdl_personalizado")

    wsdl_path = (
        frappe.db.get_single_value("Portugal Compliance Settings", "wsdl_path")
        if usar_personalizado
        else frappe.get_app_path("portugal_compliance", "wsdl", "Comunicacao_Series.wsdl")
    )

    return {
        "cert_path": frappe.db.get_single_value("Portugal Compliance Settings", "cert_path"),
        "cert_password": frappe.db.get_single_value("Portugal Compliance Settings", "cert_password", cache=False),
        "at_public_key_path": frappe.db.get_single_value("Portugal Compliance Settings", "at_public_key_path"),
        "endpoint_url": frappe.db.get_single_value("Portugal Compliance Settings", "endpoint_url"),
        "wsdl_path": wsdl_path
    }

# --- Helper Functions ---

def get_at_public_key():
    """Loads the AT's public key from the .cer file."""
    paths = get_portugal_compliance_paths()
    with open(paths["at_public_key_path"], "rb") as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )
    return public_key

def encrypt_password_with_at_public_key(password):
    """Encrypts the password using AT's public key (RSA OAEP)."""
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
    """Custom UsernameToken to handle AT's specific password encryption and nonce encoding."""
    def __init__(self, username, password=None, password_digest=None, nonce=None, created=None, use_digest=False, **kwargs):
        super().__init__(username, password, password_digest, nonce, created, use_digest, **kwargs)
        # AT expects password to be encrypted with their public key and then base64 encoded
        # The UsernameToken from zeep by default base64 encodes the password if it's not a digest.
        # We need to encrypt it first.
        if password and not use_digest:
            self.password = encrypt_password_with_at_public_key(password)

    def apply(self, envelope, headers):
        security = etree.Element(
            QName(self.namespace, "Security"),
            mustUnderstand="1",
            actor=self.actor,
        )

        # Timestamp
        timestamp = etree.SubElement(
            security, QName(self.wsse_utility_ns, "Timestamp")
        )
        if self.created is None:
            self.created = datetime.datetime.utcnow()
        if isinstance(self.created, datetime.datetime):
            created_str = self.created.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            created_str = self.created

        etree.SubElement(timestamp, QName(self.wsse_utility_ns, "Created")).text = created_str
        # Expires is typically Created + 5 minutes (300 seconds)
        expires_str = (self.created + datetime.timedelta(seconds=300)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        etree.SubElement(timestamp, QName(self.wsse_utility_ns, "Expires")).text = expires_str

        # UsernameToken
        token = etree.SubElement(security, QName(self.namespace, "UsernameToken"))
        if self.prefix:
            token.set(QName(self.wsse_utility_ns, "Id"), self.prefix + "-1")

        etree.SubElement(token, QName(self.namespace, "Username")).text = self.username

        if self.password:
            password_node = etree.SubElement(token, QName(self.namespace, "Password"))
            password_node.text = self.password
            if self.use_digest:
                password_node.set("Type", self.password_digest_uri)
            else:
                 # AT expects this type for encrypted password
                password_node.set("Type", "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#PasswordText")

        if self.nonce:
            nonce_node = etree.SubElement(token, QName(self.namespace, "Nonce"))
            # AT expects Nonce to be Base64 encoded
            nonce_node.text = base64.b64encode(self.nonce.encode("utf-8")).decode("utf-8")
            nonce_node.set("EncodingType", "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary")

        if self.created:
            if isinstance(self.created, datetime.datetime):
                created_val = self.created.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            else:
                created_val = self.created
            etree.SubElement(
                token, QName(self.wsse_utility_ns, "Created")
            ).text = created_val

        headers.insert(0, security)
        return envelope, headers

def get_soap_client(username, password):
    """Initializes and returns the Zeep SOAP client with WS-Security."""
    paths = get_portugal_compliance_paths()

    settings = Settings(strict=False, xml_huge_tree=True)
    transport = Transport(timeout=30)
    transport.client_cert = (paths["cert_path"], paths["cert_password"])

    wsse = CustomUsernameToken(username, password, nonce=os.urandom(16).hex(), created=datetime.datetime.utcnow())

    client = Client(paths["wsdl_path"], settings=settings, transport=transport, wsse=wsse)
    service = client.bind("SeriesWSService", "SeriesWSPort")
    service._binding_options["address"] = paths["endpoint_url"]

    return client.service


# --- API Functions (to be called from ERPNext hooks or UI) ---

@frappe.whitelist()
def register_serie_at(serie, tipo_serie, classe_doc, tipo_doc, num_prim_doc_serie, data_inicio_prev_utiliz, num_cert_sw_fatur, meio_processamento=None):
    """Registers a new document series with AT."""
    # Fetch username/password from ERPNext settings (Portugal Compliance Settings DocType)
    # For now, using placeholders - THIS NEEDS TO BE SECURELY FETCHED
    at_username = frappe.db.get_single_value("Portugal Compliance Settings", "at_subuser_username")
    at_password = frappe.db.get_single_value("Portugal Compliance Settings", "at_subuser_password", True) # Get decrypted

    if not at_username or not at_password:
        frappe.throw("AT Subuser credentials not configured in Portugal Compliance Settings.")

    client_service = get_soap_client(at_username, at_password)

    request_data = {
        "serie": serie,
        "tipoSerie": tipo_serie,
        "classeDoc": classe_doc,
        "tipoDoc": tipo_doc,
        "numPrimDocSerie": cint(num_prim_doc_serie),
        "dataInicioPrevUtiliz": data_inicio_prev_utiliz, # Expects YYYY-MM-DD string
        "numCertSWFatur": cint(num_cert_sw_fatur)
    }
    if meio_processamento:
        request_data["meioProcessamento"] = meio_processamento

    try:
        response = client_service.registarSerie(**request_data)
        if response and response.InfoSerie and response.InfoSerie.codValidacaoSerie:
            # Successfully registered, ATCUD received
            atcud = response.InfoSerie.codValidacaoSerie
            # Store ATCUD in ERPNext (e.g., against the DocType Series or a custom DocType)
            # frappe.db.set_value("Series", serie_docname, "atcud", atcud)
            return {"status": "success", "atcud": atcud, "response": response}
        elif response and response.listaErros:
            errors = [{"code": err.codErro, "message": err.msgErro} for err in response.listaErros.Erro]
            frappe.log_error(title="AT Series Registration Error", message=str(errors))
            return {"status": "error", "errors": errors, "response": response}
        else:
            frappe.log_error(title="AT Series Registration Unexpected Response", message=str(response))
            return {"status": "error", "message": "Unexpected response from AT.", "response": response}
    except Fault as f:
        frappe.log_error(title="AT Series Registration SOAP Fault", message=str(f))
        return {"status": "error", "message": str(f)}
    except Exception as e:
        frappe.log_error(title="AT Series Registration Exception", message=str(e))
        return {"status": "error", "message": str(e)}

def consult_series_at(serie_code):
    """
    Calls AT service to consult an existing series.
    """
    paths = get_portugal_compliance_paths()
    service = get_soap_client("TESTEWEBSERVICES", "TESTEwebservice")

    request_data = {
        "serie": serie_code,
        "anoInicioSerie": datetime.datetime.now().year
    }

    try:
        response = service.consultarSerie(request_data)
        return {
            "status": "success",
            "data": response
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def finalize_serie_at(serie_code):
    """
    Sends request to close the document series with AT.
    """
    paths = get_portugal_compliance_paths()
    service = get_soap_client("TESTEWEBSERVICES", "TESTEwebservice")

    request_data = {
        "serie": serie_code,
        "anoInicioSerie": datetime.datetime.now().year,
        "motivoAnulacao": "Encerramento normal"
    }

    try:
        response = service.anularSerie(request_data)
        return {
            "status": "success",
            "data": response
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Add other functions like finalize_serie_at, consult_series_at, anular_serie_at following a similar pattern

# Example (for direct testing, not for production use in this file):
if __name__ == "__main__":
    # This part would not run in Frappe context directly
    # You'd call register_serie_at from a Frappe server script or whitelisted method
    print("This script is intended to be used within the Frappe framework.")
    # For local testing, you might mock frappe or set up a minimal environment
    # print(encrypt_password_with_at_public_key("your_password_here"))


