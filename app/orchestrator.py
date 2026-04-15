from typing import List, Optional
import uuid
from .models import (
    AgentState, Status, Personality, CompanyDetails,
    SelectedOffer, Channel, Intent, Stage
)
from .agents import AgentNodes
from .config import settings

class PipelineOrchestrator:

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
        self.state = AgentState(
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

    def step(self) -> AgentState:
        if self.state.status == Status.PLANNING:
            self.state = AgentNodes.planner(self.state)
        elif self.state.status == Status.RESEARCHING:
            self.state = AgentNodes.researcher(self.state)
        elif self.state.status == Status.STRATEGIZING:
            self.state = AgentNodes.strategist(self.state)
        elif self.state.status == Status.WRITING:
            self.state = AgentNodes.writer(self.state)
        elif self.state.status == Status.REVISING:
            self.state = AgentNodes.writer(self.state) # Send it back to the writer
        elif self.state.status == Status.VALIDATING:
            self.state = AgentNodes.critic(self.state)

        if (
            self.state.iteration_count >= self.state.max_iterations
            and self.state.status not in [Status.COMPLETE, Status.FAILED]
        ):
            self.state.status = Status.FAILED
            self.state.next_action = {
                "type": "abort",
                "reason": "Max iterations reached"
            }

        return self.state

    def run_full_pipeline(self) -> List[AgentState]:
        history = [self.state.model_copy(deep=True)]
        max_steps = 50
        steps = 0

        while self.state.status not in [Status.COMPLETE, Status.FAILED] and steps < max_steps:
            self.state = self.step()
            history.append(self.state.model_copy(deep=True))
            steps += 1

        return history