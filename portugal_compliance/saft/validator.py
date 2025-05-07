from lxml import etree
import frappe

def validate_saft_xml(xml_content: bytes, xsd_path: str) -> bool:
    try:
        # Load and parse the XSD schema
        with open(xsd_path, 'rb') as f:
            xsd_doc = etree.parse(f)
            schema = etree.XMLSchema(xsd_doc)

        # Parse the SAF-T XML content
        xml_doc = etree.fromstring(xml_content)

        # Validate against XSD
        schema.assertValid(xml_doc)
        return True

    except etree.DocumentInvalid as e:
        frappe.log_error(str(e), "SAF-T XSD Validation Failed")
        frappe.throw(f"SAF-T file is invalid:\n\n{str(e)}")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error loading or parsing SAF-T XSD")
        frappe.throw("Unexpected error during SAF-T validation.")
