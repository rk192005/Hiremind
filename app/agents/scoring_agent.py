"""
Scoring Agent — hybrid scoring (semantic + skill overlap + experience match)
plus an optional Anthropic re-rank pass with justifications.
"""
from __future__ import annotations

import json
import os
import re
import logging
from typing import Any, Dict, List
from app.pipeline.llm_client import generate_text, is_demo_mode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hybrid scoring weights
# ---------------------------------------------------------------------------
W_SEMANTIC = 0.40
W_SKILL = 0.35
W_EXPERIENCE = 0.25


def _skill_overlap_score(candidate_skills: List[str], required_skills: List[str]) -> float:
    """Jaccard-like skill overlap percentage."""
    if not required_skills:
        return 1.0
    cand_set = {s.lower().strip() for s in candidate_skills}
    req_set = {s.lower().strip() for s in required_skills}
    if not req_set:
        return 1.0
    overlap = len(cand_set & req_set)
    return overlap / len(req_set)


def _experience_score(candidate_years: int, min_years: int, max_years: int) -> float:
    """Score based on how well the candidate's experience fits the range."""
    if candidate_years >= min_years and candidate_years <= max_years:
        return 1.0
    if candidate_years < min_years:
        gap = min_years - candidate_years
        return max(0.0, 1.0 - (gap / max(min_years, 1)) * 0.5)
    # Over-qualified — slight penalty
    gap = candidate_years - max_years
    return max(0.3, 1.0 - (gap / max(max_years, 1)) * 0.3)


def compute_hybrid_scores(
    candidates: List[Dict[str, Any]],
    parsed_jd: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Compute hybrid scores for each candidate. Returns sorted list."""
    required_skills = parsed_jd.get("required_skills", [])
    min_years = parsed_jd.get("min_years", 0)
    max_years = parsed_jd.get("max_years", 99)

    scored = []
    for cand in candidates:
        semantic = cand.get("_score", 0.5)  # from retrieval
        skill = _skill_overlap_score(cand.get("skills", []), required_skills)
        exp = _experience_score(cand.get("experience_years", 0), min_years, max_years)

        hybrid = (W_SEMANTIC * semantic) + (W_SKILL * skill) + (W_EXPERIENCE * exp)
        # Normalize to 0–100
        final_score = round(min(100, max(0, hybrid * 100)), 1)

        enriched = dict(cand)
        enriched["score"] = final_score
        enriched["score_breakdown"] = {
            "semantic_similarity": round(semantic, 3),
            "skill_overlap": round(skill, 3),
            "experience_match": round(exp, 3),
        }
        scored.append(enriched)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Anthropic re-rank pass
# ---------------------------------------------------------------------------

RERANK_SYSTEM = """You are an expert technical recruiter. Given a job description and a list of candidates with their scores, provide a brief justification (2-3 sentences) for each candidate's ranking.

Return ONLY valid JSON — an array of objects with this schema:
[
  {
    "name": "Candidate Name",
    "justification": "2-3 sentence justification",
    "score_adjustment": 0
  }
]

score_adjustment should be between -5 and +5 (integer). Only adjust if the algorithmic score clearly misses something important. Most adjustments should be 0."""


def _rerank_with_claude(
    candidates: List[Dict[str, Any]],
    parsed_jd: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Use the LLM client to add justifications and optional score adjustments."""

    # Build prompt
    jd_summary = parsed_jd.get("summary", "")
    skills_str = ", ".join(parsed_jd.get("required_skills", []))
    cand_summaries = []
    for i, c in enumerate(candidates[:10], 1):  # top 10 max for context
        cand_summaries.append(
            f"{i}. {c['name']} — Score: {c['score']}, "
            f"Skills: {', '.join(c.get('skills', []))}, "
            f"Exp: {c.get('experience_years', '?')} yrs"
        )

    user_prompt = (
        f"Job Description Summary: {jd_summary}\n"
        f"Required Skills: {skills_str}\n\n"
        f"Candidates (ranked by algorithm):\n" + "\n".join(cand_summaries)
    )

    raw = generate_text(RERANK_SYSTEM, user_prompt, response_format="json_object")
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    return json.loads(raw)


def _demo_justifications(candidates: List[Dict[str, Any]], parsed_jd: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate realistic demo justifications without API calls."""
    required = parsed_jd.get("required_skills", [])
    results = []
    for c in candidates:
        cand_skills = set(s.lower() for s in c.get("skills", []))
        req_skills = set(s.lower() for s in required)
        matched = cand_skills & req_skills
        missing = req_skills - cand_skills

        if c["score"] >= 75:
            quality = "Strong"
            detail = f"Demonstrates solid alignment with {len(matched)}/{len(req_skills)} required skills."
        elif c["score"] >= 50:
            quality = "Moderate"
            detail = f"Covers {len(matched)}/{len(req_skills)} required skills with some gaps."
        else:
            quality = "Partial"
            detail = f"Matches only {len(matched)}/{len(req_skills)} required skills."

        gap_note = ""
        if missing:
            gap_note = f" Key gaps: {', '.join(list(missing)[:3])}."

        justification = (
            f"{quality} match for the role. {detail}"
            f" {c.get('experience_years', '?')} years of experience "
            f"{'aligns well with' if c.get('score', 0) >= 60 else 'is below'} "
            f"the target range.{gap_note}"
        )

        results.append({
            "name": c["name"],
            "justification": justification,
            "score_adjustment": 0,
        })
    return results


def score_candidates(
    candidates: List[Dict[str, Any]],
    parsed_jd: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Full scoring pipeline:
    1. Compute hybrid scores
    2. Re-rank with Claude (or demo justifications)
    3. Apply score adjustments
    4. Return final sorted list
    """
    scored = compute_hybrid_scores(candidates, parsed_jd)

    # Re-rank pass
    demo_mode = os.getenv("DEMO_MODE", "").lower() in ("true", "1", "yes") or is_demo_mode()

    if demo_mode:
        reranked = _demo_justifications(scored, parsed_jd)
    else:
        try:
            reranked = _rerank_with_claude(scored, parsed_jd)
        except Exception as e:
            logger.warning("Claude re-rank failed (%s), using demo justifications", e)
            reranked = _demo_justifications(scored, parsed_jd)

    # Merge justifications and score adjustments
    rerank_map = {r["name"]: r for r in reranked}
    for cand in scored:
        info = rerank_map.get(cand["name"], {})
        cand["justification"] = info.get("justification", "No justification available.")
        adj = info.get("score_adjustment", 0)
        cand["score"] = round(min(100, max(0, cand["score"] + adj)), 1)

    scored.sort(key=lambda x: x["score"], reverse=True)

    # Assign ranks
    for i, cand in enumerate(scored, 1):
        cand["rank"] = i

    return scored
