__version__ = "1.0.0"

# Explicitly import doctypes to aid discovery/search
try:
    from .doctype.portugal_compliance_settings.portugal_compliance_settings import PortugalComplianceSettings
    from .doctype.document_series_pt.document_series_pt import DocumentSeriesPT
    from .doctype.compliance_audit_log.compliance_audit_log import ComplianceAuditLog
    from .doctype.taxonomy_code.taxonomy_code import TaxonomyCode
except ImportError:
    # Handle cases where doctypes might not exist during initial setup/migration phases
    pass

