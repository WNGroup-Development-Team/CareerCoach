from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional


SECTION_ALIASES = {
    "profile": {"profilo", "profilo professionale", "chi sono", "obiettivo", "summary", "about me"},
    "experience": {"esperienza", "esperienze", "esperienza professionale", "esperienze professionali", "work experience"},
    "projects": {"progetti", "projects", "portfolio", "pagina aggiuntiva", "attivita rilevanti"},
    "hard_skills": {"hard skills", "competenze tecniche", "technical skills"},
    "soft_skills": {"soft skills", "competenze trasversali"},
    "education": {"formazione", "istruzione", "education"},
    "languages": {"lingue", "languages", "comunicazione"},
    "contacts": {"contatti", "contact", "contacts"},
}
ALL_HEADINGS = {item for values in SECTION_ALIASES.values() for item in values}
HEADING_TO_KEY = {alias: key for key, aliases in SECTION_ALIASES.items() for alias in aliases}

CATEGORY_LABELS = {
    "profile": "Profilo professionale",
    "experience": "Esperienze",
    "project": "Progetti",
    "skills": "Competenze tecniche",
    "soft_skills": "Soft skills",
}

NOISE_KEYWORDS = {
    "voglio", "prepararmi", "colloquio", "per", "un", "una", "di", "da", "con",
    "voglio prepararmi", "prepararmi per", "per un", "un colloquio", "colloquio di",
    "scientist", "analyst", "engineer", "designer", "developer", "manager", "hard",
}
BAD_PROFILE_MARKERS = {
    "captive portal", "identity provider", "tesi di laurea", "progetto con l obiettivo",
    "progetto con l'obiettivo", "corso di laurea", "universita", "università",
    "discussa il", "laurea con votazione",
}
BAD_PROPOSED_MARKERS = {
    "percorso formativo valorizzato",
    "percorso formativo coerente",
    "keyword tecniche gia supportate",
    "keyword tecniche già supportate",
    "strumenti hard",
    "progetti rilevanti per il ruolo di project manager /",
    "progetti rilevanti per il ruolo di",
}
COMMON_SKILLS = [
    "Python", "SQL", "Java", "C++", "C#", "Linux", "Networking", "Big Data",
    "ML & AI", "Machine Learning", "Artificial Intelligence", "Data Engineering",
    "Data Analysis", "RAG", "Retrieval-Augmented Generation", "NLP", "LLM",
    "Cloud Computing", "Power BI", "Tableau", "Excel", "BigQuery", "Google Analytics",
    "Docker", "Git", "GitHub", "PostgreSQL", "MongoDB", "Unity", "Unreal Engine",
    "Blender", "Figma", "Miro",
]
CONTACT_HINTS = ["@", "linkedin", "github", "http://", "https://", "www.", "telefono", "phone", "mobile", "via "]


