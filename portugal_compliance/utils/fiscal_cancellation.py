# Copyright (c) 2025, Manus Team and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today

def prevent_direct_cancellation_of_fiscal_document(doc, method):
    """
    Called from on_cancel hook of fiscal documents like Sales Invoice.
    Prevents direct cancellation of submitted and signed/certified documents.
    Advises to issue a rectifying document instead.
    """
    if doc.docstatus == 1: # Submitted document
        # Check if the document is fiscally signed/certified
        # Using pt_assinatura_digital_rsa or pt_atcud as indicators of certification
        is_certified = doc.get("pt_assinatura_digital_rsa") or doc.get("pt_atcud")

        if is_certified:
            if doc.get("pt_estado_documento_fiscal") == "Anulado":
                frappe.msgprint(frappe._("Este documento ({0}) já se encontra fiscalmente anulado por {1}.").format(doc.name, doc.get("pt_documento_anulador_ref")))
                # Allow Frappe's cancel to proceed if it's just changing status of an already fiscally voided doc.
                # However, to be safe and adhere to immutability, it's better to prevent changes after fiscal processing.
                # For now, we'll still throw to prevent any alteration of docstatus=2 by user directly on certified docs.
                # The fiscal state is the source of truth.
            
            frappe.throw(
                frappe._("Documentos fiscais certificados ({0}) não podem ser cancelados diretamente. "
                         "Deve emitir um documento retificativo (ex: Nota de Crédito) para o anular fiscalmente.").format(doc.name)
            )
        else:
            # Document is submitted but not yet certified (e.g., error during on_submit signing)
            # Standard cancellation might be permissible but needs careful consideration.
            # For now, let's assume all submitted fiscal docs follow the rectifying document rule.
            frappe.msgprint(frappe._("Para anular fiscalmente o documento {0}, por favor emita o respetivo documento retificativo. "
                                 "Se este documento não foi certificado devido a um erro, corrija e submeta novamente, ou proceda com a anulação fiscal via documento retificativo.").format(doc.name))
            # To strictly prevent, uncomment:
            # frappe.throw(frappe._("Documentos submetidos devem ser anulados via documento retificativo."))
    # If doc.docstatus == 0 (Draft), Frappe's standard cancellation is allowed and this hook might not be strictly necessary
    # or should allow it.

def process_fiscal_cancellation_via_rectifying_document(rectifying_doc, method):
    """
    Called from on_submit hook of a rectifying document (e.g., Credit Note / Journal Entry / Return Sales Invoice).
    Updates the original fiscally cancelled document.
    """
    original_doc_name = None
    original_doc_doctype = None
    reason_for_cancellation = rectifying_doc.get("remark") or rectifying_doc.get("remarks") or "Anulado via documento retificativo."

    # Scenario 1: Journal Entry as Credit Note referencing a Sales Invoice
    if rectifying_doc.doctype == "Journal Entry" and rectifying_doc.get("pt_ref_documento_original"):
        # The patch added 'pt_ref_documento_original' (Link to Sales Invoice) to Journal Entry.
        original_doc_name = rectifying_doc.pt_ref_documento_original
        # Assuming the link field 'pt_ref_documento_original' is correctly configured to link to 'Sales Invoice'
        # We can get the doctype from the field's options if needed, but for now, assume Sales Invoice.
        ref_field_meta = frappe.get_meta("Journal Entry").get_field("pt_ref_documento_original")
        if ref_field_meta and ref_field_meta.options == "Sales Invoice":
            original_doc_doctype = "Sales Invoice"
        else:
            frappe.log_warning("Fiscal Cancellation", f"Campo pt_ref_documento_original no Journal Entry {rectifying_doc.name} não está configurado para Sales Invoice.")
            return # Cannot determine original doctype

    # Scenario 2: Sales Invoice marked as Return (is_return=1) referencing original Sales Invoice
    elif rectifying_doc.doctype == "Sales Invoice" and rectifying_doc.get("is_return") == 1 and rectifying_doc.get("return_against"):
        original_doc_name = rectifying_doc.return_against
        original_doc_doctype = "Sales Invoice" # A return Sales Invoice rectifies another Sales Invoice
        if hasattr(rectifying_doc, "reason_for_return") and rectifying_doc.reason_for_return:
            reason_for_cancellation = rectifying_doc.reason_for_return

    # Add other scenarios if different DocTypes are used for rectification (e.g., a dedicated Credit Note DocType)

    if original_doc_name and original_doc_doctype:
        try:
            original_doc = frappe.get_doc(original_doc_doctype, original_doc_name)
            
            # Proceed only if original document is submitted (docstatus=1) and not already fiscally cancelled by another document
            if original_doc.docstatus == 1:
                if original_doc.get("pt_estado_documento_fiscal") == "Anulado" and 	doc.get("pt_documento_anulador_ref") and original_doc.get("pt_documento_anulador_ref") != rectifying_doc.name:
                    frappe.msgprint(
                        frappe._("O documento original {0} ({1}) já se encontra fiscalmente anulado por {2}. A anulação por {3} não será processada novamente.").format(
                            original_doc.name, original_doc_doctype, original_doc.pt_documento_anulador_ref, rectifying_doc.name
                        )
                    )
                    return

                update_values = {
                    "pt_estado_documento_fiscal": "Anulado",
                    "pt_data_anulacao": rectifying_doc.get("posting_date") or today(),
                    "pt_documento_anulador_doctype": rectifying_doc.doctype,
                    "pt_documento_anulador_ref": rectifying_doc.name,
                    "pt_motivo_anulacao_texto": reason_for_cancellation
                }
                
                frappe.db.set_value(original_doc_doctype, original_doc_name, update_values, update_modified=False)
                frappe.msgprint(
                    frappe._("O documento original {0} ({1}) foi marcado como fiscalmente anulado devido à submissão de {2}.").format(
                        original_doc.name, original_doc_doctype, rectifying_doc.name
                    )
                )
            elif original_doc.docstatus != 1:
                 frappe.log_warning(
                    title="Fiscal Cancellation Logic",
                    message=f"Tentativa de anular fiscalmente o documento original {original_doc_name} ({original_doc_doctype}) que não está submetido (docstatus={original_doc.docstatus}), pela retificação {rectifying_doc.name}. Anulação fiscal não aplicada."
                )

        except frappe.DoesNotExistError:
            frappe.log_error(
                title="Fiscal Cancellation Error",
                message=f"Documento original {original_doc_name} ({original_doc_doctype}) não encontrado ao processar anulação fiscal por {rectifying_doc.name}."
            )
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Erro ao processar anulação fiscal para {original_doc_name} ({original_doc_doctype}) via {rectifying_doc.name}")
    # else: No original document linked, or not a recognized rectifying scenario for this function.
    # This is not an error, as the submitted document (e.g., Journal Entry) might serve other purposes.

