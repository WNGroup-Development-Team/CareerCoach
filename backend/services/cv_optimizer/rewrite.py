from __future__ import annotations

from typing import Any, Dict, Optional


def build_resume_rewrite_result(
    cv_text: str,
    company: str,
    role: str,
    goal: str,
    accepted_suggestions: Optional[Any] = None,
    user_additional_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply accepted suggestions and return the final structured CV rewrite."""
    from fastapi import HTTPException
    from main import (
        CV_REWRITE_LLM_ENABLED,
        CoachSuggestionEngine,
        ResumeParser,
        ResumeRewriter,
        build_additional_rewrite_instructions,
        build_confirmed_skill_rewrite_instructions,
        build_cv_rewrite_prompt,
        call_rewrite_llm,
        consolidate_rewrite_instructions,
        extract_resume_sections,
        normalize_plain_text,
    )
    from services.cv_optimizer.safe_cv_guard import sanitize_accepted_cv_suggestions
    from services.cv_optimizer.structured_cv_engine import build_optimized_cv_text

    parser = ResumeParser()
    sections = parser.parse_text(cv_text)
    accepted = CoachSuggestionEngine().accepted_only(accepted_suggestions)
    accepted = sanitize_accepted_cv_suggestions(accepted)
    confirmed_instructions = build_confirmed_skill_rewrite_instructions(
        cv_text, user_additional_data or {}, role
    )
    additional_instructions = build_additional_rewrite_instructions(user_additional_data or {}, role)
    clean_additional_data = {
        key: str(value).strip()[:300] if isinstance(value, str) else value
        for key, value in (user_additional_data or {}).items()
        if value
    }

    rewriter = ResumeRewriter(parser)
    prompt = build_cv_rewrite_prompt(
        cv_text=cv_text,
        company=company,
        role=role,
        goal=goal,
        job_link="",
        sources=[],
        cv_evaluation=None,
        strategic_analysis=None,
        recommended_adaptations=None,
        accepted_coach_suggestions=accepted,
        clean_additional_data=clean_additional_data,
    )

    if CV_REWRITE_LLM_ENABLED and (accepted or confirmed_instructions):
        try:
            result = call_rewrite_llm(
                prompt,
                context="resume_rewrite_instructions",
                temperature=0.08,
                max_tokens=700,
                timeout=45,
            )
            instructions = rewriter.instructions_from_result(result)
            if not instructions and accepted:
                instructions = rewriter.instructions_from_suggestions(accepted)
        except Exception as exc:
            print(f"Errore nella generazione istruzioni LLM: {exc}")
            instructions = rewriter.instructions_from_suggestions(accepted)
    else:
        instructions = rewriter.instructions_from_suggestions(accepted)

    instructions.extend(confirmed_instructions)
    instructions.extend(additional_instructions)
    if instructions:
        instructions = consolidate_rewrite_instructions(
            cv_text,
            instructions,
            company,
            role,
            goal,
            use_llm=CV_REWRITE_LLM_ENABLED,
        )

    structured_suggestions = list(accepted)
    existing_keys = {
        (
            normalize_plain_text(str(item.get("section") or item.get("target_section") or "")),
            normalize_plain_text(str(item.get("proposed_text") or item.get("replacement") or item.get("new_text") or "")),
        )
        for item in structured_suggestions
        if isinstance(item, dict)
    }
    for index, instruction in enumerate(instructions):
        key = (
            normalize_plain_text(instruction.section),
            normalize_plain_text(instruction.replacement),
        )
        if not key[1] or key in existing_keys:
            continue
        structured_suggestions.append({
            "id": instruction.source_id or f"rewrite-instruction-{index + 1}",
            "type": "actionableEdit",
            "category": instruction.category or instruction.section,
            "section": instruction.section,
            "original_text": instruction.original,
            "proposed_text": instruction.replacement,
            "description": instruction.reason,
            "supported_by_cv": True,
            "requires_confirmation": False,
        })
        existing_keys.add(key)

    try:
        optimized_text = build_optimized_cv_text(
            cv_text,
            structured_suggestions,
            user_additional_data or {},
            role=role,
            company=company,
            use_llm=False,
        )
        if (
            not (optimized_text or "").strip()
            or (
                instructions
                and len((optimized_text or "").strip()) < 120
                and normalize_plain_text(optimized_text) == normalize_plain_text(cv_text)
            )
        ):
            optimized_text = rewriter.apply_to_text(cv_text, instructions)
    except Exception as exc:
        print(f"Generazione CV strutturato non disponibile, uso rewriter esistente: {exc}")
        optimized_text = rewriter.apply_to_text(cv_text, instructions)

    if instructions and normalize_plain_text(optimized_text) == normalize_plain_text(cv_text):
        raise HTTPException(
            status_code=422,
            detail=(
                "Le modifiche validate non hanno prodotto alcuna variazione nel CV. "
                "Nessun file identico all'originale verrà salvato."
            ),
        )

    preview = {}
    headings = {
        "profile": "PROFILO",
        "experience": "ESPERIENZE PROFESSIONALI",
        "education": "FORMAZIONE",
        "hard_skills": "HARD SKILLS",
        "soft_skills": "SOFT SKILLS",
        "languages": "LINGUE",
        "projects": "PROGETTI",
        "certifications": "CERTIFICAZIONI",
        "contacts": "CONTATTI",
    }
    for section_key, section_text in extract_resume_sections(optimized_text).items():
        if section_text.strip():
            preview[headings.get(section_key, section_key.replace("_", " ").title())] = section_text.strip()
    if not preview:
        for instruction in instructions:
            name = (instruction.section or "Altro").capitalize()
            preview[name] = (
                f"{preview[name]}\n\n{instruction.replacement}"
                if name in preview
                else instruction.replacement
            )

    return {
        "optimized_text": optimized_text,
        "instructions": instructions,
        "grouped_changes": {"sections": [item.section for item in instructions]},
        "accepted_suggestions": accepted,
        "missing_proposed_text_count": 0,
        "sections": sections,
        "previewFinalCvContent": preview,
    }