def strip_accents(value: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", value or "") if not unicodedata.combining(ch))


def norm(value: Any) -> str:
    text = strip_accents(str(value or "")).lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9+#&./\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" \t-•·:/\\")


def is_noise_keyword(value: Any) -> bool:
    cleaned = norm(value)
    if not cleaned or cleaned in NOISE_KEYWORDS:
        return True
    if any(token in cleaned for token in ["voglio", "prepararmi", "colloquio"]):
        return True
    words = cleaned.split()
    if len(words) > 4 and not any(anchor in cleaned for anchor in ["machine learning", "data analysis", "data engineering", "project management", "game design", "user experience", "artificial intelligence", "gestione di progetti"]):
        return True
    return False


def unique(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        cleaned = clean_line(item)
        key = norm(cleaned)
        if cleaned and key and key not in seen and not is_noise_keyword(cleaned):
            seen.add(key)
            out.append(cleaned)
    return out


def heading_key(line: str) -> Optional[str]:
    cleaned = norm(line).strip(":")
    if cleaned in HEADING_TO_KEY:
        return HEADING_TO_KEY[cleaned]
    return None


def looks_like_contact(line: str) -> bool:
    plain = norm(line)
    return (
        any(hint in plain for hint in CONTACT_HINTS)
        or bool(re.search(r"\+?\d[\d\s().-]{7,}", line or ""))
    )


def split_heading_line(line: str) -> List[str]:
    stripped = clean_line(line)
    if not stripped:
        return []
    for heading in sorted(ALL_HEADINGS, key=len, reverse=True):
        pattern = rf"^\s*{re.escape(heading)}\s*:?\s*(.*)$"
        match = re.match(pattern, stripped, flags=re.IGNORECASE)
        if match:
            rest = clean_line(match.group(1))
            return [heading.upper()] + ([rest] if rest else [])
    return [stripped]


def prepare_lines(text: str) -> List[str]:
    raw = re.sub(r"\r\n?", "\n", text or "")
    lines: List[str] = []
    for original_line in raw.splitlines():
        for part in split_heading_line(original_line):
            if part:
                lines.append(part)
    return lines


def compact(value: str, max_chars: int = 850) -> str:
    text = re.sub(r"[ \t]+", " ", value or "")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    text = dedupe_repetition(text)
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    end = max(cut.rfind("."), cut.rfind(";"), cut.rfind("!"), cut.rfind("?"))
    if end > 220:
        return cut[:end + 1].strip()
    return cut.rsplit(" ", 1)[0].strip()


def dedupe_repetition(text: str) -> str:
    flat = re.sub(r"\s+", " ", text or "").strip()
    if not flat:
        return ""
    tokens = flat.split()
    for n in (32, 24, 18, 14, 10):
        if len(tokens) <= n * 2:
            continue
        prefix = " ".join(tokens[:n])
        pos = flat.find(prefix, len(prefix) + 10)
        if pos > 80:
            return flat[:pos].strip(" .;:") + "."
    return text.strip()


def is_bad_profile_text(value: str) -> bool:
    plain = norm(value)
    if not plain or len(plain.split()) < 6:
        return True
    return any(marker in plain for marker in BAD_PROFILE_MARKERS)


def find_real_profile(lines: List[str]) -> str:
    profile_lines: List[str] = []
    capture = False
    for line in lines:
        key = heading_key(line)
        if key == "profile":
            capture = True
            continue
        if capture and key and key != "profile":
            break
        if capture and not looks_like_contact(line):
            profile_lines.append(line)
    candidate = compact(" ".join(profile_lines), 650)
    if candidate and not is_bad_profile_text(candidate):
        return candidate

    candidates = []
    for line in lines:
        plain = norm(line)
        if looks_like_contact(line):
            continue
        if any(marker in plain for marker in ["sono interessato", "sono una persona", "amo lavorare", "obiettivo professionale"]):
            candidates.append(line)
    merged = compact(" ".join(candidates[:3]), 650)
    return merged if merged and not is_bad_profile_text(merged) else ""


def parse_sections(cv_text: str) -> Dict[str, str]:
    lines = prepare_lines(cv_text)
    sections: Dict[str, List[str]] = {"header": []}
    current = "header"

    for line in lines:
        key = heading_key(line)
        if key:
            current = key
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)

    result: Dict[str, str] = {}
    for key, raw_lines in sections.items():
        filtered: List[str] = []
        for line in raw_lines:
            plain = norm(line)
            if key not in {"header", "contacts"} and looks_like_contact(line):
                continue
            if key in {"hard_skills", "soft_skills"} and (
                heading_key(line)
                or any(marker in plain for marker in ["obiettivo", "formazione", "esperienza", "progetti", "lingue", "comunicazione"])
            ):
                continue
            if clean_line(line) in {"/", "\\", "-", "•"}:
                continue
            filtered.append(line)
        text = "\n".join(unique(filtered)) if key in {"hard_skills", "soft_skills"} else "\n".join(filtered)
        text = compact(text, 1200)
        if text:
            result[key] = text

    if is_bad_profile_text(result.get("profile", "")):
        candidate = find_real_profile(lines)
        if candidate:
            result["profile"] = candidate
        else:
            result.pop("profile", None)
    return result


def extract_skills(value: str) -> List[str]:
    text = " " + norm(value) + " "
    skills: List[str] = []
    for skill in COMMON_SKILLS:
        if norm(skill) in text:
            skills.append(skill)

    cleaned_text = re.sub(r"[●○■□▪▫]+", " ", value or "")
    for part in re.split(r"[,;|•·\n]+", cleaned_text):
        part = clean_line(part)
        plain = norm(part)
        if not part or looks_like_contact(part):
            continue
        if plain in {"hard", "skills", "hard skills", "soft skills", "competenze"}:
            continue
        if 1 <= len(part.split()) <= 4:
            skills.append(part)
    return unique(skills)[:20]


def group_skills(skills: List[str]) -> str:
    groups = {
        "Linguaggi e database": [],
        "Data, AI e analisi": [],
        "Sistemi, reti e sviluppo": [],
        "Strumenti": [],
    }
    for skill in skills:
        plain = norm(skill)
        if plain in {"python", "sql", "java", "c++", "c#"}:
            groups["Linguaggi e database"].append(skill)
        elif any(x in plain for x in ["data", "big data", "machine", "ml", "ai", "rag", "nlp", "llm", "cloud", "kpi", "dashboard"]):
            groups["Data, AI e analisi"].append(skill)
        elif any(x in plain for x in ["linux", "network", "docker", "git", "database", "postgres", "mongo"]):
            groups["Sistemi, reti e sviluppo"].append(skill)
        else:
            groups["Strumenti"].append(skill)

    lines = []
    for label, values in groups.items():
        values = unique(values)
        if values:
            lines.append(f"{label}: {', '.join(values)}")
    proposed = "\n".join(lines)
    if norm(proposed) in {"strumenti hard", "hard"}:
        return ""
    return proposed


def target_from_evaluation(evaluation: Dict[str, Any]) -> Dict[str, str]:
    target = evaluation.get("target") if isinstance(evaluation.get("target"), dict) else {}
    return {
        "role": str(target.get("role") or evaluation.get("role") or "").strip(),
        "company": str(target.get("company") or evaluation.get("company") or "").strip(),
    }


def present_signals(sections: Dict[str, str]) -> List[str]:
    full = "\n".join(sections.values())
    return unique([skill for skill in COMMON_SKILLS if norm(skill) in norm(full)])[:7]


def make_id(section: str, title: str, original: str) -> str:
    raw = norm(f"{section}-{title}-{original[:80]}")
    return re.sub(r"[^a-z0-9]+", "-", raw).strip("-")[:96] or "cv-suggestion"


def normalize_pair_equal(a: str, b: str) -> bool:
    na, nb = norm(a), norm(b)
    return na == nb or SequenceMatcher(None, na, nb).ratio() >= 0.96


def make_action(category: str, section: str, title: str, original: str, proposed: str, reason: str, impact: str, priority: int, keywords: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    original = compact(original, 950)
    proposed = compact(proposed, 1100)
    if not original or not proposed or normalize_pair_equal(original, proposed):
        return None
    payload = {
        "id": make_id(section, title, original),
        "type": "actionableEdit",
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, "Suggerimento"),
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
    return None if is_bad_suggestion(payload) else payload


def select_relevant_experience(experience_text: str, target: Dict[str, str]) -> str:
    chunks = re.split(r"\n(?=\d{4}|Tirocinio|Poste|Common|[A-Z].{0,40}-)", experience_text or "")
    best = ""
    best_score = -999
    role_plain = norm(target.get("role") or "")
    company_plain = norm(target.get("company") or "")
    for chunk in chunks:
        clean = compact(chunk, 850)
        plain = norm(clean)
        if len(plain.split()) < 8:
            continue
        score = 0
        for term in ["rag", "chatbot", "pipeline", "dati", "data", "documenti", "nlp", "llm", "metriche", "progetto"]:
            if term in plain:
                score += 2
        if company_plain and company_plain in plain:
            score += 3
        if role_plain and role_plain in plain:
            score += 1
        if "post" in plain:
            score += 2
        if "captive portal" in plain or "identity provider" in plain:
            score -= 4
        if score > best_score:
            best_score = score
            best = clean
    return best or compact(experience_text, 850)


def build_structured_cv_suggestions(evaluation: Dict[str, Any]) -> List[Dict[str, Any]]:
    cv_text = str(evaluation.get("cv_text") or "")
    target = target_from_evaluation(evaluation)
    role = target["role"] or "ruolo target"
    company = target["company"]
    sections = parse_sections(cv_text)
    signals = present_signals(sections)
    suggestions: List[Dict[str, Any]] = []

    profile = sections.get("profile", "")
    if profile:
        company_part = f" presso {company}" if company else ""
        signal_part = f", valorizzando competenze in {', '.join(signals[:5])}" if signals else ""
        proposed = (
            f"{profile.rstrip('.')}. Obiettivo professionale: contribuire a iniziative coerenti con il ruolo di {role}{company_part}"
            f"{signal_part}, con un approccio orientato ad analisi, progetti, collaborazione e risultati concreti."
        )
        item = make_action("profile", "PROFILO", "Riscrivi il profilo in funzione del ruolo", profile, proposed, "Rende il profilo più mirato al ruolo usando solo informazioni già presenti nel CV.", "alto", 1, [role])
        if item:
            suggestions.append(item)

    hard = sections.get("hard_skills", "")
    skills = extract_skills(hard)
    grouped = group_skills(skills)
    if hard and grouped:
        item = make_action("skills", "HARD SKILLS", "Riorganizza le competenze tecniche già presenti", hard, grouped, "Rende le competenze più leggibili per recruiter e ATS senza aggiungere competenze non confermate.", "alto", 2, skills)
        if item:
            suggestions.append(item)

    exp = sections.get("experience", "")
    if exp:
        selected = select_relevant_experience(exp, target)
        bullets = []
        for sentence in re.split(r"(?<=[.!?])\s+", compact(selected, 850)):
            sentence = sentence.strip().rstrip(".")
            if sentence:
                bullets.append(f"- {sentence}.")
        proposed = f"Esperienza rilevante per il ruolo di {role}:\n" + "\n".join(bullets[:5])
        item = make_action("experience", "ESPERIENZE PROFESSIONALI", "Valorizza l’esperienza più rilevante", selected, proposed, "Trasforma l’esperienza in bullet leggibili e orientati al ruolo, mantenendo i fatti presenti.", "alto", 3, [])
        if item:
            suggestions.append(item)

    projects = sections.get("projects", "")
    if projects:
        project_lines = []
        for part in re.split(r"\n|·|•", projects):
            part = clean_line(part).strip(".")
            if len(norm(part).split()) >= 5 and part not in {"/", "\\"}:
                project_lines.append(f"- {part}.")
        proposed = f"Progetti rilevanti per il ruolo di {role}:\n" + "\n".join(unique(project_lines)[:7])
        item = make_action("project", "PROGETTI", "Valorizza i progetti più coerenti", projects, proposed, "Rende i progetti più chiari e collegati alla candidatura senza inventare dettagli.", "medio", 4, [])
        if item:
            suggestions.append(item)

    soft = sections.get("soft_skills", "")
    if soft:
        soft_items = unique(re.split(r"[,;|•·\n]+", soft))
        if len(soft_items) >= 2:
            proposed = "Soft skills: " + ", ".join(soft_items[:8])
            item = make_action("soft_skills", "SOFT SKILLS", "Rendi più chiara la sezione soft skills", soft, proposed, "Mantiene le soft skill reali e le presenta in modo più pulito.", "medio", 5, soft_items)
            if item:
                suggestions.append(item)

    clean: List[Dict[str, Any]] = []
    seen = set()
    for item in sorted(suggestions, key=lambda x: int(x.get("priority", 99))):
        if is_bad_suggestion(item):
            continue
        key = (item["section"], norm(item["original_text"])[:180], norm(item["proposed_text"])[:180])
        if key not in seen:
            seen.add(key)
            clean.append(item)
    return clean[:8]


def is_bad_suggestion(item: Dict[str, Any]) -> bool:
    section = norm(item.get("section") or item.get("category") or "")
    category = norm(item.get("category") or "")
    original = norm(item.get("original_text") or item.get("original") or "")
    proposed = norm(item.get("proposed_text") or item.get("replacement") or "")
    combined = f"{original} {proposed}"
    if category == "education" or section in {"formazione", "education", "istruzione"}:
        return True
    if category == "profile" or section in {"profilo", "profile", "chi sono", "obiettivo"}:
        if any(marker in combined for marker in BAD_PROFILE_MARKERS):
            return True
        if original.startswith("di realizzare") or original.startswith("progetto con"):
            return True
    if "strumenti hard" in proposed or proposed.strip() in {"/", "progetti rilevanti per il ruolo di project manager /"}:
        return True
    if any(marker in proposed for marker in BAD_PROPOSED_MARKERS):
        if not (category == "project" and len(proposed.split()) > 10):
            return True
    if not original or not proposed or normalize_pair_equal(original, proposed):
        return True
    return False


def sanitize_accepted_cv_suggestions(suggestions: Any) -> List[Dict[str, Any]]:
    if not isinstance(suggestions, list):
        return []
    clean: List[Dict[str, Any]] = []
    seen = set()
    for item in suggestions:
        if not isinstance(item, dict) or item.get("type") != "actionableEdit":
            continue
        if is_bad_suggestion(item):
            continue
        key = (
            norm(item.get("section") or item.get("category") or ""),
            norm(item.get("original_text") or item.get("original") or "")[:180],
            norm(item.get("proposed_text") or item.get("replacement") or "")[:180],
        )
        if key in seen:
            continue
        seen.add(key)
        clean.append(item)
    return clean[:30]


def filter_confirmation_items(items: Any) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    clean: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("skill") or "").strip()
        key = norm(name)
        if is_noise_keyword(name) or key in seen:
            continue
        seen.add(key)
        clean.append(item)
    return clean

# ---------------------------------------------------------------------------
# Patch CareerCoach 2026-06: deterministic Resume Matcher/OpenResume style
# ---------------------------------------------------------------------------
# The original guard was intentionally very strict and could return an empty
# suggestion list. The definitions below override the previous public functions
# with a more robust local engine: it uses only text already present in the CV,
# never calls an LLM, and still returns actionableEdit items the existing
# DocxPreserver/ResumeRewriter pipeline can apply safely.

ROLE_MATCHER_LIBRARY = {
    "game design": {
        "role_terms": ["game design", "game designer", "level design", "unity", "unreal"],
        "hard_skills": ["Game design", "Level design", "Prototipazione", "Game mechanics", "User experience", "Playtesting", "Storytelling"],
        "tools": ["Unity", "Unreal Engine", "Blender", "Figma", "Miro"],
        "languages": ["C#", "C++", "Python"],
        "soft_skills": ["Creatività", "Problem solving", "Collaborazione", "Comunicazione", "Iterazione su feedback"],
    },
    "data analyst": {
        "role_terms": ["data analyst", "analista dati", "analisi dati", "business intelligence", "reporting", "kpi"],
        "hard_skills": ["Analisi dati", "SQL", "Python", "Data visualization", "Reporting", "KPI", "Business intelligence"],
        "tools": ["Excel", "Power BI", "Tableau", "Looker", "Google Analytics"],
        "languages": ["Python", "SQL"],
        "soft_skills": ["Pensiero analitico", "Comunicazione", "Problem solving", "Attenzione ai dettagli"],
    },
    "data scientist": {
        "role_terms": ["data scientist", "data science", "machine learning", "modelli predittivi"],
        "hard_skills": ["Python", "Machine Learning", "SQL", "Analisi predittiva", "Modelli statistici", "Data preprocessing", "Feature engineering"],
        "tools": ["pandas", "scikit-learn", "Jupyter", "TensorFlow", "Tableau"],
        "languages": ["Python", "SQL", "R"],
        "soft_skills": ["Problem solving", "Pensiero analitico", "Comunicazione scientifica", "Collaborazione"],
    },
    "project manager": {
        "role_terms": ["project manager", "project management", "gestione progetti", "pianificazione", "stakeholder"],
        "hard_skills": ["Pianificazione attività", "Gestione scadenze", "Coordinamento team", "Monitoraggio avanzamento", "Risk management", "Budget management"],
        "tools": ["Excel", "Trello", "Jira", "Notion", "Microsoft Project", "Asana"],
        "languages": [],
        "soft_skills": ["Comunicazione", "Organizzazione", "Problem solving", "Leadership", "Gestione priorità", "Negoziazione"],
    },
    "software engineer": {
        "role_terms": ["software engineer", "software developer", "sviluppatore", "developer", "programmatore"],
        "hard_skills": ["Sviluppo software", "Debugging", "Version control", "Unit testing", "Code review", "API"],
        "tools": ["Git", "GitHub", "Docker", "VS Code", "PostgreSQL"],
        "languages": ["Python", "Java", "JavaScript", "C++"],
        "soft_skills": ["Problem solving", "Collaborazione", "Comunicazione tecnica", "Precisione"],
    },
}


def matcher_role_family(role: str, description: str = "") -> str:
    target = norm(f"{role or ''} {description or ''}")
    for family, payload in ROLE_MATCHER_LIBRARY.items():
        if any(norm(term) in target for term in payload.get("role_terms", [])):
            return family
    return ""


def matcher_library_for(role: str, description: str = "") -> Dict[str, List[str]]:
    family = matcher_role_family(role, description)
    if family:
        return ROLE_MATCHER_LIBRARY[family]
    return {
        "role_terms": [],
        "hard_skills": ["Competenza tecnica principale", "Competenza tecnica secondaria"],
        "tools": [],
        "languages": [],
        "soft_skills": ["Problem solving", "Comunicazione", "Collaborazione", "Organizzazione"],
    }


def _phrase_present(text: str, phrase: str) -> bool:
    haystack = f" {norm(text)} "
    needle = norm(phrase)
    if not needle:
        return False
    if len(needle) <= 3:
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack))
    return needle in haystack


