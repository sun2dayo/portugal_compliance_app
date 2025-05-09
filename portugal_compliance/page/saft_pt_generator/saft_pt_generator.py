@frappe.whitelist()
def generate_saft_pt_file(fiscal_year, start_date=None, end_date=None):
    import base64
    from frappe.utils.file_manager import save_file
    from .generator import SaftGenerator

    try:
        # Get the default company from user preferences
        company = frappe.defaults.get_user_default("Company")
        if not company:
            frappe.throw("Default company is not defined.")

        # Instantiate the SAF-T generator with the fiscal year and company
        generator = SaftGenerator(fiscal_year=fiscal_year, company=company)

        # If start_date and end_date are provided, override the fiscal year dates
        if start_date and end_date:
            generator.start_date = start_date
            generator.end_date = end_date

        # Generate the XML SAF-T content
        xml_content = generator.generate_file()
        file_name = f"SAFT_PT_{company}_{fiscal_year}.xml"

        # Optionally save the file in ERPNext's file system
        save_file(file_name, xml_content, "Company", company, is_private=1)

        # Return a base64-encoded version of the file for direct download
        encoded = base64.b64encode(xml_content).decode("utf-8")
        return {
            "filename": file_name,
            "filecontent": encoded
        }

    except Exception as e:
        # Log the full traceback if something goes wrong
        frappe.log_error(frappe.get_traceback(), "Error generating SAF-T")
        frappe.throw("Error generating SAF-T file. Please check the Error Log.")
