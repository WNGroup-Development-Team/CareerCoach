from __future__ import annotations

from typing import Any, Dict, List


def build_cv_job_suggestions(
    evaluation: Dict[str, Any],
    allow_llm: bool = True,
) -> List[Dict[str, Any]]:
    """Build, validate and deduplicate actionable CV suggestions."""
    from main import (
        build_coach_suggestions_from_evaluation,
        is_valid_actionable_suggestion,
        suggestion_targets_current_cv,
    )

    suggestions = build_coach_suggestions_from_evaluation(evaluation, allow_llm=allow_llm)
    if not isinstance(suggestions, list):
        return []

    cv_text = str(evaluation.get("cv_text") or "")
    filtered: List[Dict[str, Any]] = []
    seen = set()
    for item in suggestions:
        if not isinstance(item, dict):
            continue
        if not is_valid_actionable_suggestion(item):
            continue
        if not suggestion_targets_current_cv(item, cv_text):
            continue
        item_id = str(item.get("id") or "").strip()
        if item_id and item_id in seen:
            continue
        if item_id:
            seen.add(item_id)
        filtered.append(item)
    return filtered[:8]
