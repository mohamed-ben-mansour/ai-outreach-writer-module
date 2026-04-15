from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import logging

from .models import AgentState, GenerateRequest, Status
from .orchestrator import PipelineOrchestrator
from .config import settings

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

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
    """
    Full pipeline. Returns step-by-step history of agent states.
    """
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
    """
    Same pipeline but returns only the final message.
    """
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )