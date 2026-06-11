
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
import json
from typing import Any, Dict, Iterable, List, Optional


SECTION_ALIASES: Dict[str, set[str]] = {
    "header": {"header", "intestazione"},
    "contacts": {"contatti", "contact", "contacts"},
    "profile": {"profilo", "profilo professionale", "chi sono", "obiettivo", "summary", "about me", "personal profile"},
    "experience": {"esperienza", "esperienze", "esperienza professionale", "esperienze professionali", "work experience", "professional experience"},
    "education": {"formazione", "istruzione", "education"},
    "hard_skills": {"hard skills", "competenze", "competenze tecniche", "technical skills", "skills"},
    "soft_skills": {"soft skills", "competenze trasversali"},
    "languages": {"lingue", "languages", "comunicazione"},
    "projects": {"progetti", "projects", "portfolio", "pagina aggiuntiva", "attivita rilevanti"},
    "certifications": {"certificazioni", "certificati", "certifications", "attestati"},
}
CANONICAL_TO_HEADING = {
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
ALL_HEADINGS = {alias for aliases in SECTION_ALIASES.values() for alias in aliases}
SECTION_ORDER = ["header", "profile", "experience", "projects", "hard_skills", "soft_skills", "education", "languages", "certifications", "contacts"]

CATEGORY_LABELS = {
    "profile": "Profilo professionale",
    "experience": "Esperienze",
    "project": "Progetti",
    "skills": "Competenze tecniche",
    "soft_skills": "Soft skills",
    "education": "Formazione",
    "ats_keywords": "Keyword ATS",
    "missing_info": "Informazioni da confermare",
}

ROLE_LIBRARY: Dict[str, Dict[str, List[str]]] = {
    "game design": {
        "role_terms": ["game design", "game designer", "level design", "game mechanics", "playtesting", "storytelling", "user experience", "prototipazione"],
        "hard_skills": ["Game design", "Level design", "Game mechanics", "Prototipazione", "User experience", "Playtesting", "Storytelling"],
        "tools": ["Unity", "Unreal Engine", "Blender", "Figma", "Miro"],
        "soft_skills": ["Creatività", "Collaborazione", "Problem solving", "Comunicazione", "Iterazione su feedback"],
    },
    "project manager": {
        "role_terms": ["project management", "project manager", "pianificazione", "gestione scadenze", "coordinamento", "monitoraggio", "stakeholder"],
        "hard_skills": ["Pianificazione attività", "Gestione scadenze", "Coordinamento team", "Monitoraggio avanzamento", "Risk management"],
        "tools": ["Jira", "Trello", "Asana", "Microsoft Project", "Miro", "Excel"],
        "soft_skills": ["Comunicazione", "Organizzazione", "Problem solving", "Leadership", "Gestione priorità"],
    },
    "data analyst": {
        "role_terms": ["data analyst", "analisi dati", "reporting", "dashboard", "kpi", "business intelligence"],
        "hard_skills": ["SQL", "Python", "Analisi dati", "Reporting", "Data visualization", "KPI", "Business intelligence"],
        "tools": ["Excel", "Power BI", "Tableau", "Looker", "Google Analytics"],
        "soft_skills": ["Pensiero analitico", "Attenzione ai dettagli", "Comunicazione", "Problem solving"],
    },
    "data scientist": {
        "role_terms": ["data scientist", "machine learning", "modelli predittivi", "statistica", "feature engineering", "python"],
        "hard_skills": ["Python", "Machine Learning", "SQL", "Modelli statistici", "Data preprocessing", "Feature engineering"],
        "tools": ["pandas", "scikit-learn", "Jupyter", "TensorFlow", "Tableau"],
        "soft_skills": ["Pensiero analitico", "Problem solving", "Comunicazione scientifica", "Collaborazione"],
    },
    "backend developer": {
        "role_terms": ["backend", "api", "database", "server", "fastapi", "django", "spring"],
        "hard_skills": ["API development", "Database design", "Autenticazione", "Testing backend", "Architetture REST"],
        "tools": ["FastAPI", "Django", "Spring", "PostgreSQL", "MongoDB", "Docker"],
        "soft_skills": ["Problem solving", "Precisione", "Collaborazione", "Documentazione tecnica"],
    },
    "software engineer": {
        "role_terms": ["software engineer", "software developer", "sviluppo software", "testing", "debugging", "git"],
        "hard_skills": ["Sviluppo software", "Debugging", "Version control", "Unit testing", "Code review"],
        "tools": ["Git", "GitHub", "Docker", "VS Code", "Cloud"],
        "soft_skills": ["Problem solving", "Collaborazione", "Comunicazione tecnica", "Precisione"],
    },
}

GENERIC_NOISE = {
    "voglio", "prepararmi", "colloquio", "per", "un", "una", "di", "da", "con", "il", "lo", "la",
    "role", "ruolo", "azienda", "candidatura", "lavoro", "stage", "junior", "senior", "presso",
    "scientist", "analyst", "engineer", "developer", "designer", "manager", "specialist",
    "voglio prepararmi", "prepararmi per", "per un", "un colloquio", "colloquio di",
}
CONTACT_HINTS = ["@", "linkedin", "github", "http://", "https://", "telefono", "phone", "mobile", "via "]
COMMON_SKILLS = [
    "Python", "SQL", "Java", "C++", "C#", "Linux", "Networking", "Big Data", "ML & AI", "Machine Learning",
    "Artificial Intelligence", "Data Engineering", "Data Analysis", "RAG", "Retrieval-Augmented Generation",
    "NLP", "LLM", "Cloud Computing", "Docker", "Git", "GitHub", "PostgreSQL", "MongoDB", "FastAPI",
    "Unity", "Unreal Engine", "Blender", "Figma", "Miro", "Power BI", "Tableau", "Excel", "Jira", "Trello", "Asana"
]

OLLAMA_COPYWRITING_TIMEOUT = 20


@dataclass
class ParsedCV:
    sections: Dict[str, str] = field(default_factory=dict)
    order: List[str] = field(default_factory=list)


def strip_accents(value: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", value or "") if not unicodedata.combining(ch))


def normalize(value: Any) -> str:
    text = strip_accents(str(value or "")).lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9+#&./\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_noise_keyword(value: Any) -> bool:
    cleaned = normalize(value)
    if not cleaned or cleaned in GENERIC_NOISE:
        return True
    if any(term in cleaned for term in ["voglio", "prepararmi", "colloquio"]):
        return True
    words = cleaned.split()
    if len(words) > 4 and not any(anchor in cleaned for anchor in ["machine learning", "project management", "user experience", "game design", "data engineering", "artificial intelligence"]):
        return True
    if len(words) == 1 and words[0] in GENERIC_NOISE:
        return True
    return False


def canonical_heading(line: str) -> Optional[str]:
    clean = normalize(line).strip(":")
    if not clean:
        return None
    for key, aliases in SECTION_ALIASES.items():
        if clean in aliases:
            return key
    stripped = (line or "").strip().strip(":")
    if len(stripped) <= 42 and stripped.upper() == stripped and any(ch.isalpha() for ch in stripped):
        for key, aliases in SECTION_ALIASES.items():
            if clean in aliases:
                return key
    return None


def looks_like_contact(line: str) -> bool:
    plain = normalize(line)
    return (
        any(hint in plain for hint in CONTACT_HINTS)
        or bool(re.search(r"[\w.+-]+@[\w.-]+\.\w+", line or ""))
        or bool(re.search(r"\+?\d[\d\s().-]{7,}", line or ""))
    )


def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line or "").strip(" \t-•·")


def dedupe_repeated_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""
    tokens = text.split()
    for n in (34, 28, 22, 18, 14, 10, 8):
        if len(tokens) <= n * 2:
            continue
        prefix = " ".join(tokens[:n])
        second = text.find(prefix, len(prefix) + 12)
        if second > 80:
            return text[:second].strip(" .;:") + "."
    chunks = re.split(r"(?<=[.!?])\s+", text)
    result: List[str] = []
    seen = set()
    for chunk in chunks:
        key = normalize(chunk)[:160]
        if key and key not in seen:
            seen.add(key)
            result.append(chunk)
    return " ".join(result).strip()


def shorten(text: str, max_chars: int = 850) -> str:
    text = dedupe_repeated_text(text)
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    end = max(cut.rfind("."), cut.rfind(";"), cut.rfind("!"), cut.rfind("?"))
    if end > 220:
        return cut[:end + 1].strip()
    return cut.rsplit(" ", 1)[0].strip()


def unique(values: Any) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values or []:
        item = clean_line(str(value or ""))
        key = normalize(item)
        if item and key and key not in seen and not is_noise_keyword(item):
            seen.add(key)
            result.append(item)
    return result


def prepare_lines(cv_text: str) -> List[str]:
    prepared = re.sub(r"\r\n?", "\n", cv_text or "")
    for aliases in SECTION_ALIASES.values():
        for heading in sorted(aliases, key=len, reverse=True):
            prepared = re.sub(
                rf"(?<![\wÀ-ÖØ-öø-ÿ])({re.escape(heading)})\s*:?(?=\s|$)",
                lambda m: "\n" + m.group(1).strip().upper() + "\n",
                prepared,
                flags=re.IGNORECASE,
            )
    return [clean_line(line) for line in prepared.splitlines() if clean_line(line)]


def parse_cv(cv_text: str) -> ParsedCV:
    sections: Dict[str, List[str]] = {"header": []}
    order: List[str] = ["header"]
    current = "header"
    for line in prepare_lines(cv_text):
        heading = canonical_heading(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            if current not in order:
                order.append(current)
            continue
        sections.setdefault(current, []).append(line)

    # Nei DOCX a colonne il titolo FORMAZIONE può andare perso durante
    # l'estrazione. Recuperiamo solo righe con segnali accademici forti.
    profile_lines = sections.get("profile", [])
    education_start = None
    for index, line in enumerate(profile_lines):
        plain = normalize(line)
        starts_academic = plain.startswith((
            "universita ", "università ", "university ", "liceo ", "istituto ",
        ))
        has_degree = any(term in plain for term in (
            "laurea triennale", "laurea magistrale", "master ", "diploma ",
        ))
        has_date_context = bool(re.search(r"\b(?:19|20)\d{2}\b", line))
        if starts_academic or (has_degree and has_date_context):
            education_start = index
            break
    if education_start is not None:
        recovered_education = profile_lines[education_start:]
        sections["profile"] = profile_lines[:education_start]
        sections.setdefault("education", [])
        sections["education"] = [*recovered_education, *sections["education"]]
        if "education" not in order:
            profile_position = order.index("profile") if "profile" in order else 0
            order.insert(profile_position + 1, "education")

    cleaned_sections: Dict[str, str] = {}
    for key, lines in sections.items():
        filtered: List[str] = []
        for line in lines:
            plain = normalize(line)
            if not plain:
                continue
            if key not in {"contacts", "header"} and looks_like_contact(line):
                continue
            if key in {"hard_skills", "soft_skills"} and any(marker in plain for marker in ["obiettivo", "formazione", "esperienza", "progetti", "lingue", "comunicazione"]):
                continue
            filtered.append(line)
        text = "\n".join(unique(filtered)) if key in {"hard_skills", "soft_skills"} else "\n".join(filtered)
        text = shorten(text, 1100)
        if text:
            cleaned_sections[key] = text

    return ParsedCV(sections=cleaned_sections, order=[key for key in order if key in cleaned_sections])


def infer_role_family(role: str, description: str = "", required_skills: str = "") -> str:
    target = normalize(" ".join([role or "", description or "", required_skills or ""]))
    best_family = ""
    best_score = 0
    for family, payload in ROLE_LIBRARY.items():
        score = 0
        for term in payload.get("role_terms", []):
            normalized_term = normalize(term)
            if normalized_term and normalized_term in target:
                score += 3 if len(normalized_term.split()) > 1 else 1
        for skill in [*payload.get("hard_skills", []), *payload.get("tools", []), *payload.get("soft_skills", [])]:
            normalized_skill = normalize(skill)
            if normalized_skill and normalized_skill in target:
                score += 1
        if score > best_score:
            best_score = score
            best_family = family
    if best_family:
        return best_family
    if any(term in target for term in ["project", "pianificazione", "stakeholder", "scadenze"]):
        return "project manager"
    if any(term in target for term in ["game", "unity", "unreal", "prototip"]):
        return "game design"
    if any(term in target for term in ["data", "analytics", "kpi", "dashboard", "reporting", "business intelligence"]):
        return "data analyst"
    if any(term in target for term in ["machine learning", "ml", "ai", "modelli", "statistica", "prediction"]):
        return "data scientist"
    if any(term in target for term in ["backend", "api", "server", "database", "rest", "fastapi", "django", "spring"]):
        return "backend developer"
    if any(term in target for term in ["software", "developer", "svilupp", "engineering", "engineering"]):
        return "software engineer"
    return ""


def build_target_profile(role: str, company: str = "", description: str = "", required_skills: str = "") -> Dict[str, Any]:
    family = infer_role_family(role, description, required_skills)
    library = ROLE_LIBRARY.get(family, {"hard_skills": [], "soft_skills": [], "tools": [], "role_terms": []})
    requested = unique(re.split(r"[,;\n]+", required_skills or ""))
    return {
        "role": clean_line(role or ""),
        "company": clean_line(company or ""),
        "family": family,
        "hard_skills": unique([*library.get("hard_skills", []), *requested])[:10],
        "soft_skills": unique(library.get("soft_skills", []))[:8],
        "tools": unique(library.get("tools", []))[:8],
        "keywords": unique([*library.get("role_terms", []), *requested])[:14],
    }


def strip_section_titles(text: str) -> str:
    forbidden = {
        "profilo", "obiettivo", "esperienze", "esperienze professionali", "esperienza professionale",
        "formazione", "istruzione", "progetti", "hard skills", "soft skills", "competenze",
        "contatti", "lingue", "certificazioni",
    }
    lines: List[str] = []
    for raw_line in (text or "").splitlines():
        line = clean_line(raw_line)
        normalized = normalize(line).strip(":")
        if not line:
            continue
        if normalized in forbidden:
            continue
        if normalized.upper() == normalized and len(normalized) <= 42 and any(char.isalpha() for char in normalized):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def sanitize_rewrite_instruction(instruction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(instruction, dict):
        return None
    section = normalize(str(instruction.get("section") or instruction.get("target_section") or "")).strip()
    replacement = str(instruction.get("replacement") or instruction.get("proposed_text") or instruction.get("new_text") or "").strip()
    original = str(instruction.get("original") or instruction.get("original_text") or instruction.get("old_text_hint") or "").strip()
    if not section or not replacement:
        return None
    replacement = strip_section_titles(replacement)
    if not replacement:
        return None
    norm_replacement = normalize(replacement)
    blocked_pairs = {
        "profile": (
            "formazione", "percorso formativo", "universita", "università", "laurea",
            "diploma", "esperienze", "progetti", "hard skills", "soft skills",
            "competenze", "lingue", "certificazioni",
        ),
        "objective": ("formazione", "esperienze", "progetti", "hard skills", "soft skills", "competenze", "lingue", "certificazioni"),
        "obiettivo": ("formazione", "esperienze", "progetti", "hard skills", "soft skills", "competenze", "lingue", "certificazioni"),
        "education": ("esperienza", "progetti", "profilo", "obiettivo", "hard skills", "soft skills"),
        "experience": ("formazione", "progetti", "profilo", "obiettivo", "hard skills", "soft skills"),
        "skills": ("formazione", "esperienze", "progetti", "profilo", "obiettivo"),
        "hard_skills": ("formazione", "esperienze", "progetti", "profilo", "obiettivo"),
        "soft_skills": ("formazione", "esperienze", "progetti", "profilo", "obiettivo"),
    }
    for marker in blocked_pairs.get(section, ()):
        if marker in norm_replacement:
            return None
    cleaned = dict(instruction)
    cleaned["section"] = section
    cleaned["original"] = original
    cleaned["replacement"] = replacement
    cleaned["proposed_text"] = replacement
    cleaned["new_text"] = replacement
    return cleaned


def _load_json_output(raw: Any) -> Optional[Dict[str, Any]]:
    try:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            import json
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None
    return None


def _call_copywriting_llm(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Multi-model copywriting step:
    - first try Ollama for the local rewrite plan
    - fall back to Groq if the local model is unavailable or returns invalid JSON
    """
    try:
        from main import call_ollama
        raw = call_ollama(prompt, temperature=0.1, max_tokens=1100, timeout=OLLAMA_COPYWRITING_TIMEOUT, json_mode=True)
        parsed = _load_json_output(raw)
        if parsed is not None:
            return parsed
    except Exception:
        pass

    try:
        from main import call_groq
        raw = call_groq(prompt, temperature=0.1, max_tokens=1100, timeout=OLLAMA_COPYWRITING_TIMEOUT, json_mode=True)
        return _load_json_output(raw)
    except Exception:
        return None


def _rewrite_llm_enabled() -> bool:
    try:
        from main import CV_REWRITE_LLM_ENABLED as enabled
        return bool(enabled)
    except Exception:
        return False


def _build_copywriting_instruction_json(
    section_key: str,
    old_text: str,
    new_text: str,
    used_existing_evidence: List[str],
    forbidden_added_claims: List[str],
) -> Dict[str, Any]:
    return {
        "target_section": section_key,
        "action": "replace",
        "old_text_hint": old_text,
        "new_text": new_text,
        "used_existing_evidence": used_existing_evidence,
        "forbidden_added_claims": forbidden_added_claims,
    }


def strip_section_titles(text: str) -> str:
    forbidden = {
        "profilo", "obiettivo", "esperienze", "esperienze professionali", "esperienza professionale",
        "formazione", "istruzione", "progetti", "hard skills", "soft skills", "competenze",
        "contatti", "lingue", "certificazioni",
    }
    cleaned_lines: List[str] = []
    for raw_line in (text or "").splitlines():
        line = clean_line(raw_line)
        normalized = normalize(line).strip(":")
        if not line:
            continue
        if normalized in forbidden:
            continue
        if normalized.upper() == normalized and len(normalized) <= 42 and any(char.isalpha() for char in normalized):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def extract_skill_terms(text: str) -> List[str]:
    haystack = " " + normalize(text) + " "
    found = []
    for skill in COMMON_SKILLS:
        if normalize(skill) in haystack:
            found.append(skill)
    for part in re.split(r"[,;|•·\n]+", text or ""):
        part = re.sub(r"[●○■□▪▫]+", " ", part)
        part = clean_line(part)
        if not part or looks_like_contact(part):
            continue
        if 1 <= len(part.split()) <= 4:
            found.append(part)
    return unique(found)[:20]


def group_skills(skills: List[str]) -> str:
    buckets = {
        "Linguaggi e database": [],
        "Data, AI e analisi": [],
        "Sistemi, reti e sviluppo": [],
        "Strumenti e metodi": [],
    }
    for skill in skills:
        plain = normalize(skill)
        if plain in {"python", "sql", "java", "c++", "c#"}:
            buckets["Linguaggi e database"].append(skill)
        elif any(term in plain for term in ["data", "big data", "machine", "ml", "ai", "rag", "nlp", "llm", "cloud"]):
            buckets["Data, AI e analisi"].append(skill)
        elif any(term in plain for term in ["linux", "network", "git", "docker", "api", "database", "postgres", "mongo"]):
            buckets["Sistemi, reti e sviluppo"].append(skill)
        else:
            buckets["Strumenti e metodi"].append(skill)
    rows = []
    for label, values in buckets.items():
        values = unique(values)
        if values:
            rows.append(f"{label}: {', '.join(values)}")
    return "\n".join(rows)


def suggestion_id(section: str, title: str, original: str) -> str:
    raw = normalize(f"{section}-{title}-{original[:80]}")
    return re.sub(r"[^a-z0-9]+", "-", raw).strip("-")[:96] or "cv-suggestion"


def make_suggestion(category: str, section: str, title: str, original: str, proposed: str, reason: str, impact: str, priority: int, keywords: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    original = shorten(original, 950)
    proposed = re.sub(r"\n{3,}", "\n\n", (proposed or "").strip())
    if not original or not proposed:
        return None
    if normalize(original) == normalize(proposed):
        return None
    if SequenceMatcher(None, normalize(original), normalize(proposed)).ratio() >= 0.96:
        return None
    label = CATEGORY_LABELS.get(category, "Suggerimento")
    return {
        "id": suggestion_id(section, title, original),
        "type": "actionableEdit",
        "category": category,
        "category_label": label,
        "title": title,
        "message": reason,
        "description": reason,
        "reason": reason,
        "action": "",
        "section": section,
        "original_text": original,
        "proposed_text": proposed,
        "impact": impact,
        "priority": priority,
        "requires_confirmation": False,
        "supported_by_cv": True,
        "keywords_added": [kw for kw in unique(keywords or []) if not is_noise_keyword(kw)][:8],
    }


def profile_rewrite(original: str, parsed: ParsedCV, target: Dict[str, Any]) -> str:
    role = (target.get("role") or "ruolo target").strip() or "ruolo target"
    company = (target.get("company") or "").strip()
    family = target.get("family") or infer_role_family(role)
    cv_all = "\n".join(parsed.sections.values())

    present_skills = []
    for skill in [*COMMON_SKILLS, *target.get("hard_skills", []), *target.get("soft_skills", []), *target.get("tools", [])]:
        normalized_skill = normalize(skill)
        if normalized_skill and normalized_skill in normalize(cv_all):
            present_skills.append(skill)
    present_skills = unique(present_skills)[:6]

    role_descriptor = role if family else "profilo professionale"
    company_part = f" per {company}" if company else ""
    skills_part = f" Competenze emerse: {', '.join(present_skills)}." if present_skills else ""

    if family in {"data analyst", "data scientist", "backend developer", "software engineer", "frontend developer", "project manager", "game design"}:
        context_map = {
            "data analyst": "analisi dati e miglioramento dei processi",
            "data scientist": "analisi quantitativa, sperimentazione e modelli",
            "backend developer": "sviluppo software e integrazione applicativa",
            "software engineer": "sviluppo software e progettazione tecnica",
            "frontend developer": "interfacce digitali e esperienza utente",
            "project manager": "coordinamento, pianificazione e obiettivi",
            "game design": "creazione di esperienze interattive e progettazione di prodotto",
        }
        context_type = context_map.get(family, "contesti tecnici e organizzati")
        profile_text = (
            f"{role_descriptor.capitalize()} con formazione coerente e obiettivo di contribuire in contesti {context_type}{company_part}."
            f"{skills_part}"
            f" Profilo orientato a risultati, collaborazione e crescita professionale."
        )
    else:
        profile_text = (
            f"{role_descriptor.capitalize()} con formazione coerente e obiettivo di contribuire in contesti dinamici e strutturati{company_part}."
            f"{skills_part}"
            f" Profilo orientato a competenze tecniche, affidabilità, apprendimento continuo e collaborazione."
        )

    return strip_section_titles(profile_text)


def experience_rewrite(original: str, target: Dict[str, Any]) -> str:
    role = (target.get("role") or "ruolo target").strip() or "ruolo target"
    family = target.get("family") or infer_role_family(role)
    raw_lines = [re.sub(r"\s+", " ", line).strip(" -•·") for line in re.sub(r"\r\n?", "\n", original or "").splitlines() if line.strip()]
    header_lines: List[str] = []
    body_lines: List[str] = []
    for index, line in enumerate(raw_lines):
        if index < 2 and len(normalize(line).split()) <= 18:
            header_lines.append(line)
            continue
        body_lines.append(line)
    text = shorten(" ".join(body_lines) if body_lines else " ".join(raw_lines), 900)
    sentences = [s.strip().rstrip(".") for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        sentences = [text.rstrip(".")]
    bullets: List[str] = []
    for sentence in sentences[:6]:
        norm = normalize(sentence)
        if len(norm) < 20:
            continue
        bullets.append(f"- {sentence}.")
    if not bullets:
        return ""

    if family in {"data analyst", "data scientist"}:
        intro = f"Esperienza orientata ad analisi dati, automazione e valutazione dei risultati per il ruolo di {role}:\n"
    elif family in {"backend developer", "software engineer", "frontend developer"}:
        intro = f"Esperienza orientata a sviluppo software, qualità del codice e collaborazione tecnica per il ruolo di {role}:\n"
    elif family == "project manager":
        intro = f"Esperienza orientata a pianificazione, coordinamento e rispetto delle scadenze per il ruolo di {role}:\n"
    else:
        intro = f"Esperienza professionale orientata al ruolo di {role}:\n"

    return intro + ("\n".join(header_lines) + "\n" if header_lines else "") + "\n".join(bullets)


def projects_rewrite(original: str, target: Dict[str, Any]) -> str:
    role = target.get("role") or "ruolo target"
    target_terms = unique([
        *target.get("hard_skills", []),
        *target.get("tools", []),
        *target.get("keywords", []),
    ])
    normalized_terms = [normalize(term) for term in target_terms if normalize(term)]
    parts = []
    for part in re.split(r"\n|·|•", original or ""):
        part = clean_line(part).strip(".")
        if part:
            normalized = normalize(part)
            if not normalized_terms or any(token in normalized for token in normalized_terms):
                parts.append(f"- {part}.")
    parts = unique(parts)[:7]
    if not parts:
        return ""
    return f"Progetti rilevanti per il ruolo di {role}:\n" + "\n".join(parts)


def education_rewrite(original: str, parsed: ParsedCV, target: Dict[str, Any]) -> str:
    # La formazione deve restare fattuale: niente frasi sintetiche costruite
    # usando segnali presi da altre sezioni del CV.
    return strip_section_titles(shorten(original, 780))


def build_structured_cv_suggestions(evaluation: Dict[str, Any]) -> List[Dict[str, Any]]:
    cv_text = str(evaluation.get("cv_text") or "")
    target_raw = evaluation.get("target") if isinstance(evaluation.get("target"), dict) else {}
    role = str(target_raw.get("role") or evaluation.get("role") or "")
    company = str(target_raw.get("company") or evaluation.get("company") or "")
    description = str(target_raw.get("description") or evaluation.get("description") or "")
    required = str(evaluation.get("required_skills") or "")
    target = build_target_profile(role, company, description, required)
    role_family = target.get("family") or infer_role_family(role, description, required)
    parsed = parse_cv(cv_text)
    sections = parsed.sections
    suggestions: List[Dict[str, Any]] = []

    if sections.get("profile") and role_family not in {"data analyst", "data scientist", "project manager", "software engineer", "backend developer", "frontend developer"}:
        item = make_suggestion("profile", "PROFILO", "Riscrivi il profilo in funzione del ruolo", sections["profile"], profile_rewrite(sections["profile"], parsed, target), "Rende il profilo più mirato al ruolo usando solo informazioni già presenti nel CV.", "alto", 1, [role])
        if item:
            suggestions.append(item)

    skills_text = sections.get("hard_skills", "")
    skills = extract_skill_terms(skills_text or "\n".join(sections.values()))
    grouped = group_skills(skills)
    if skills_text and grouped:
        grouped_lines = [line.strip() for line in grouped.splitlines() if line.strip()]
        if role_family in {"data analyst", "data scientist", "project manager", "software engineer", "backend developer", "frontend developer"}:
            preferred_map = {
                "data analyst": ["SQL", "Python", "Excel", "Power BI", "Tableau", "KPI", "Reporting", "Data visualization", "Business intelligence"],
                "data scientist": ["Python", "Machine Learning", "SQL", "Feature engineering", "Data preprocessing", "Statistica", "Modelli predittivi"],
                "project manager": ["Pianificazione attività", "Gestione scadenze", "Coordinamento team", "Risk management", "Budget management", "Stakeholder", "Jira", "Trello"],
                "software engineer": ["Sviluppo software", "Version control", "Unit testing", "Code review", "API", "Git", "Docker"],
                "backend developer": ["API", "Database design", "Testing backend", "Architetture REST", "Autenticazione", "Git", "PostgreSQL"],
                "frontend developer": ["HTML/CSS", "JavaScript", "User Interface Design", "User Experience", "Responsive Design", "Accessibilita", "Figma"],
            }
            preferred = preferred_map.get(role_family, [])
            if preferred:
                ordered = []
                lower_grouped = [line.lower() for line in grouped_lines]
                for skill in preferred:
                    for idx, line in enumerate(grouped_lines):
                        if skill.lower() in lower_grouped[idx] and line not in ordered:
                            ordered.append(line)
                grouped_lines = ordered + [line for line in grouped_lines if line not in ordered]
        item = make_suggestion("skills", "HARD SKILLS", "Riorganizza le competenze tecniche già presenti", skills_text, grouped, "Rende le competenze più leggibili per recruiter e ATS senza aggiungere skill non confermate.", "alto", 2, skills)
        if item:
            if grouped_lines:
                item["proposed_text"] = "Competenze tecniche:\n" + "\n".join(f"- {line}" for line in grouped_lines[:10])
            suggestions.append(item)

    missing_keywords = unique([
        *evaluation.get("missing_keywords", []),
        *evaluation.get("missing_hard_skills", []),
        *evaluation.get("missing_soft_skills", []),
    ])
    if missing_keywords and skills_text:
        keyword_lines = unique([kw for kw in missing_keywords if kw.strip()])[:8]
        if keyword_lines:
            item = make_suggestion(
                "ats_keywords",
                "Keyword ATS",
                "Evidenzia le parole chiave più pertinenti al ruolo",
                skills_text,
                "Keyword da valorizzare:\n" + "\n".join(f"- {kw}" for kw in keyword_lines),
                f"Allinea il CV alle keyword richieste per {role or 'il ruolo target'} senza aggiungere competenze non presenti.",
                "medio",
                2,
                keyword_lines,
            )
            if item:
                suggestions.append(item)

    if sections.get("experience"):
        exp_reason = {
            "data analyst": "Trasforma l’esperienza in bullet orientati a dati, analisi e risultati, mantenendo i fatti presenti.",
            "data scientist": "Trasforma l’esperienza in bullet orientati a dati, modelli e sperimentazione, mantenendo i fatti presenti.",
            "project manager": "Trasforma l’esperienza in bullet orientati a pianificazione, coordinamento e scadenze, mantenendo i fatti presenti.",
            "software engineer": "Trasforma l’esperienza in bullet orientati a qualità del codice, sviluppo e collaborazione tecnica, mantenendo i fatti presenti.",
            "backend developer": "Trasforma l’esperienza in bullet orientati a API, database e affidabilità tecnica, mantenendo i fatti presenti.",
            "frontend developer": "Trasforma l’esperienza in bullet orientati a interfacce, UX e dettaglio visivo, mantenendo i fatti presenti.",
        }.get(role_family, "Trasforma l’esperienza in bullet leggibili e orientati al ruolo, mantenendo i fatti presenti.")
        item = make_suggestion("experience", "ESPERIENZE PROFESSIONALI", "Valorizza l’esperienza più rilevante", sections["experience"], experience_rewrite(sections["experience"], target), exp_reason, "alto", 3, [])
        if item:
            suggestions.append(item)

    if sections.get("projects"):
        item = make_suggestion("project", "PROGETTI", "Valorizza i progetti più coerenti", sections["projects"], projects_rewrite(sections["projects"], target), "Rende i progetti più chiari e collegati alla candidatura senza inventare dettagli.", "medio", 4, [])
        if item:
            suggestions.append(item)

    if sections.get("soft_skills"):
        soft = unique(re.split(r"[,;|•·\n]+", sections["soft_skills"]))
        if len(soft) >= 2:
            soft_priority = {
                "data analyst": ["Pensiero analitico", "Attenzione ai dettagli", "Comunicazione dei risultati", "Problem solving", "Collaborazione"],
                "data scientist": ["Pensiero analitico", "Problem solving", "Comunicazione scientifica", "Collaborazione", "Attenzione ai dettagli"],
                "project manager": ["Organizzazione", "Gestione priorità", "Comunicazione", "Leadership", "Negoziazione"],
                "software engineer": ["Problem solving", "Collaborazione", "Comunicazione tecnica", "Precisione", "Pensiero logico"],
                "backend developer": ["Problem solving", "Precisione", "Collaborazione", "Documentazione tecnica", "Comunicazione tecnica"],
                "frontend developer": ["Creatività", "Attenzione ai dettagli", "Collaborazione", "Comunicazione", "Problem solving"],
            }.get(role_family, [])
            ordered_soft = unique([*soft_priority, *soft])
            item = make_suggestion("soft_skills", "SOFT SKILLS", "Rendi più chiara la sezione soft skills", sections["soft_skills"], "Soft skills:\n" + "\n".join(f"- {skill}" for skill in ordered_soft[:8]), "Mantiene le soft skill reali e le presenta in modo più pulito e più coerente con il ruolo.", "medio", 5, soft)
            if item:
                suggestions.append(item)

    if sections.get("education") and len(suggestions) < 5:
        item = make_suggestion("education", "FORMAZIONE", "Rendi la formazione più mirata", sections["education"], education_rewrite(sections["education"], parsed, target), "Collega la formazione al target solo attraverso aree realmente presenti nel CV.", "basso", 6, [])
        if item:
            suggestions.append(item)

    if not suggestions:
        full_text = cv_text.strip()
        if full_text:
            profile_text = profile_rewrite(full_text, parsed, target)
            if profile_text:
                item = make_suggestion("profile", "PROFILO", "Rendi il CV più mirato al ruolo", full_text[:900], profile_text, "Crea una base più leggibile e orientata al ruolo anche quando il CV non ha sezioni pulite.", "alto", 1, [role])
                if item:
                    suggestions.append(item)
            skill_terms = extract_skill_terms(full_text)
            if skill_terms:
                grouped = group_skills(skill_terms)
                item = make_suggestion("skills", "HARD SKILLS", "Metti in evidenza le competenze già presenti", full_text[:900], grouped, "Riorganizza le competenze emerse dal testo libero in una sezione leggibile e ATS-friendly.", "alto", 2, skill_terms)
                if item:
                    suggestions.append(item)
            experience_text = experience_rewrite(full_text, target)
            if experience_text:
                item = make_suggestion("experience", "ESPERIENZE PROFESSIONALI", "Trasforma il testo in esperienza leggibile", full_text[:900], experience_text, "Ricostruisce un blocco esperienza più chiaro partendo dal testo grezzo disponibile.", "alto", 3, [])
                if item:
                    suggestions.append(item)

    unique_suggestions: List[Dict[str, Any]] = []
    seen = set()
    for item in sorted(suggestions, key=lambda s: int(s.get("priority", 99))):
        key = (item["section"], normalize(item["original_text"])[:180], normalize(item["proposed_text"])[:180])
        if key in seen:
            continue
        seen.add(key)
        unique_suggestions.append(item)
    if len(unique_suggestions) == 1 and unique_suggestions[0].get("category") == "education" and (sections.get("experience") or sections.get("projects") or sections.get("hard_skills")):
        return []
    return unique_suggestions[:8]


def filter_confirmation_items(items: Any) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    filtered: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("skill") or "").strip()
        key = normalize(name)
        if is_noise_keyword(name) or key in seen:
            continue
        seen.add(key)
        filtered.append(item)
    return filtered


def build_optimized_cv_text(
    cv_text: str,
    accepted_suggestions: Any,
    user_additional_data: Optional[Dict[str, Any]],
    role: str = "",
    company: str = "",
    use_llm: bool = True,
) -> str:
    parsed = parse_cv(cv_text)
    sections = dict(parsed.sections)
    target = build_target_profile(role, company)
    accepted = [item for item in accepted_suggestions or [] if isinstance(item, dict) and item.get("type") == "actionableEdit"]
    accepted_payload: List[Dict[str, Any]] = []
    section_buckets: Dict[str, List[Dict[str, Any]]] = {}

    def _apply_forced_section_change(section_key: str, base_text: str, proposed_texts: List[str]) -> str:
        base_text = (base_text or "").strip()
        cleaned_proposals = [re.sub(r"\n{3,}", "\n\n", str(text or "").strip()) for text in proposed_texts if str(text or "").strip()]
        if not cleaned_proposals:
            return base_text

        merged_proposal = _merge_unique_lines(base_text, *cleaned_proposals)
        if not merged_proposal:
            return base_text

        normalized_base = normalize(base_text)
        normalized_merged = normalize(merged_proposal)
        if normalized_merged and normalized_merged != normalized_base:
            return strip_section_titles(merged_proposal)

        if base_text and cleaned_proposals[0]:
            if normalize(cleaned_proposals[0]) not in normalized_base:
                return strip_section_titles(_merge_unique_lines(base_text, cleaned_proposals[0]))

        return strip_section_titles(merged_proposal)

    def _canonical_section_key(section_label: str) -> str:
        normalized_label = normalize(section_label)
        for key, heading in CANONICAL_TO_HEADING.items():
            if normalized_label == normalize(heading) or normalized_label in SECTION_ALIASES.get(key, set()):
                return key
        if normalized_label in {"objective", "obiettivo"}:
            return "profile"
        if normalized_label in {"skills", "hard_skills", "soft_skills", "competenze"}:
            return "hard_skills"
        if normalized_label in {"experience", "esperienza"}:
            return "experience"
        if normalized_label in {"project", "projects", "progetti"}:
            return "projects"
        if normalized_label in {"education", "istruzione", "formazione"}:
            return "education"
        return "profile"

    for item in accepted:
        section_label = str(item.get("section") or "")
        original = str(item.get("original_text") or item.get("original") or "").strip()
        proposed = str(item.get("proposed_text") or item.get("replacement") or "").strip()
        if not proposed:
            continue
        section_key = _canonical_section_key(section_label)
        sanitized = sanitize_rewrite_instruction({
            "section": section_key,
            "original": original,
            "replacement": proposed,
            "id": item.get("id"),
            "category": item.get("category"),
        })
        if not sanitized:
            continue
        payload_item = {
            "target_section": section_key,
            "action": "replace",
            "old_text_hint": original[:250],
            "new_text": sanitized["replacement"][:900],
            "used_existing_evidence": True,
            "forbidden_added_claims": [],
            "source_id": item.get("id"),
        }
        accepted_payload.append(payload_item)
        section_buckets.setdefault(section_key, []).append(payload_item)

    body_sections = [key for key in sections.keys() if key != "header"]
    if not body_sections:
        full_text = cv_text or ""
        profile_text = profile_rewrite(full_text, parsed, target)
        if profile_text:
            sections["profile"] = profile_text
            if "profile" not in parsed.order:
                parsed.order.append("profile")
        experience_text = experience_rewrite(full_text, target)
        if experience_text:
            sections["experience"] = experience_text
            if "experience" not in parsed.order:
                parsed.order.append("experience")
        hard_skills_text = group_skills(extract_skill_terms(full_text))
        if hard_skills_text:
            sections["hard_skills"] = hard_skills_text
            if "hard_skills" not in parsed.order:
                parsed.order.append("hard_skills")

    ollama_instructions: List[Dict[str, Any]] = []
    if use_llm and _rewrite_llm_enabled() and (role or company or accepted_payload or (user_additional_data or {})):
        prompt = f"""
Restituisci SOLO JSON valido, senza markdown, con questa forma:
{{
  "instructions": [
    {{
      "target_section": "profile | experience | projects | education | skills",
      "action": "replace",
      "old_text_hint": "frammento già presente nel CV",
      "new_text": "testo riscritto professionale",
      "used_existing_evidence": ["lista di fatti realmente presenti nel CV o nei dati utente"],
      "forbidden_added_claims": ["lista vuota oppure claim vietati evitati"]
    }}
  ]
}}

Regole:
- usa solo informazioni presenti nel CV originale, nei suggerimenti accettati e nei dati aggiuntivi utente;
- non inventare esperienze, numeri, certificazioni, risultati o competenze;
- non inserire titoli di sezione nel new_text;
- il DOCX non deve essere generato qui;
- limita le istruzioni alle sezioni profile, experience, projects, education, skills.

Ruolo target: {role or "Non specificato"}
Azienda target: {company or "Non specificata"}

CV originale:
{cv_text[:7000]}

Suggerimenti accettati:
{json.dumps(accepted_payload, ensure_ascii=False)}

Dati aggiuntivi utente:
{json.dumps(user_additional_data or {}, ensure_ascii=False)}

Suggerisci istruzioni solo per le sezioni che hanno davvero valore.
"""
        raw_ollama = _call_copywriting_llm(prompt)
        if raw_ollama and isinstance(raw_ollama.get("instructions"), list):
            for item in raw_ollama.get("instructions", []):
                sanitized = sanitize_rewrite_instruction(item)
                if sanitized:
                    ollama_instructions.append(sanitized)
                    section_buckets.setdefault(str(sanitized.get("section") or "profile"), []).append({
                        "target_section": str(sanitized.get("section") or "profile"),
                        "action": "replace",
                        "old_text_hint": str(sanitized.get("original") or "")[:250],
                        "new_text": str(sanitized.get("replacement") or "")[:900],
                        "used_existing_evidence": True,
                        "forbidden_added_claims": [],
                    })
    def _merge_unique_lines(*chunks: str) -> str:
        lines: List[str] = []
        seen_lines = set()
        for chunk in chunks:
            for raw_line in str(chunk or "").splitlines():
                line = clean_line(raw_line)
                if not line:
                    continue
                marker = normalize(line)
                if marker in seen_lines:
                    continue
                seen_lines.add(marker)
                lines.append(line)
        return "\n".join(lines).strip()

    if "profile" in section_buckets:
        before_profile = sections.get("profile", "")
        proposed_texts = [str(item.get("new_text") or "") for item in section_buckets["profile"]]
        after_profile = _apply_forced_section_change("profile", profile_rewrite(before_profile, parsed, target), proposed_texts)
        if after_profile:
            sections["profile"] = after_profile

    if "experience" in section_buckets:
        base = experience_rewrite(sections.get("experience", ""), target)
        proposed_texts = [str(item.get("new_text") or "") for item in section_buckets["experience"]]
        merged_experience = _apply_forced_section_change("experience", base, proposed_texts)
        if merged_experience:
            sections["experience"] = merged_experience

    if "projects" in section_buckets:
        base = projects_rewrite(sections.get("projects", ""), target)
        proposed_texts = [str(item.get("new_text") or "") for item in section_buckets["projects"]]
        merged_projects = _apply_forced_section_change("projects", base, proposed_texts)
        if merged_projects:
            sections["projects"] = merged_projects

    if "education" in section_buckets:
        base = education_rewrite(sections.get("education", ""), parsed, target)
        proposed_texts = [str(item.get("new_text") or "") for item in section_buckets["education"]]
        merged_education = _apply_forced_section_change("education", base, proposed_texts)
        if merged_education:
            sections["education"] = merged_education

    if any(key in section_buckets for key in ("skills", "hard_skills", "soft_skills")):
        current = sections.get("hard_skills", "")
        incoming = []
        for key in ("skills", "hard_skills", "soft_skills"):
            incoming.extend([str(item.get("new_text") or "") for item in section_buckets.get(key, [])])
        incoming_text = _merge_unique_lines(*incoming)
        if incoming_text:
            existing_terms = extract_skill_terms(current)
            incoming_terms = extract_skill_terms(incoming_text)
            merged_terms = unique([*existing_terms, *incoming_terms, *[clean_line(line) for line in incoming_text.splitlines() if clean_line(line)]])
            sections["hard_skills"] = group_skills(merged_terms) or incoming_text
            if normalize(sections["hard_skills"]) == normalize(current) and normalize(incoming_text) != normalize(current):
                sections["hard_skills"] = incoming_text

    confirmed = (user_additional_data or {}).get("confirmed_skills", [])
    confirmed_names: List[str] = []
    if isinstance(confirmed, list):
        for item in confirmed:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("skill") or "").strip()
            else:
                name = str(item or "").strip()
            if name and not is_noise_keyword(name):
                confirmed_names.append(name)
    if confirmed_names:
        existing = extract_skill_terms(sections.get("hard_skills", ""))
        merged = unique([*existing, *confirmed_names])
        sections["hard_skills"] = group_skills(merged) or ", ".join(merged)
        if "hard_skills" not in parsed.order:
            parsed.order.append("hard_skills")

    order = [key for key in SECTION_ORDER if key in sections]
    for key in parsed.order:
        if key in sections and key not in order:
            order.append(key)

    rows: List[str] = []
    for key in order:
        text = sections.get(key, "").strip()
        if not text:
            continue
        if key == "header":
            rows.append(text)
        else:
            heading = CANONICAL_TO_HEADING.get(key, key.upper())
            rows.append(f"{heading}\n{text}")
    optimized_text = "\n\n".join(rows).strip()
    return optimized_text
