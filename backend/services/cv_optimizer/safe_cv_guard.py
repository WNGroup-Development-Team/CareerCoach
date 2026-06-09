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


def _llm_rewrite(prompt: str, fallback: str, max_tokens: int = 400) -> str:
    """Call Groq/LLM to rewrite a CV section. Returns fallback on any error."""
    try:
        import os
        from openai import OpenAI

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return fallback
        model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1", timeout=15.0)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.4,
        )
        result = (response.choices[0].message.content or "").strip()
        if len(result) < 20:
            return fallback
        return result
    except Exception:
        return fallback


def _llm_rewrite_profile(original: str, role: str, company: str, signals: List[str]) -> str:
    company_part = f" per {company}" if company else ""
    signals_str = f"Competenze rilevanti presenti nel CV: {', '.join(signals[:6])}." if signals else ""
    fallback_company = f" presso {company}" if company else ""
    fallback_signals = f", valorizzando competenze in {', '.join(signals[:5])}" if signals else ""
    fallback = (
        f"{original.rstrip('.')}. Obiettivo professionale: contribuire a iniziative coerenti con il ruolo di {role}{fallback_company}"
        f"{fallback_signals}, con un approccio orientato ad analisi, progetti, collaborazione e risultati concreti."
    )
    prompt = f"""Sei un career coach esperto. Riscrivi il profilo professionale di questo CV per renderlo più efficace per il ruolo di {role}{company_part}.

PROFILO ORIGINALE:
{original}

{signals_str}

REGOLE IMPORTANTI:
- Usa SOLO le informazioni già presenti nel profilo originale e nel CV, non inventare nulla
- Mantieni il tono in prima persona o terza persona coerente con l'originale
- Massimo 4-5 frasi, circa 80-120 parole
- Il testo deve essere fluente e naturale, non elenchi puntati
- Non iniziare con frasi generiche come "Sono un professionista" o "Con X anni di esperienza"
- Integra il ruolo target in modo naturale

Rispondi SOLO con il testo riscritto, senza spiegazioni o prefissi."""
    return _llm_rewrite(prompt, fallback, max_tokens=250)


def _llm_rewrite_experience(original: str, role: str, company: str) -> str:
    company_part = f" per {company}" if company else ""
    bullets = []
    for sentence in re.split(r"(?<=[.!?])\s+", compact(original, 850)):
        sentence = sentence.strip().rstrip(".")
        if sentence:
            bullets.append(f"- {sentence}.")
    fallback = f"Esperienza rilevante per il ruolo di {role}:\n" + "\n".join(bullets[:5])
    prompt = f"""Sei un career coach esperto. Riscrivi questa sezione ESPERIENZE di un CV per renderla più efficace per il ruolo di {role}{company_part}.

ESPERIENZA ORIGINALE:
{original}

REGOLE IMPORTANTI:
- Usa SOLO le informazioni già presenti nel testo originale, non inventare nulla
- Riformula in 3-5 bullet point iniziando con verbi di azione forti (es: "Sviluppato", "Gestito", "Implementato", "Coordinato")
- Ogni bullet deve essere conciso (max 2 righe) e orientato ai risultati quando possibile
- Mantieni date, nomi di aziende e ruoli esatti così come appaiono nell'originale
- Non aggiungere intestazioni ridondanti come "Esperienza valorizzata per il ruolo di"

Rispondi SOLO con i bullet point riscritti, senza spiegazioni o prefissi."""
    return _llm_rewrite(prompt, fallback, max_tokens=350)


def _llm_rewrite_projects(original: str, role: str) -> str:
    project_lines = []
    for part in re.split(r"\n|·|•", original):
        part = clean_line(part).strip(".")
        if len(norm(part).split()) >= 5 and part not in {"/", "\\"}:
            project_lines.append(f"- {part}.")
    fallback = f"Progetti rilevanti per il ruolo di {role}:\n" + "\n".join(unique(project_lines)[:7])
    if not project_lines:
        return fallback
    prompt = f"""Sei un career coach esperto. Riscrivi questa sezione PROGETTI di un CV per renderla più efficace per il ruolo di {role}.

PROGETTI ORIGINALI:
{original}

REGOLE IMPORTANTI:
- Usa SOLO i progetti già presenti nel testo originale, non inventarne di nuovi
- Per ogni progetto, evidenzia tecnologie usate, il tuo ruolo e l'impatto o risultato
- Usa bullet point concisi (max 2 righe ciascuno)
- Mantieni i nomi dei progetti esatti
- Non aggiungere intestazioni ridondanti come "Progetti rilevanti per il ruolo di"

Rispondi SOLO con i bullet point riscritti, senza spiegazioni o prefissi."""
    return _llm_rewrite(prompt, fallback, max_tokens=350)


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
        proposed = _llm_rewrite_profile(profile, role, company, signals)
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
        proposed = _llm_rewrite_experience(selected, role, company)
        item = make_action("experience", "ESPERIENZE PROFESSIONALI", "Valorizza l'esperienza più rilevante", selected, proposed, "Trasforma l'esperienza in bullet leggibili e orientati al ruolo, mantenendo i fatti presenti.", "alto", 3, [])
        if item:
            suggestions.append(item)

    projects = sections.get("projects", "")
    if projects:
        proposed = _llm_rewrite_projects(projects, role)
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