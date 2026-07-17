"""
Interview Prep Agent — generates tailored interview questions
for top candidates based on JD-profile gaps.
"""
from __future__ import annotations

import json
import os
import re
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _is_demo_mode() -> bool:
    if os.getenv("DEMO_MODE", "").lower() in ("true", "1", "yes"):
        return True
    return not os.getenv("ANTHROPIC_API_KEY", "").strip()


INTERVIEW_SYSTEM = """You are a senior technical interviewer. Given a job description and a candidate profile, generate exactly 3 tailored interview questions.

Focus on:
1. Skill gaps between the JD requirements and the candidate's profile
2. Depth-probing questions on claimed experience
3. Role-specific scenario questions

Return ONLY valid JSON — no markdown fences:
{
  "questions": [
    {"question": "...", "focus_area": "skill_gap|depth_probe|scenario", "target_skill": "..."},
    {"question": "...", "focus_area": "...", "target_skill": "..."},
    {"question": "...", "focus_area": "...", "target_skill": "..."}
  ]
}"""


def _generate_with_claude(candidate: Dict[str, Any], parsed_jd: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate interview questions using Claude."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    cand_skills = ", ".join(candidate.get("skills", []))
    jd_skills = ", ".join(parsed_jd.get("required_skills", []))

    user_prompt = (
        f"Job Description:\n"
        f"  Role: {parsed_jd.get('role_type', 'unknown')} ({parsed_jd.get('experience_level', 'mid')} level)\n"
        f"  Required Skills: {jd_skills}\n"
        f"  Summary: {parsed_jd.get('summary', '')}\n\n"
        f"Candidate Profile:\n"
        f"  Name: {candidate.get('name', 'Unknown')}\n"
        f"  Skills: {cand_skills}\n"
        f"  Experience: {candidate.get('experience_years', '?')} years\n"
        f"  Summary: {candidate.get('summary', '')}"
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=INTERVIEW_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    data = json.loads(raw)
    return data.get("questions", [])


def _generate_demo_questions(candidate: Dict[str, Any], parsed_jd: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate realistic demo interview questions based on skill gaps."""
    cand_skills = set(s.lower() for s in candidate.get("skills", []))
    req_skills = set(s.lower() for s in parsed_jd.get("required_skills", []))
    gaps = list(req_skills - cand_skills)
    matched = list(req_skills & cand_skills)

    questions = []

    # Question 1: Skill gap
    if gaps:
        skill = gaps[0]
        questions.append({
            "question": f"Your profile doesn't list {skill} as a core competency. Can you describe a project where you worked with {skill} or a closely related technology, and how you ramped up?",
            "focus_area": "skill_gap",
            "target_skill": skill,
        })
    else:
        questions.append({
            "question": f"You cover all the required skills well. Which of these — {', '.join(list(req_skills)[:3])} — do you consider your deepest expertise, and why?",
            "focus_area": "depth_probe",
            "target_skill": list(req_skills)[0] if req_skills else "general",
        })

    # Question 2: Depth probe on strongest match
    if matched:
        skill = matched[0]
        questions.append({
            "question": f"You list {skill} as a skill. Walk me through the most architecturally complex system you built using {skill}. What trade-offs did you make?",
            "focus_area": "depth_probe",
            "target_skill": skill,
        })
    else:
        questions.append({
            "question": f"With {candidate.get('experience_years', 'several')} years of experience, what's the most challenging technical problem you've solved, and what was your systematic approach?",
            "focus_area": "depth_probe",
            "target_skill": "problem-solving",
        })

    # Question 3: Scenario
    role = parsed_jd.get("role_type", "fullstack")
    scenarios = {
        "backend": "You're tasked with designing a REST API that needs to handle 10x traffic spikes during peak hours. Walk me through your approach to architecture, caching, and graceful degradation.",
        "frontend": "A key user flow has a 40% drop-off rate. How would you diagnose the issue, prototype solutions, and measure improvement?",
        "fullstack": "You inherit a monolithic application that needs to be broken into microservices while maintaining zero downtime. What's your migration strategy?",
        "data": "A critical data pipeline starts producing stale data. How do you debug the issue, implement monitoring, and prevent recurrence?",
        "ml": "Your production ML model's accuracy has degraded by 15% over the last month. Walk me through your investigation and remediation process.",
        "devops": "Your CI/CD pipeline takes 45 minutes per deployment. How would you analyze and optimize it to under 10 minutes?",
    }
    questions.append({
        "question": scenarios.get(role, scenarios["fullstack"]),
        "focus_area": "scenario",
        "target_skill": role,
    })

    return questions


def generate_interview_questions(
    candidates: List[Dict[str, Any]],
    parsed_jd: Dict[str, Any],
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    Generate 3 tailored interview questions for the top-N candidates.
    Returns candidates with an added 'interview_questions' field.
    """
    demo_mode = _is_demo_mode()

    for cand in candidates[:top_n]:
        try:
            if demo_mode:
                questions = _generate_demo_questions(cand, parsed_jd)
            else:
                questions = _generate_with_claude(cand, parsed_jd)
        except Exception as e:
            logger.warning("Interview question generation failed for %s: %s", cand.get("name"), e)
            questions = _generate_demo_questions(cand, parsed_jd)

        cand["interview_questions"] = questions

    # Candidates beyond top_n get empty questions
    for cand in candidates[top_n:]:
        cand["interview_questions"] = []

    return candidates
