from frappe import _

def get_data():
	return [
		{
			"label": _("Integrations"),
			"items": [
				{
					"type": "doctype",
					"name": "Portugal Compliance Settings",
					"label": _("Portugal Compliance Settings"),
					"description": _("Configure Portugal fiscal compliance settings (SAF-T, ATCUD, Signature)."),
					"onboard": 1,
				}
			]
		}
	]

