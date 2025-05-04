from frappe import _

def get_data():
	return [
		{
			"module_name": "Portugal Compliance",
			"color": "grey",
			"icon": "octicon octicon-law",
			"type": "module",
			"label": _("Portugal Compliance"),
			"items": [
				{
					"type": "doctype",
					"name": "Portugal Compliance Settings",
					"label": _("Settings"),
					"description": _("Configure Portugal fiscal compliance settings.")
				}
			]
		}
	]

