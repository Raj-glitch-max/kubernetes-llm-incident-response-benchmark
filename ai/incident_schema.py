from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class IncidentInput:
    """
    Everything that goes INTO the LLM.
    Think about it as: what would a real SRE look at when an incident fires?
    """
    pod_logs: str
    describe_output: str
    events: str
    alert_name: str
    chaos_metadata: Dict[str, Any]

@dataclass
class LLMOutput:
    """
    Everything that comes OUT of the LLM.
    Output must always be valid JSON matching this schema.
    """
    root_cause_description: str
    category_label: str  # Must match one of your 4 chaos types
    confidence_score: float
    evidence_cited: List[str]
    suggested_fix: str
    kubectl_commands: List[str]
