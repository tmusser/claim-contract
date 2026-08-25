from .binding import ContractBinding, build_contract_binding
from .io import load_contract
from .metadata import REPORT_SCHEMA_VERSION, TOOL_VERSION
from .models import Finding, Report, Severity, Verdict
from .profiles import ProfileManifest, RuleSpec, get_profile_manifest
from .validator import validate_contract

__all__ = [
    "ContractBinding",
    "Finding",
    "ProfileManifest",
    "Report",
    "RuleSpec",
    "Severity",
    "Verdict",
    "REPORT_SCHEMA_VERSION",
    "build_contract_binding",
    "get_profile_manifest",
    "load_contract",
    "validate_contract",
]

__version__ = TOOL_VERSION
