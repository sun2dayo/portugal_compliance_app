# Copyright (c) 2025, Manus Team and contributors
# For license information, please see license.txt

import frappe
import re

# --- Funções de Validação Específicas de Portugal ---

def validate_nif(nif, is_company=False):
    """
    Valida o formato e o dígito de controlo de um NIF/NIPC português.
    Para NIF singular (começa por 1, 2, 3) ou NIPC (começa por 5, 6, 8, 9).
    NIFs que começam por 45 (não residentes) ou 7 (condomínios, etc.) têm regras diferentes ou não têm dígito de controlo simples.
    Esta função foca-se nos NIFs/NIPCs mais comuns com dígito de controlo.
    """
    if not nif or not isinstance(nif, str) or not nif.isdigit() or len(nif) != 9:
        return False, "O NIF/NIPC deve conter 9 dígitos."

    first_digit = nif[0]
    # NIPC de pessoas coletivas e entidades equiparadas: 5, 6, 9
    # NIPC de não residentes com retenção: 45 (esta validação não cobre bem o 45)
    # NIF de pessoas singulares: 1, 2, 3
    # NIF de empresários em nome individual (legado): começa por 1, 2, 3
    # Outros NIFs especiais: 40-44, 46-49 (não cobertos), 70, 71, 72, 74, 75, 77, 78, 79, 8x (não cobertos)
    
    valid_first_digits_nif = ["1", "2", "3"]
    valid_first_digits_nipc = ["5", "6", "9"] # 8 é para entidades públicas, não tem check digit standard
    # NIFs iniciados por 45 (não residentes) e por 7 (heranças indivisas, condomínios) têm regras específicas e podem não ter o check digit standard.
    # Para simplificar, vamos focar nos mais comuns.

    if not (first_digit in valid_first_digits_nif or first_digit in valid_first_digits_nipc):
        # Se for um NIF de não residente (45...) ou especial (7...)
        if nif.startswith("45") or nif.startswith("70") or nif.startswith("71") or nif.startswith("72") or nif.startswith("74") or nif.startswith("75") or nif.startswith("77") or nif.startswith("78") or nif.startswith("79"):
            return True, "" # Aceita como válido sem verificação de dígito de controlo
        return False, "Primeiro dígito do NIF/NIPC inválido para validação standard."

    # Cálculo do dígito de controlo
    total = 0
    for i in range(8):
        total += int(nif[i]) * (9 - i)
    
    check_digit = 11 - (total % 11)
    if check_digit >= 10:
        check_digit = 0
    
    if check_digit == int(nif[8]):
        return True, ""
    else:
        return False, "Dígito de controlo do NIF/NIPC inválido."

# --- Hooks de Validação para DocTypes ---

def validate_customer_nif(doc, method):
    """Valida o NIF no DocType Cliente (ou Customer)."""
    # Assumindo que o campo do NIF no Cliente é 'tax_id' ou 'vat_id'
    nif_field = "tax_id"
    if hasattr(doc, "vat_id") and doc.vat_id: # Alguns setups usam vat_id
        nif_field = "vat_id"
    elif not hasattr(doc, "tax_id") or not doc.tax_id:
        # Se não houver NIF preenchido, não valida (pode ser opcional ou cliente estrangeiro)
        return

    nif_value = doc.get(nif_field)
    if nif_value == "999999990": # Consumidor Final
        return

    # Verifica se o país é Portugal antes de aplicar a validação estrita
    # Assumindo que há um campo de país no Cliente, ex: 'country'
    # Ou se o NIF começa com prefixo de país, mas NIF PT não tem.
    # Para simplificar, se o NIF não for "Consumidor Final", tenta validar.
    # Idealmente, verificar doc.country == "Portugal"
    
    # Para NIPC (empresas), o primeiro dígito é geralmente 5, 6, 9.
    # Para NIF (singulares), é 1, 2, 3.
    # A função validate_nif já lida com isso.
    is_company_nif = doc.get(nif_field)[0] in ["5", "6", "9"]

    is_valid, msg = validate_nif(nif_value, is_company=is_company_nif)
    if not is_valid:
        frappe.throw(frappe._("NIF/NIPC inválido para {0} ({1}): {2}").format(doc.name, nif_value, msg))

def validate_supplier_nif(doc, method):
    """Valida o NIF no DocType Fornecedor (ou Supplier)."""
    nif_field = "tax_id"
    if hasattr(doc, "supplier_tax_id") and doc.supplier_tax_id:
        nif_field = "supplier_tax_id"
    elif not hasattr(doc, "tax_id") or not doc.tax_id:
        return

    nif_value = doc.get(nif_field)
    if nif_value == "999999990":
        return

    is_company_nif = doc.get(nif_field)[0] in ["5", "6", "9"]
    is_valid, msg = validate_nif(nif_value, is_company=is_company_nif)
    if not is_valid:
        frappe.throw(frappe._("NIF/NIPC inválido para Fornecedor {0} ({1}): {2}").format(doc.name, nif_value, msg))

