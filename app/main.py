from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import List, Dict
import logging

from .models import AgentState, GenerateRequest, Status, HumanDecision, ReviewResponse
from .orchestrator import PipelineOrchestrator
from .config import settings
from .mcp_server import app as mcp_app
from .send_tools import send_email, send_linkedin_dm
from .graph import run_pipeline
from .memory import MemoryService
from mcp.server.sse import SseServerTransport

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# In-memory store for drafts awaiting human review — keyed by task_id
# Replace with Redis when you add persistence
_pending_review: Dict[str, AgentState] = {}

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-agent AI system for generating personalized outreach messages"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP SSE transport — external agents connect to /mcp
sse_transport = SseServerTransport("/mcp/messages")


@app.get("/mcp")
async def mcp_sse_endpoint(request: Request):
    """SSE endpoint for MCP agent-to-agent connections."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request.send
    ) as streams:
        await mcp_app.run(
            streams[0], streams[1], mcp_app.create_initialization_options()
        )
    return Response()


@app.post("/mcp/messages")
async def mcp_messages(request: Request):
    """Message posting endpoint required by the SSE transport."""
    await sse_transport.handle_post_message(
        request.scope, request.receive, request.send
    )
    return Response()


@app.get("/")
async def root():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "using_mock_data": settings.USE_MOCK_DATA
    }


@app.post("/api/generate", response_model=List[AgentState])
async def generate_outreach(request: GenerateRequest):
    """Full pipeline. Returns step-by-step history of agent states."""
    try:
        logger.info(
            f"Generating for {request.target_prospect} at {request.target_company} "
            f"| channel={request.channel} stage={request.stage} intent={request.intent}"
        )
        orchestrator = PipelineOrchestrator(
            target_prospect=request.target_prospect,
            target_company=request.target_company,
            prospect_role=request.prospect_role,
            channel=request.channel,
            intent=request.intent,
            stage=request.stage,
            personality=request.personality,
            company_details=request.company_details,
            selected_offer=request.selected_offer
        )
        history = orchestrator.run_full_pipeline()
        final = history[-1]
        logger.info(
            f"Done | status={final.status} "
            f"score={final.validation.score if final.validation else 'N/A'}"
        )
        return history
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/simple")
async def generate_simple(request: GenerateRequest):
    """Same pipeline but returns only the final message."""
    try:
        orchestrator = PipelineOrchestrator(
            target_prospect=request.target_prospect,
            target_company=request.target_company,
            prospect_role=request.prospect_role,
            channel=request.channel,
            intent=request.intent,
            stage=request.stage,
            personality=request.personality,
            company_details=request.company_details,
            selected_offer=request.selected_offer
        )
        history = orchestrator.run_full_pipeline()
        final = history[-1]

        if final.status == Status.COMPLETE and final.draft:
            return {
                "success": True,
                "task_id": final.task_id,
                "channel": final.channel,
                "stage": final.stage,
                "message": final.draft.body,
                "subject": final.draft.subject,
                "score": final.validation.score if final.validation else None,
                "warnings": final.validation.warnings if final.validation else [],
                "attribution": [a.dict() for a in final.draft.sentence_attribution]
            }
        elif final.status == Status.AWAITING_HUMAN and final.draft:
            # Park the state so the review endpoint can pick it up
            _pending_review[final.task_id] = final
            return {
                "success": True,
                "awaiting_human": True,
                "task_id": final.task_id,
                "message": final.draft.body,
                "subject": final.draft.subject,
                "score": final.validation.score if final.validation else None,
                "warnings": final.validation.warnings if final.validation else [],
                "review_url": f"/api/review/{final.task_id}"
            }
        else:
            return {
                "success": False,
                "task_id": final.task_id,
                "error": final.next_action.get("reason") if final.next_action else "Unknown error",
                "score": final.validation.score if final.validation else None,
                "warnings": final.validation.warnings if final.validation else []
            }
    except Exception as e:
        logger.error(f"Simple generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reply")
async def record_reply(
    prospect_name: str,
    prospect_company: str,
    sentiment: str = "positive"
):
    """
    Call this when a prospect replies to a message.
    Updates prospect memory and feeds the learning system.
    sentiment: positive | negative | neutral
    """
    MemoryService.prospects.mark_replied(
        name=prospect_name,
        company=prospect_company,
        sentiment=sentiment
    )
    return {"success": True, "message": f"Reply recorded for {prospect_name} at {prospect_company}"}


@app.get("/api/review/{task_id}", response_model=ReviewResponse)
async def get_review(task_id: str):
    """Get the draft waiting for human approval."""
    state = _pending_review.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="No draft pending review for this task_id")
    return ReviewResponse(
        task_id=state.task_id,
        prospect=state.target_prospect,
        company=state.target_company,
        channel=state.channel.value,
        message=state.draft.body,
        subject=state.draft.subject,
        score=state.validation.score if state.validation else 0,
        warnings=state.validation.warnings if state.validation else [],
    )


@app.post("/api/review/{task_id}/decision")
async def submit_decision(task_id: str, decision: HumanDecision):
    """
    Approve → send via email or LinkedIn.
    Reject  → rerun writer with your feedback.
    """
    state = _pending_review.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="No draft pending review for this task_id")

    if decision.approved:
        channel = state.channel.value
        message = state.draft.body
        subject = state.draft.subject or ""

        if channel == "email":
            if not decision.prospect_email:
                raise HTTPException(status_code=400, detail="prospect_email is required for email channel")
            result = send_email(to_address=decision.prospect_email, subject=subject, body=message)

        elif channel in ("linkedin_dm", "linkedin_inmail"):
            if not decision.prospect_linkedin_id:
                raise HTTPException(status_code=400, detail="prospect_linkedin_id is required for LinkedIn channel")
            result = send_linkedin_dm(
                account_id=settings.UNIPILE_DEFAULT_ACCOUNT_ID or "",
                message=message,
                attendee_provider_id=decision.prospect_linkedin_id,
                attendee_name=state.target_prospect,
            )
        else:
            result = {"success": True, "channel": channel, "note": "Manual send required for this channel"}

        if result.get("success"):
            state.status = Status.COMPLETE
            _pending_review.pop(task_id, None)
            return {"success": True, "sent": True, "result": result}
        else:
            raise HTTPException(status_code=500, detail=f"Send failed: {result.get('error')}")

    else:
        feedback = decision.feedback or "Human reviewer rejected this draft. Please rewrite it."
        state.status = Status.REVISING
        state.iteration_count += 1
        state.next_action = {"type": "retry", "reason": "Rejected by human reviewer", "feedback": feedback}
        _pending_review.pop(task_id, None)

        history = run_pipeline(state)
        final = history[-1]

        if final.status == Status.AWAITING_HUMAN and final.draft:
            _pending_review[final.task_id] = final
            return {
                "success": True,
                "rewritten": True,
                "awaiting_human": True,
                "task_id": final.task_id,
                "message": final.draft.body,
                "subject": final.draft.subject,
                "score": final.validation.score if final.validation else None,
                "review_url": f"/api/review/{final.task_id}",
            }
        elif final.status == Status.COMPLETE and final.draft:
            return {"success": True, "rewritten": True, "message": final.draft.body}
        else:
            return {"success": False, "error": final.next_action.get("reason") if final.next_action else "Rewrite failed"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )
