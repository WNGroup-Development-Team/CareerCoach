from __future__ import annotations

from typing import Any, Dict, List
import json


def build_skill_mini_shot_suggestions(evaluation: Dict[str, Any]) -> List[Dict[str, Any]]:
    from main import (
        build_role_skill_suggestions,
        call_lightweight_analysis_llm,
        extract_resume_sections,
        infer_role_family,
        is_valid_actionable_suggestion,
        normalize_plain_text,
        role_keyword_snapshot,
        skill_semantically_present,
        suggestion_targets_current_cv,
    )
    from services.cv_optimizer.structured_cv_engine import extract_skill_terms

    cv_text = str(evaluation.get("cv_text") or "")
    target = evaluation.get("target") if isinstance(evaluation.get("target"), dict) else {}
    role = str(target.get("role") or evaluation.get("role") or "").strip()
    company = str(target.get("company") or evaluation.get("company") or "").strip()
    role_family = str(target.get("family") or infer_role_family(role, str(target.get("description") or evaluation.get("description") or ""), str(evaluation.get("required_skills") or ""))).strip()

    def _unique_text(values: Any) -> List[str]:
        if not isinstance(values, list):
            return []
        ordered: List[str] = []
        seen_local = set()
        for value in values:
            text = str(value or "").strip()
            if not text:
                continue
            key = normalize_plain_text(text)
            if key in seen_local:
                continue
            seen_local.add(key)
            ordered.append(text)
        return ordered

    cv_terms = _unique_text(extract_skill_terms(cv_text)[:28])
    role_snapshot = role_keyword_snapshot(
        cv_text,
        role,
        str(target.get("description") or evaluation.get("description") or ""),
        str(evaluation.get("required_skills") or ""),
    )
    role_skill_snapshot = build_role_skill_suggestions(
        cv_text,
        role,
        str(target.get("description") or evaluation.get("description") or ""),
        str(evaluation.get("required_skills") or ""),
    )
    missing_hard = [str(x).strip() for x in (evaluation.get("missing_hard_skills") or []) if str(x).strip()]
    missing_soft = [str(x).strip() for x in (evaluation.get("missing_soft_skills") or []) if str(x).strip()]
    present_skills = [str(x).strip() for x in (evaluation.get("relevant_skills_found") or evaluation.get("present_keywords") or []) if str(x).strip()]
    confirmation_items = [
        {
            "name": str(item.get("name") or "").strip(),
            "status": str(item.get("status") or "").strip(),
        }
        for item in (role_skill_snapshot.get("confirmation_items") or [])[:12]
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]
    role_library_candidates = {
        "hard_skills": [str(x).strip() for x in (role_skill_snapshot.get("hard_skills") or []) if str(x).strip()],
        "soft_skills": [str(x).strip() for x in (role_skill_snapshot.get("soft_skills") or []) if str(x).strip()],
        "tools": [str(x).strip() for x in (role_skill_snapshot.get("tools") or []) if str(x).strip()],
        "already_present": [str(x).strip() for x in (role_skill_snapshot.get("already_present") or []) if str(x).strip()],
    }

    def _retrieved_skill_candidates(group: str) -> List[str]:
        source = role_library_candidates.get(group, [])
        scored = []
        seen = set()
        for skill in source:
            normalized_skill = normalize_plain_text(skill)
            if not normalized_skill or normalized_skill in seen:
                continue
            seen.add(normalized_skill)
            overlap = 0
            skill_plain = normalize_plain_text(skill)
            for term in cv_terms:
                term_plain = normalize_plain_text(term)
                if term_plain and (term_plain in skill_plain or skill_plain in term_plain):
                    overlap += 1
            if any(normalize_plain_text(item.get("name") or "") == normalized_skill for item in confirmation_items):
                overlap += 2
            if group == "soft_skills":
                overlap += 1 if any(word in skill_plain for word in ["collabor", "comunic", "team", "organ", "problem", "lead", "precision", "analit"]) else 0
            if group == "hard_skills":
                overlap += 1 if any(word in skill_plain for word in ["api", "sql", "python", "testing", "git", "docker", "design", "dashboard", "rest", "database"]) else 0
            scored.append((overlap, skill))
        scored.sort(key=lambda item: (-item[0], normalize_plain_text(item[1])))
        return [skill for score, skill in scored if score > 0][:8]

    retrieved_hard = _retrieved_skill_candidates("hard_skills")
    retrieved_soft = _retrieved_skill_candidates("soft_skills")
    role_hint = {
        "software engineer": "software engineering, testing, version control, system design, CI/CD, collaborazione tecnica",
        "backend developer": "API, database, REST, microservizi, testing backend, affidabilita",
        "frontend developer": "UI, UX, HTML/CSS, JavaScript, component architecture, accessibilita",
        "data analyst": "SQL, Python, Excel, dashboard, reporting, KPI",
        "data scientist": "Python, machine learning, statistica, feature engineering, sperimentazione",
        "project manager": "pianificazione, coordinamento, stakeholder, rischio, priorita",
    }.get(role_family, "competenze tecniche e trasversali coerenti col ruolo")

    sections = extract_resume_sections(cv_text)
    hard_original = str(sections.get("hard_skills") or "").strip()
    soft_original = str(sections.get("soft_skills") or "").strip()
    prompt = f"""
Restituisci SOLO JSON valido con 2-3 skill per un CV {role or role_family}.
Scegli soltanto dai candidati. Non inventare esperienze.

Presenti: {json.dumps((present_skills + role_skill_snapshot.get("already_present", []))[:10], ensure_ascii=False)}
Hard candidate: {json.dumps((retrieved_hard + missing_hard + role_snapshot.get("to_confirm", []))[:10], ensure_ascii=False)}
Soft candidate: {json.dumps((retrieved_soft + missing_soft)[:8], ensure_ascii=False)}
Focus: {role_hint}

{{
  "suggestions": [
    {{
      "bucket": "hard_add | soft_emphasize | present_reorder",
      "skill": "nome esatto",
      "reason": "massimo 12 parole"
    }}
  ]
}}

Regole:
- massimo 3 elementi, senza duplicati
- almeno una hard skill; soft solo se candidata
- usa nomi esatti delle liste
- italiano, niente markdown o testo extra
"""

    try:
        mini_result = call_lightweight_analysis_llm(
            prompt,
            context="cv_skill_suggestions_mini",
            temperature=0.1,
            max_tokens=180,
            timeout=40,
        )
        mini_items = mini_result.get("suggestions") if isinstance(mini_result, dict) else []
        cleaned_mini: List[Dict[str, Any]] = []
        for item in mini_items if isinstance(mini_items, list) else []:
            if not isinstance(item, dict):
                continue
            candidate = dict(item)
            bucket = str(candidate.get("bucket") or "").strip()
            skill = str(candidate.get("skill") or "").strip()
            if not skill:
                continue
            if skill_semantically_present(cv_text, skill):
                continue
            reason = str(candidate.get("reason") or "").strip()
            candidate.update({
                "type": "actionableEdit",
                "category": "skills",
                "message": reason or f"Rende {skill} più visibile per il ruolo.",
                "description": reason or f"Rende {skill} più visibile per il ruolo.",
                "reason": reason or f"Competenza coerente con il ruolo {role or role_family}.",
                "action": "Conferma e inserisci la skill nella sezione corretta.",
                "requires_confirmation": bucket == "hard_add",
                "supported_by_cv": bucket != "hard_add",
                "keywords_added": [skill],
            })
            if bucket == "hard_add":
                candidate["section"] = "hard_skills"
                candidate["title"] = "HARD SKILLS"
                candidate["impact"] = candidate.get("impact") or "alto"
                candidate["original_text"] = hard_original
                candidate["proposed_text"] = (
                    f"{hard_original} · {skill}" if hard_original else skill
                )
            elif bucket == "soft_emphasize":
                candidate["section"] = "soft_skills"
                candidate["title"] = "SOFT SKILLS"
                candidate["impact"] = candidate.get("impact") or "medio"
                candidate["original_text"] = soft_original
                candidate["proposed_text"] = (
                    f"{soft_original} · {skill}" if soft_original else skill
                )
            elif bucket == "present_reorder":
                candidate["section"] = "hard_skills"
                candidate["title"] = "HARD SKILLS"
                candidate["impact"] = candidate.get("impact") or "medio"
                candidate["original_text"] = hard_original
                candidate["proposed_text"] = (
                    f"{skill} · {hard_original}" if hard_original else skill
                )
            else:
                continue
            candidate.setdefault("priority", 20)
            candidate.setdefault("impact", "medio")
            candidate.setdefault("requires_confirmation", True)
            candidate.setdefault("supported_by_cv", True)
            if is_valid_actionable_suggestion(candidate) and suggestion_targets_current_cv(candidate, cv_text):
                cleaned_mini.append(candidate)
        if cleaned_mini:
            print(f"Mini-shot skill suggestions generate: {len(cleaned_mini)}")
            return cleaned_mini[:5]
    except Exception as exc:
        print(f"Mini-shot skill suggestions non riuscito: {exc}")

    return []
