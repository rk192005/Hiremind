"""
FastAPI application — HireMind Candidate Ranking System.

Endpoints:
  POST /rank          — synchronous ranking
  POST /rank/stream   — SSE streaming with pipeline status updates
  GET  /health        — healthcheck
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.orchestrator import run_pipeline, run_pipeline_async

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class RankRequest(BaseModel):
    """Request body for the /rank endpoint."""
    job_description: str = Field(..., min_length=10, description="Full job description text")
    resumes: List[str] = Field(..., min_length=2, max_length=20, description="List of resume texts (2 to 20 candidates)")


class ScoreBreakdown(BaseModel):
    semantic_similarity: float = 0.0
    skill_overlap: float = 0.0
    experience_match: float = 0.0


class InterviewQuestion(BaseModel):
    question: str
    focus_area: str = ""
    target_skill: str = ""


class BiasFlag(BaseModel):
    type: str
    severity: str = "low"
    detail: str = ""
    category: Optional[str] = None
    words: Optional[List[str]] = None


class BiasAudit(BaseModel):
    risk_level: str = "low"
    risk_score: int = 0
    flags: List[BiasFlag] = []
    disclaimer: str = ""
    distribution_check: Optional[Dict[str, Any]] = None


class CandidateResult(BaseModel):
    rank: int
    name: str
    score: float
    skills: List[str] = []
    experience_years: int = 0
    education: str = ""
    summary: str = ""
    justification: str = ""
    score_breakdown: ScoreBreakdown = ScoreBreakdown()
    interview_questions: List[InterviewQuestion] = []
    bias_audit: BiasAudit = BiasAudit()


class RankResponse(BaseModel):
    """Response body for the /rank endpoint."""
    candidates: List[CandidateResult]
    total_candidates: int
    pipeline_status: str = "completed"
    parsed_jd: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="HireMind — AI Candidate Ranking System",
    description="Multi-agent pipeline for intelligent candidate screening and ranking.",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Healthcheck endpoint."""
    return {
        "status": "healthy",
        "service": "hiremind",
        "demo_mode": os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
                     or not os.getenv("ANTHROPIC_API_KEY", "").strip(),
    }


@app.post("/rank", response_model=RankResponse)
async def rank_candidates(request: RankRequest):
    """
    Run the full ranking pipeline synchronously.
    Returns ranked candidates with scores, justifications,
    interview questions, and bias audit results.
    """
    logger.info("POST /rank — JD length=%d, resumes=%d", len(request.job_description), len(request.resumes))

    try:
        result = await run_pipeline_async(
            job_description=request.job_description,
            resume_texts=request.resumes,
        )
    except Exception as e:
        logger.error("Pipeline error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    # Transform to response model
    candidates = []
    for cand in result.get("final_candidates", []):
        # Build bias audit
        raw_audit = cand.get("bias_audit", {})
        bias_flags = [
            BiasFlag(**f) for f in raw_audit.get("flags", [])
        ]
        bias_audit = BiasAudit(
            risk_level=raw_audit.get("risk_level", "low"),
            risk_score=raw_audit.get("risk_score", 0),
            flags=bias_flags,
            disclaimer=raw_audit.get("disclaimer", ""),
            distribution_check=raw_audit.get("distribution_check"),
        )

        # Build interview questions
        iq = [
            InterviewQuestion(**q) for q in cand.get("interview_questions", [])
        ]

        # Build score breakdown
        sb = cand.get("score_breakdown", {})

        candidates.append(CandidateResult(
            rank=cand.get("rank", 0),
            name=cand.get("name", "Unknown"),
            score=cand.get("score", 0),
            skills=cand.get("skills", []),
            experience_years=cand.get("experience_years", 0),
            education=cand.get("education", ""),
            summary=cand.get("summary", ""),
            justification=cand.get("justification", ""),
            score_breakdown=ScoreBreakdown(**sb) if sb else ScoreBreakdown(),
            interview_questions=iq,
            bias_audit=bias_audit,
        ))

    return RankResponse(
        candidates=candidates,
        total_candidates=len(candidates),
        pipeline_status="completed",
        parsed_jd=result.get("parsed_jd"),
    )


@app.post("/rank/stream")
async def rank_candidates_stream(request: RankRequest):
    """
    SSE endpoint that streams pipeline status updates in real-time.
    Each event has the agent name and its current status.
    Final event contains the full results.
    """
    logger.info("POST /rank/stream — JD length=%d, resumes=%d", len(request.job_description), len(request.resumes))

    async def event_generator():
        status_updates = []
        seen_statuses = set()

        def status_callback(agent: str, status: str):
            key = f"{agent}:{status}"
            if key not in seen_statuses:
                seen_statuses.add(key)
                status_updates.append({"agent": agent, "status": status})

        # Run pipeline in background
        loop = asyncio.get_event_loop()
        pipeline_task = loop.run_in_executor(
            None,
            run_pipeline,
            request.job_description,
            request.resumes,
            status_callback,
        )

        # Poll and yield status updates
        while not pipeline_task.done():
            while status_updates:
                update = status_updates.pop(0)
                yield {
                    "event": "status",
                    "data": json.dumps(update),
                }
            await asyncio.sleep(0.3)

        # Yield any remaining status updates
        while status_updates:
            update = status_updates.pop(0)
            yield {
                "event": "status",
                "data": json.dumps(update),
            }

        # Get result
        result = await pipeline_task

        # Yield final result
        candidates_data = []
        for cand in result.get("final_candidates", []):
            # Clean for JSON serialization (remove internal fields)
            clean = {k: v for k, v in cand.items() if not k.startswith("_")}
            candidates_data.append(clean)

        yield {
            "event": "result",
            "data": json.dumps({
                "candidates": candidates_data,
                "total_candidates": len(candidates_data),
                "pipeline_status": "completed" if not result.get("error") else "error",
                "parsed_jd": result.get("parsed_jd"),
                "error": result.get("error"),
            }),
        }

        yield {
            "event": "done",
            "data": json.dumps({"status": "complete"}),
        }

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
