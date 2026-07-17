"""
Evaluation script — computes Precision@5, Precision@10, and Spearman
rank correlation against a human-labeled ground truth CSV.

Ground truth CSV format:
  candidate_name,human_rank
  Sarah Chen,1
  Maria Rodriguez,2
  ...

Usage:
  python evaluate.py --ground-truth ground_truth.csv --results results.json
  python evaluate.py --demo   # uses built-in demo data
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from typing import Dict, List, Tuple

from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Demo ground truth (for testing without a CSV)
# ---------------------------------------------------------------------------

DEMO_GROUND_TRUTH = {
    "Sarah Chen": 1,
    "Maria Rodriguez": 2,
    "Arjun Mehta": 3,
    "Yuki Tanaka": 4,
    "David Kim": 5,
    "Liam O'Connor": 6,
    "Priya Sharma": 7,
    "James Wilson": 8,
    "Aisha Patel": 9,
    "Emily Foster": 10,
}


def load_ground_truth(csv_path: str) -> Dict[str, int]:
    """Load ground truth from CSV file."""
    gt = {}
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("candidate_name", "").strip()
            rank = int(row.get("human_rank", 0))
            if name and rank > 0:
                gt[name] = rank
    return gt


def load_results(json_path: str) -> List[Dict]:
    """Load pipeline results from JSON file."""
    with open(json_path, "r") as f:
        data = json.load(f)
    return data.get("candidates", data) if isinstance(data, dict) else data


def precision_at_k(
    predicted: List[str],
    ground_truth: Dict[str, int],
    k: int,
) -> float:
    """
    Precision@K: fraction of top-K predicted candidates that appear
    in the top-K of ground truth.
    """
    gt_top_k = {name for name, rank in ground_truth.items() if rank <= k}
    pred_top_k = set(predicted[:k])
    if not gt_top_k:
        return 0.0
    overlap = pred_top_k & gt_top_k
    return len(overlap) / k


def spearman_correlation(
    predicted: List[str],
    ground_truth: Dict[str, int],
) -> Tuple[float, float]:
    """
    Compute Spearman rank correlation between predicted and ground truth.
    Only considers candidates present in both lists.
    """
    common = [name for name in predicted if name in ground_truth]
    if len(common) < 3:
        return 0.0, 1.0  # Not enough data

    pred_ranks = [predicted.index(name) + 1 for name in common]
    gt_ranks = [ground_truth[name] for name in common]

    correlation, p_value = spearmanr(pred_ranks, gt_ranks)
    return float(correlation), float(p_value)


def evaluate(
    predicted: List[str],
    ground_truth: Dict[str, int],
) -> Dict[str, float]:
    """Run all evaluation metrics."""
    p5 = precision_at_k(predicted, ground_truth, 5)
    p10 = precision_at_k(predicted, ground_truth, 10)
    spearman, p_value = spearman_correlation(predicted, ground_truth)

    return {
        "precision_at_5": round(p5, 4),
        "precision_at_10": round(p10, 4),
        "spearman_correlation": round(spearman, 4),
        "spearman_p_value": round(p_value, 6),
        "num_predicted": len(predicted),
        "num_ground_truth": len(ground_truth),
        "num_overlap": len(set(predicted) & set(ground_truth.keys())),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate HireMind ranking pipeline")
    parser.add_argument("--ground-truth", type=str, help="Path to ground truth CSV")
    parser.add_argument("--results", type=str, help="Path to pipeline results JSON")
    parser.add_argument("--demo", action="store_true", help="Run with demo data")
    parser.add_argument("--output", type=str, default="evaluation_results.json", help="Output file")
    args = parser.parse_args()

    # Load ground truth
    if args.demo:
        gt = DEMO_GROUND_TRUTH
        logger.info("Using demo ground truth (%d candidates)", len(gt))
    elif args.ground_truth:
        gt = load_ground_truth(args.ground_truth)
        logger.info("Loaded ground truth from %s (%d candidates)", args.ground_truth, len(gt))
    else:
        logger.error("Provide --ground-truth CSV or --demo")
        sys.exit(1)

    # Load or generate predicted ranking
    if args.results:
        results = load_results(args.results)
        predicted = [r.get("name", "") for r in results]
        logger.info("Loaded results from %s (%d candidates)", args.results, len(predicted))
    elif args.demo:
        # Simulate a reasonable predicted ranking
        predicted = [
            "Sarah Chen", "Arjun Mehta", "Maria Rodriguez",
            "Yuki Tanaka", "David Kim", "Priya Sharma",
            "Liam O'Connor", "Aisha Patel", "James Wilson", "Emily Foster",
        ]
        logger.info("Using demo predicted ranking")
    else:
        logger.error("Provide --results JSON or --demo")
        sys.exit(1)

    # Run evaluation
    metrics = evaluate(predicted, gt)

    # Display results
    print("\n" + "=" * 50)
    print("  HireMind Evaluation Results")
    print("=" * 50)
    print(f"  Precision@5:            {metrics['precision_at_5']:.2%}")
    print(f"  Precision@10:           {metrics['precision_at_10']:.2%}")
    print(f"  Spearman Correlation:   {metrics['spearman_correlation']:.4f}")
    print(f"  Spearman p-value:       {metrics['spearman_p_value']:.6f}")
    print(f"  Candidates evaluated:   {metrics['num_overlap']}/{metrics['num_ground_truth']}")
    print("=" * 50 + "\n")

    # Save to file
    with open(args.output, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Results saved to %s", args.output)

    return metrics


if __name__ == "__main__":
    main()
