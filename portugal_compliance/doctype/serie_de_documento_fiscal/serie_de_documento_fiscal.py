# Copyright (c) 2025, Manus Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, cstr

class SerieDeDocumentoFiscal(Document):
    def validate(self):
        self.validar_campos_obrigatorios()
        # A unicidade do nome (prefixo_serie) é garantida pelo Frappe se autoname="field:prefixo_serie"
        # Se for necessário validar combinações únicas (ex: empresa, tipo_documento, ano_fiscal devem ser únicos para um prefixo)
        # essa lógica adicional pode ser inserida aqui.
        # Por exemplo, garantir que um prefixo_serie não seja reutilizado para um tipo_documento diferente no mesmo ano e empresa.
        if self.is_new():
            filters = {
                "empresa": self.empresa,
                "tipo_documento": self.tipo_documento,
                "ano_fiscal": self.ano_fiscal,
                "prefixo_serie": self.prefixo_serie,
                "name": ["!=", self.name] # Exclui o próprio documento durante a validação de um novo
            }
            if frappe.db.exists("Serie de Documento Fiscal", filters):
                frappe.throw(frappe._("Já existe uma série com o mesmo prefixo ({0}), tipo de documento ({1}), ano fiscal ({2}) e empresa ({3}).").format(
                    self.prefixo_serie, self.tipo_documento, self.ano_fiscal, self.empresa))

    def validar_campos_obrigatorios(self):
        if not self.tipo_documento:
            frappe.throw(frappe._("O campo 'Tipo de Documento' é obrigatório."))
        if not self.prefixo_serie:
            frappe.throw(frappe._("O campo 'Prefixo da Série' é obrigatório."))
        if not self.ano_fiscal:
            frappe.throw(frappe._("O campo 'Ano Fiscal' é obrigatório."))
        if not self.empresa:
            frappe.throw(frappe._("O campo 'Empresa' é obrigatório."))

    def get_next_number(self):
        if not self.ativo:
            frappe.throw(frappe._("A série {0} não está ativa.").format(self.name))

        # Bloqueia o documento para evitar race conditions ao obter o próximo número.
        # Este é um lock a nível de registo do Frappe.
        frappe.db.commit() # Garante que transações anteriores são commitadas antes do SELECT FOR UPDATE
        current_doc = frappe.db.sql("""SELECT numero_sequencial_atual 
                                        FROM `tabSerie de Documento Fiscal` 
                                        WHERE name = %s FOR UPDATE""", self.name, as_dict=True)
        
        if not current_doc:
            frappe.throw(frappe._("Série {0} não encontrada.").format(self.name))

        current_number = cint(current_doc[0].numero_sequencial_atual)
        next_number = current_number + 1
        
        frappe.db.set_value("Serie de Documento Fiscal", self.name, "numero_sequencial_atual", next_number, update_modified=False)
        self.numero_sequencial_atual = next_number # Atualiza o valor no objeto em memória também
        frappe.db.commit() # Libera o lock
        
        return next_number

    def get_formatted_document_number(self, sequence_number=None):
        if sequence_number is None:
            sequence_number = self.numero_sequencial_atual
        
        # A formatação pode ser mais complexa ou configurável no futuro.
        # Exemplo: FT2023/00001. O prefixo_serie já pode conter o ano (ex: FT2023)
        return f"{self.prefixo_serie}/{str(sequence_number).zfill(5)}"

    def get_atcud(self, sequence_number=None):
        if not self.codigo_validacao_serie_at:
            # De acordo com os requisitos, o ATCUD é obrigatório.
            # Se o código de validação não estiver presente, pode ser um erro de configuração.
            frappe.log_error(title="Código de Validação AT em Falta", message=f"Série {self.name} não tem Código de Validação da Série (AT) definido.")
            frappe.throw(frappe._("Código de Validação da Série (AT) não definido para a série {0}. Este código é necessário para gerar o ATCUD.").format(self.name))
        
        if sequence_number is None:
            sequence_number = self.numero_sequencial_atual
            # Se for o primeiro número, e numero_sequencial_atual ainda é 0 (antes do primeiro get_next_number)
            # o número sequencial efetivo para o ATCUD será 1.
            if sequence_number == 0:
                 frappe.throw(frappe._("Número sequencial inválido (0) para gerar ATCUD para a série {0}. Obtenha o próximo número primeiro.").format(self.name))

        return f"{self.codigo_validacao_serie_at}-{cstr(sequence_number)}"

# Funções Whitelisted para serem chamadas via API ou de scripts de cliente/servidor
@frappe.whitelist()
def get_next_sequential_number(serie_name):
    try:
        doc_serie = frappe.get_doc("Serie de Documento Fiscal", serie_name)
        next_seq = doc_serie.get_next_number()
        return {
            "next_sequential_number": next_seq,
            "formatted_number": doc_serie.get_formatted_document_number(next_seq),
            "atcud": doc_serie.get_atcud(next_seq) if doc_serie.codigo_validacao_serie_at else None
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Erro ao obter próximo número para série {serie_name}")
        return {"error": str(e)}

@frappe.whitelist()
def get_current_atcud_for_document(serie_name, sequence_number):
    try:
        doc_serie = frappe.get_doc("Serie de Documento Fiscal", serie_name)
        seq_int = cint(sequence_number)
        if seq_int <= 0:
            return {"error": "Número sequencial inválido."}
        return {"atcud": doc_serie.get_atcud(seq_int)}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Erro ao obter ATCUD para série {serie_name}, número {sequence_number}")
        return {"error": str(e)}

