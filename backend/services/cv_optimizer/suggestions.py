from __future__ import annotations

from typing import Any, Dict, List


def refine_cv_job_suggestions(
    suggestions: List[Dict[str, Any]],
    evaluation: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Refine each deterministic suggestion with one small local LLM call."""
    from main import (
        call_lightweight_analysis_llm,
        is_valid_actionable_suggestion,
        normalize_plain_text,
        suggestion_targets_current_cv,
    )

    cv_text = str(evaluation.get("cv_text") or "")
    target = evaluation.get("target") if isinstance(evaluation.get("target"), dict) else {}
    role = str(target.get("role") or evaluation.get("role") or "").strip()
    company = str(target.get("company") or evaluation.get("company") or "").strip()
    refined: List[Dict[str, Any]] = []

    for index, item in enumerate(suggestions[:4]):
        original = str(item.get("original_text") or "").strip()
        local_proposal = str(item.get("proposed_text") or "").strip()
        section = str(item.get("section") or "").strip()
        if not original or not local_proposal or not section:
            refined.append(item)
            continue

        prompt = f"""
Restituisci SOLO JSON valido.

Riscrivi un singolo suggerimento per il CV in italiano naturale e professionale.
Ruolo target: {role or "non specificato"}
Azienda: {company or "non specificata"}
Sezione: {section}

Testo originale:
{original[:1200]}

Bozza locale:
{local_proposal[:1200]}

Schema:
{{
  "title": "titolo breve e specifico",
  "reason": "motivo concreto, massimo 18 parole",
  "proposed_text": "testo finale della sola sezione"
}}

Regole:
- conserva esclusivamente fatti, skill e significati presenti nel testo originale;
- migliora sintassi, chiarezza, tono professionale e allineamento al ruolo;
- non aggiungere il ruolo o l'azienda come esperienza posseduta;
- non inventare risultati, strumenti, date, responsabilita o competenze;
- non aggiungere titoli di altre sezioni;
- non restituire spiegazioni o markdown.
"""
        try:
            result = call_lightweight_analysis_llm(
                prompt,
                context=f"cv_coach_suggestion_{index + 1}",
                temperature=0.08,
                max_tokens=320,
                timeout=35,
            )
        except Exception as exc:
            print(f"Rifinitura Ollama suggerimento {index + 1} non riuscita: {exc}")
            refined.append(item)
            continue

        proposed = str(result.get("proposed_text") or "").strip()
        candidate = {
            **item,
            "title": str(result.get("title") or item.get("title") or "").strip(),
            "description": str(result.get("reason") or item.get("description") or "").strip(),
            "reason": str(result.get("reason") or item.get("reason") or "").strip(),
            "proposed_text": proposed,
            "generated_by": "ollama",
        }
        changed = normalize_plain_text(proposed) != normalize_plain_text(original)
        if (
            changed
            and is_valid_actionable_suggestion(candidate)
            and suggestion_targets_current_cv(candidate, cv_text)
        ):
            refined.append(candidate)
        else:
            refined.append(item)

    return refined


def build_cv_job_suggestions(
    evaluation: Dict[str, Any],
    allow_llm: bool = False,
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
    fallback: List[Dict[str, Any]] = []
    seen = set()
    for item in suggestions:
        if not isinstance(item, dict):
            continue
        if not is_valid_actionable_suggestion(item):
            continue
        fallback.append(item)
        if not suggestion_targets_current_cv(item, cv_text):
            continue
        item_id = str(item.get("id") or "").strip()
        if item_id and item_id in seen:
            continue
        if item_id:
            seen.add(item_id)
        filtered.append(item)
    selected = filtered[:8] if filtered else fallback[:8]
    if allow_llm and selected:
        return refine_cv_job_suggestions(selected, evaluation)
    return selected
