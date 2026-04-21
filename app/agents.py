from typing import List, Dict, Any
import uuid
from .models import (
    AgentState, Status, Strategy, MessageDraft,
    SentenceAttribution, Validation, Signal, ActionType
)
from .tools import ResearchTools, ReasoningTools
from .llm_service import llm_service
from .config import settings
from .memory import MemoryService   # NEW

class AgentNodes:

    @staticmethod
    def planner(state: AgentState) -> AgentState:
        """Decides what step to run next based on what's missing"""

        needs_research = not state.research_signals
        needs_strategy = state.research_signals and not state.strategy
        needs_draft = state.strategy and not state.draft
        needs_validation = state.draft and not state.validation

        if needs_research:
            state.status = Status.RESEARCHING
            state.next_action = {
                "step": "research",
                "reason": "No research signals yet"
            }
        elif needs_strategy:
            state.status = Status.STRATEGIZING
            state.next_action = {
                "step": "strategize",
                "reason": "Research done, building strategy"
            }
        elif needs_draft:
            state.status = Status.WRITING
            state.next_action = {
                "step": "write",
                "reason": "Strategy ready, writing message"
            }
        elif needs_validation:
            state.status = Status.VALIDATING
            state.next_action = {
                "step": "validate",
                "reason": "Draft ready, validating quality"
            }
        else:
            state.status = Status.COMPLETE

        return state

    @staticmethod
    def researcher(state: AgentState) -> AgentState:
        """Gathers research signals and loads prospect memory"""

        # --- NEW: Load prospect memory ---
        prospect_memory = MemoryService.prospects.get_or_create(
            name=state.target_prospect,
            company=state.target_company,
            role=state.prospect_role
        )

        # --- NEW: Hard stop if do not contact ---
        if prospect_memory.do_not_contact:
            state.status = Status.FAILED
            state.next_action = {
                "type": ActionType.ABORT,
                "reason": f"{state.target_prospect} is marked as do not contact"
            }
            return state

        # --- NEW: Store memory context so strategist and writer can use it ---
        state.memory["prospect_record"] = prospect_memory.model_dump()
        state.memory["hooks_already_used"] = prospect_memory.hooks_used
        state.memory["angles_already_tried"] = prospect_memory.angles_tried
        state.memory["times_contacted_before"] = prospect_memory.times_contacted
        state.memory["ever_replied"] = prospect_memory.ever_replied

        # --- UNCHANGED: Normal research flow ---
        linkedin_signals = ResearchTools.fetch_linkedin_posts(
            state.target_prospect,
            state.target_company
        )

        company_signals = ResearchTools.fetch_company_news(
            state.target_company
        )

        crm_data = ResearchTools.get_crm_history(
            state.target_prospect
        )

        state.research_signals = linkedin_signals + company_signals
        state.memory["crm_history"] = crm_data
        state.memory["total_signals_found"] = len(state.research_signals)
        state.status = Status.STRATEGIZING

        return state

    @staticmethod
    def strategist(state: AgentState) -> AgentState:
        """Uses LLM to pick hooks and build strategy"""

        if not state.research_signals:
            state.strategy = Strategy(
                primary_hook=f"Your work at {state.target_company}",
                secondary_hook="Industry developments",
                angle="General professional connection",
                tone=state.personality.base_template.value,
                cta_style=state.selected_offer.cta if state.selected_offer else "soft_question",
                reasoning="No research signals available"
            )
            state.status = Status.WRITING
            return state

        try:
            # Step 1: Analyze signals
            analysis = llm_service.analyze_research_signals(
                signals=state.research_signals,
                prospect_name=state.target_prospect,
                company=state.target_company,
                personality=state.personality,
                # NEW: Pass what hooks we have already used so LLM avoids repeating them
                hooks_already_used=state.memory.get("hooks_already_used", [])
            )

            state.llm_calls.append({
                "step": "strategist",
                "purpose": "analyze_research_signals",
                "output": analysis
            })

            # Step 2: Build full strategy
            strategy = llm_service.create_strategy(
                primary_hook=analysis.get("primary_hook"),
                secondary_hook=analysis.get("secondary_hook"),
                prospect_name=state.target_prospect,
                company=state.target_company,
                prospect_role=state.prospect_role,
                personality=state.personality,
                company_details=state.company_details,
                selected_offer=state.selected_offer,
                channel=state.channel,
                intent=state.intent,
                stage=state.stage,
                # NEW: Pass what angles we have already tried so LLM avoids repeating them
                angles_already_tried=state.memory.get("angles_already_tried", [])
            )

            state.llm_calls.append({
                "step": "strategist",
                "purpose": "create_strategy",
                "output": strategy.dict()
            })

            state.strategy = strategy

        except Exception as e:
            state.strategy = Strategy(
                primary_hook=state.research_signals[0].content,
                secondary_hook=state.research_signals[1].content if len(state.research_signals) > 1 else "",
                angle="Professional connection",
                tone=state.personality.base_template.value,
                cta_style=state.selected_offer.cta if state.selected_offer else "soft_question",
                reasoning=f"Fallback due to error: {str(e)}"
            )
            state.memory["strategist_error"] = str(e)

        state.status = Status.WRITING
        return state

    @staticmethod
    def writer(state: AgentState) -> AgentState:
        """Uses LLM to write the message, or revise it based on feedback."""

        if not state.strategy:
            state.status = Status.PLANNING
            return state

        # --- NEW: Check if this is a revision call and get the feedback ---
        is_revision = state.status == Status.REVISING
        previous_draft = state.draft.body if is_revision and state.draft else None
        feedback = state.next_action.get("feedback") if is_revision and state.next_action else None

        try:
            message_data = llm_service.write_message(
                strategy=state.strategy,
                prospect_name=state.target_prospect,
                company=state.target_company,
                prospect_role=state.prospect_role,
                personality=state.personality,
                company_details=state.company_details,
                selected_offer=state.selected_offer,
                channel=state.channel,
                intent=state.intent,
                stage=state.stage,
                times_contacted_before=state.memory.get("times_contacted_before", 0),
                last_message_sent=state.memory.get("prospect_record", {}).get("last_message_sent"),
                
                # --- NEW: Pass the revision context to the LLM service ---
                is_revision=is_revision,
                previous_draft=previous_draft,
                feedback_from_critic=feedback
            )

            state.llm_calls.append({
                "step": "writer",
                "purpose": "write_message (revision)" if is_revision else "write_message (first_draft)",
                "output": message_data
            })

            attributions = [
                SentenceAttribution(
                    text=item.get("text", ""),
                    driven_by=item.get("driven_by", []),
                    purpose=item.get("purpose", "unknown")
                )
                for item in message_data.get("sentence_breakdown", [])
            ]

            state.draft = MessageDraft(
                body=message_data.get("body", ""),
                subject=message_data.get("subject"),
                sentence_attribution=attributions
            )

        except Exception as e:
            fallback = f"Hi {state.target_prospect}, came across your work at {state.target_company} and wanted to connect."
            state.draft = MessageDraft(
                body=fallback,
                subject=None,
                sentence_attribution=[
                    SentenceAttribution(
                        text=fallback,
                        driven_by=["fallback"],
                        purpose="complete_message"
                    )
                ]
            )
            state.memory["writer_error"] = str(e)

        state.status = Status.VALIDATING
        return state

    # --- UPDATED critic FUNCTION ---
    @staticmethod
    def critic(state: AgentState) -> AgentState:
        """Uses LLM to validate the message and decides on refinement."""

        if not state.draft:
            state.status = Status.PLANNING
            return state

        try:
            validation_result = llm_service.validate_message(
                message=state.draft.body,
                prospect_name=state.target_prospect,
                channel=state.channel,
                personality=state.personality
            )
            state.llm_calls.append({"step": "critic", "purpose": "validate_message", "output": validation_result})

            # Post-LLM rule checks — these are deterministic and override the LLM
            extra_issues: List[str] = []
            if ReasoningTools.detect_overpersonalization(state.draft.body):
                extra_issues.append("Remove overly personal references that may feel intrusive.")
                validation_result["score"] = max(0, validation_result["score"] - 20)
            for phrase in state.personality.never_use_phrases:
                if phrase.lower() in state.draft.body.lower():
                    extra_issues.append(f"Remove banned phrase: '{phrase}'.")
                    validation_result["score"] = max(0, validation_result["score"] - 10)
            if ReasoningTools.detect_placeholder_text(state.draft.body):
                extra_issues.append("Remove all placeholder text like [Company], [Name], [Result] — use only real data or omit entirely.")
                validation_result["score"] = max(0, validation_result["score"] - 40)

            if extra_issues:
                validation_result["warnings"].extend(extra_issues)
                validation_result["valid"] = False
                # Append to suggested_fixes so the writer knows what to fix
                existing_fixes = validation_result.get("suggested_fixes") or ""
                combined = (existing_fixes + " " + " | ".join(extra_issues)).strip()
                validation_result["suggested_fixes"] = combined

            # Final safety: if score is below threshold, force valid=False
            if validation_result.get("score", 0) < settings.MIN_QUALITY_SCORE:
                validation_result["valid"] = False

            state.validation = Validation(**validation_result)
        except Exception as e:
            state.validation = Validation(valid=False, score=0, warnings=[f"Validation failed: {str(e)}"], suggested_fixes="Rewrite the message from scratch.")
            state.memory["critic_error"] = str(e)

        # --- UPDATED: Refinement Logic ---

        # Case 1: Validation passed
        if state.validation.valid:
            # If human review is enabled, pause here instead of completing
            if settings.ENABLE_HUMAN_REVIEW:
                state.status = Status.AWAITING_HUMAN
                state.next_action = {
                    "type": ActionType.HUMAN_REVIEW,
                    "reason": f"Message approved by critic (score: {state.validation.score}). Awaiting human decision."
                }
            else:
                state.status = Status.COMPLETE
                state.next_action = {"type": ActionType.SAVE_DRAFT, "reason": f"Score: {state.validation.score}"}

            # Record everything in memory regardless
            MemoryService.prospects.record_outreach(name=state.target_prospect, company=state.target_company, channel=state.channel.value, stage=state.stage.value, hook_used=state.strategy.primary_hook if state.strategy else "", angle_used=state.strategy.angle if state.strategy else "", offer_name=state.selected_offer.offer_name if state.selected_offer else "", message_sent=state.draft.body if state.draft else "")
            MemoryService.learning.record_generation(quality_score=state.validation.score, channel=state.channel.value, stage=state.stage.value, template=state.personality.base_template.value)
            if state.selected_offer:
                MemoryService.offers.record_usage(offer_name=state.selected_offer.offer_name, channel=state.channel.value, angle=state.strategy.angle if state.strategy else "", prospect_role=state.prospect_role, quality_score=state.validation.score)

        # Case 2: Validation failed, but we have specific fixes to try (and haven't exhausted retries)
        elif state.validation.suggested_fixes and state.iteration_count <= state.max_iterations:
            state.status = Status.REVISING  # Tell the orchestrator to go back to the writer
            state.iteration_count += 1
            state.next_action = {
                "type": ActionType.RETRY,
                "reason": f"Validation failed (score: {state.validation.score}). Attempting revision.",
                "feedback": state.validation.suggested_fixes # This is the crucial part
            }
            # We do NOT clear state.draft, the writer needs it to revise

        # Case 3: Validation failed badly, or we're out of retries. Start over from scratch.
        else:
            if state.iteration_count >= state.max_iterations:
                state.status = Status.FAILED
                state.next_action = {"type": ActionType.ABORT, "reason": f"Max iterations hit, final score: {state.validation.score}"}
            else: # Major failure with no suggested fixes
                state.status = Status.PLANNING
                state.iteration_count += 1
                state.draft = None # Clear draft for a full rewrite
                state.strategy = None # Clear strategy, it might have been the problem
                state.next_action = {"type": ActionType.RETRY, "reason": f"Major failure (score {state.validation.score}), planning full retry."}

        return state