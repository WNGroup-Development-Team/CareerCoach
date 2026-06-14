from __future__ import annotations

import re
import unicodedata
from typing import Dict, Optional, Set


SECTION_ALIASES: Dict[str, Set[str]] = {
    "header": {"header", "intestazione", "dati personali", "personal details"},
    "contacts": {
        "contatti", "informazioni di contatto", "recapiti", "dati di contatto",
        "contact", "contacts", "contact details", "personal information",
        "pagina web personale", "personal website",
    },
    "profile": {
        "profilo", "profilo personale", "profilo professionale", "chi sono",
        "presentazione", "su di me", "obiettivo", "obiettivo professionale",
        "sintesi professionale", "summary", "professional summary", "about",
        "about me", "personal profile", "career objective",
    },
    "experience": {
        "esperienza", "esperienze", "esperienza professionale",
        "esperienze professionali", "esperienza lavorativa",
        "esperienze lavorative", "carriera professionale", "carriera",
        "percorso professionale", "storia lavorativa", "impieghi",
        "impieghi precedenti", "attivita professionali", "attivita lavorative",
        "work experience", "professional experience", "employment",
        "employment history", "career history", "work history",
    },
    "education": {
        "formazione", "formazione accademica", "istruzione", "studi",
        "istruzione e formazione",
        "percorso di studi", "percorso accademico", "titoli di studio",
        "educazione", "education", "academic background", "academic history",
        "qualifications", "studies",
    },
    "hard_skills": {
        "hard skills", "competenze", "competenze tecniche",
        "abilita tecniche", "capacita tecniche", "conoscenze tecniche",
        "tecnologie", "strumenti", "strumenti e tecnologie",
        "linguaggi e tecnologie", "technical skills", "skills",
        "technical competencies", "core competencies", "tools and technologies",
        "it skills", "computer skills", "digital skills",
    },
    "soft_skills": {
        "soft skills", "competenze trasversali", "competenze personali",
        "capacita personali", "abilita personali", "qualita personali",
        "personal skills", "interpersonal skills", "soft competencies",
        "capacita", "abilita",
    },
    "languages": {
        "lingue", "lingue straniere", "conoscenze linguistiche",
        "competenze linguistiche", "idiomi", "languages",
        "language", "language skills", "language proficiency", "comunicazione",
    },
    "projects": {
        "progetti", "progetti personali", "progetti professionali",
        "progetti accademici", "project work", "projects", "portfolio",
        "portfolio progetti", "attivita rilevanti", "esperienze aggiuntive",
        "pagina aggiuntiva", "selected projects", "personal projects",
        "academic projects", "additional information", "additional activities",
    },
    "certifications": {
        "certificazioni", "certificati", "attestati", "abilitazioni",
        "licenze", "corsi e certificazioni", "certifications", "certificates",
        "licenses", "courses and certifications",
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


def aliases_for(section: str) -> Set[str]:
    return set(NORMALIZED_SECTION_ALIASES.get(section, set()))
