from __future__ import annotations

import re
import unicodedata
from typing import Dict, Optional, Set


SECTION_ALIASES: Dict[str, Set[str]] = {
    "header": {
        "header", "intestazione", "dati personali", "personal details",
    },
    "contacts": {
        "contatti", "informazioni di contatto", "recapiti", "dati di contatto",
        "contact", "contacts", "contact details", "personal information",
        "informazioni personali", "dati personali", "personal details",
        "contact information", "personal data", "pagina web personale", "personal website",
    },
    "profile": {
        "profilo", "profilo personale", "profilo professionale", "chi sono",
        "presentazione", "su di me", "obiettivo", "obiettivo professionale",
        "sintesi professionale", "summary", "professional summary", "about",
        "about me", "personal profile", "career objective", "objective",
        "executive summary", "career summary",
    },
    "experience": {
        "esperienza", "esperienze", "esperienza professionale",
        "esperienze professionali", "esperienza lavorativa",
        "esperienze lavorative", "carriera professionale", "carriera",
        "percorso professionale", "storia lavorativa", "impieghi",
        "impieghi precedenti", "attivita professionali", "attivita lavorative",
        "attivita professionale", "attivita lavorativa", "background professionale",
        "profilo professionale esperienze", "esperienze di lavoro",
        "work experience", "professional experience", "employment",
        "employment history", "career history", "work history", "working experience",
    },
    "education": {
        "formazione", "formazione accademica", "istruzione", "studi",
        "istruzione e formazione",
        "percorso di studi", "percorso accademico", "titoli di studio",
        "percorso formativo", "background accademico", "educazione",
        "education", "academic background", "academic history",
        "qualifications", "studies", "education and training",
    },
    "hard_skills": {
        "hard skills", "competenze", "competenze tecniche",
        "competenze professionali", "skill tecniche", "skills tecniche",
        "skill professionali", "competenze specialistiche",
        "abilita tecniche", "capacita tecniche", "conoscenze tecniche",
        "tecnologie", "strumenti", "strumenti e tecnologie",
        "linguaggi e tecnologie", "technical skills", "skills",
        "technical competencies", "core competencies", "tools and technologies",
        "it skills", "computer skills", "digital skills",
    },
    "soft_skills": {
        "soft skills", "competenze trasversali", "competenze personali",
        "capacita personali", "abilita personali", "qualita personali",
        "capacita relazionali", "capacita organizzative", "soft skill",
        "personal skills", "interpersonal skills", "soft competencies",
        "capacita", "abilita",
    },
    "languages": {
        "lingue", "lingue straniere", "conoscenze linguistiche",
        "competenze linguistiche", "idiomi", "languages",
        "language", "language skills", "language proficiency", "foreign languages",
        "comunicazione",
    },
    "projects": {
        "progetti", "progetto", "progetti personali", "progetto personale",
        "progetti professionali", "progetti universitari", "progetto universitario",
        "progetti accademici", "project work", "projects", "portfolio",
        "portfolio progetti", "attivita rilevanti", "esperienze aggiuntive",
        "pagina aggiuntiva", "selected projects", "personal projects",
        "academic projects", "additional information", "additional activities",
    },
    "certifications": {
        "certificazioni", "certificati", "attestati", "abilitazioni",
        "licenze", "corsi", "corso", "corsi e certificazioni",
        "certifications", "certificates", "licenses", "courses and certifications",
    },
    "publications": {
        "pubblicazioni", "pubblicazione", "publications", "publication",
        "articoli scientifici", "scientific publications", "research publications",
    },
}


def normalize_section_title(value: str) -> str:
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", str(value or ""))
        if not unicodedata.combining(char)
    ).lower()
    text = re.sub(r"[\s:|/_\-\u2012\u2013\u2014\u2212]+", " ", text)
    text = re.sub(r"[^a-z0-9+#&. ]", "", text)
    return re.sub(r"\s+", " ", text).strip(" .")


NORMALIZED_SECTION_ALIASES: Dict[str, Set[str]] = {
    key: {normalize_section_title(alias) for alias in aliases}
    for key, aliases in SECTION_ALIASES.items()
}

HEADING_TO_SECTION = {
    alias: key
    for key, aliases in NORMALIZED_SECTION_ALIASES.items()
    for alias in aliases
}

ADDITIONAL_FIELD_SECTION_KEYS: Dict[str, str] = {
    "experiences": "experience",
    "experience": "experience",
    "work_experience": "experience",
    "professional_experience": "experience",
    "esperienza_lavorativa": "experience",
    "esperienze_lavorative": "experience",
    "esperienza_professionale": "experience",
    "esperienze_professionali": "experience",
    "projects": "projects",
    "project": "projects",
    "portfolio": "projects",
    "measurable_results": "projects",
    "results": "projects",
    "achievements": "projects",
    "certifications": "certifications",
    "certification": "certifications",
    "certificates": "certifications",
    "licenses": "certifications",
    "languages": "languages",
    "language": "languages",
    "education": "education",
    "training": "education",
    "courses": "education",
    "percorso_formativo": "education",
    "technical_skills": "hard_skills",
    "hard_skills": "hard_skills",
    "tools": "hard_skills",
    "technologies": "hard_skills",
    "skills": "hard_skills",
    "competenze_tecniche": "hard_skills",
    "competenze_professionali": "hard_skills",
    "soft_skills": "soft_skills",
    "personal_skills": "soft_skills",
    "competenze_trasversali": "soft_skills",
    "company_role_notes": "profile",
    "role_notes": "profile",
    "target_notes": "profile",
    "additional_notes": "profile",
    "profile": "profile",
    "summary": "profile",
    "objective": "profile",
    "informazioni_personali": "contacts",
    "personal_information": "contacts",
}


def canonical_section_key(value: str) -> Optional[str]:
    normalized = normalize_section_title(value)
    exact = HEADING_TO_SECTION.get(normalized)
    if exact:
        return exact
    without_dates = re.sub(
        r"(?:\s*(?:\b(?:19|20)\d{2}\b|\bin corso\b))+$",
        "",
        normalized,
    ).strip()
    return HEADING_TO_SECTION.get(without_dates)


def additional_field_section_key(value: str) -> Optional[str]:
    normalized = normalize_section_title(value)
    if not normalized:
        return None
    underscored = normalized.replace(" ", "_")
    return (
        ADDITIONAL_FIELD_SECTION_KEYS.get(underscored)
        or ADDITIONAL_FIELD_SECTION_KEYS.get(normalized)
        or canonical_section_key(normalized)
    )


def aliases_for(section: str) -> Set[str]:
    return set(NORMALIZED_SECTION_ALIASES.get(section, set()))
