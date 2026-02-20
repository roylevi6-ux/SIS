"""SIS Agent modules — 10-agent sequential-parallel pipeline.

Pipeline:
  Agent 1 (sequential) → Agents 2-8 (parallel) → Agent 9 (sequential) → Agent 10 (sequential)
"""

from .runner import AgentError, AgentResult, run_agent, strip_for_downstream
from .schemas import ConfidenceAssessment, EvidenceCitation, ENVELOPE_PROMPT_FRAGMENT

from .stage_classifier import StageClassifierOutput, StageClassifierFindings, run_stage_classifier
from .relationship import RelationshipOutput, RelationshipFindings, run_relationship
from .commercial import CommercialOutput, CommercialFindings, run_commercial
from .momentum import MomentumOutput, MomentumFindings, run_momentum
from .technical import TechnicalOutput, TechnicalFindings, run_technical
from .economic_buyer import EconomicBuyerOutput, EconomicBuyerFindings, run_economic_buyer
from .msp_next_steps import MSPNextStepsOutput, MSPNextStepsFindings, run_msp_next_steps
from .competitive import CompetitiveOutput, CompetitiveFindings, run_competitive
from .open_discovery import OpenDiscoveryOutput, OpenDiscoveryFindings, run_open_discovery
from .synthesis import SynthesisOutput, run_synthesis

__all__ = [
    # Runner
    "run_agent",
    "AgentError",
    "AgentResult",
    "strip_for_downstream",
    # Shared schemas
    "EvidenceCitation",
    "ConfidenceAssessment",
    "ENVELOPE_PROMPT_FRAGMENT",
    # Agent 1: Stage & Progress
    "run_stage_classifier",
    "StageClassifierOutput",
    "StageClassifierFindings",
    # Agent 2: Relationship & Power Map
    "run_relationship",
    "RelationshipOutput",
    "RelationshipFindings",
    # Agent 3: Commercial & Risk
    "run_commercial",
    "CommercialOutput",
    "CommercialFindings",
    # Agent 4: Momentum & Engagement
    "run_momentum",
    "MomentumOutput",
    "MomentumFindings",
    # Agent 5: Technical Validation
    "run_technical",
    "TechnicalOutput",
    "TechnicalFindings",
    # Agent 6: Economic Buyer
    "run_economic_buyer",
    "EconomicBuyerOutput",
    "EconomicBuyerFindings",
    # Agent 7: MSP & Next Steps
    "run_msp_next_steps",
    "MSPNextStepsOutput",
    "MSPNextStepsFindings",
    # Agent 8: Competitive Displacement
    "run_competitive",
    "CompetitiveOutput",
    "CompetitiveFindings",
    # Agent 9: Open Discovery
    "run_open_discovery",
    "OpenDiscoveryOutput",
    "OpenDiscoveryFindings",
    # Agent 10: Synthesis
    "run_synthesis",
    "SynthesisOutput",
]
