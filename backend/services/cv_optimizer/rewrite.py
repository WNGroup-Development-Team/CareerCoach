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
        CoachSuggestionEngine,
        ResumeParser,
        ResumeRewriter,
        build_additional_rewrite_instructions,
        build_confirmed_skill_rewrite_instructions,
        extract_resume_sections,
        is_additive_user_rewrite_source,
        normalize_plain_text,
    )
    from services.cv_optimizer.structured_cv_engine import (
        extract_skill_terms,
        normalize_professional_language,
    )

    def _deduplicate_skill_append(instruction: Any) -> Optional[Any]:
        source_id = str(getattr(instruction, "source_id", "") or "")
        original = str(getattr(instruction, "original", "") or "").strip()
        replacement = str(getattr(instruction, "replacement", "") or "").strip()
        section = normalize_plain_text(str(getattr(instruction, "section", "") or ""))
        if not replacement:
            return None

        if is_additive_user_rewrite_source(source_id) or not original:
            if section in {"hard skills", "soft skills", "competenze", "competenze tecniche", "skills"}:
                existing_terms = {
                    normalize_plain_text(term)
                    for term in extract_skill_terms(cv_text)
                }
                incoming_terms = []
                seen_terms = set()
                for term in extract_skill_terms(replacement):
                    key = normalize_plain_text(term)
                    if key and key not in existing_terms and key not in seen_terms:
                        seen_terms.add(key)
                        incoming_terms.append(term)
                if incoming_terms:
                    instruction.replacement = ", ".join(incoming_terms)
                else:
                    return None
        return instruction

    def _local_instruction(instruction: Any) -> Optional[Any]:
        """Keep the original CV as base and allow only local edits or additive appends."""
        original = str(getattr(instruction, "original", "") or "").strip()
        replacement = str(getattr(instruction, "replacement", "") or "").strip()
        section = normalize_plain_text(str(getattr(instruction, "section", "") or ""))
        if not replacement:
            return None

        if not original:
            instruction.original = ""
            return _deduplicate_skill_append(instruction)

        if replacement.startswith(original):
            tail = replacement[len(original):].strip(" \n\t.-:;")
            if tail:
                instruction.original = ""
                instruction.replacement = (tail[:1].upper() + tail[1:]).rstrip(".") + "."
                return _deduplicate_skill_append(instruction)

        if original in cv_text:
            if section in {"hard skills", "soft skills", "competenze", "competenze tecniche", "skills"}:
                instruction.original = ""
                return _deduplicate_skill_append(instruction)
            return instruction

        return None

    parser = ResumeParser()
    sections = parser.parse_text(cv_text)
    rewriter = ResumeRewriter(parser)
    accepted = CoachSuggestionEngine().accepted_only(accepted_suggestions)
    accepted_instructions = rewriter.instructions_from_suggestions(accepted)
    confirmed_instructions = build_confirmed_skill_rewrite_instructions(
        cv_text, user_additional_data or {}, role
    )
    additional_instructions = build_additional_rewrite_instructions(
        user_additional_data or {},
        role,
        cv_text,
    )

    instructions = [*accepted_instructions, *confirmed_instructions, *additional_instructions]
    instructions = [
        local_instruction
        for instruction in instructions
        for local_instruction in [_local_instruction(instruction)]
        if local_instruction is not None
    ]

    if not instructions:
        optimized_text = cv_text or ""
    else:
        optimized_text = rewriter.apply_to_text(cv_text, instructions)

    optimized_text = normalize_professional_language(optimized_text)
    optimized_text = rewriter.clean_final_text(optimized_text)

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
