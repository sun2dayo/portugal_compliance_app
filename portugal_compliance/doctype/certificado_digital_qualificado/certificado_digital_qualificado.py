# Copyright (c) 2025, Manus Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_site_path, get_files_path
import os

class CertificadoDigitalQualificado(Document):
    def validate(self):
        self.validar_campos_obrigatorios()
        self.validar_datas_certificado()
        if self.is_new() and self.ativo:
            self.desativar_outros_certificados_ativos_para_empresa()

    def validar_campos_obrigatorios(self):
        if not self.nome_certificado:
            frappe.throw(frappe._("O campo 'Nome do Certificado' é obrigatório."))
        if not self.empresa:
            frappe.throw(frappe._("O campo 'Empresa Associada' é obrigatório."))
        if not self.ficheiro_certificado_privado:
            frappe.throw(frappe._("O campo 'Ficheiro do Certificado (Chave Privada)' é obrigatório."))
        # A password pode ser opcional se o certificado não estiver protegido por uma.

    def validar_datas_certificado(self):
        if self.valido_de and self.valido_ate and self.valido_de > self.valido_ate:
            frappe.throw(frappe._("A data 'Válido De' não pode ser posterior à data 'Válido Até'."))

    def on_update(self):
        if self.ativo:
            self.desativar_outros_certificados_ativos_para_empresa()

    def desativar_outros_certificados_ativos_para_empresa(self):
        # Garante que apenas um certificado está ativo por empresa
        outros_certificados = frappe.get_all(
            "Certificado Digital Qualificado",
            filters={
                "empresa": self.empresa,
                "ativo": 1,
                "name": ["!=", self.name]
            },
            fields=["name"]
        )
        for cert_info in outros_certificados:
            try:
                cert_doc = frappe.get_doc("Certificado Digital Qualificado", cert_info.name)
                cert_doc.ativo = 0
                cert_doc.save(ignore_permissions=True) # Salva diretamente para evitar loops ou validações complexas
                frappe.log_info(f"Certificado {cert_info.name} desativado devido à ativação do certificado {self.name} para a empresa {self.empresa}.", "Desativação Automática de Certificado")
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"Erro ao desativar certificado {cert_info.name}")

    def get_certificate_data(self):
        if not self.ficheiro_certificado_privado:
            frappe.throw(frappe._("Ficheiro do certificado não encontrado para {0}").format(self.name))

        file_url = self.ficheiro_certificado_privado
        # O file_url pode ser /private/files/nome_ficheiro.pfx ou /files/nome_ficheiro.pfx
        # Precisamos do caminho absoluto no sistema de ficheiros.
        
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        file_path = os.path.join(get_files_path(is_private=file_doc.is_private), file_doc.file_name)

        if not os.path.exists(file_path):
             # Tentar um caminho alternativo se o primeiro falhar (caso o is_private não seja preciso)
            file_path_public = os.path.join(get_files_path(is_private=False), file_doc.file_name)
            file_path_private = os.path.join(get_files_path(is_private=True), file_doc.file_name)
            if os.path.exists(file_path_public):
                file_path = file_path_public
            elif os.path.exists(file_path_private):
                file_path = file_path_private
            else:
                frappe.throw(frappe._("Ficheiro do certificado não localizado no sistema de ficheiros: {0}").format(file_url))

        try:
            with open(file_path, "rb") as f:
                pfx_data = f.read()
            return pfx_data, self.password_certificado
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Erro ao ler ficheiro do certificado {self.name}")
            frappe.throw(frappe._("Erro ao ler o ficheiro do certificado: {0}").format(e))

@frappe.whitelist()
def get_active_certificate_for_company(company):
    if not company:
        company = frappe.defaults.get_user_default("Company")
    if not company:
        frappe.throw(frappe._("Empresa não especificada e nenhuma empresa padrão definida para o utilizador."))

    active_certs = frappe.get_all(
        "Certificado Digital Qualificado",
        filters={"empresa": company, "ativo": 1},
        fields=["name", "valido_ate"],
        order_by="valido_ate desc"
    )

    if not active_certs:
        return None # Ou frappe.throw para exigir um certificado ativo
    
    # Poderia adicionar lógica para verificar a validade (valido_ate)
    # Por agora, retorna o primeiro encontrado (que deve ser o único ativo pela lógica de desativação)
    return active_certs[0].name

