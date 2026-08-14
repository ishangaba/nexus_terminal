"""Confidence calibration over resolved trade signals.

`trade_signal.confidence` is stored as a category (low/medium/high) — the model's actual
verdict, not a synthetic numeric score. Bucketing by that category, rather than forcing it
into fabricated numeric percentile buckets (50-60%, 60-70%, ...), is the honest choice: it
doesn't manufacture precision the underlying data doesn't have. Brier score needs a
probability, so categories are mapped to representative midpoint probabilities for *that one
calculation only* — the bucket breakdown itself stays categorical. True numeric calibration
becomes possible once signals carry a numeric confidence (as `ResearchThesis` already does).
"""

from intelligence.evaluators.signal_evaluator import is_correct, resolved_outcome

CONFIDENCE_PROBABILITY = {"low": 0.55, "medium": 0.70, "high": 0.85}
CONFIDENCE_LEVELS = ("low", "medium", "high")


def confidence_calibration(signals: list[dict]) -> dict:
    buckets = {level: {"n": 0, "correct": 0} for level in CONFIDENCE_LEVELS}
    brier_terms = []

    for signal in signals:
        correct = is_correct(resolved_outcome(signal))
        if correct is None:
            continue

        confidence = signal.get("confidence")
        if confidence in buckets:
            buckets[confidence]["n"] += 1
            if correct:
                buckets[confidence]["correct"] += 1

        probability = CONFIDENCE_PROBABILITY.get(confidence)
        if probability is not None:
            actual = 1.0 if correct else 0.0
            brier_terms.append((probability - actual) ** 2)

    bucket_accuracy = {
        level: {
            "n": bucket["n"],
            "correct": bucket["correct"],
            "accuracy": round(bucket["correct"] / bucket["n"], 4) if bucket["n"] else None,
        }
        for level, bucket in buckets.items()
    }

    return {
        "buckets": bucket_accuracy,
        "brier_score": round(sum(brier_terms) / len(brier_terms), 4) if brier_terms else None,
        "brier_sample_size": len(brier_terms),
    }
