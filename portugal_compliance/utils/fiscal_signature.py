# Copyright (c) 2025, Manus Team and contributors
# For license information, please see license.txt

import frappe
import hashlib
import base64
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pkcs12
from cryptography.hazmat.backends import default_backend
import qrcode
import io

# --- Funções de Assinatura Digital ---

def get_active_certificate_details(company):
    """Obtém os detalhes do certificado digital ativo para a empresa."""
    active_cert_name = frappe.call("portugal_compliance.portugal_compliance.doctype.certificado_digital_qualificado.certificado_digital_qualificado.get_active_certificate_for_company", company=company)
    if not active_cert_name:
        frappe.throw(frappe._("Nenhum certificado digital ativo encontrado para a empresa {0}.").format(company))
    
    cert_doc = frappe.get_doc("Certificado Digital Qualificado", active_cert_name)
    pfx_data, pfx_password = cert_doc.get_certificate_data()
    
    password_bytes = pfx_password.encode("utf-8") if pfx_password else None
        
    private_key, certificate, _ = load_pkcs12(
        pfx_data, 
        password_bytes,
        default_backend()
    )
    return private_key, certificate

def create_signature_string(invoice_date_obj, invoice_time_str, invoice_number, invoice_total_float, previous_invoice_hash_str):
    """Cria a string de dados a ser assinada, conforme requisitos da AT.
       Formato: DataDaFatura;HoraDaFatura;NumeroDaFatura;TotalComImpostos;HashDaFaturaAnterior
    """
    formatted_date = invoice_date_obj.strftime("%Y-%m-%d")
    # HoraDaFatura (HH:MM:SS) - invoice_time_str is assumed to be in this format or convertible
    # invoice_number (Série/Número)
    formatted_total = "{:.2f}".format(invoice_total_float) # TotalComImpostos
    
    data_string = f"{formatted_date};{invoice_time_str};{invoice_number};{formatted_total};{previous_invoice_hash_str}"
    return data_string.encode("utf-8")

