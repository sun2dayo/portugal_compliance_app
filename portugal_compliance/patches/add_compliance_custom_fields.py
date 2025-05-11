import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    frappe.reload_doc("accounts", "doctype", "sales_invoice")
    # If Credit Notes are a different DocType (e.g., a custom one or if Journal Entry is not used for this)
    # frappe.reload_doc("module_name", "doctype", "credit_note_doctype_name")

    # Fields for Sales Invoice (and potentially other cancellable fiscal documents)
    cancellable_fiscal_docs_fields = {
        "Sales Invoice": [
            {
                "fieldname": "pt_serie_fiscal",
                "label": "Série Fiscal",
                "fieldtype": "Link",
                "options": "Serie de Documento Fiscal",
                "insert_after": "naming_series",
                "description": "Referência à série de documento fiscal utilizada para este documento.",
                "reqd": 0, 
            },
            {
                "fieldname": "pt_atcud",
                "label": "ATCUD",
                "fieldtype": "Data",
                "insert_after": "pt_serie_fiscal",
                "description": "Código Único do Documento, gerado a partir da série fiscal e do número sequencial.",
                "read_only": 1,
            },
            {
                "fieldname": "pt_document_type_code",
                "label": "Código do Tipo de Documento (para QR)",
                "fieldtype": "Data",
                "insert_after": "pt_atcud",
                "description": "Código abreviado do tipo de documento (ex: FT, NC, FS) usado na string do QR Code.",
                "read_only": 1,
            },
            {
                "fieldname": "pt_hash_dados_documento_sha1",
                "label": "Hash SHA-1 Dados Documento (Encadeamento)",
                "fieldtype": "Small Text",
                "insert_after": "pt_document_type_code",
                "description": "Hash SHA-1 da string de dados da fatura atual. Usado para encadeamento.",
                "read_only": 1,
            },
            {
                "fieldname": "pt_assinatura_digital_rsa",
                "label": "Assinatura Digital RSA (Base64)",
                "fieldtype": "Text",
                "insert_after": "pt_hash_dados_documento_sha1",
                "description": "Assinatura digital RSA dos dados do documento, codificada em Base64.",
                "read_only": 1,
            },
            {
                "fieldname": "pt_assinatura_4_caracteres",
                "label": "Caracteres da Assinatura (Impressão)",
                "fieldtype": "Data",
                "insert_after": "pt_assinatura_digital_rsa",
                "description": "Os 4 caracteres específicos do hash SHA1 da string de dados do documento.",
                "read_only": 1,
            },
            {
                "fieldname": "pt_qr_code_string",
                "label": "String do QR Code",
                "fieldtype": "Text",
                "insert_after": "pt_assinatura_4_caracteres",
                "description": "A string completa de dados utilizada para gerar o QR Code.",
                "read_only": 1,
            },
            {
                "fieldname": "pt_qr_code_imagem",
                "label": "Imagem do QR Code",
                "fieldtype": "Attach Image",
                "insert_after": "pt_qr_code_string",
                "description": "A imagem do QR Code gerada para este documento.",
                "read_only": 1,
            },
            # New fields for cancellation management
            {
                "fieldname": "pt_estado_documento_fiscal",
                "label": "Estado Fiscal do Documento",
                "fieldtype": "Select",
                "options": "\nNormal\nAnulado",
                "default": "Normal",
                "insert_after": "status", # Or another suitable field
                "description": "Indica o estado fiscal do documento (Normal, Anulado).",
                "read_only": 1, # Typically set programmatically
            },
            {
                "fieldname": "pt_documento_anulador_ref",
                "label": "Documento Anulador (Ref.)",
                "fieldtype": "Dynamic Link",
                "options": "pt_documento_anulador_doctype",
                "insert_after": "pt_estado_documento_fiscal",
                "description": "Referência ao documento que anula este (ex: Nota de Crédito).",
                "read_only": 1,
            },
            {
                "fieldname": "pt_documento_anulador_doctype",
                "label": "Tipo de Documento Anulador",
                "fieldtype": "Link",
                "options": "DocType",
                "hidden": 1,
                "insert_after": "pt_documento_anulador_ref",
            },
            {
                "fieldname": "pt_data_anulacao",
                "label": "Data de Anulação Fiscal",
                "fieldtype": "Date",
                "insert_after": "pt_documento_anulador_doctype",
                "description": "Data em que o documento foi fiscalmente anulado.",
                "read_only": 1,
            },
            {
                "fieldname": "pt_motivo_anulacao_texto",
                "label": "Motivo da Anulação Fiscal",
                "fieldtype": "Small Text",
                "insert_after": "pt_data_anulacao",
                "description": "Motivo da anulação fiscal do documento.",
                # Not read_only, can be set by user if direct cancellation is allowed and needs reason
            }
        ]
    }

    create_custom_fields(cancellable_fiscal_docs_fields, ignore_validate=True)
    frappe.db.commit()
    frappe.msgprint("Patch para campos personalizados de conformidade Portugal (incluindo anulação) executado/atualizado com sucesso.")

    # If Credit Notes are handled by Journal Entry and need to reference the original invoice:
    frappe.reload_doc("accounts", "doctype", "journal_entry")
    custom_fields_journal_entry = {
        "Journal Entry": [
            {
                "fieldname": "pt_ref_documento_original",
                "label": "Ref. Documento Original (Anulado/Retificado)",
                "fieldtype": "Link",
                "options": "Sales Invoice", # Or other relevant DocTypes
                "insert_after": "voucher_type", # Adjust as needed
                "description": "Referência ao documento original que esta Nota de Crédito está a retificar/anular."
            }
        ]
    }
    create_custom_fields(custom_fields_journal_entry, ignore_validate=True)
    frappe.db.commit()
    frappe.msgprint("Patch para campos de referência em Journal Entry (Notas de Crédito) executado com sucesso.")


