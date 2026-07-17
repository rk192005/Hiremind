"""
Setup script — creates Qdrant collection and loads sample candidate data.
Run once before starting the server (optional — the pipeline works without it).
"""
import os
import sys
import logging

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample candidate data for demo purposes
SAMPLE_CANDIDATES = [
    {
        "name": "Arjun Mehta",
        "skills": ["python", "fastapi", "docker", "postgresql", "aws", "machine learning", "react"],
        "experience_years": 6,
        "education": "M.Tech CS, IIT Bombay",
        "summary": "Full-stack engineer with 6 years building scalable Python microservices and ML pipelines. Led a team of 4 at a Series-B startup.",
    },
    {
        "name": "Sarah Chen",
        "skills": ["python", "django", "react", "typescript", "kubernetes", "terraform", "graphql"],
        "experience_years": 8,
        "education": "MS CS, Stanford",
        "summary": "Staff engineer with deep expertise in distributed systems. Built real-time data platforms serving 10M+ users.",
    },
    {
        "name": "Priya Sharma",
        "skills": ["python", "data engineering", "spark", "airflow", "sql", "gcp", "kafka"],
        "experience_years": 4,
        "education": "B.Tech CS, NIT Trichy",
        "summary": "Data engineer specializing in batch and streaming pipelines. Reduced ETL latency by 60% at previous role.",
    },
    {
        "name": "James Wilson",
        "skills": ["javascript", "react", "node.js", "typescript", "mongodb", "redis", "docker"],
        "experience_years": 5,
        "education": "BS CS, UC Berkeley",
        "summary": "Frontend-focused full-stack developer. Built component libraries used across 3 product teams.",
    },
    {
        "name": "Maria Rodriguez",
        "skills": ["python", "machine learning", "deep learning", "pytorch", "nlp", "fastapi", "docker"],
        "experience_years": 7,
        "education": "PhD ML, MIT",
        "summary": "ML engineer with publications in NeurIPS. Deployed production NLP models serving 1M+ daily predictions.",
    },
    {
        "name": "David Kim",
        "skills": ["go", "kubernetes", "docker", "terraform", "aws", "ci/cd", "linux", "microservices"],
        "experience_years": 9,
        "education": "MS CS, CMU",
        "summary": "Platform/DevOps engineer. Architected multi-region k8s deployments handling 50k RPS.",
    },
    {
        "name": "Aisha Patel",
        "skills": ["python", "react", "typescript", "postgresql", "redis", "docker", "agile"],
        "experience_years": 3,
        "education": "B.Tech IT, BITS Pilani",
        "summary": "Versatile developer comfortable across the stack. Strong communicator who thrives in agile teams.",
    },
    {
        "name": "Liam O'Connor",
        "skills": ["java", "spring", "microservices", "kafka", "sql", "docker", "aws", "ci/cd"],
        "experience_years": 10,
        "education": "BS CS, Trinity College Dublin",
        "summary": "Backend architect with a decade in enterprise Java. Migrated monolith to 40+ microservices at fintech scale.",
    },
    {
        "name": "Yuki Tanaka",
        "skills": ["python", "rust", "machine learning", "pytorch", "tensorflow", "docker", "linux"],
        "experience_years": 5,
        "education": "MS AI, University of Tokyo",
        "summary": "ML/systems engineer bridging research and production. Optimized inference latency by 4x using Rust bindings.",
    },
    {
        "name": "Emily Foster",
        "skills": ["python", "sql", "data engineering", "airflow", "gcp", "spark", "agile", "scrum"],
        "experience_years": 2,
        "education": "BS Data Science, Georgia Tech",
        "summary": "Early-career data engineer with strong SQL and pipeline skills. Eager learner with 2 production Airflow DAGs.",
    },
]


def main():
    from app.pipeline.embed import embed_batch, get_embedding_dim
    from app.pipeline.qdrant_client import ensure_collection, upsert_candidates

    logger.info("Setting up Qdrant with %d sample candidates", len(SAMPLE_CANDIDATES))

    # Build text representations for embedding
    texts = []
    for c in SAMPLE_CANDIDATES:
        parts = [c["name"], c["summary"], "Skills: " + ", ".join(c["skills"]),
                 f"Experience: {c['experience_years']} years", c["education"]]
        texts.append(" | ".join(parts))

    # Embed
    logger.info("Embedding candidates...")
    vectors = embed_batch(texts)
    vec_dim = len(vectors[0])
    logger.info("Embedding dimension: %d", vec_dim)

    # Create collection and upsert
    ensure_collection("candidates", vector_size=vec_dim)
    upsert_candidates(SAMPLE_CANDIDATES, vectors, "candidates")

    logger.info("✅ Setup complete! %d candidates indexed.", len(SAMPLE_CANDIDATES))


if __name__ == "__main__":
    main()
