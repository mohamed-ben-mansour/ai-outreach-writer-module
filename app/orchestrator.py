from typing import List, Optional
import uuid

from .models import (
    AgentState, Status, Personality, CompanyDetails,
    SelectedOffer, Channel, Intent, Stage
)
from .graph import run_pipeline
from .config import settings


class PipelineOrchestrator:
    """
    Public interface unchanged — main.py calls this exactly as before.
    Internally delegates to the LangGraph pipeline (graph.py) instead
    of the old manual while-loop.
    """

    def __init__(
        self,
        target_prospect: str,
        target_company: str,
        prospect_role: Optional[str],
        channel: Channel,
        intent: Intent,
        stage: Stage,
        personality: Personality,
        company_details: CompanyDetails,
        selected_offer: SelectedOffer
    ):
        self.initial_state = AgentState(
            task_id=str(uuid.uuid4()),
            target_prospect=target_prospect,
            target_company=target_company,
            prospect_role=prospect_role,
            channel=channel,
            intent=intent,
            stage=stage,
            personality=personality,
            company_details=company_details,
            selected_offer=selected_offer,
            status=Status.PLANNING,
            iteration_count=0,
            max_iterations=settings.MAX_ITERATIONS
        )

    def run_full_pipeline(self) -> List[AgentState]:
        """Run the LangGraph pipeline and return the full step history."""
        return run_pipeline(self.initial_state)
