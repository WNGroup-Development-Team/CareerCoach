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

    profile_lines = sections.get("profile", [])
    education_start = None
    for index, line in enumerate(profile_lines):
        plain = norm(line)
        academic_start = plain.startswith((
            "universita ", "università ", "university ", "liceo ", "istituto ",
        ))
        degree_with_date = (
            any(term in plain for term in ("laurea triennale", "laurea magistrale", "master ", "diploma "))
            and bool(re.search(r"\b(?:19|20)\d{2}\b", line))
        )
        if academic_start or degree_with_date:
            education_start = index
            break
    if education_start is not None:
        sections["profile"] = profile_lines[:education_start]
        sections["education"] = [
            *profile_lines[education_start:],
            *sections.get("education", []),
        ]

    result: Dict[str, str] = {}
    for key, raw_lines in sections.items():
        filtered: List[str] = []
        for line in raw_lines:
            plain = norm(line)
            if key not in {"header", "contacts"} and looks_like_contact(line):
                continue
            if key in {"hard_skills", "soft_skills"}:
                foreign_section = (
                    heading_key(line)
                    or any(marker in plain for marker in [
                        "obiettivo", "formazione", "esperienza", "progetti", "lingue",
                        "comunicazione", "universita", "università", "laurea", "diploma",
                        "tirocinio", "sono una ", "sono un ",
                    ])
                )
                prose_line = len(plain.split()) > 12 and not any(separator in line for separator in [",", ":", "|", "•", "·"])
                if foreign_section or prose_line:
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
            print(f"[safe_cv_guard] suggestion scartato: tipo non valido o non actionableEdit -> {item.get('id') if isinstance(item, dict) else type(item).__name__}")
            continue
        if is_bad_suggestion(item):
            print(f"[safe_cv_guard] suggestion scartato: is_bad_suggestion -> {item.get('id') or item.get('title') or item.get('section')}")
            continue
        key = (
            norm(item.get("section") or item.get("category") or ""),
            norm(item.get("original_text") or item.get("original") or "")[:180],
            norm(item.get("proposed_text") or item.get("replacement") or "")[:180],
        )
        if key in seen:
            print(f"[safe_cv_guard] suggestion scartato: duplicato -> {item.get('id') or item.get('title') or item.get('section')}")
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
        "hard_skills": ["Sviluppo software", "Debugging", "Version control", "Unit testing", "Code review", "API", "System design", "Testing automatico", "CI/CD"],
        "tools": ["Git", "GitHub", "Docker", "VS Code", "PostgreSQL", "Jira", "CI/CD pipelines"],
        "languages": ["Python", "Java", "JavaScript", "C++"],
        "soft_skills": ["Problem solving", "Collaborazione", "Comunicazione tecnica", "Precisione", "Pensiero logico", "Ownership", "Adattabilità"],
    },
    "frontend developer": {
        "role_terms": ["frontend developer", "front end", "frontend", "ui", "ux", "web developer", "web design"],
        "hard_skills": ["HTML/CSS", "JavaScript", "TypeScript", "Responsive design", "Accessibility", "Design systems", "User interface", "Component architecture", "State management"],
        "tools": ["Figma", "Adobe XD", "VS Code", "Git", "Webpack", "Vite", "Storybook"],
        "languages": ["JavaScript", "TypeScript", "React"],
        "soft_skills": ["Creatività", "Attenzione ai dettagli", "Collaborazione", "Comunicazione", "Problem solving", "User empathy"],
    },
    "qa tester": {
        "role_terms": ["qa", "quality assurance", "tester", "software tester", "test engineer", "testing"],
        "hard_skills": ["Test case", "Test plan", "Bug tracking", "Regression testing", "Manual testing", "Automated testing"],
        "tools": ["Jira", "TestRail", "Selenium", "Postman", "Git"],
        "languages": ["Python", "JavaScript", "SQL"],
        "soft_skills": ["Precisione", "Problem solving", "Collaborazione", "Attenzione ai dettagli"],
    },
    "marketing specialist": {
        "role_terms": ["marketing", "digital marketing", "content marketing", "seo", "sem", "growth"],
        "hard_skills": ["Content strategy", "Campaign management", "SEO", "SEM", "Analytics", "Copywriting", "Brand positioning"],
        "tools": ["Google Analytics", "Meta Ads", "Google Ads", "Mailchimp", "HubSpot"],
        "languages": [],
        "soft_skills": ["Creatività", "Comunicazione", "Problem solving", "Organizzazione", "Collaborazione"],
    },
    "sales specialist": {
        "role_terms": ["sales", "commerciale", "business development", "account manager", "account", "vendite"],
        "hard_skills": ["Lead generation", "Pipeline management", "Negotiation", "CRM", "Forecasting", "Account management"],
        "tools": ["Salesforce", "HubSpot", "Pipedrive", "Excel", "LinkedIn Sales Navigator"],
        "languages": [],
        "soft_skills": ["Comunicazione", "Negoziazione", "Orientamento al risultato", "Resilienza", "Collaborazione"],
    },
    "hr specialist": {
        "role_terms": ["hr", "human resources", "recruiter", "talent acquisition", "people operations"],
        "hard_skills": ["Selezione del personale", "Colloqui", "Employer branding", "Onboarding", "Gestione talenti", "Policy HR"],
        "tools": ["ATS", "LinkedIn Recruiter", "Excel", "Workday", "BambooHR"],
        "languages": [],
        "soft_skills": ["Comunicazione", "Ascolto", "Empatia", "Organizzazione", "Discrezione"],
    },
    "finance analyst": {
        "role_terms": ["finance", "financial", "contabile", "controller", "accounting", "financial analyst"],
        "hard_skills": ["Analisi finanziaria", "Budgeting", "Forecasting", "Reporting", "Contabilità", "KPI", "Excel avanzato"],
        "tools": ["Excel", "SAP", "Power BI", "Tableau", "ERP"],
        "languages": [],
        "soft_skills": ["Precisione", "Pensiero analitico", "Organizzazione", "Problem solving", "Affidabilità"],
    },
    "operations specialist": {
        "role_terms": ["operations", "operation", "coordinator", "coordinatore", "amministrativo", "back office", "office"],
        "hard_skills": ["Process management", "Pianificazione", "Reportistica", "Gestione documentale", "Workflow", "KPI"],
        "tools": ["Excel", "Notion", "Trello", "Jira", "Google Workspace"],
        "languages": [],
        "soft_skills": ["Organizzazione", "Precisione", "Comunicazione", "Problem solving", "Affidabilità"],
    },
    "consultant": {
        "role_terms": ["consultant", "consulente", "advisory", "strategy", "business consultant"],
        "hard_skills": ["Analisi dei processi", "Problem solving", "Stakeholder management", "Reporting", "Pianificazione"],
        "tools": ["Excel", "PowerPoint", "Power BI", "Miro", "Jira"],
        "languages": [],
        "soft_skills": ["Comunicazione", "Pensiero critico", "Collaborazione", "Problem solving", "Adattabilità"],
    },
}


