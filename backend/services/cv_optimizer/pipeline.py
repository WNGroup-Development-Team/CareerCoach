from __future__ import annotations

import io
import re
import shutil
import subprocess
import tempfile
import textwrap
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional


SECTION_ALIASES = {
    "profilo": {"profilo", "profilo professionale", "chi sono", "summary", "about"},
    "esperienze": {
        "esperienze",
        "esperienza",
        "esperienze professionali",
        "esperienza professionale",
        "work experience",
        "professional experience",
    },
    "formazione": {"formazione", "istruzione", "education"},
    "competenze": {"competenze", "skills", "hard skills", "soft skills", "competenze tecniche"},
    "lingue": {"lingue", "languages"},
    "certificazioni": {"certificazioni", "certificati", "certifications"},
    "progetti": {"progetti", "projects", "pagina aggiuntiva", "esperienze aggiuntive", "attivita rilevanti"},
    "contatti": {"contatti", "contact", "contacts"},
}

SECTION_HEADINGS = {heading for values in SECTION_ALIASES.values() for heading in values}
SECTION_LEAK_MARKERS = {
    "contatti", "lingue", "hard skills", "soft skills", "formazione",
    "istruzione", "esperienze professionali", "esperienza professionale",
    "esperienze", "progetti", "certificazioni",
}
GENERIC_KEYWORDS = {
    "data", "analyst", "analysis", "business", "project", "manager", "team", "office",
    "azienda", "ruolo", "junior", "senior", "stage", "internship", "lavoro",
}
SYNONYMS = {
    "analisi dati": {"data analysis", "data analytics", "analisi dati"},
    "excel": {"excel", "microsoft excel", "fogli di calcolo"},
    "power bi": {"power bi", "powerbi", "business intelligence"},
    "sql": {"sql", "database", "query"},
    "python": {"python", "pandas", "numpy"},
    "ai": {"ai", "artificial intelligence", "intelligenza artificiale"},
    "machine learning": {"machine learning", "ml", "apprendimento automatico"},
    "nlp": {"nlp", "natural language processing", "elaborazione del linguaggio naturale"},
    "llm": {"llm", "large language models", "large language model", "modelli llm"},
    "clustering testuale": {"clustering testuale", "clustering", "text clustering"},
    "accuratezza": {"accuratezza", "accuracy"},
    "tempi di risposta": {"tempi di risposta", "response time", "response times"},
    "preparazione dati": {"preparazione dati", "data preparation", "preprocessing", "preparazione dei dati"},
    "confronto modelli": {"confronto modelli", "model comparison", "confronto delle prestazioni"},
    "comunicazione": {"comunicazione", "communication"},
    "problem solving": {"problem solving", "risoluzione problemi"},
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").lower()).strip()


def tokenize(value: str) -> List[str]:
    return re.findall(r"[a-zA-ZÀ-ÖØ-öø-ÿ0-9][a-zA-ZÀ-ÖØ-öø-ÿ0-9+#.-]{1,}", normalize_text(value))


def is_section_heading(line: str) -> bool:
    clean = normalize_text(line).strip(":")
    stripped = (line or "").strip().strip(":")
    return clean in SECTION_HEADINGS or (
        bool(clean)
        and len(clean) <= 42
        and stripped.upper() == stripped
        and any(char.isalpha() for char in clean)
    )


def canonical_section(line: str) -> str:
    clean = normalize_text(line).strip(":")
    for canonical, aliases in SECTION_ALIASES.items():
        if clean in aliases:
            return canonical
    return clean or "contenuto"


@dataclass
class ResumeSection:
    name: str
    heading: str
    lines: List[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()


@dataclass
class RewriteInstruction:
    section: str
    original: str
    replacement: str
    reason: str = ""
    category: str = ""
    source_id: str = ""


@dataclass
class ParagraphContext:
    paragraph: Any
    section: str


class ResumeParser:
    def _prepared_lines(self, cv_text: str) -> List[str]:
        prepared = re.sub(r"\r\n?", "\n", cv_text or "")
        prepared = re.sub(r"[ \t]+", " ", prepared)
        heading_pattern = "|".join(
            re.escape(heading)
            for heading in sorted(SECTION_HEADINGS, key=len, reverse=True)
        )
        if heading_pattern:
            prepared = re.sub(
                rf"(?<![\wÀ-ÖØ-öø-ÿ])({heading_pattern})\s*:?(?=\s|$)",
                lambda match: f"\n{match.group(1).strip()}\n",
                prepared,
                flags=re.IGNORECASE,
            )
        return [line.strip() for line in prepared.splitlines() if line.strip()]

    def parse_text(self, cv_text: str) -> List[ResumeSection]:
        sections: List[ResumeSection] = []
        current = ResumeSection(name="intestazione", heading="", lines=[])

        for line in self._prepared_lines(cv_text):
            if is_section_heading(line):
                if current.heading or current.lines:
                    sections.append(current)
                current = ResumeSection(name=canonical_section(line), heading=line, lines=[])
            else:
                current.lines.append(line)

        if current.heading or current.lines:
            sections.append(current)
        return sections

    def section_text_map(self, cv_text: str) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for section in self.parse_text(cv_text):
            result.setdefault(section.name, section.text)
        return result


class JobAnalyzer:
    def __init__(self, normalizer: Callable[[str], str] = normalize_text):
        self.normalizer = normalizer

    def extract_keywords(self, role: str, description: str = "", required_skills: str = "") -> List[str]:
        explicit = [
            item.strip()
            for item in re.split(r"[,;\n]+", required_skills or "")
            if item.strip()
        ]
        source = description.strip() or role.strip()
        candidates = explicit + self._phrases(source) + tokenize(source)

        keywords: List[str] = []
        seen = set()
        for candidate in candidates:
            clean = self.normalizer(candidate).strip(" .,:;")
            if not clean or clean in seen:
                continue
            if clean in GENERIC_KEYWORDS or (len(clean) < 4 and clean not in {"sql"}):
                continue
            if " " not in clean and clean in {"data", "analyst"}:
                continue
            seen.add(clean)
            keywords.append(candidate.strip())
            if len(keywords) >= 20:
                break
        return keywords

    def _phrases(self, text: str) -> List[str]:
        normalized = self.normalizer(text)
        phrases = []
        for phrase in sorted(SYNONYMS, key=len, reverse=True):
            if phrase in normalized or any(alias in normalized for alias in SYNONYMS[phrase]):
                phrases.append(phrase)
        words = [word for word in tokenize(text) if word not in GENERIC_KEYWORDS]
        for size in (3, 2):
            for index in range(0, max(len(words) - size + 1, 0)):
                phrase = " ".join(words[index:index + size])
                if phrase and phrase not in GENERIC_KEYWORDS:
                    phrases.append(phrase)
        quoted = re.findall(r"['\"]([^'\"]{4,40})['\"]", text or "")
        return phrases + quoted


class MatchingEngine:
    def __init__(self, normalizer: Callable[[str], str] = normalize_text):
        self.normalizer = normalizer

    def split_present_missing(self, cv_text: str, keywords: Iterable[str]) -> Dict[str, List[str]]:
        cv_plain = self.normalizer(cv_text)
        present: List[str] = []
        missing: List[str] = []
        for keyword in keywords:
            variants = SYNONYMS.get(self.normalizer(keyword), {self.normalizer(keyword)})
            if any(variant and variant in cv_plain for variant in variants):
                present.append(keyword)
            else:
                missing.append(keyword)
        return {"present": present, "missing": missing}


class CoachSuggestionEngine:
    def accepted_only(self, suggestions: Any) -> List[Dict[str, Any]]:
        if not isinstance(suggestions, list):
            return []
        accepted = []
        for item in suggestions:
            if isinstance(item, dict) and item.get("type") == "actionableEdit":
                description = str(item.get("description") or item.get("action") or item.get("coach_tip") or "").strip()
                proposed_text = str(item.get("proposed_text") or item.get("replacement") or "").strip()
                original_text = str(item.get("original_text") or item.get("original") or "").strip()
                section = str(item.get("section") or "").strip()
                if proposed_text and original_text and section:
                    accepted.append({
                        **item,
                        "description": description,
                        "section": section,
                        "original_text": original_text,
                        "proposed_text": proposed_text,
                    })
        return accepted[:30]


class ResumeRewriter:
    FORBIDDEN_OUTPUT_MARKERS = (
        "CV ottimizzato - bozza guidata",
        "Ottimizzazioni accettate dall'utente",
        "CV originale da rifinire",
        "Punteggio",
        "ATS simulato",
        "Suggerimenti coach",
    )

    def __init__(self, parser: Optional[ResumeParser] = None):
        self.parser = parser or ResumeParser()

    def build_prompt(
        self,
        cv_text: str,
        target: Dict[str, str],
        accepted_suggestions: List[Dict[str, Any]],
        user_data: Dict[str, Any],
        sections: Optional[List[ResumeSection]] = None,
    ) -> str:
        section_payload = [
            {"name": section.name, "heading": section.heading, "text": section.text[:2500]}
            for section in (sections or self.parser.parse_text(cv_text))
        ]
        return f"""
Sei un resume editor. Devi restituire SOLO JSON valido.

Obiettivo: crea SOLO istruzioni di riscrittura puntuali per piccoli blocchi del CV.
Non generare mai un CV completo e non restituire testo completo da incollare nel DOCX.

Target:
{target}

Sezioni CV originali:
{section_payload}

Modifiche accettate dall'utente:
{accepted_suggestions}

Dati confermati dall'utente:
{user_data}

Schema JSON:
{{
  "instructions": [
    {{
      "section": "nome sezione canonico",
      "original": "testo esatto o frase del CV da sostituire. Lascia vuoto '' SOLO se stai aggiungendo una entry del tutto nuova.",
      "replacement": "nuovo testo naturale o lista",
      "reason": "breve motivo interno"
    }}
  ]
}}

Regole:
- DEVI ASSOLUTAMENTE includere e integrare nel CV TUTTE le modifiche accettate dall'utente e TUTTI i dati confermati (es. confirmed_skills). Se non lo fai, l'utente perderà i dati inseriti!
- Per AGGIUNGERE nuove competenze/skill (es. confermate dall'utente) usa SEMPRE una istruzione dedicata con `section`: "competenze", `original`: "" e `replacement`: "Nome skill 1, Nome skill 2". NON copiare le vecchie skill nel replacement di questa istruzione, il sistema appenderà quelle nuove automaticamente alla sezione corretta.
- ATTENZIONE CRITICA: Se invece stai modificando o migliorando un'esperienza, formazione o profilo GIÀ PRESENTE nel CV, DEVI OBBLIGATORIAMENTE inserire in `original` il frammento esatto di testo originale da sostituire.
- Non duplicare mai sezioni già presenti. Usa `original: ""` SOLO ED ESCLUSIVAMENTE per aggiungere skill, progetti o esperienze completamente nuove non menzionate nel CV.
- Riscrivi in modo intelligente e naturale.
- Mantieni separazione tra Hard Skills e Soft Skills se necessario, oppure uniscile logicamente.
- Ogni replacement con original NON vuoto deve sostituire solo il blocco originale della stessa sezione.
- Non inventare esperienze o competenze non confermate.
- Restituisci da 1 a 15 istruzioni concrete.
"""

    def apply_to_text(self, cv_text: str, instructions: List[RewriteInstruction]) -> str:
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

    def fallback_text(self, cv_text: str, accepted_suggestions: List[Dict[str, Any]], user_data: Dict[str, Any]) -> str:
        # Fallback intentionally conservative: preserves original CV text and avoids reports.
        return self.clean_final_text(cv_text)

    def instructions_from_result(self, result: Dict[str, Any]) -> List[RewriteInstruction]:
        instructions = []
        for item in result.get("instructions") or []:
            if not isinstance(item, dict):
                continue
            original = str(item.get("original") or "").strip()
            raw_replacement = str(item.get("replacement") or "").strip()
            section = canonical_section(str(item.get("section") or ""))
            if not self.is_safe_replacement(section, raw_replacement):
                print(
                    "Suggerimento riscrittura scartato: "
                    f"id={item.get('id') or item.get('title') or 'llm_instruction'}, "
                    f"section={section}, replacement={raw_replacement[:180]}"
                )
                continue
            replacement = self.clean_replacement(raw_replacement)
            if not replacement or original == replacement:
                continue
            instructions.append(RewriteInstruction(
                section=section,
                original=original,
                replacement=replacement,
                reason=str(item.get("reason") or "").strip(),
                category=str(item.get("category") or "").strip(),
                source_id=str(item.get("id") or item.get("title") or "llm_instruction").strip(),
            ))
        return instructions[:40]

    def instructions_from_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[RewriteInstruction]:
        instructions = []
        for item in suggestions:
            original = str(item.get("original_text") or item.get("original") or "").strip()
            raw_proposed = str(item.get("proposed_text") or item.get("replacement") or "").strip()
            section = canonical_section(str(item.get("section") or item.get("category") or ""))
            if not raw_proposed:
                continue
            if not self.is_safe_replacement(section, raw_proposed):
                print(
                    "Suggerimento coach scartato: "
                    f"id={item.get('id') or item.get('title') or 'coach_suggestion'}, "
                    f"section={section}, category={item.get('category') or ''}, "
                    f"proposed_text={raw_proposed[:180]}"
                )
                continue
            proposed = self.clean_replacement(raw_proposed)
            instructions.append(RewriteInstruction(
                section=section,
                original=original,
                replacement=proposed,
                reason=str(item.get("reason") or item.get("description") or "").strip(),
                category=str(item.get("category") or "").strip(),
                source_id=str(item.get("id") or item.get("title") or "coach_suggestion").strip(),
            ))
        return instructions[:40]

    def is_safe_replacement(self, section: str, replacement: str) -> bool:
        raw = replacement or ""
        normalized = normalize_text(raw)
        if not normalized:
            return False
        section_name = canonical_section(section)
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        exact_heading_lines = {
            normalize_text(marker).strip(":")
            for marker in SECTION_LEAK_MARKERS
        }
        if any(normalize_text(line).strip(":") in exact_heading_lines for line in lines):
            return False
        word_count = len(tokenize(replacement))
        max_words = {
            "profilo": 250,
            "competenze": 300,
            "formazione": 300,
            "esperienze": 600,
        }.get(section_name, 500)
        if word_count > max_words:
            return False
        if section_name == "profilo" and len(lines) > 15:
            return False
        blocked_profile_lines = {"formazione", "esperienze professionali", "esperienza professionale", "contatti", "lingue"}
        if section_name == "competenze" and any(normalize_text(line).strip(":") in blocked_profile_lines for line in lines):
            return False
        if section_name == "formazione" and any(normalize_text(line).strip(":") in {"contatti", "lingue", "hard skills", "soft skills", "esperienze professionali", "esperienza professionale"} for line in lines):
            return False
        if section_name == "esperienze" and any(normalize_text(line).strip(":") in {"contatti", "lingue", "hard skills", "soft skills", "formazione"} for line in lines):
            return False
        return True

    def clean_final_text(self, text: str) -> str:
        lines = []
        for raw_line in (text or "").splitlines():
            line = self.clean_line(raw_line)
            if not line:
                continue
            if any(marker.lower() in line.lower() for marker in self.FORBIDDEN_OUTPUT_MARKERS):
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    def clean_line(self, line: str) -> str:
        line = re.sub(r"\s+", " ", line or "").strip()
        for heading in SECTION_HEADINGS:
            upper = heading.upper()
            line = re.sub(rf"(?<!^)\b{re.escape(upper)}\b(?!$)", "", line)
        return re.sub(r"\s{2,}", " ", line).strip()

    def clean_replacement(self, value: str) -> str:
        lines = [self.clean_line(line) for line in (value or "").splitlines()]
        return "\n".join(line for line in lines if line).strip()


class DocxPreserver:
    def __init__(self) -> None:
        self.applied_source_ids: List[str] = []
        self.skipped_source_ids: List[str] = []

    def apply(self, original_file_bytes: bytes, instructions: List[RewriteInstruction]) -> tuple[bytes, int]:
        from docx import Document

        self.applied_source_ids = []
        self.skipped_source_ids = []
        document = Document(io.BytesIO(original_file_bytes))
        applied = 0
        for instruction in instructions:
            if not self._valid_instruction(instruction):
                self.skipped_source_ids.append(instruction.source_id or instruction.section)
                continue
            contexts = self._paragraph_contexts(document)
            if self._should_append(instruction):
                self._append_section(document, instruction)
                applied += 1
                self.applied_source_ids.append(instruction.source_id or instruction.section)
                continue
            if instruction.original and self._replace_exact(contexts, instruction):
                applied += 1
                self.applied_source_ids.append(instruction.source_id or instruction.section)
                continue
            if instruction.original and self._replace_similar(contexts, instruction):
                applied += 1
                self.applied_source_ids.append(instruction.source_id or instruction.section)
                continue
            if instruction.original and self._replace_section_block(contexts, instruction):
                applied += 1
                self.applied_source_ids.append(instruction.source_id or instruction.section)
                continue
            if self._replace_in_section(contexts, instruction):
                applied += 1
                self.applied_source_ids.append(instruction.source_id or instruction.section)
                continue
            if self._append_to_target_section(document, instruction):
                applied += 1
                self.applied_source_ids.append(instruction.source_id or instruction.section)
                continue
            self.skipped_source_ids.append(instruction.source_id or instruction.section)

        output = io.BytesIO()
        document.save(output)
        return output.getvalue(), applied

    def _paragraph_contexts(self, document) -> List[ParagraphContext]:
        contexts: List[ParagraphContext] = []
        current_section = "intestazione"
        for paragraph in document.paragraphs:
            text = (paragraph.text or "").strip()
            if is_section_heading(text):
                current_section = canonical_section(text)
            contexts.append(ParagraphContext(paragraph=paragraph, section=current_section))
        for table in document.tables:
            contexts.extend(self._table_paragraph_contexts(table, current_section))
        return contexts

    def _table_paragraph_contexts(self, table, inherited_section: str = "intestazione") -> List[ParagraphContext]:
        contexts: List[ParagraphContext] = []
        current_section = inherited_section or "intestazione"
        for row in table.rows:
            row_section = current_section
            for cell in row.cells:
                cell_section = row_section
                for paragraph in cell.paragraphs:
                    text = (paragraph.text or "").strip()
                    if is_section_heading(text):
                        cell_section = canonical_section(text)
                        row_section = cell_section
                        current_section = cell_section
                    contexts.append(ParagraphContext(paragraph=paragraph, section=cell_section))
                for nested_table in cell.tables:
                    nested_contexts = self._table_paragraph_contexts(nested_table, cell_section)
                    contexts.extend(nested_contexts)
                    if nested_contexts:
                        cell_section = nested_contexts[-1].section
                        row_section = cell_section
                        current_section = cell_section
        return contexts

    def _valid_instruction(self, instruction: RewriteInstruction) -> bool:
        if not instruction.replacement.strip():
            return False
        if not ResumeRewriter().is_safe_replacement(instruction.section, instruction.replacement):
            self._log_blocked(instruction, "replacement non valido per la sezione")
            return False
        return True

    def _replace_exact(self, contexts: List[ParagraphContext], instruction: RewriteInstruction) -> bool:
        original_norm = normalize_text(instruction.original)
        for context in contexts:
            paragraph = context.paragraph
            paragraph_text = paragraph.text or ""
            if not self._is_editable_paragraph(paragraph):
                continue
            if normalize_text(paragraph_text) == original_norm or instruction.original in paragraph_text:
                section = context.section
                if not self._section_matches_instruction(section, instruction):
                    self._log_blocked(instruction, f"testo originale trovato fuori sezione: {section or 'sconosciuta'}")
                    continue
                self._replace_and_cleanup(contexts, context, instruction)
                return True
        return False

    def _replace_similar(self, contexts: List[ParagraphContext], instruction: RewriteInstruction) -> bool:
        original_tokens = set(tokenize(instruction.original))
        if len(original_tokens) < 4:
            return False
        best = None
        best_score = 0
        for context in contexts:
            paragraph = context.paragraph
            if not self._is_editable_paragraph(paragraph):
                continue
            current_section = context.section
            if not self._section_matches_instruction(current_section, instruction):
                continue
            paragraph_tokens = set(tokenize(paragraph.text or ""))
            if not paragraph_tokens:
                continue
            score = len(original_tokens.intersection(paragraph_tokens)) / max(len(original_tokens), 1)
            if score > best_score:
                best = context
                best_score = score
        if best is not None and best_score >= 0.74:
            self._replace_and_cleanup(contexts, best, instruction)
            return True
        return False

    def _replace_in_section(self, contexts: List[ParagraphContext], instruction: RewriteInstruction) -> bool:
        section_names = self._section_candidates(instruction)
        if not section_names:
            return False

        start_index = None
        for index, context in enumerate(contexts):
            text = normalize_text(context.paragraph.text or "").strip(":")
            if self._is_heading_for_candidates(text, section_names):
                start_index = index
                break
        if start_index is None:
            self._log_blocked(instruction, "sezione non trovata in modo sicuro")
            return False

        for context in contexts[start_index + 1:start_index + 10]:
            paragraph = context.paragraph
            text = (paragraph.text or "").strip()
            if not text:
                continue
            if is_section_heading(text):
                break
            if not self._section_matches_instruction(context.section, instruction):
                continue
            if not self._is_editable_paragraph(paragraph):
                continue
            self._replace_and_cleanup(contexts, context, instruction)
            return True
        self._log_blocked(instruction, "nessun paragrafo sostituibile trovato sotto la sezione")
        return False

    def _replace_section_block(
        self,
        contexts: List[ParagraphContext],
        instruction: RewriteInstruction,
    ) -> bool:
        expected = canonical_section(instruction.section or instruction.category or "")
        if not expected or expected == "contenuto":
            return False

        candidates = [
            context
            for context in contexts
            if context.section == expected and self._is_editable_paragraph(context.paragraph)
        ]
        if not candidates:
            return False

        original_tokens = set(tokenize(instruction.original))
        if not original_tokens:
            return False

        best_contexts: List[ParagraphContext] = []
        best_score = 0.0
        for start in range(len(candidates)):
            block: List[ParagraphContext] = []
            block_tokens = set()
            for candidate in candidates[start:start + 8]:
                block.append(candidate)
                block_tokens.update(tokenize(candidate.paragraph.text or ""))
                score = len(original_tokens.intersection(block_tokens)) / max(len(original_tokens), 1)
                if score > best_score:
                    best_score = score
                    best_contexts = list(block)
                if score >= 0.9:
                    break

        if not best_contexts or best_score < 0.55:
            return False

        self._replace_paragraph_block(best_contexts, instruction.replacement)
        return True

    def _replace_paragraph_block(
        self,
        contexts: List[ParagraphContext],
        replacement: str,
    ) -> None:
        lines = [line.strip() for line in (replacement or "").splitlines() if line.strip()]
        if not lines:
            lines = [replacement.strip()]

        for index, context in enumerate(contexts):
            value = lines[index] if index < len(lines) else ""
            self._replace_preserving_first_run(context.paragraph, value)

        if len(lines) <= len(contexts):
            return

        anchor = contexts[-1].paragraph
        format_reference = contexts[-1].paragraph
        for value in lines[len(contexts):]:
            parent = anchor._parent
            new_paragraph = parent.add_paragraph(value)
            new_paragraph._p.getparent().remove(new_paragraph._p)
            anchor._p.addnext(new_paragraph._p)
            self._copy_paragraph_format(format_reference, new_paragraph)
            anchor = new_paragraph

    def _append_to_target_section(self, document, instruction: RewriteInstruction) -> bool:
        if not instruction.replacement.strip():
            return False
        self._append_section(document, RewriteInstruction(
            section=instruction.section,
            original="",
            replacement=instruction.replacement,
            reason=instruction.reason,
            category=instruction.category,
            source_id=instruction.source_id,
        ))
        return True

    def _should_append(self, instruction: RewriteInstruction) -> bool:
        if instruction.original.strip():
            return False
            
        section_name = canonical_section(instruction.section)
        category = normalize_text(instruction.category)
        
        return (
            section_name in {
                "progetti", "esperienze", "formazione", 
                "certificazioni", "competenze", "lingue"
            }
            or category in {
                "project", "extra_page", "skills", "soft_skills",
                "experience", "education", "certification", "hard_skill", "soft_skill"
            }
        )

    def _append_section(self, document, instruction: RewriteInstruction) -> None:
        heading = (instruction.section or "PROGETTI").strip().upper()
        if heading == "PAGINA AGGIUNTIVA":
            heading = "PROGETTI"
        section_name = canonical_section(heading)
        contexts = self._paragraph_contexts(document)
        matching_heading_index = next(
            (
                index
                for index, context in enumerate(contexts)
                if is_section_heading(context.paragraph.text or "")
                and canonical_section(context.paragraph.text or "") == section_name
            ),
            None,
        )

        if matching_heading_index is not None:
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
            body_paragraph._p.getparent().remove(body_paragraph._p)
            anchor._p.addnext(body_paragraph._p)
            if body_reference is not None:
                self._copy_paragraph_format(body_reference, body_paragraph)
            return

        heading_reference = self._last_heading_paragraph(document)
        body_reference = self._last_styled_paragraph(document)
        document.add_page_break()
        heading_paragraph = document.add_paragraph(heading)
        body_paragraph = document.add_paragraph(instruction.replacement)
        if heading_reference is not None:
            self._copy_paragraph_format(heading_reference, heading_paragraph)
        if body_reference is not None:
            self._copy_paragraph_format(body_reference, body_paragraph)

    def _replace_and_cleanup(
        self,
        contexts: List[ParagraphContext],
        context: ParagraphContext,
        instruction: RewriteInstruction,
    ) -> None:
        self._replace_preserving_first_run(context.paragraph, instruction.replacement)
        if canonical_section(instruction.section) != "profilo":
            return

        replacement_norm = normalize_text(instruction.replacement)
        try:
            start_index = next(
                index for index, candidate in enumerate(contexts)
                if candidate.paragraph is context.paragraph
            )
        except StopIteration:
            return

        replacement_tokens = set(tokenize(instruction.replacement))
        for candidate in contexts[start_index + 1:]:
            if candidate.section != context.section:
                break
            paragraph = candidate.paragraph
            text = (paragraph.text or "").strip()
            if not text:
                continue
            if is_section_heading(text):
                break
            text_norm = normalize_text(text)
            text_tokens = set(tokenize(text))
            overlap = (
                len(text_tokens.intersection(replacement_tokens)) / max(len(text_tokens), 1)
                if text_tokens
                else 0
            )
            if text_norm in replacement_norm or overlap >= 0.85:
                self._replace_preserving_first_run(paragraph, "")
                continue
            break

    def _last_heading_paragraph(self, document):
        for context in reversed(self._paragraph_contexts(document)):
            if is_section_heading(context.paragraph.text or ""):
                return context.paragraph
        return None

    def _last_styled_paragraph(self, document):
        for context in reversed(self._paragraph_contexts(document)):
            paragraph = context.paragraph
            text = (paragraph.text or "").strip()
            if text and not is_section_heading(text):
                return paragraph
        return None

    def _copy_paragraph_format(self, source, target) -> None:
        try:
            target.style = source.style
        except Exception:
            pass
        if source._p.pPr is not None:
            if target._p.pPr is not None:
                target._p.remove(target._p.pPr)
            target._p.insert(0, deepcopy(source._p.pPr))

        source_run = next((run for run in source.runs if (run.text or "").strip()), None)
        target_run = target.runs[0] if target.runs else target.add_run()
        if source_run is not None and source_run._r.rPr is not None:
            if target_run._r.rPr is not None:
                target_run._r.remove(target_run._r.rPr)
            target_run._r.insert(0, deepcopy(source_run._r.rPr))

    def _section_candidates(self, instruction: RewriteInstruction) -> List[str]:
        raw_values = [instruction.section, instruction.category]
        candidates = set()
        for value in raw_values:
            clean = canonical_section(value or "")
            if clean and clean != "contenuto":
                candidates.add(clean)
                candidates.update(SECTION_ALIASES.get(clean, set()))
        if instruction.category == "profile":
            candidates.update(SECTION_ALIASES["profilo"])
        elif instruction.category == "experience":
            candidates.update(SECTION_ALIASES["esperienze"])
        elif instruction.category == "skills":
            candidates.update(SECTION_ALIASES["competenze"])
        elif instruction.category == "education":
            candidates.update(SECTION_ALIASES["formazione"])
        return [normalize_text(candidate) for candidate in candidates if candidate]

    def _is_editable_paragraph(self, paragraph) -> bool:
        text = (paragraph.text or "").strip()
        return bool(text) and not is_section_heading(text)

    def _is_heading_for_candidates(self, normalized_text: str, section_names: List[str]) -> bool:
        clean = normalize_text(normalized_text).strip(":")
        return clean in section_names

    def _section_matches_instruction(self, current_section: str, instruction: RewriteInstruction) -> bool:
        expected = canonical_section(instruction.section or instruction.category or "")
        if not expected or expected == "contenuto":
            return True
        if current_section == expected:
            return True
        if instruction.category == "profile" and current_section == "profilo":
            return True
        if instruction.category == "experience" and current_section == "esperienze":
            return True
        if instruction.category == "skills" and current_section == "competenze":
            return True
        if instruction.category == "education" and current_section == "formazione":
            return True
        return False

    def _log_blocked(self, instruction: RewriteInstruction, reason: str) -> None:
        print(
            "Inserimento CV bloccato: "
            f"id={instruction.source_id or 'unknown'}, "
            f"section={instruction.section}, category={instruction.category}, "
            f"reason={reason}, proposed_text={instruction.replacement[:220]}"
        )

    def _replace_preserving_first_run(self, paragraph, replacement: str) -> None:
        runs = list(paragraph.runs)
        if not runs:
            paragraph.add_run(replacement)
            return
        runs[0].text = replacement
        for run in runs[1:]:
            run.text = ""


class ExportService:
    DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def docx_to_pdf(self, docx_bytes: bytes) -> Optional[bytes]:
        executable = shutil.which("soffice") or shutil.which("libreoffice")
        if not executable:
            return None
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docx_path = tmp_path / "cv-ottimizzato.docx"
            docx_path.write_bytes(docx_bytes)
            subprocess.run(
                [executable, "--headless", "--convert-to", "pdf", "--outdir", str(tmp_path), str(docx_path)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            pdf_path = tmp_path / "cv-ottimizzato.pdf"
            return pdf_path.read_bytes() if pdf_path.exists() else None

    def plain_pdf(self, text: str) -> tuple[bytes, str, str]:
        try:
            import fitz

            doc = fitz.open()
            page = doc.new_page()
            y = 46
            for paragraph in (text or "").splitlines():
                for line in textwrap.wrap(paragraph.strip(), width=92) or [""]:
                    if y > 790:
                        page = doc.new_page()
                        y = 46
                    page.insert_text((48, y), line, fontsize=10.2, fontname="helv", color=(0.16, 0.20, 0.25))
                    y += 13.5
                y += 5
            pdf_bytes = doc.write()
            doc.close()
            return pdf_bytes, "application/pdf", "pdf"
        except Exception:
            return text.encode("utf-8"), "text/plain; charset=utf-8", "txt"
