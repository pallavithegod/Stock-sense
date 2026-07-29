"""Evaluate matured prediction fixtures offline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.domain.predictions import canonicalize_prediction, evaluate_prediction, summarize_evaluations


DEFAULT_FIXTURE = Path("tests/fixtures/predictions/evaluation_fixture.json")


def evaluate_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, object]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    evaluations = []
    for row in rows:
        prediction = canonicalize_prediction(row)
        if prediction is None:
            continue
        evaluations.append(
            evaluate_prediction(
                prediction,
                actual_price=row.get("actual_price"),
                evaluated_at=row.get("evaluated_at"),
            )
        )
    return summarize_evaluations(evaluations)


def main() -> None:
    print(json.dumps(evaluate_fixture(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
