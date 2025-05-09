from lxml import etree

class SaftValidator:
    """
    A class to validate SAF-T XML files against an XSD schema.
    """
    def __init__(self, xsd_path):
        """
        Initializes the validator by parsing the XSD schema.

        Args:
            xsd_path (str): Path to the XSD schema file.
        
        Raises:
            etree.XMLSchemaParseError: If the XSD schema cannot be parsed.
            FileNotFoundError: If the XSD file does not exist.
        """
        self.xsd_path = xsd_path
        self.schema = None
        try:
            # Parse the XSD schema
            with open(xsd_path, 'rb') as f:
                xsd_doc = etree.XML(f.read())
            self.schema = etree.XMLSchema(xsd_doc)
            print(f"Successfully parsed XSD schema: {xsd_path}")
        except FileNotFoundError:
            print(f"Error: XSD file not found at {xsd_path}")
            raise
        except etree.XMLSchemaParseError as e:
            print(f"XSD Parse Error for {xsd_path}: {e}")
            # Propagate the error so the caller knows schema loading failed
            raise 
        except Exception as e:
            print(f"An unexpected error occurred during XSD parsing for {xsd_path}: {e}")
            raise

    def validate_xml_file(self, xml_path):
        """
        Validates an XML file against the loaded XSD schema.

        Args:
            xml_path (str): Path to the XML file to validate.

        Returns:
            tuple: (bool, list) where bool is True if validation is successful,
                   False otherwise. list contains error messages if validation fails.
        """
        if not self.schema:
            return False, ["XSD schema was not loaded successfully. Cannot validate."]
        
        try:
            # Parse the XML file
            with open(xml_path, 'rb') as f:
                xml_doc = etree.parse(f)

            # Validate the XML against the schema
            is_valid = self.schema.validate(xml_doc)

            if is_valid:
                return True, []
            else:
                return False, [str(error) for error in self.schema.error_log]

        except FileNotFoundError:
            return False, [f"Error: XML file not found at {xml_path}"]
        except etree.XMLSyntaxError as e:
            return False, [f"XML Parse Error for {xml_path}: {e}"]
        except Exception as e:
            return False, [f"An unexpected error occurred during XML validation of {xml_path}: {e}"]

if __name__ == '__main__':
    # This section is for direct script execution testing (optional)
    print("SaftValidator class defined. This script can be imported as a module.")
    print("To use it from another script:")
    print("from saft_validator import SaftValidator")
    print("validator = SaftValidator('path_to_your.xsd')")
    print("is_valid, errors = validator.validate_xml_file('path_to_your_saft.xml')")

    # Example of direct testing (requires dummy files or actual paths)
    # XSD_TEST_PATH = "/home/ubuntu/SAFTPT1.04_01_official_utf8_no_asserts_v3.xsd" # or a simpler dummy XSD
    # XML_TEST_PATH = "/home/ubuntu/minimal_saft_for_validation.xml" # or a simpler dummy XML

    # try:
    #     print(f"\nAttempting direct test with XSD: {XSD_TEST_PATH} and XML: {XML_TEST_PATH}")
    #     validator_instance = SaftValidator(XSD_TEST_PATH)
    #     if validator_instance.schema:
    #         valid, errors = validator_instance.validate_xml_file(XML_TEST_PATH)
    #         if valid:
    #             print("Direct test: XML is valid.")
    #         else:
    #             print("Direct test: XML is NOT valid. Errors:")
    #             for err in errors:
    #                 print(f"- {err}")
    #     else:
    #         print("Direct test: Schema not loaded, cannot validate XML.")
    # except Exception as e:
    #     print(f"Direct test failed: {e}")

