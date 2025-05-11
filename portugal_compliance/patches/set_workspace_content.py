import frappe
import json

def execute():
    if not frappe.db.exists("Workspace", "Portugal Compliance"):
        return

    content = [
        {"type": "header", "data": {"text": "Configurações", "level": 4, "col": 12}},
        {"type": "shortcut", "data": {
            "shortcut_name": "Portugal Compliance Settings",
            "link_to": "Portugal Compliance Settings",
            "type": "doctype",
            "label": "Portugal Compliance Settings",
            "col": 4,
            "icon": "fa fa-cog"
        }},
        {"type": "shortcut", "data": {
            "shortcut_name": "Document Series PT",
            "link_to": "Document Series PT",
            "type": "doctype",
            "label": "Séries Documentais",
            "col": 4,
            "icon": "fa fa-list-ol"
        }},
        {"type": "header", "data": {"text": "Utilitários Fiscais", "level": 4, "col": 12}},
        {"type": "shortcut", "data": {
            "shortcut_name": "SAF-T Generator",
            "link_to": "/app/saft-pt-generator",
            "type": "page",
            "label": "Gerador SAF-T",
            "col": 4,
            "icon": "fa fa-file-code"
        }},
        {"type": "shortcut", "data": {
            "shortcut_name": "ATCUD Logs",
            "link_to": "Compliance Audit Log",
            "type": "doctype",
            "label": "Logs ATCUD",
            "col": 4,
            "icon": "fa fa-shield-alt"
        }},
        {"type": "shortcut", "data": {
            "shortcut_name": "Taxonomy Code",
            "link_to": "Taxonomy Code",
            "type": "doctype",
            "label": "Códigos de Taxonomia",
            "col": 4,
            "icon": "fa fa-tags"
        }}
    ]

    ws = frappe.get_doc("Workspace", "Portugal Compliance")
    ws.content = json.dumps(content)
    ws.save(ignore_permissions=True)
    frappe.db.commit()
