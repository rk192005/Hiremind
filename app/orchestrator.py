"""
LangGraph Orchestrator — wires all agents into a stateful graph:

  intake → retrieval → scoring → [interview_prep, bias_audit] (parallel) → merge

Supports optional LangSmith tracing and real-time status callbacks.
"""
from __future__ import annotations

import os
import logging
import asyncio
from typing import Any, Callable, Dict, List, Optional, TypedDict
from concurrent.futures import ThreadPoolExecutor

from langgraph.graph import StateGraph, END

from app.agents.intake_agent import parse_job_description, parse_resumes
from app.agents.retrieval_agent import retrieve_candidates
from app.agents.scoring_agent import score_candidates
from app.agents.interview_prep_agent import generate_interview_questions
from app.agents.bias_audit_agent import audit_candidates

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------


class PipelineState(TypedDict, total=False):
    """Typed state flowing through the LangGraph pipeline."""
    job_description: str
    resume_texts: List[str]
    parsed_jd: Dict[str, Any]
    parsed_resumes: List[Dict[str, Any]]
    retrieved_candidates: List[Dict[str, Any]]
    scored_candidates: List[Dict[str, Any]]
    final_candidates: List[Dict[str, Any]]
    status_log: List[Dict[str, str]]
    error: Optional[str]


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def _update_status(state: PipelineState, agent: str, status: str) -> PipelineState:
    """Helper to append a status update."""
    log = list(state.get("status_log", []))
    log.append({"agent": agent, "status": status})
    return {**state, "status_log": log}


def intake_node(state: PipelineState) -> PipelineState:
    """Parse JD and resumes."""
    logger.info("🔄 Intake agent running")
    state = _update_status(state, "intake", "running")

    parsed_jd = parse_job_description(state["job_description"])
    parsed_resumes = parse_resumes(state["resume_texts"])

    state = {
        **state,
        "parsed_jd": parsed_jd,
        "parsed_resumes": parsed_resumes,
    }
    return _update_status(state, "intake", "completed")


def retrieval_node(state: PipelineState) -> PipelineState:
    """Embed and retrieve top candidates."""
    logger.info("🔄 Retrieval agent running")
    state = _update_status(state, "retrieval", "running")

    retrieved = retrieve_candidates(
        state["parsed_jd"],
        state["parsed_resumes"],
        top_k=20,
    )

    state = {**state, "retrieved_candidates": retrieved}
    return _update_status(state, "retrieval", "completed")


def scoring_node(state: PipelineState) -> PipelineState:
    """Score and rank candidates."""
    logger.info("🔄 Scoring agent running")
    state = _update_status(state, "scoring", "running")

    scored = score_candidates(
        state["retrieved_candidates"],
        state["parsed_jd"],
    )

    state = {**state, "scored_candidates": scored}
    return _update_status(state, "scoring", "completed")


def interview_prep_node(state: PipelineState) -> PipelineState:
    """Generate interview questions for top candidates."""
    logger.info("🔄 Interview prep agent running")
    state = _update_status(state, "interview_prep", "running")

    candidates = [dict(c) for c in state["scored_candidates"]]
    candidates = generate_interview_questions(candidates, state["parsed_jd"], top_n=5)

    state = {**state, "scored_candidates": candidates}
    return _update_status(state, "interview_prep", "completed")


def bias_audit_node(state: PipelineState) -> PipelineState:
    """Run bias audit on scored candidates."""
    logger.info("🔄 Bias audit agent running")
    state = _update_status(state, "bias_audit", "running")

    candidates = [dict(c) for c in state["scored_candidates"]]
    candidates = audit_candidates(candidates)

    state = {**state, "scored_candidates": candidates}
    return _update_status(state, "bias_audit", "completed")


def parallel_node(state: PipelineState) -> PipelineState:
    """Run interview prep and bias audit in parallel using threads."""
    logger.info("🔄 Running interview prep + bias audit in parallel")

    candidates = [dict(c) for c in state["scored_candidates"]]

    # Run both agents in parallel threads
    with ThreadPoolExecutor(max_workers=2) as executor:
        interview_future = executor.submit(
            generate_interview_questions,
            [dict(c) for c in candidates],
            state["parsed_jd"],
            5,
        )
        bias_future = executor.submit(
            audit_candidates,
            [dict(c) for c in candidates],
        )

        interview_results = interview_future.result()
        bias_results = bias_future.result()

    # Merge results: interview questions from one, bias audit from the other
    merged = []
    for i_cand, b_cand in zip(interview_results, bias_results):
        final = dict(i_cand)
        final["bias_audit"] = b_cand.get("bias_audit", {})
        merged.append(final)

    state = {
        **state,
        "scored_candidates": merged,
        "final_candidates": merged,
    }
    state = _update_status(state, "interview_prep", "completed")
    state = _update_status(state, "bias_audit", "completed")
    return _update_status(state, "merge", "completed")


def merge_node(state: PipelineState) -> PipelineState:
    """Final merge — just copies scored_candidates to final_candidates."""
    logger.info("🔄 Merge node — finalizing results")
    state = _update_status(state, "merge", "running")
    state = {**state, "final_candidates": state.get("scored_candidates", [])}
    return _update_status(state, "merge", "completed")


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Build the LangGraph pipeline."""
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("intake", intake_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("scoring", scoring_node)
    graph.add_node("parallel", parallel_node)
    graph.add_node("merge", merge_node)

    # Define edges (linear with parallel fan-out handled inside parallel_node)
    graph.set_entry_point("intake")
    graph.add_edge("intake", "retrieval")
    graph.add_edge("retrieval", "scoring")
    graph.add_edge("scoring", "parallel")
    graph.add_edge("parallel", "merge")
    graph.add_edge("merge", END)

    return graph


_compiled_graph = None


def get_compiled_graph():
    """Return the compiled graph (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        graph = build_graph()

        # Enable LangSmith tracing if configured
        if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
            logger.info("LangSmith tracing enabled (project: %s)", os.getenv("LANGSMITH_PROJECT", "default"))

        _compiled_graph = graph.compile()
    return _compiled_graph


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_pipeline(
    job_description: str,
    resume_texts: List[str],
    status_callback: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, Any]:
    """
    Execute the full ranking pipeline.

    Args:
        job_description: Raw JD text.
        resume_texts: List of raw resume texts.
        status_callback: Optional fn(agent_name, status) called on each transition.

    Returns:
        Final pipeline state dict with 'final_candidates'.
    """
    compiled = get_compiled_graph()

    initial_state: PipelineState = {
        "job_description": job_description,
        "resume_texts": resume_texts,
        "parsed_jd": {},
        "parsed_resumes": [],
        "retrieved_candidates": [],
        "scored_candidates": [],
        "final_candidates": [],
        "status_log": [],
        "error": None,
    }

    try:
        # Stream through the graph to get intermediate states
        final_state = None
        for state_update in compiled.stream(initial_state):
            # state_update is {node_name: state_dict}
            for node_name, node_state in state_update.items():
                final_state = node_state
                if status_callback and "status_log" in node_state:
                    for entry in node_state.get("status_log", []):
                        status_callback(entry["agent"], entry["status"])

        return final_state or initial_state
    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        return {**initial_state, "error": str(e)}


async def run_pipeline_async(
    job_description: str,
    resume_texts: List[str],
    status_callback: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, Any]:
    """Async wrapper for run_pipeline — runs in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        run_pipeline,
        job_description,
        resume_texts,
        status_callback,
    )
