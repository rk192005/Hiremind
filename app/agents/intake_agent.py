"""
Intake Agent — parses job descriptions and resumes using Anthropic Claude.
Falls back to heuristic extraction in demo mode.
"""
from __future__ import annotations

import json
import os
import re
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Anthropic-powered parsing
# ---------------------------------------------------------------------------

from app.pipeline.llm_client import generate_text, is_demo_mode


# ---------------------------------------------------------------------------
# Job Description parsing
# ---------------------------------------------------------------------------

JD_SYSTEM_PROMPT = """You are a precise JSON extraction engine. Given a job description, extract structured data.
Return ONLY valid JSON with this exact schema — no markdown fences, no commentary:
{
  "required_skills": ["skill1", "skill2"],
  "nice_to_have_skills": ["skill1"],
  "experience_level": "senior|mid|junior|lead|staff",
  "role_type": "backend|frontend|fullstack|data|ml|devops|other",
  "min_years": 0,
  "max_years": 99,
  "summary": "one-line summary of the role"
}"""


def parse_job_description(jd: str) -> Dict[str, Any]:
    """Parse a job description into structured fields."""
    if is_demo_mode():
        return _demo_parse_jd(jd)

    try:
        raw = generate_text(JD_SYSTEM_PROMPT, jd, response_format="json_object")
        # Strip markdown fences if present
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)
        return json.loads(raw)
    except Exception as e:
        logger.warning("Claude JD parse failed (%s), using heuristic fallback", e)
        return _demo_parse_jd(jd)


# ---------------------------------------------------------------------------
# Resume parsing
# ---------------------------------------------------------------------------

RESUME_SYSTEM_PROMPT = """You are a precise JSON extraction engine. Given a resume/CV text, extract structured data.
Return ONLY valid JSON with this exact schema — no markdown fences, no commentary:
{
  "name": "Full Name",
  "skills": ["skill1", "skill2"],
  "experience_years": 0,
  "education": "highest degree and institution",
  "summary": "2-3 sentence professional summary"
}"""


def parse_resume(resume_text: str) -> Dict[str, Any]:
    """Parse a single resume into structured fields."""
    if is_demo_mode():
        return _demo_parse_resume(resume_text)

    try:
        raw = generate_text(RESUME_SYSTEM_PROMPT, resume_text, response_format="json_object")
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)
        return json.loads(raw)
    except Exception as e:
        logger.warning("Claude resume parse failed (%s), using heuristic fallback", e)
        return _demo_parse_resume(resume_text)


def parse_resumes(resume_texts: List[str]) -> List[Dict[str, Any]]:
    """Parse multiple resumes."""
    return [parse_resume(r) for r in resume_texts]


# ---------------------------------------------------------------------------
# Demo / fallback heuristics
# ---------------------------------------------------------------------------

def _is_demo_mode() -> bool:
    if os.getenv("DEMO_MODE", "").lower() in ("true", "1", "yes"):
        return True
    return is_demo_mode()


_COMMON_SKILLS = [
    "python", "javascript", "typescript", "react", "node.js", "java", "go",
    "rust", "sql", "postgresql", "mongodb", "redis", "docker", "kubernetes",
    "aws", "gcp", "azure", "terraform", "ci/cd", "git", "linux",
    "machine learning", "deep learning", "pytorch", "tensorflow", "nlp",
    "fastapi", "django", "flask", "graphql", "rest api", "microservices",
    "kafka", "spark", "airflow", "data engineering", "agile", "scrum",
]


def _demo_parse_jd(jd: str) -> Dict[str, Any]:
    """Heuristic JD parsing for demo mode."""
    jd_lower = jd.lower()
    skills = [s for s in _COMMON_SKILLS if s in jd_lower]
    if not skills:
        skills = ["python", "communication", "problem-solving"]

    # Guess experience level
    level = "mid"
    for keyword, lvl in [("senior", "senior"), ("lead", "lead"), ("staff", "staff"),
                         ("junior", "junior"), ("principal", "lead"), ("intern", "junior")]:
        if keyword in jd_lower:
            level = lvl
            break

    # Guess role type
    role = "fullstack"
    for keyword, rt in [("backend", "backend"), ("frontend", "frontend"),
                        ("data engineer", "data"), ("machine learning", "ml"),
                        ("ml engineer", "ml"), ("devops", "devops"), ("sre", "devops")]:
        if keyword in jd_lower:
            role = rt
            break

    return {
        "required_skills": skills[:10],
        "nice_to_have_skills": skills[10:15],
        "experience_level": level,
        "role_type": role,
        "min_years": {"junior": 0, "mid": 2, "senior": 5, "lead": 7, "staff": 8}.get(level, 2),
        "max_years": {"junior": 2, "mid": 5, "senior": 10, "lead": 15, "staff": 20}.get(level, 10),
        "summary": jd[:200].strip(),
    }


