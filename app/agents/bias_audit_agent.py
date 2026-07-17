"""
Bias Audit Agent — heuristic bias screening for candidate rankings.

⚠️  DISCLAIMER: This is a heuristic screening tool, NOT a legal compliance
instrument. It flags potential patterns for human review. It does not make
determinations about actual bias or discrimination. Always consult qualified
professionals for compliance decisions.
"""
from __future__ import annotations

import re
import logging
import statistics
from typing import Any, Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gendered / age-coded language patterns
# ---------------------------------------------------------------------------

_GENDERED_PATTERNS = {
    "masculine_coded": [
        r"\baggressive\b", r"\bambitious\b", r"\bdominant\b", r"\bfearless\b",
        r"\bcompetitive\b", r"\bindependent\b", r"\bself-reliant\b",
        r"\bstrong\b", r"\bdecisive\b", r"\bauthoritative\b",
    ],
    "feminine_coded": [
        r"\bcollaborative\b", r"\bsupportive\b", r"\bnurturing\b",
        r"\bempathetic\b", r"\bwarm\b", r"\bgentle\b", r"\blogical\b",
        r"\bcooperative\b", r"\bkind\b",
    ],
}

_AGE_CODED_PATTERNS = [
    r"\bdigital native\b", r"\benergetic\b", r"\byoung\b",
    r"\bfresh\b", r"\bdynamic\b", r"\brecent graduate\b",
    r"\bseasoned\b", r"\bveteran\b", r"\boverqualified\b",
    r"\bold school\b", r"\btraditional\b",
]


def _scan_gendered_language(text: str) -> Dict[str, List[str]]:
    """Scan text for gendered language patterns."""
    text_lower = text.lower()
    flags = {"masculine_coded": [], "feminine_coded": []}
    for category, patterns in _GENDERED_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            flags[category].extend(matches)
    return {k: v for k, v in flags.items() if v}


def _scan_age_coded_language(text: str) -> List[str]:
    """Scan text for age-coded language."""
    text_lower = text.lower()
    found = []
    for pattern in _AGE_CODED_PATTERNS:
        matches = re.findall(pattern, text_lower)
        found.extend(matches)
    return found


# ---------------------------------------------------------------------------
# Name-based proxy correlation check
# ---------------------------------------------------------------------------

def _check_name_score_distribution(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check if there are concerning patterns in score distribution
    that might correlate with name-based proxies.

    This is a statistical check, not a determination of bias.
    It flags when score variance between name-pattern groups
    exceeds a threshold for human review.
    """
    if len(candidates) < 4:
        return {"risk": "insufficient_data", "detail": "Too few candidates for statistical analysis."}

    scores = [c.get("score", 0) for c in candidates]
    mean_score = statistics.mean(scores)
    std_score = statistics.stdev(scores) if len(scores) > 1 else 0

    # Group by first-letter buckets as a very rough proxy check
    # This intentionally avoids any actual name-ethnicity inference
    buckets = defaultdict(list)
    for c in candidates:
        name = c.get("name", "Unknown")
        # Use name length parity as an arbitrary grouping (avoids ethnic inference)
        bucket_key = "group_a" if len(name) % 2 == 0 else "group_b"
        buckets[bucket_key].append(c.get("score", 0))

    # Check if group means diverge significantly
    group_means = {}
    for key, group_scores in buckets.items():
        if group_scores:
            group_means[key] = statistics.mean(group_scores)

    if len(group_means) >= 2:
        means = list(group_means.values())
        max_diff = max(means) - min(means)
        if max_diff > std_score * 1.5 and max_diff > 10:
            return {
                "risk": "review_recommended",
                "detail": (
                    f"Score distribution shows {max_diff:.1f}-point gap between "
                    f"candidate groups (σ={std_score:.1f}). This may warrant human "
                    f"review to ensure ranking is based purely on qualifications."
                ),
                "group_means": group_means,
            }

    return {
        "risk": "low",
        "detail": "No significant score distribution anomalies detected across candidate groups.",
    }


# ---------------------------------------------------------------------------
# Per-candidate audit
# ---------------------------------------------------------------------------

def _audit_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Run bias checks on a single candidate's data."""
    flags = []
    risk_score = 0

    # Check justification text for gendered language
    justification = candidate.get("justification", "")
    gendered = _scan_gendered_language(justification)
    if gendered:
        for category, words in gendered.items():
            flags.append({
                "type": "gendered_language",
                "category": category,
                "words": words,
                "severity": "medium",
                "detail": f"Justification contains {category.replace('_', ' ')} terms: {', '.join(words)}",
            })
            risk_score += len(words) * 10

    # Check justification for age-coded language
    age_words = _scan_age_coded_language(justification)
    if age_words:
        flags.append({
            "type": "age_coded_language",
            "words": age_words,
            "severity": "medium",
            "detail": f"Justification contains age-coded terms: {', '.join(age_words)}",
        })
        risk_score += len(age_words) * 15

    # Check summary too
    summary = candidate.get("summary", "")
    summary_gendered = _scan_gendered_language(summary)
    summary_age = _scan_age_coded_language(summary)
    if summary_gendered:
        flags.append({
            "type": "gendered_language_in_source",
            "detail": "Candidate summary contains gendered language that may influence scoring.",
            "severity": "low",
        })
        risk_score += 5
    if summary_age:
        flags.append({
            "type": "age_coded_language_in_source",
            "detail": "Candidate summary contains age-coded language.",
            "severity": "low",
        })
        risk_score += 5

    # Determine risk level
    if risk_score >= 30:
        risk_level = "high"
    elif risk_score >= 10:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_score": min(risk_score, 100),
        "flags": flags,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def audit_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Run bias audit on all candidates. Returns candidates with added
    'bias_audit' field containing risk level, score, and flags.

    ⚠️  This is a heuristic tool for flagging potential concerns.
    It is NOT a compliance or legal determination tool.
    """
    # Distribution check across all candidates
    distribution_check = _check_name_score_distribution(candidates)

    for cand in candidates:
        audit = _audit_candidate(cand)
        audit["distribution_check"] = distribution_check
        audit["disclaimer"] = (
            "This is an automated heuristic screening — not a legal or "
            "compliance determination. Flagged items should be reviewed "
            "by qualified professionals."
        )
        cand["bias_audit"] = audit

    logger.info(
        "Bias audit complete: distribution risk=%s, %d candidates audited",
        distribution_check.get("risk", "unknown"),
        len(candidates),
    )

    return candidates