def sign_data_rsa_sha256(private_key, data_to_sign_bytes):
    """Assina os dados usando a chave privada RSA com SHA-256."""
    signature = private_key.sign(
        data_to_sign_bytes,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return signature

def get_data_hash_4_chars(data_bytes_for_hash):
    """Calcula o hash SHA-1 da string de dados, codifica em Base64 e extrai os caracteres específicos.
       Posições: 1ª, 11ª, 21ª, 31ª do hash SHA-1 da string de dados, em base64.
    """
    hash_obj = hashlib.sha1(data_bytes_for_hash)
    b64_hash = base64.b64encode(hash_obj.digest()).decode("utf-8")
    chars = []
    positions = [0, 10, 20, 30] # 0-indexed for 1st, 11th, 21st, 31st
    for pos in positions:
        if pos < len(b64_hash):
            chars.append(b64_hash[pos])
        else:
            chars.append("X") # Fallback if hash is too short
    return "-".join(chars)

# --- Funções de QR Code ---

def generate_qr_code_string(atcud, nif_emitter, nif_acquirer, country_emitter, country_acquirer, doc_type_code, doc_status, doc_date_obj, doc_number, taxable_amount_float, vat_amount_float, gross_total_float, signature_hash_4_chars, software_cert_number):
    """Gera a string para o QR Code conforme Portaria n.º 195/2020."""
    
    fmt_taxable = "{:.2f}".format(taxable_amount_float)
    fmt_vat = "{:.2f}".format(vat_amount_float)
    fmt_gross = "{:.2f}".format(gross_total_float)
    
    nif_acquirer_final = "0" if nif_acquirer == "999999990" or not nif_acquirer else nif_acquirer

    qr_fields = [
        f"A:{atcud}",
        f"B:{nif_emitter}",
        f"C:{country_emitter}",
        f"D:{nif_acquirer_final}",
        f"E:{country_acquirer}",
        f"F:{doc_type_code}",
        f"G:{doc_status}",
        f"H:{doc_date_obj.strftime("%Y%m%d")}",
        f"I1:{doc_number}",
        f"I2:{fmt_taxable}",
        f"I3:{fmt_vat}",
        f"I4:{fmt_gross}",
        f"I7:{signature_hash_4_chars}",
        f"I8:{software_cert_number}",
        f"P:1"
    ]
    return "*".join(qr_fields)

def generate_qr_code_image_bytes(qr_string):
    """Gera uma imagem QR Code a partir da string e retorna como bytes PNG."""
    qr = qrcode.QRCode(
        version=None, # Auto-detect version
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4, # Smaller box size for smaller image
        border=2,
    )
    qr.add_data(qr_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    return img_byte_arr.getvalue()

# --- Função de utilidade para obter o hash da fatura anterior ---

def get_previous_document_data_hash(current_doc):
    """Obtém o hash SHA-1 da string de dados do documento fiscal imediatamente anterior na mesma série."""
    # Uses posting_date and name for ordering within the series.
    # Assumes current_doc has pt_serie_fiscal, company, posting_date, name, and doctype fields.
    
    # Find the last submitted document in the same series strictly before the current one.
    # Order by posting_date desc, then by name desc to get the immediate predecessor.
    last_docs = frappe.db.sql(f"""
        SELECT name, pt_hash_dados_documento_sha1 
        FROM `tab{current_doc.doctype}`
        WHERE company = %(company)s
          AND pt_serie_fiscal = %(pt_serie_fiscal)s
          AND docstatus = 1
          AND (
              (posting_date < %(posting_date)s) OR 
              (posting_date = %(posting_date)s AND name < %(name)s)
          )
        ORDER BY posting_date DESC, name DESC
        LIMIT 1
        """, {
            "company": current_doc.company,
            "pt_serie_fiscal": current_doc.pt_serie_fiscal,
            "posting_date": current_doc.posting_date,
            "name": current_doc.name
        }, as_dict=True)

    if last_docs and last_docs[0].pt_hash_dados_documento_sha1:
        return last_docs[0].pt_hash_dados_documento_sha1
    else:
        return "0" # As per AT requirement for the first document in a series

def get_document_type_code_for_qr(serie_fiscal_doc_name):
    serie_doc = frappe.get_doc("Serie de Documento Fiscal", serie_fiscal_doc_name)
    mapping = {
        "Fatura": "FT",
        "Nota de Crédito": "NC",
        "Nota de Débito": "ND",
        "Guia de Remessa": "GT",
        "Fatura Simplificada": "FS",
        "Fatura-Recibo": "FR"
        # Add other mappings as necessary
    }
    return mapping.get(serie_doc.tipo_documento, "XX") # XX for unknown/error

# --- Função principal para assinar um documento e gerar QR Code ---
@frappe.whitelist()
def sign_document_and_generate_qr(doc_name, doctype_name):
    doc = frappe.get_doc(doctype_name, doc_name)
    company = doc.company

    if not doc.pt_serie_fiscal:
        frappe.throw(frappe._("Campo 'Série Fiscal' (pt_serie_fiscal) não preenchido no documento {0}.").format(doc_name))

    # 1. Obter detalhes do certificado
    private_key, _ = get_active_certificate_details(company)

    # 2. Obter hash do documento anterior
    previous_hash = get_previous_document_data_hash(doc)

    # 3. Construir a string de dados para assinatura
    # Ensure posting_time is a string in HH:MM:SS format
    posting_time_str = doc.get_formatted("posting_time") if doc.posting_time else "00:00:00"
    if isinstance(doc.posting_time, str) and len(doc.posting_time.split(":")) == 3:
        posting_time_str = doc.posting_time
    elif hasattr(doc.posting_time, "strftime") : # if it is a time object
        posting_time_str = doc.posting_time.strftime("%H:%M:%S")
    
    data_to_sign_bytes = create_signature_string(
        doc.posting_date, 
        posting_time_str, 
        doc.name, # Document number (e.g., FT ABC/00001)
        doc.grand_total, 
        previous_hash
    )
    
    # 4. Calcular o hash SHA-1 da string de dados (para encadeamento e para os 4 caracteres)
    current_doc_data_hash_sha1 = hashlib.sha1(data_to_sign_bytes).hexdigest()

    # 5. Assinar os dados com RSA-SHA256
    rsa_signature_bytes = sign_data_rsa_sha256(private_key, data_to_sign_bytes)
    rsa_signature_b64 = base64.b64encode(rsa_signature_bytes).decode("utf-8")

    # 6. Obter os 4 caracteres (do hash SHA1 da string de dados)
    signature_4_chars = get_data_hash_4_chars(data_to_sign_bytes)

    # 7. Gerar string do QR Code
    company_tax_id = frappe.db.get_value("Company", company, "tax_id")
    # Assume customer_tax_id is stored in 'tax_id' field on the invoice document for the customer
    customer_tax_id = doc.get("tax_id") or doc.get("customer_tax_id") or "999999990" 
    
    doc_type_code_qr = get_document_type_code_for_qr(doc.pt_serie_fiscal)
    if doc_type_code_qr == "XX":
        frappe.throw(frappe._("Mapeamento do tipo de documento para código QR não encontrado para a série {0}.").format(doc.pt_serie_fiscal))

    # ATCUD should be pre-filled on the document via Serie de Documento Fiscal logic
    if not doc.pt_atcud:
        frappe.throw(frappe._("ATCUD (pt_atcud) não encontrado no documento {0}.").format(doc_name))

    software_cert_number = frappe.db.get_single_value("Portugal Compliance Settings", "numero_certificado_software_at")
    if not software_cert_number:
        frappe.throw(frappe._("Número do certificado do software (AT) não configurado em Portugal Compliance Settings."))

    # Taxable amount and VAT amount for QR code
    # Assuming doc.net_total is the sum of item net amounts (taxable base)
    # Assuming doc.total_taxes_and_charges contains only VAT for this calculation
    # This might need refinement based on specific ERPNext tax setup
    qr_taxable_amount = doc.net_total
    qr_vat_amount = doc.grand_total - doc.net_total # Simplification: Assumes grand_total = net_total + all_vat
    # A more robust way for qr_vat_amount would be to sum specific VAT head accounts from doc.taxes table.

    qr_string = generate_qr_code_string(
        atcud=doc.pt_atcud,
        nif_emitter=company_tax_id,
        nif_acquirer=customer_tax_id,
        country_emitter="PT",
        country_acquirer="PT", # Needs logic if customer is foreign
        doc_type_code=doc_type_code_qr,
        doc_status="N", # N: Normal, A: Anulado, S: Autofaturação (needs logic for A)
        doc_date_obj=doc.posting_date,
        doc_number=doc.name,
        taxable_amount_float=qr_taxable_amount,
        vat_amount_float=qr_vat_amount,
        gross_total_float=doc.grand_total,
        signature_hash_4_chars=signature_4_chars,
        software_cert_number=software_cert_number
    )

    # 8. Gerar imagem do QR Code e anexar ao documento
    qr_image_content_bytes = generate_qr_code_image_bytes(qr_string)
    qr_file = frappe.new_doc("File")
    qr_file.file_name = f"{doc.name.replace('/', '_')}_qrcode.png"
    qr_file.is_private = 0 # Public so it can be embedded in prints
    qr_file.content = qr_image_content_bytes
    qr_file.attached_to_doctype = doctype_name
    qr_file.attached_to_name = doc_name
    qr_file.save(ignore_permissions=True)

    # 9. Salvar os dados da assinatura e hashes no documento
    update_values = {
        "pt_hash_dados_documento_sha1": current_doc_data_hash_sha1,
        "pt_assinatura_digital_rsa": rsa_signature_b64,
        "pt_assinatura_4_caracteres": signature_4_chars,
        "pt_qr_code_string": qr_string,
        "pt_qr_code_imagem": qr_file.file_url
    }
    frappe.db.set_value(doctype_name, doc_name, update_values)
    
    frappe.msgprint(frappe._("Documento {0} assinado e QR Code gerado com sucesso.").format(doc_name))
    return update_values