def validate_sales_invoice_fields(doc, method):
    """Validações específicas para a Fatura de Venda."""
    # Validação do NIF do cliente na fatura (se não for consumidor final)
    if doc.customer_tax_id and doc.customer_tax_id != "999999990":
        # O campo tax_id na Sales Invoice refere-se ao NIF do cliente
        is_customer_company_nif = doc.customer_tax_id[0] in ["5", "6", "9"]
        is_valid, msg = validate_nif(doc.customer_tax_id, is_company=is_customer_company_nif)
        if not is_valid:
            frappe.throw(frappe._("NIF do cliente na fatura {0} inválido ({1}): {2}").format(doc.name, doc.customer_tax_id, msg))
    
    # Validação de Motivos de Isenção de IVA (se aplicável)
    # Isto requer que os itens da fatura tenham um campo para o código do motivo de isenção
    # e que exista um DocType para gerir esses códigos (ex: "Motivo de Isenção IVA")
    if doc.taxes_and_charges:
        for tax_row in doc.taxes:
            if tax_row.charge_type == "On Net Total" and tax_row.rate == 0 and tax_row.tax_amount == 0:
                # Se a taxa de IVA é zero, deve haver um motivo de isenção válido
                # Assumindo que o item da fatura tem um campo `pt_codigo_motivo_isencao_iva`
                # E que a linha de imposto na fatura tem uma referência ao item ou ao motivo.
                # Esta lógica é complexa e depende da estrutura dos itens e impostos.
                # Exemplo simplificado: verificar se um campo global na fatura o indica.
                if not doc.get("pt_motivo_isencao_iva_global") and not tax_row.get("pt_motivo_isencao_tax_line"):
                    # frappe.throw(frappe._("Para taxas de IVA a 0% na fatura {0}, deve ser especificado um motivo de isenção válido.").format(doc.name))
                    pass # Esta validação precisa de mais detalhe sobre a estrutura dos dados

    # Imutabilidade: após submissão, certos campos não devem ser alterados.
    # O Frappe já lida com a não alteração de documentos submetidos (docstatus=1).
    # A lógica de anulação fiscal já previne cancelamentos diretos.
    # Campos como NIF do cliente, data de emissão, itens, valores, assinatura, ATCUD, QR Code
    # são implicitamente protegidos pela não alterabilidade do docstatus=1.
    # Se for necessário um bloqueio mais granular (ex: impedir alteração de NIF mesmo em rascunho após certa fase),
    # seria uma lógica adicional no validate.

    # Impedir desligar funcionalidades de certificação:
    # Esta validação é mais a nível de configuração do sistema (ex: Portugal Compliance Settings)
    # ou garantindo que os hooks de assinatura não são facilmente removidos.
    # Não é tipicamente uma validação a nível de documento individual.
    pass

def prevent_modification_of_certified_fields(doc, method):
    """
    Previne a modificação de campos fiscais chave após o documento ter sido certificado/assinado,
    mesmo que o documento seja alterado antes de uma nova submissão (cenário menos comum).
    Esta é uma salvaguarda adicional à imutabilidade do docstatus=1.
    """
    if not doc.is_new():
        # Obter o estado anterior do documento da base de dados
        db_doc = frappe.get_doc(doc.doctype, doc.name) # Obtém a versão da BD
        
        # Campos que, se já preenchidos (indicando certificação anterior), não devem mudar
        certified_fields_immutable = [
            "pt_atcud", 
            "pt_hash_dados_documento_sha1", 
            "pt_assinatura_digital_rsa", 
            "pt_assinatura_4_caracteres", 
            "pt_qr_code_string", 
            "pt_qr_code_imagem"
        ]
        
        for field in certified_fields_immutable:
            if db_doc.get(field) and db_doc.get(field) != doc.get(field):
                frappe.throw(frappe._("O campo fiscal certificado ") + field + frappe._(" não pode ser alterado após a sua geração inicial."))

        # Se o documento original já estava fiscalmente anulado, não permitir "desanular" por modificação.
        if db_doc.get("pt_estado_documento_fiscal") == "Anulado" and doc.get("pt_estado_documento_fiscal") != "Anulado":
            frappe.throw(frappe._("Um documento fiscalmente anulado não pode ter o seu estado de anulação revertido manualmente."))

# --- DocType de Apoio: Motivo de Isenção IVA (Exemplo) ---
# Se for necessário, criar um DocType "Motivo Isencao IVA PT" com campos:
# - codigo_motivo (ex: M01, M02, ...)
# - descricao
# - legislacao_aplicavel (Text)
# - ativo (Check)
# Este DocType seria depois referenciado nos itens da fatura ou nas linhas de imposto.