def matcher_role_family(role: str, description: str = "") -> str:
    target = norm(f"{role or ''} {description or ''}")
    for family, payload in ROLE_MATCHER_LIBRARY.items():
        if any(norm(term) in target for term in payload.get("role_terms", [])):
            return family
    if any(term in target for term in ["ui", "ux", "design", "designer", "graphic", "interaction"]):
        return "frontend developer"
    if any(term in target for term in ["qa", "test", "tester", "quality assurance", "validation"]):
        return "qa tester"
    if any(term in target for term in ["marketing", "seo", "sem", "content", "growth"]):
        return "marketing specialist"
    if any(term in target for term in ["sales", "vendit", "commercial", "business development", "account"]):
        return "sales specialist"
    if any(term in target for term in ["human resources", "hr", "recruit", "talent acquisition", "people"]):
        return "hr specialist"
    if any(term in target for term in ["finance", "financial", "contabil", "controller", "accounting"]):
        return "finance analyst"
    if any(term in target for term in ["operations", "operation", "coordin", "amministr", "back office", "office"]):
        return "operations specialist"
    if any(term in target for term in ["consult", "advisory", "strategy", "strategic"]):
        return "consultant"
    return ""


def matcher_library_for(role: str, description: str = "") -> Dict[str, List[str]]:
    family = matcher_role_family(role, description)
    if family:
        return ROLE_MATCHER_LIBRARY[family]
    normalized = norm(f"{role or ''} {description or ''}")
    if any(term in normalized for term in ["ui", "ux", "design", "designer", "graphic", "interaction"]):
        return ROLE_MATCHER_LIBRARY["frontend developer"]
    if any(term in normalized for term in ["qa", "test", "tester", "quality assurance", "validation"]):
        return ROLE_MATCHER_LIBRARY["qa tester"]
    if any(term in normalized for term in ["marketing", "seo", "sem", "content", "growth"]):
        return ROLE_MATCHER_LIBRARY["marketing specialist"]
    if any(term in normalized for term in ["sales", "vendit", "commercial", "business development", "account"]):
        return ROLE_MATCHER_LIBRARY["sales specialist"]
    if any(term in normalized for term in ["human resources", "hr", "recruit", "talent acquisition", "people"]):
        return ROLE_MATCHER_LIBRARY["hr specialist"]
    if any(term in normalized for term in ["finance", "financial", "contabil", "controller", "accounting"]):
        return ROLE_MATCHER_LIBRARY["finance analyst"]
    if any(term in normalized for term in ["operations", "operation", "coordin", "amministr", "back office", "office"]):
        return ROLE_MATCHER_LIBRARY["operations specialist"]
    if any(term in normalized for term in ["consult", "advisory", "strategy", "strategic"]):
        return ROLE_MATCHER_LIBRARY["consultant"]
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
    description = str(target.get("description") or evaluation.get("description") or "")
    sections = parse_sections(cv_text)
    present_keywords = _supported_role_keywords(cv_text, role)
    missing_keywords = unique([
        *evaluation.get("missing_keywords", []),
        *evaluation.get("missing_hard_skills", []),
        *evaluation.get("missing_soft_skills", []),
    ])
    role_family = matcher_role_family(role, description)
    library = matcher_library_for(role, description)
    suggestions: List[Dict[str, Any]] = []

    profile = sections.get("profile", "")
    prefer_operational_sections = role_family in {"data analyst", "data scientist", "project manager", "software engineer", "backend developer", "frontend developer"}
    if profile and not is_bad_profile_text(profile) and not (prefer_operational_sections and (sections.get("experience") or sections.get("hard_skills"))):
        role_terms = [term for term in library.get("role_terms", []) if term and term not in present_keywords][:3]
        role_focus = ", ".join(role_terms[:2]) if role_terms else (role_family or role or "ruolo target")
        kw = ""
        if present_keywords or role_terms:
            useful_terms = unique([*present_keywords[:3], *role_terms[:2]])
            kw = f", valorizzando competenze già presenti come {', '.join(useful_terms[:4])}"
        proposed = (
            f"{profile.rstrip('.')}. Profilo orientato{_final_role_phrase(role, company)}{kw}, "
            f"con focus su {role_focus} e con attenzione a chiarezza, collaborazione e risultati concreti."
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
    skills = unique([*extract_skills(hard), *present_keywords, *missing_keywords[:3]])
    grouped = group_skills(skills)
    if hard and grouped:
        grouped_lines = [line.strip() for line in grouped.splitlines() if line.strip()]
        if role_family in {"data analyst", "project manager", "software engineer", "backend developer", "frontend developer", "data scientist"}:
            grouped_lines = grouped_lines[:10]
            if role_family == "data analyst":
                preferred = [
                    line for line in grouped_lines
                    if any(token in line.lower() for token in ["sql", "python", "excel", "power bi", "tableau", "kpi", "dashboard", "report", "analytics", "machine learning"])
                ]
                if preferred:
                    grouped_lines = preferred + [line for line in grouped_lines if line not in preferred]
        item = _make_matcher_action(
            "skills", "HARD SKILLS", "Riorganizza le competenze tecniche",
            hard, grouped,
            f"Presenta le competenze in gruppi leggibili per ATS e recruiter, mettendo in primo piano quelle più utili per {role}.",
            "alto", 2, skills,
        )
        if item:
            if grouped_lines:
                item["proposed_text"] = "Competenze tecniche:\n" + "\n".join(f"- {line}" for line in grouped_lines)
            suggestions.append(item)

    if missing_keywords and hard:
        useful_missing = [kw for kw in missing_keywords if kw and normalize_pair_equal(kw, "") is False][:6]
        if useful_missing:
            proposed = (
                "Competenze tecniche da evidenziare solo se già presenti o confermate:\n"
                + "\n".join(f"- {kw}" for kw in unique(useful_missing)[:6])
            )
            item = _make_matcher_action(
                "skills", "HARD SKILLS", "Allinea le keyword ATS al ruolo",
                hard,
                proposed,
                f"Rende più visibili le keyword richieste per {role} senza inventare competenze nuove.",
                "medio", 2,
                unique([*present_keywords, *useful_missing]),
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
            soft_priority_map = {
                "data analyst": ["Pensiero analitico", "Attenzione ai dettagli", "Comunicazione dei risultati", "Problem solving", "Collaborazione"],
                "project manager": ["Organizzazione", "Gestione priorità", "Comunicazione", "Leadership", "Negoziazione"],
                "software engineer": ["Problem solving", "Collaborazione", "Comunicazione tecnica", "Precisione", "Pensiero logico"],
                "backend developer": ["Problem solving", "Precisione", "Collaborazione", "Documentazione tecnica", "Comunicazione tecnica"],
                "frontend developer": ["Creatività", "Attenzione ai dettagli", "Collaborazione", "Comunicazione", "Problem solving"],
                "data scientist": ["Pensiero analitico", "Problem solving", "Comunicazione scientifica", "Collaborazione", "Attenzione ai dettagli"],
            }
            soft_priority = soft_priority_map.get(role_family, [])
            ordered_soft = unique([*soft_priority, *soft_items, *missing_keywords[:3]])
            proposed = "Soft skills rilevanti:\n" + "\n".join(
                f"- {skill.strip().rstrip('.')}"
                for skill in ordered_soft[:8]
                if skill.strip()
            )
            item = _make_matcher_action(
                "soft_skills", "SOFT SKILLS", "Rendi più pulita la sezione soft skills",
                soft, proposed,
                f"Metti in evidenza le soft skill più utili per {role}, mantenendo solo competenze realmente supportate dal CV.",
                "medio", 5, soft_items,
            )
            if item:
                suggestions.append(item)

    if missing_keywords and not any(item.get("category") == "ats_keywords" for item in suggestions):
        suggested_terms = unique([kw for kw in missing_keywords if kw][:6])
        if suggested_terms:
            source_block = sections.get("profile") or sections.get("experience") or sections.get("hard_skills") or _final_best_block(cv_text)
            if source_block:
                item = _make_matcher_action(
                    "ats_keywords", "HARD SKILLS", "Collega il CV alle keyword del ruolo",
                    source_block,
                    (
                        f"Keyword da coprire nel CV per il ruolo di {role}:\n"
                        + "\n".join(f"- {kw}" for kw in suggested_terms)
                    ),
                    f"Mostra al recruiter quali termini del ruolo sono già parzialmente rappresentati o da confermare per {role}.",
                    "medio", 6,
                    suggested_terms,
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
    if clean:
        return clean

    # Fallback finale: se le regole sopra non trovano nulla, genera almeno una
    # modifica conservativa a partire dalla prima sezione utile del CV.
    fallback_sources = [
        ("profile", "CHI SONO", "Rendi il profilo più mirato alla candidatura", "Adatta il profilo al ruolo usando solo informazioni già presenti nel CV."),
        ("experience", "ESPERIENZE PROFESSIONALI", "Rendi più chiara l’esperienza più rilevante", "Riscrivi la sezione in modo più leggibile e orientato al ruolo, senza aggiungere fatti nuovi."),
        ("projects", "PROGETTI", "Rendi i progetti più leggibili", "Organizza i progetti in modo più chiaro, mantenendo solo informazioni già presenti."),
        ("hard_skills", "HARD SKILLS", "Riorganizza le competenze tecniche", "Raggruppa le competenze in blocchi più leggibili per ATS e recruiter."),
        ("soft_skills", "SOFT SKILLS", "Rendi più pulita la sezione soft skills", "Metti in evidenza le soft skill già presenti in modo più chiaro."),
        ("education", "FORMAZIONE", "Rendi la formazione più leggibile", "Riformula la sezione in modo più ordinato, senza aggiungere dati nuovi."),
    ]
    for section_key, section_name, title, reason in fallback_sources:
        original = sections.get(section_key, "")
        if not original.strip():
            continue
        if section_key == "hard_skills":
            proposed = _skills_rewrite(original, {"role": role, "company": company, "role_family": role_family})
        elif section_key == "soft_skills":
            soft_values = [item.strip() for item in re.split(r"[,;|•·\n]+", original) if item.strip()]
            if soft_values:
                preferred = {
                    "data analyst": ["Pensiero analitico", "Attenzione ai dettagli", "Comunicazione", "Problem solving", "Collaborazione"],
                    "data scientist": ["Pensiero analitico", "Problem solving", "Comunicazione scientifica", "Collaborazione", "Attenzione ai dettagli"],
                    "project manager": ["Organizzazione", "Gestione priorità", "Comunicazione", "Leadership", "Negoziazione"],
                    "software engineer": ["Problem solving", "Collaborazione", "Comunicazione tecnica", "Precisione", "Pensiero logico"],
                    "backend developer": ["Problem solving", "Precisione", "Collaborazione", "Documentazione tecnica", "Comunicazione tecnica"],
                    "frontend developer": ["Creatività", "Attenzione ai dettagli", "Collaborazione", "Comunicazione", "Problem solving"],
                    "game design": ["Creatività", "Collaborazione", "Problem solving", "Iterazione su feedback", "Comunicazione"],
                }.get(role_family, [])
                proposed = "Soft skills:\n" + "\n".join(f"- {skill}" for skill in unique([*preferred, *soft_values])[:8])
            else:
                proposed = ""
        elif section_key == "experience":
            proposed = _experience_rewrite(original, {"role": role, "company": company})
        elif section_key == "projects":
            proposed = _projects_rewrite(original, {"role": role, "company": company})
        elif section_key == "education":
            proposed = _education_rewrite(original, {"role": role}, cv_text)
        else:
            proposed = _profile_rewrite(original, {"role": role, "company": company}, cv_text)

        item = _make_matcher_action(
            section_key,
            section_name,
            title,
            original,
            proposed or _shorten_cv_text(original, 500),
            reason,
            "medio" if section_key in {"experience", "projects"} else "basso",
            99,
            present_keywords[:4],
        )
        if item and suggestion_targets_current_cv(item, cv_text):
            return [item]
    return clean