_DEMO_CANDIDATES = [
    {"name": "Arjun Mehta", "skills": ["python", "fastapi", "docker", "postgresql", "aws", "machine learning", "react"], "experience_years": 6, "education": "M.Tech CS, IIT Bombay", "summary": "Full-stack engineer with 6 years building scalable Python microservices and ML pipelines. Led a team of 4 at a Series-B startup."},
    {"name": "Sarah Chen", "skills": ["python", "django", "react", "typescript", "kubernetes", "terraform", "graphql"], "experience_years": 8, "education": "MS CS, Stanford", "summary": "Staff engineer with deep expertise in distributed systems. Built real-time data platforms serving 10M+ users."},
    {"name": "Priya Sharma", "skills": ["python", "data engineering", "spark", "airflow", "sql", "gcp", "kafka"], "experience_years": 4, "education": "B.Tech CS, NIT Trichy", "summary": "Data engineer specializing in batch and streaming pipelines. Reduced ETL latency by 60% at previous role."},
    {"name": "James Wilson", "skills": ["javascript", "react", "node.js", "typescript", "mongodb", "redis", "docker"], "experience_years": 5, "education": "BS CS, UC Berkeley", "summary": "Frontend-focused full-stack developer. Built component libraries used across 3 product teams."},
    {"name": "Maria Rodriguez", "skills": ["python", "machine learning", "deep learning", "pytorch", "nlp", "fastapi", "docker"], "experience_years": 7, "education": "PhD ML, MIT", "summary": "ML engineer with publications in NeurIPS. Deployed production NLP models serving 1M+ daily predictions."},
    {"name": "David Kim", "skills": ["go", "kubernetes", "docker", "terraform", "aws", "ci/cd", "linux", "microservices"], "experience_years": 9, "education": "MS CS, CMU", "summary": "Platform/DevOps engineer. Architected multi-region k8s deployments handling 50k RPS."},
    {"name": "Aisha Patel", "skills": ["python", "react", "typescript", "postgresql", "redis", "docker", "agile"], "experience_years": 3, "education": "B.Tech IT, BITS Pilani", "summary": "Versatile developer comfortable across the stack. Strong communicator who thrives in agile teams."},
    {"name": "Liam O'Connor", "skills": ["java", "spring", "microservices", "kafka", "sql", "docker", "aws", "ci/cd"], "experience_years": 10, "education": "BS CS, Trinity College Dublin", "summary": "Backend architect with a decade in enterprise Java. Migrated monolith to 40+ microservices at fintech scale."},
    {"name": "Yuki Tanaka", "skills": ["python", "rust", "machine learning", "pytorch", "tensorflow", "docker", "linux"], "experience_years": 5, "education": "MS AI, University of Tokyo", "summary": "ML/systems engineer bridging research and production. Optimized inference latency by 4x using Rust bindings."},
    {"name": "Emily Foster", "skills": ["python", "sql", "data engineering", "airflow", "gcp", "spark", "agile", "scrum"], "experience_years": 2, "education": "BS Data Science, Georgia Tech", "summary": "Early-career data engineer with strong SQL and pipeline skills. Eager learner with 2 production Airflow DAGs."},
]


def _demo_parse_resume(resume_text: str) -> Dict[str, Any]:
    """Heuristic resume parsing for demo mode — tries keyword matching,
    falls back to a demo candidate if text is too short."""
    text = resume_text.strip()

    # If the text has any meaningful content, attempt extraction
    if len(text) > 20:
        text_lower = text.lower()
        skills = [s for s in _COMMON_SKILLS if s in text_lower]

        # Try to extract a name (first line or before first dash/comma)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        first_line = lines[0] if lines else text
        # Name is usually before the first " - " or first newline
        name_match = re.match(r"^([A-Za-z\s'.]+?)(?:\s*[-–—|,]|\n)", first_line)
        if name_match:
            name = name_match.group(1).strip()
        else:
            name = first_line[:60]

        # Try to find years of experience (various patterns)
        years_match = re.search(r"(\d{1,2})\+?\s*years?", text_lower)
        years = int(years_match.group(1)) if years_match else 3

        return {
            "name": name,
            "skills": skills[:12] or ["python", "sql"],
            "experience_years": years,
            "education": "Not specified",
            "summary": text[:250],
        }

    # Very short text → pick from demo pool based on hash for consistency
    idx = hash(text) % len(_DEMO_CANDIDATES)
    return dict(_DEMO_CANDIDATES[idx])

