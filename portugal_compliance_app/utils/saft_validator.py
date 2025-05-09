from lxml import etree

def validate_saft_xml(xml_path, xsd_path):
    """
    Validates an XML file against an XSD schema.

    Args:
        xml_path (str): Path to the XML file to validate.
        xsd_path (str): Path to the XSD schema file.

    Returns:
        tuple: (bool, list) where bool is True if validation is successful,
               False otherwise. list contains error messages if validation fails.
    """
    try:
        # Parse the XSD schema
        with open(xsd_path, 'rb') as f:
            xsd_doc = etree.XML(f.read())
        schema = etree.XMLSchema(xsd_doc)

        # Parse the XML file
        with open(xml_path, 'rb') as f:
            xml_doc = etree.parse(f)

        # Validate the XML against the schema
        is_valid = schema.validate(xml_doc)

        if is_valid:
            return True, []
        else:
            return False, [str(error) for error in schema.error_log]

    except etree.XMLSchemaParseError as e:
        return False, [f"XSD Parse Error: {e}"]
    except etree.XMLSyntaxError as e:
        return False, [f"XML Parse Error: {e}"]
    except Exception as e:
        return False, [f"An unexpected error occurred: {e}"]

if __name__ == '__main__':
    # This is a placeholder for actual usage.
    # In the ERPNext app, this function will be called with paths to the
    # generated SAF-T XML and the SAFTPT1.04_01.xsd file.
    print("SAF-T XSD Validation script created.")
    print("To use it, call validate_saft_xml(path_to_saft_xml, path_to_xsd)")

    # Example (requires dummy files to run):
    # with open("dummy_saft.xml", "w") as f:
    #     f.write("<AuditFile xmlns='urn:OECD:StandardAuditFile-Tax:PT_1.04_01'><Header><CompanyID>501234567</CompanyID></Header></AuditFile>") # A very minimal validish XML
    # with open("dummy.xsd", "w") as f:
    #     f.write("""
    #     <xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema' 
    #     targetNamespace='urn:OECD:StandardAuditFile-Tax:PT_1.04_01' 
    #     xmlns='urn:OECD:StandardAuditFile-Tax:PT_1.04_01' 
    #     elementFormDefault='qualified'>
    #         <xs:element name='AuditFile'>
    #             <xs:complexType>
    #                 <xs:sequence>
    #                     <xs:element name='Header'>
    #                         <xs:complexType>
    #                             <xs:sequence>
    #                                 <xs:element name='CompanyID' type='xs:string'/>
    #                             </xs:sequence>
    #                         </xs:complexType>
    #                     </xs:element>
    #                 </xs:sequence>
    #             </xs:complexType>
    #         </xs:element>
    #     </xs:schema>
    #     """)
    # valid, errors = validate_saft_xml("dummy_saft.xml", "dummy.xsd")
    # if valid:
    #     print("Dummy XML is valid against dummy XSD.")
    # else:
    #     print("Dummy XML is NOT valid against dummy XSD. Errors:")
    #     for error in errors:
    #         print(error)

