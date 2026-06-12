from __future__ import annotations

from typing import Any, Dict, List, Optional
import json


def evaluate_cv_for_job(
    cv_text: str,
    company: str,
    role: str,
    description: str,
    link: str,
    sources: Optional[List[Dict[str, str]]] = None,
    required_skills: str = "",
) -> Dict[str, Any]:
    """Orchestrate deterministic evaluation with structured LLM enrichment."""
    from main import (
        CV_EVALUATION_LLM_ENABLED,
        OLLAMA_TEXT_TIMEOUT,
        build_fallback_cv_job_evaluation,
        build_lightweight_cv_evaluation_prompt,
        call_analysis_llm,
        call_lightweight_analysis_llm,
        generate_cv_optimization_questions,
        normalize_cv_job_evaluation,
        sources_to_prompt,
    )

    sources = sources or []
    fallback = build_fallback_cv_job_evaluation(
        cv_text, company, role, description, sources, required_skills
    )
    sources_prompt = sources_to_prompt(sources)
    ats_analysis = fallback["ats_analysis"]

    def _with_questions(evaluation: Dict[str, Any]) -> Dict[str, Any]:
        questions = generate_cv_optimization_questions(
            cv_text,
            evaluation,
            evaluation.get("ats_analysis", ats_analysis),
        )
        evaluation["optimization_questions"] = questions
        evaluation["questions_for_user"] = questions
        return evaluation

    if not CV_EVALUATION_LLM_ENABLED:
        print("Valutazione CV per candidatura: uso motore locale rapido; LLM riservato a suggerimenti e riscrittura.")
        return _with_questions(fallback)

    prompt = f"""
Sei un recruiter senior. Restituisci solo JSON valido.

Input:
- Azienda: {company}
- Ruolo: {role}
- Descrizione: {description}
- Competenze richieste: {required_skills or "Non specificate"}
- Link: {link or "Non inserito"}
- Fonti: {sources_prompt}
- ATS: {json.dumps(ats_analysis, ensure_ascii=False)}
- CV: {cv_text[:2200]}

Output JSON richiesto:
{{
  "overall_score": 0,
  "ats_score": 0,
  "job_match_score": 0,
  "role_match_score": 0,
  "company_fit_score": 0,
  "clarity_score": 0,
  "completeness_score": 0,
  "professionalism_score": 0,
  "strengths": [],
  "weaknesses": [],
  "present_keywords": [],
  "missing_keywords": [],
  "sections_to_improve": [],
  "questions_for_user": [],
  "summary": ""
}}

Regole:
- Solo italiano.
- Solo il JSON sopra, niente markdown o introduzioni.
- Usa stringhe vuote o liste vuote quando non hai evidenza.
- Valuta il CV: non generare modifiche applicabili in questo passaggio.
"""

    try:
        result = call_analysis_llm(
            prompt,
            context="cv_job_evaluation",
            temperature=0.2,
            max_tokens=900,
            timeout=45,
        )
        return _with_questions(normalize_cv_job_evaluation(result, fallback))
    except Exception as exc:
        print(f"Valutazione CV per candidatura non riuscita, provo fallback leggero: {exc}")

    lightweight_prompt = build_lightweight_cv_evaluation_prompt(
        company=company,
        role=role,
        description=description,
        required_skills=required_skills,
        link=link,
        sources_prompt=sources_prompt,
        ats_analysis=ats_analysis,
        cv_text=cv_text,
    )
    try:
        result = call_lightweight_analysis_llm(
            lightweight_prompt,
            context="cv_job_evaluation_light",
            temperature=0.1,
            max_tokens=700,
            timeout=min(45, OLLAMA_TEXT_TIMEOUT),
        )
        print("Valutazione CV per candidatura fallback leggero riuscita.")
        return _with_questions(normalize_cv_job_evaluation(result, fallback))
    except Exception as exc:
        print(f"Fallback leggero CV non riuscito, uso fallback locale: {exc}")
        return _with_questions(fallback)