def _supported_role_keywords(cv_text: str, role: str, description: str = "") -> List[str]:
    library = matcher_library_for(role, description)
    candidates = []
    for key in ("hard_skills", "tools", "languages", "soft_skills"):
        candidates.extend(library.get(key, []))
    candidates.extend([skill for skill in COMMON_SKILLS if _phrase_present(cv_text, skill)])
    return unique([kw for kw in candidates if _phrase_present(cv_text, kw)])[:14]


def _missing_role_keywords(cv_text: str, role: str, description: str = "") -> List[str]:
    library = matcher_library_for(role, description)
    candidates = []
    for key in ("hard_skills", "tools", "languages", "soft_skills"):
        candidates.extend(library.get(key, []))
    return unique([kw for kw in candidates if not _phrase_present(cv_text, kw)])[:14]


def _best_free_text_block(cv_text: str) -> str:
    lines = prepare_lines(cv_text)
    candidates: List[str] = []
    buffer: List[str] = []
    for line in lines:
        if heading_key(line) or looks_like_contact(line):
            if buffer:
                candidates.append(compact(" ".join(buffer), 850))
                buffer = []
            continue
        if len(norm(line).split()) >= 4:
            buffer.append(line)
        if len(" ".join(buffer)) > 650:
            candidates.append(compact(" ".join(buffer), 850))
            buffer = []
    if buffer:
        candidates.append(compact(" ".join(buffer), 850))
    candidates = [c for c in candidates if len(norm(c).split()) >= 10]
    if not candidates:
        return ""
    # Prefer blocks that contain project/technical signals, otherwise the first readable block.
    scored = []
    for candidate in candidates:
        plain = norm(candidate)
        score = sum(2 for term in ["progetto", "project", "svilupp", "analisi", "data", "software", "tesi", "team"] if term in plain)
        scored.append((score, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def _compact_to_bullets(text: str, max_items: int = 5) -> str:
    chunks = []
    for part in re.split(r"\n+|(?<=[.!?])\s+|[•·]", text or ""):
        clean = clean_line(part).rstrip(".")
        if len(norm(clean).split()) >= 5:
            chunks.append(clean)
    chunks = unique(chunks)[:max_items]
    return "\n".join(f"- {chunk}." for chunk in chunks)


def _make_matcher_action(
    category: str,
    section: str,
    title: str,
    original: str,
    proposed: str,
    reason: str,
    impact: str,
    priority: int,
    keywords: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    original = compact(original, 950)
    proposed = compact(proposed, 1100)
    if not original or not proposed or normalize_pair_equal(original, proposed):
        return None
    payload = {
        "id": make_id(section, title, original),
        "type": "actionableEdit",
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, "Suggerimento"),
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
    # Keep only basic safety checks. The old guard filtered out too many useful edits.
    if not payload["original_text"] or not payload["proposed_text"]:
        return None
    if any(marker in norm(payload["proposed_text"]) for marker in BAD_PROPOSED_MARKERS):
        return None
    return payload


def build_structured_cv_suggestions(evaluation: Dict[str, Any]) -> List[Dict[str, Any]]:  # type: ignore[override]
    cv_text = str(evaluation.get("cv_text") or "")
    target = target_from_evaluation(evaluation)
    role = target.get("role") or "ruolo target"
    company = target.get("company") or ""
    sections = parse_sections(cv_text)
    present_keywords = _supported_role_keywords(cv_text, role)
    suggestions: List[Dict[str, Any]] = []

    profile = sections.get("profile", "")
    if profile and not is_bad_profile_text(profile):
        company_part = f" presso {company}" if company else ""
        keyword_part = f", valorizzando competenze già presenti come {', '.join(present_keywords[:4])}" if present_keywords else ""
        proposed = (
            f"{profile.rstrip('.')}. Profilo orientato al ruolo di {role}{company_part}"
            f"{keyword_part}, con attenzione a chiarezza, collaborazione e risultati concreti."
        )
        item = _make_matcher_action(
            "profile", "PROFILO", "Rendi il profilo più mirato alla candidatura",
            profile, proposed,
            "Adatta il profilo al ruolo usando solo competenze già presenti nel CV.",
            "alto", 1, [role, *present_keywords[:4]],
        )
        if item:
            suggestions.append(item)

    hard = sections.get("hard_skills", "")
    skills = unique([*extract_skills(hard), *present_keywords])
    grouped = group_skills(skills)
    if hard and grouped:
        item = _make_matcher_action(
            "skills", "HARD SKILLS", "Riorganizza le competenze tecniche",
            hard, grouped,
            "Presenta le competenze in gruppi leggibili per ATS e recruiter, senza aggiungere skill non supportate.",
            "alto", 2, skills,
        )
        if item:
            suggestions.append(item)

    exp = sections.get("experience", "")
    if exp:
        selected = select_relevant_experience(exp, target)
        bullets = _compact_to_bullets(selected, 5)
        proposed = bullets or selected
        item = _make_matcher_action(
            "experience", "ESPERIENZE PROFESSIONALI", "Trasforma l’esperienza in bullet più leggibili",
            selected, proposed,
            "Rende l’esperienza più chiara e scansionabile, mantenendo i fatti del CV originale.",
            "alto", 3, present_keywords,
        )
        if item:
            suggestions.append(item)

    projects = sections.get("projects", "")
    if projects:
        bullets = _compact_to_bullets(projects, 6)
        item = _make_matcher_action(
            "project", "PROGETTI", "Rendi i progetti più chiari",
            projects, bullets,
            "Organizza i progetti in righe più leggibili, senza inventare dettagli.",
            "medio", 4, present_keywords,
        )
        if item:
            suggestions.append(item)

    soft = sections.get("soft_skills", "")
    if soft:
        soft_items = unique(re.split(r"[,;|•·\n]+", soft))
        if len(soft_items) >= 2:
            proposed = "Soft skills: " + ", ".join(soft_items[:8])
            item = _make_matcher_action(
                "soft_skills", "SOFT SKILLS", "Rendi più pulita la sezione soft skills",
                soft, proposed,
                "Mantiene le soft skill reali e le mostra in modo più ordinato.",
                "medio", 5, soft_items,
            )
            if item:
                suggestions.append(item)

    if not suggestions:
        block = _best_free_text_block(cv_text)
        if block:
            bullets = _compact_to_bullets(block, 4)
            if bullets:
                item = _make_matcher_action(
                    "phrases", "ESPERIENZE PROFESSIONALI", "Rendi più leggibile un blocco del CV",
                    block, bullets,
                    "Fallback locale: trasforma un blocco già presente in bullet più chiari e compatibili con ATS.",
                    "medio", 6, present_keywords,
                )
                if item:
                    suggestions.append(item)

    clean: List[Dict[str, Any]] = []
    seen = set()
    for item in sorted(suggestions, key=lambda x: int(x.get("priority", 99))):
        key = (item.get("section"), norm(item.get("original_text") or "")[:200], norm(item.get("proposed_text") or "")[:200])
        if key in seen:
            continue
        seen.add(key)
        clean.append(item)
    return clean[:8]


def build_matcher_keyword_snapshot(cv_text: str, role: str, description: str = "") -> Dict[str, List[str]]:
    """Small helper for debug/tests: Resume Matcher style present/missing keywords."""
    return {
        "present": _supported_role_keywords(cv_text, role, description),
        "missing": _missing_role_keywords(cv_text, role, description),
        "role_family": [matcher_role_family(role, description)] if matcher_role_family(role, description) else [],
    }


# =========================
# Fallback finale più permissivo stile Resume Matcher
# =========================

def _final_best_block(cv_text: str) -> str:
    lines = prepare_lines(cv_text)
    blocks: List[str] = []
    buffer: List[str] = []
    for line in lines:
        if heading_key(line) or looks_like_contact(line):
            if buffer:
                blocks.append(compact(" ".join(buffer), 900))
                buffer = []
            continue
        plain = norm(line)
        if len(plain.split()) >= 4:
            buffer.append(line)
        if len(" ".join(buffer)) >= 500:
            blocks.append(compact(" ".join(buffer), 900))
            buffer = []
    if buffer:
        blocks.append(compact(" ".join(buffer), 900))
    blocks = [b for b in blocks if len(norm(b).split()) >= 10]
    if not blocks:
        return ""
    return sorted(
        blocks,
        key=lambda b: sum(1 for term in ["progetto", "project", "svilupp", "analisi", "data", "software", "team", "tesi"] if term in norm(b)),
        reverse=True,
    )[0]


def _final_role_phrase(role: str, company: str = "") -> str:
    role = clean_line(role) or "ruolo target"
    company = clean_line(company)
    return f" per il ruolo di {role}" + (f" presso {company}" if company else "")


def build_structured_cv_suggestions(evaluation: Dict[str, Any]) -> List[Dict[str, Any]]:  # type: ignore[override]
    """Versione finale: deve restituire almeno una modifica applicabile se il CV è leggibile."""
    cv_text = str(evaluation.get("cv_text") or "")
    if not cv_text.strip():
        return []
    target = target_from_evaluation(evaluation)
    role = target.get("role") or "ruolo target"
    company = target.get("company") or ""
    sections = parse_sections(cv_text)
    present_keywords = _supported_role_keywords(cv_text, role)
    suggestions: List[Dict[str, Any]] = []

    profile = sections.get("profile", "")
    if profile and not is_bad_profile_text(profile):
        kw = f", valorizzando competenze già presenti come {', '.join(present_keywords[:4])}" if present_keywords else ""
        proposed = (
            f"{profile.rstrip('.')}. Profilo orientato{_final_role_phrase(role, company)}{kw}, "
            "con attenzione a chiarezza, collaborazione e risultati concreti."
        )
        item = _make_matcher_action(
            "profile", "PROFILO", "Rendi il profilo più mirato alla candidatura",
            profile, proposed,
            "Adatta il profilo al ruolo usando solo informazioni già presenti nel CV.",
            "alto", 1, [role, *present_keywords[:4]],
        )
        if item:
            suggestions.append(item)

    hard = sections.get("hard_skills", "")
    skills = unique([*extract_skills(hard), *present_keywords])
    grouped = group_skills(skills)
    if hard and grouped:
        item = _make_matcher_action(
            "skills", "HARD SKILLS", "Riorganizza le competenze tecniche",
            hard, grouped,
            "Presenta le competenze in gruppi leggibili per ATS e recruiter, senza aggiungere skill non supportate.",
            "alto", 2, skills,
        )
        if item:
            suggestions.append(item)

    exp = sections.get("experience", "") or _final_best_block(cv_text)
    if exp:
        proposed = (
            f"Esperienza valorizzata{_final_role_phrase(role, company)}, evidenziando attività già presenti nel CV:\n"
            + (_compact_to_bullets(exp, 5) or f"- {compact(exp, 700).rstrip('.')}.")
        )
        item = _make_matcher_action(
            "experience", "ESPERIENZE PROFESSIONALI", "Valorizza l’esperienza più rilevante",
            exp, proposed,
            "Rende il contenuto più leggibile e orientato alla candidatura, senza inventare esperienze.",
            "alto", 3, present_keywords,
        )
        if item:
            suggestions.append(item)

    projects = sections.get("projects", "")
    if projects:
        proposed = f"Progetti valorizzati{_final_role_phrase(role, company)}:\n" + (_compact_to_bullets(projects, 6) or f"- {compact(projects, 700).rstrip('.')}.")
        item = _make_matcher_action(
            "project", "PROGETTI", "Rendi i progetti più chiari",
            projects, proposed,
            "Organizza i progetti in righe più leggibili, senza inventare dettagli.",
            "medio", 4, present_keywords,
        )
        if item:
            suggestions.append(item)

    soft = sections.get("soft_skills", "")
    if soft:
        soft_items = unique(re.split(r"[,;|•·\n]+", soft))
        if len(soft_items) >= 2:
            proposed = "Soft skills: " + ", ".join(soft_items[:8])
            item = _make_matcher_action(
                "soft_skills", "SOFT SKILLS", "Rendi più pulita la sezione soft skills",
                soft, proposed,
                "Mantiene le soft skill reali e le mostra in modo più ordinato.",
                "medio", 5, soft_items,
            )
            if item:
                suggestions.append(item)

    clean: List[Dict[str, Any]] = []
    seen = set()
    for item in sorted(suggestions, key=lambda x: int(x.get("priority", 99))):
        # Evita proposte identiche o troppo diagnostiche.
        original = norm(item.get("original_text") or "")
        proposed = norm(item.get("proposed_text") or "")
        if not original or not proposed or original == proposed:
            continue
        key = (item.get("section"), original[:220], proposed[:220])
        if key in seen:
            continue
        seen.add(key)
        clean.append(item)
        if len(clean) >= 8:
            break
    return clean
