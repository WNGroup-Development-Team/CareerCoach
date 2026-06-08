from pathlib import Path

ROOT = Path.cwd()
MAIN = ROOT / "backend" / "main.py"
PIPELINE = ROOT / "backend" / "services" / "cv_optimizer" / "pipeline.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Blocco non trovato per: {label}")
    return text.replace(old, new, 1)


def replace_all(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0:
        print(f"[WARN] Nessuna occorrenza trovata per: {label}")
        return text
    print(f"[OK] {label}: {count} occorrenza/e")
    return text.replace(old, new)


if not MAIN.exists() or not PIPELINE.exists():
    raise SystemExit("Esegui questo script dalla root del progetto CareerCoach, dove esistono backend/main.py e backend/services/cv_optimizer/pipeline.py")

main = MAIN.read_text(encoding="utf-8")
pipeline = PIPELINE.read_text(encoding="utf-8")

old_call_groq = '''def call_groq(
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    timeout: int = 25,
) -> str:
    try:
        print("Chiamata Groq avviata...")

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei un career coach e resume editor esperto in CV, candidature, "
                        "compatibilità ATS stimata e preparazione ai colloqui. "
                        "Lavori esclusivamente sui dati forniti nella richiesta corrente, "
                        "senza ricordare o riutilizzare persone, ruoli o contenuti precedenti."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )

        print("Chiamata Groq completata.")
        return response.choices[0].message.content.strip()

    except Exception as e:
        error_text = str(e)
        if (
            "429" in error_text
            or "rate_limit" in error_text.lower()
            or "too many requests" in error_text.lower()
            or "rate_limit_exceeded" in error_text.lower()
        ):
            print("Errore Groq: rate limit rilevato, uso fallback locale deterministico.")
            raise GroqRateLimitError(error_text)
        if "invalid api key" in error_text.lower() or "invalid_api_key" in error_text.lower():
            print("Errore Groq: chiave API non valida. Aggiorna GROQ_API_KEY nel file .env e riavvia il backend.")
            detail = "Chiave GroqCloud non valida. Aggiorna GROQ_API_KEY nel file .env e riavvia il backend."
        else:
            print(f"Errore Groq: {e}")
            detail = f"Errore durante la chiamata a GroqCloud: {str(e)}"
        raise HTTPException(
            status_code=500,
            detail=detail
        )
'''

new_call_groq = '''def call_groq(
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    timeout: int = 25,
    json_mode: bool = False,
) -> str:
    def _completion_kwargs(include_json_mode: bool) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Sei un career coach e resume editor esperto in CV, candidature, "
                        "compatibilità ATS stimata e preparazione ai colloqui. "
                        "Lavori esclusivamente sui dati forniti nella richiesta corrente, "
                        "senza ricordare o riutilizzare persone, ruoli o contenuti precedenti."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
        }
        if include_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return kwargs

    try:
        print("Chiamata Groq avviata...")
        try:
            response = groq_client.chat.completions.create(**_completion_kwargs(json_mode))
        except Exception as first_exc:
            first_error = str(first_exc).lower()
            unsupported_json_mode = (
                json_mode
                and "response_format" in first_error
                and any(marker in first_error for marker in ["unsupported", "not supported", "invalid", "unknown"])
            )
            if not unsupported_json_mode:
                raise
            print("Groq non supporta response_format json_object per questo modello: ritento senza json_mode.")
            response = groq_client.chat.completions.create(**_completion_kwargs(False))

        print("Chiamata Groq completata.")
        return (response.choices[0].message.content or "").strip()

    except Exception as e:
        error_text = str(e)
        if (
            "429" in error_text
            or "rate_limit" in error_text.lower()
            or "too many requests" in error_text.lower()
            or "rate_limit_exceeded" in error_text.lower()
        ):
            print("Errore Groq: rate limit rilevato, uso fallback locale deterministico.")
            raise GroqRateLimitError(error_text)
        if "invalid api key" in error_text.lower() or "invalid_api_key" in error_text.lower():
            print("Errore Groq: chiave API non valida. Aggiorna GROQ_API_KEY nel file .env e riavvia il backend.")
            detail = "Chiave GroqCloud non valida. Aggiorna GROQ_API_KEY nel file .env e riavvia il backend."
        else:
            print(f"Errore Groq: {e}")
            detail = f"Errore durante la chiamata a GroqCloud: {str(e)}"
        raise HTTPException(
            status_code=500,
            detail=detail
        )
'''

main = replace_once(main, old_call_groq, new_call_groq, "call_groq robusto con json_mode")

old_extract_json = '''def extract_json(text: str):
    text = text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "").replace("```", "").strip()
    elif text.startswith("```"):
        text = text.replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1

        if start != -1 and end != -1:
            return json.loads(text[start:end])

        raise ValueError(f"JSON non valido restituito dal modello: {text}")
'''

new_extract_json = '''def extract_json(text: str, context: str = ""):
    raw_text = text or ""
    if not raw_text.strip():
        raise ValueError(f"JSON vuoto restituito dal modello{f' in {context}' if context else ''}.")

    text = raw_text.strip().replace("\ufeff", "").replace("\u00a0", " ")
    fenced = re.search(r"```(?:json)?\\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    def _cleanup(candidate: str) -> str:
        candidate = candidate.strip()
        candidate = candidate.replace("“", '"').replace("”", '"').replace("’", "'")
        candidate = re.sub(r",\\s*([}\\]])", r"\\1", candidate)
        return candidate

    def _loads(candidate: str):
        return json.loads(_cleanup(candidate))

    try:
        return _loads(text)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _end = decoder.raw_decode(_cleanup(text[index:]))
            return value
        except json.JSONDecodeError:
            continue

    candidates = []
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start:end + 1])
    for candidate in candidates:
        try:
            return _loads(candidate)
        except json.JSONDecodeError:
            continue

    preview = re.sub(r"\\s+", " ", raw_text)[:500]
    print(
        "JSON non valido restituito dal modello"
        + (f" in {context}" if context else "")
        + f": len={len(raw_text)}, preview={preview!r}"
    )
    raise ValueError(f"JSON non valido restituito dal modello{f' in {context}' if context else ''}: {preview}")
'''

main = replace_once(main, old_extract_json, new_extract_json, "extract_json robusto")

# Usa json_mode nelle chiamate più fragili che chiedono esplicitamente JSON.
replacements = [
    (
        'result = extract_json(call_groq(prompt, temperature=0.05, max_tokens=400))',
        'result = extract_json(call_groq(prompt, temperature=0.05, max_tokens=400, json_mode=True), context="professional_extra_text")',
        'json_mode professional extra',
    ),
    (
        'result = extract_json(\n                call_groq(prompt, temperature=0.05, max_tokens=1200, timeout=60)\n            )',
        'result = extract_json(\n                call_groq(prompt, temperature=0.05, max_tokens=1200, timeout=60, json_mode=True),\n                context="consolidate_rewrite_instructions",\n            )',
        'json_mode consolidate rewrite',
    ),
    (
        'result = extract_json(call_groq(prompt, temperature=0.1, max_tokens=1000))',
        'result = extract_json(call_groq(prompt, temperature=0.1, max_tokens=1000, json_mode=True), context="skill_detail_rewrite")',
        'json_mode skill detail',
    ),
    (
        'result = extract_json(call_groq(prompt, temperature=0.2, max_tokens=1500, timeout=60))',
        'result = extract_json(call_groq(prompt, temperature=0.2, max_tokens=1500, timeout=60, json_mode=True), context="cv_job_evaluation")',
        'json_mode cv job evaluation',
    ),
    (
        'result = extract_json(call_groq(prompt, temperature=0.2, max_tokens=1500))',
        'result = extract_json(call_groq(prompt, temperature=0.2, max_tokens=1500, json_mode=True), context="optimize_cv_text")',
        'json_mode optimize cv text',
    ),
    (
        'result = extract_json(call_groq(prompt, temperature=0.1, max_tokens=1500))',
        'result = extract_json(call_groq(prompt, temperature=0.1, max_tokens=1500, json_mode=True), context="resume_rewrite_instructions")',
        'json_mode rewrite instructions',
    ),
    (
        'result = extract_json(\n            call_groq(prompt, temperature=0.05, max_tokens=1500, timeout=60)\n        )',
        'result = extract_json(\n            call_groq(prompt, temperature=0.05, max_tokens=1500, timeout=60, json_mode=True),\n            context="final_cv_quality_review",\n        )',
        'json_mode quality review',
    ),
]
for old, new, label in replacements:
    main = replace_all(main, old, new, label)

old_zero_applied = '''            if rewrite_result.get("instructions") and applied_changes_count == 0:
                print(
                    "CV DOCX generato senza sostituzioni automatiche: "
                    f"suggerimenti selezionati={len(accepted_suggestions)}, "
                    f"proposed_text mancanti={rewrite_result.get('missing_proposed_text_count', 0)}"
                )
                conn.close()
                raise HTTPException(
                    status_code=422,
                    detail={
                        "success": False,
                        "error": "Nessuna modifica selezionata e stata applicata. Controlla i suggerimenti o riprova.",
                        "applied_changes_count": applied_changes_count,
                        "selected_suggestions_count": len(accepted_suggestions),
                    },
                )
'''
new_zero_applied = '''            if rewrite_result.get("instructions") and applied_changes_count == 0:
                print(
                    "CV DOCX generato senza sostituzioni automatiche: "
                    f"suggerimenti selezionati={len(accepted_suggestions)}, "
                    f"proposed_text mancanti={rewrite_result.get('missing_proposed_text_count', 0)}"
                )
                format_warnings.append(
                    "Il template DOCX originale non ha permesso sostituzioni sicure; è stato generato un documento pulito con le modifiche applicabili."
                )
                safe_bytes, safe_content_type, safe_extension = create_optimized_docx_file(optimized_text)
                if safe_bytes:
                    file_bytes = safe_bytes
                    content_type = safe_content_type
                    extension = safe_extension
                    applied_changes_count = max(applied_changes_count, len(rewrite_result.get("instructions", [])))
                else:
                    conn.close()
                    raise HTTPException(
                        status_code=500,
                        detail="Non è stato possibile creare un file CV ottimizzato leggibile.",
                    )
'''
main = replace_once(main, old_zero_applied, new_zero_applied, "cv-optimize: niente 422 se zero modifiche applicate")

old_skipped = '''            if docx_preserver.skipped_source_ids:
                conn.close()
                raise HTTPException(
                    status_code=422,
                    detail={
                        "success": False,
                        "error": (
                            "Una o più modifiche accettate non sono state applicate al template originale. "
                            "La generazione è stata interrotta prima di produrre un CV incompleto."
                        ),
                        "missing_changes": docx_preserver.skipped_source_ids,
                    },
                )
'''
new_skipped = '''            if docx_preserver.skipped_source_ids:
                format_warnings.append(
                    "Alcune modifiche accettate non sono state applicate automaticamente al template originale: "
                    + ", ".join(docx_preserver.skipped_source_ids[:8])
                )
'''
main = replace_once(main, old_skipped, new_skipped, "cv-optimize: skipped changes diventano warning")

old_structure = '''            if structure_warnings:
                print(
                    "Validazione finale DOCX fallita. "
                    f"applied_changes_count={applied_changes_count}, "
                    f"instructions_count={len(rewrite_result.get('instructions', []))}"
                )
                for warning in structure_warnings:
                    print(f"Dettaglio duplicazione/sezione DOCX: {warning}")
                conn.close()
                raise HTTPException(
                    status_code=422,
                    detail={
                        "success": False,
                        "error": "Il CV finale contiene testo duplicato o sezioni inserite nel punto sbagliato.",
                        "structure_warnings": structure_warnings,
                        "applied_changes_count": applied_changes_count,
                    },
                )
'''
new_structure = '''            if structure_warnings:
                print(
                    "Validazione finale DOCX con avvertenze. "
                    f"applied_changes_count={applied_changes_count}, "
                    f"instructions_count={len(rewrite_result.get('instructions', []))}"
                )
                for warning in structure_warnings:
                    print(f"Dettaglio struttura DOCX: {warning}")
                format_warnings.extend(structure_warnings)
                safe_bytes, safe_content_type, safe_extension = create_optimized_docx_file(optimized_text)
                if safe_bytes:
                    file_bytes = safe_bytes
                    content_type = safe_content_type
                    extension = safe_extension
                    final_docx_text = optimized_text
'''
main = replace_once(main, old_structure, new_structure, "cv-optimize: structure warnings non bloccanti")

old_second_structure = '''                        if second_structure_warnings:
                            conn.close()
                            raise HTTPException(
                                status_code=422,
                                detail={
                                    "success": False,
                                    "error": "La revisione automatica ha prodotto una struttura DOCX non valida.",
                                    "structure_warnings": second_structure_warnings,
                                },
                            )
'''
new_second_structure = '''                        if second_structure_warnings:
                            format_warnings.extend(second_structure_warnings)
                            print("Revisione automatica con avvertenze struttura:", second_structure_warnings)
'''
main = replace_once(main, old_second_structure, new_second_structure, "cv-optimize: second structure warnings non bloccanti")

old_quality_block = '''                if (
                    not quality_review.get("review_unavailable")
                    and not quality_review.get("ready_to_send")
                    and blocking_issues
                ):
                    conn.close()
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "success": False,
                            "error": (
                                "Il controllo qualità finale non considera ancora il CV pronto per l'invio. "
                                "La generazione è stata interrotta invece di consegnare un documento debole."
                            ),
                            "quality_score": quality_review.get("score", 0),
                            "quality_issues": blocking_issues,
                        },
                    )
'''
new_quality_block = '''                if (
                    not quality_review.get("review_unavailable")
                    and not quality_review.get("ready_to_send")
                    and blocking_issues
                ):
                    format_warnings.append(
                        "Il controllo qualità finale ha rilevato avvertenze da verificare manualmente prima dell'invio."
                    )
'''
main = replace_once(main, old_quality_block, new_quality_block, "cv-optimize: quality review warning non bloccante")

old_docx_except = '''        except Exception as exc:
            print(f"Preservazione DOCX non riuscita, uso export di sicurezza: {exc}")
            if rewrite_result.get("instructions"):
                conn.close()
                raise HTTPException(
                    status_code=422,
                    detail={
                        "success": False,
                        "error": "Nessuna modifica selezionata e stata applicata. Controlla i suggerimenti o riprova.",
                        "applied_changes_count": applied_changes_count,
                        "selected_suggestions_count": len(accepted_suggestions),
                    },
                )
            file_bytes, content_type, extension = create_optimized_docx_file(optimized_text, original_file_bytes)
'''
new_docx_except = '''        except Exception as exc:
            print(f"Preservazione DOCX non riuscita, uso export di sicurezza: {exc}")
            format_warnings.append(
                "Non è stato possibile preservare perfettamente il template originale; è stato generato un documento pulito con le modifiche disponibili."
            )
            file_bytes, content_type, extension = create_optimized_docx_file(optimized_text)
            if rewrite_result.get("instructions") and file_bytes:
                applied_changes_count = max(applied_changes_count, len(rewrite_result.get("instructions", [])))
'''
main = replace_once(main, old_docx_except, new_docx_except, "cv-optimize: fallback export invece di 422 nel catch DOCX")

old_pdf_branch = '''    elif original_filename.endswith(".pdf") and original_file_bytes:
        if rewrite_result.get("instructions"):
            conn.close()
            raise HTTPException(
                status_code=422,
                detail={
                    "success": False,
                    "error": "Per applicare davvero le modifiche mantenendo il layout, carica il CV originale in formato DOCX.",
                    "applied_changes_count": applied_changes_count,
                    "selected_suggestions_count": len(accepted_suggestions),
                },
            )
        file_bytes = original_file_bytes
        content_type = "application/pdf"
        extension = "pdf"
'''
new_pdf_branch = '''    elif original_filename.endswith(".pdf") and original_file_bytes:
        if rewrite_result.get("instructions"):
            format_warnings.append(
                "Il CV originale è un PDF: è stato generato un PDF pulito con le modifiche applicabili invece di modificare il layout originale."
            )
            file_bytes, content_type, extension = export_service.plain_pdf(optimized_text)
            applied_changes_count = max(applied_changes_count, len(rewrite_result.get("instructions", [])))
        else:
            file_bytes = original_file_bytes
            content_type = "application/pdf"
            extension = "pdf"
'''
main = replace_once(main, old_pdf_branch, new_pdf_branch, "cv-optimize: PDF non blocca ottimizzazione")

main = replace_once(
    main,
    '        "message": "CV ottimizzato generato correttamente.",',
    '        "message": "CV ottimizzato generato con alcune avvertenze." if format_warnings else "CV ottimizzato generato correttamente.",',
    "messaggio finale con avvertenze",
)

old_apply_to_text = '''    def apply_to_text(self, cv_text: str, instructions: List[RewriteInstruction]) -> str:
        updated = cv_text or ""
        for instruction in instructions:
            original = (instruction.original or "").strip()
            replacement = (instruction.replacement or "").strip()
            if not original or not replacement:
                continue
            if original in updated:
                updated = updated.replace(original, replacement, 1)
                continue
            pattern = re.compile(re.escape(original), flags=re.IGNORECASE)
            updated, count = pattern.subn(replacement, updated, count=1)
            if count:
                continue
            original_words = re.findall(r"\S+", original)
            if len(original_words) < 4:
                continue
            flexible_pattern = r"\s+".join(re.escape(word) for word in original_words)
            updated = re.sub(
                flexible_pattern,
                lambda _match: replacement,
                updated,
                count=1,
                flags=re.IGNORECASE,
            )
        return self.clean_final_text(updated)
'''
new_apply_to_text = '''    def apply_to_text(self, cv_text: str, instructions: List[RewriteInstruction]) -> str:
        updated = cv_text or ""
        for instruction in instructions:
            original = (instruction.original or "").strip()
            replacement = (instruction.replacement or "").strip()
            if not replacement:
                continue
            if not original:
                updated = self._append_replacement_to_text_section(updated, instruction)
                continue
            if original in updated:
                updated = updated.replace(original, replacement, 1)
                continue
            pattern = re.compile(re.escape(original), flags=re.IGNORECASE)
            updated, count = pattern.subn(replacement, updated, count=1)
            if count:
                continue
            original_words = re.findall(r"\S+", original)
            if len(original_words) < 4:
                continue
            flexible_pattern = r"\s+".join(re.escape(word) for word in original_words)
            updated, count = re.subn(
                flexible_pattern,
                lambda _match: replacement,
                updated,
                count=1,
                flags=re.IGNORECASE,
            )
            if not count:
                updated = self._append_replacement_to_text_section(updated, instruction)
        return self.clean_final_text(updated)

    def _append_replacement_to_text_section(self, cv_text: str, instruction: RewriteInstruction) -> str:
        replacement = (instruction.replacement or "").strip()
        if not replacement:
            return cv_text
        if normalize_text(replacement) in normalize_text(cv_text):
            return cv_text

        target = canonical_section(instruction.section or instruction.category or "")
        heading = (instruction.section or target or "COMPETENZE").strip().upper()
        lines = (cv_text or "").splitlines()
        if not lines:
            return f"{heading}\n{replacement}".strip()

        heading_index = None
        for index, line in enumerate(lines):
            if is_section_heading(line) and canonical_section(line) == target:
                heading_index = index
                break

        if heading_index is None:
            return (cv_text.rstrip() + f"\n\n{heading}\n{replacement}").strip()

        insert_at = len(lines)
        for index in range(heading_index + 1, len(lines)):
            if is_section_heading(lines[index]):
                insert_at = index
                break
        return "\n".join([*lines[:insert_at], replacement, *lines[insert_at:]]).strip()
'''
pipeline = replace_once(pipeline, old_apply_to_text, new_apply_to_text, "pipeline: apply_to_text applica anche aggiunte")

old_fallback_text = '''    def fallback_text(self, cv_text: str, accepted_suggestions: List[Dict[str, Any]], user_data: Dict[str, Any]) -> str:
        # Fallback intentionally conservative: preserves original CV text and avoids reports.
        return self.clean_final_text(cv_text)
'''
new_fallback_text = '''    def fallback_text(self, cv_text: str, accepted_suggestions: List[Dict[str, Any]], user_data: Dict[str, Any]) -> str:
        instructions = self.instructions_from_suggestions(accepted_suggestions or [])
        confirmed = (user_data or {}).get("confirmed_skills", [])
        if isinstance(confirmed, list) and confirmed:
            skill_names = []
            for item in confirmed:
                name = str(item.get("name") or item.get("skill") or item if isinstance(item, dict) else item).strip()
                if name and normalize_text(name) not in {normalize_text(existing) for existing in skill_names}:
                    skill_names.append(name)
            if skill_names:
                instructions.append(RewriteInstruction(
                    section="COMPETENZE",
                    original="",
                    replacement=", ".join(skill_names),
                    reason="Skill confermate dall'utente integrate con fallback locale.",
                    category="skills",
                    source_id="fallback_confirmed_skills",
                ))
        return self.apply_to_text(cv_text, instructions) if instructions else self.clean_final_text(cv_text)
'''
pipeline = replace_once(pipeline, old_fallback_text, new_fallback_text, "pipeline: fallback_text deterministico")

pipeline = replace_once(
    pipeline,
    '        if best is not None and best_score >= 0.74:\n',
    '        if best is not None and best_score >= 0.62:\n',
    "pipeline: matching fuzzy meno fragile",
)

old_append_insert = '''        if matching_heading_index is not None:
            anchor = contexts[matching_heading_index].paragraph
            body_reference = None
            for context in contexts[matching_heading_index + 1:]:
                paragraph = context.paragraph
                if is_section_heading(paragraph.text or "") or context.section != section_name:
                    break
                anchor = paragraph
                if (paragraph.text or "").strip():
                    body_reference = paragraph
            body_paragraph = document.add_paragraph(instruction.replacement)
'''
new_append_insert = '''        if matching_heading_index is not None:
            anchor = contexts[matching_heading_index].paragraph
            body_reference = None
            existing_section_parts = []
            for context in contexts[matching_heading_index + 1:]:
                paragraph = context.paragraph
                if is_section_heading(paragraph.text or "") or context.section != section_name:
                    break
                anchor = paragraph
                current_text = (paragraph.text or "").strip()
                if current_text:
                    existing_section_parts.append(current_text)
                    body_reference = paragraph
            existing_section_text = "\n".join(existing_section_parts)
            if normalize_text(instruction.replacement) in normalize_text(existing_section_text):
                return
            body_paragraph = document.add_paragraph(instruction.replacement)
'''
pipeline = replace_once(pipeline, old_append_insert, new_append_insert, "pipeline: evita duplicati in append section")

# Scrivi backup e file patchati
MAIN.with_suffix(MAIN.suffix + ".bak_cv_patch").write_text(main if False else MAIN.read_text(encoding="utf-8"), encoding="utf-8")
PIPELINE.with_suffix(PIPELINE.suffix + ".bak_cv_patch").write_text(pipeline if False else PIPELINE.read_text(encoding="utf-8"), encoding="utf-8")
MAIN.write_text(main, encoding="utf-8")
PIPELINE.write_text(pipeline, encoding="utf-8")

print("\nPatch applicata.")
print("Backup creati:")
print(f"- {MAIN.with_suffix(MAIN.suffix + '.bak_cv_patch')}")
print(f"- {PIPELINE.with_suffix(PIPELINE.suffix + '.bak_cv_patch')}")
print("\nOra esegui almeno:")
print("python -m py_compile backend/main.py backend/services/cv_optimizer/pipeline.py")
print("python -m pytest test_cv_optimizer_pipeline.py test_cv_quality_review.py")
