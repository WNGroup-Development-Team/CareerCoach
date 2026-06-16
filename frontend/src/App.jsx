import React, { useEffect, useRef, useState } from "react";
import "./App.css";
/* eslint-disable react-hooks/set-state-in-effect, react-hooks/exhaustive-deps, react-hooks/immutability */

import logoCareerCoach from "./assets/career-coach-logo.png";
import PersonalizeExperience from "./PersonalizeExperience";
import {
  SparkleIcon,
  LinkedInIcon,
  InstagramIcon,
  GitHubIcon,
  CheckCircleIcon,
  ExportIcon,
  BrainIcon,
  HammerIcon,
  PuzzleIcon,
} from "./digital-icons";


const IS_DEV = import.meta.env.DEV;
<<<<<<< HEAD
const API_URL = import.meta.env.VITE_API_URL || (IS_DEV ? "http://127.0.0.1:8000" : "/api");
=======
const isLocalBrowserHost = () => {
  if (typeof window === "undefined" || !window.location?.hostname) {
    return true;
  }
  const { hostname } = window.location;
  return hostname === "localhost" || hostname === "127.0.0.1";
};
const API_URL = import.meta.env.VITE_API_URL || (IS_DEV && isLocalBrowserHost() ? "http://127.0.0.1:8000" : "/api");
>>>>>>> main
const API_URL_FALLBACKS = (() => {
  const localOrigins = [API_URL];

  if (IS_DEV) {
    localOrigins.push(
      "/api",
      API_URL.includes("127.0.0.1") ? API_URL.replace("127.0.0.1", "localhost") : API_URL,
      "http://localhost:8000",
      "http://127.0.0.1:8000"
    );
  }

  if (IS_DEV && typeof window !== "undefined" && window.location?.hostname) {
    localOrigins.push(`http://${window.location.hostname}:8000`);
  }

  return [...new Set(localOrigins)];
})();
const AUTH_TOKEN_KEY = "careercoach_auth_token";
const INTRO_SPLASH_DURATION_MS = 3000;
const TRANSITION_DURATION_MS = 2000;
const CV_ADDITIONAL_DATA_FIELDS = [
  { key: "experiences", label: "Esperienze da valorizzare" },
  { key: "projects", label: "Progetti importanti" },
  { key: "measurable_results", label: "Risultati misurabili ottenuti" },
  { key: "certifications", label: "Certificazioni o corsi" },
  { key: "company_role_notes", label: "Informazioni specifiche per azienda e ruolo" },
  { key: "additional_notes", label: "Note aggiuntive per l'ottimizzazione" },
];

const CV_COACH_CATEGORY_LABELS = {
  profile: "Profilo professionale",
  experience: "Esperienze da riscrivere meglio",
  phrases: "Frasi da migliorare",
  skills: "Competenze da evidenziare",
  education: "Formazione",
  project: "Progetti",
  extra_page: "Pagina aggiuntiva",
  soft_skills: "Soft skills",
  experiences: "Esperienze da riscrivere meglio",
  missing_info: "Informazioni mancanti da confermare",
  sections: "Sezioni poco chiare o poco efficaci",
};

const getDefaultProfile = () => ({
  name: "",
  email: "",
  phone: "",
  education: "",
  target_role: "",
  sector: "",
  experience_level: "Junior",
  interview_language: "Italiano",
  cv_filename: "",
  cv_uploaded: false,
  cv_text: "",
  linkedin_url: "",
  linkedin_profile_filename: "",
  linkedin_profile_uploaded: false,
  portfolio_url: "",
  instagram_handle: "",
  auth_provider: "",
});

const getEmptyCvAdditionalData = () =>
  CV_ADDITIONAL_DATA_FIELDS.reduce((fields, item) => ({
    ...fields,
    [item.key]: "",
  }), {});

const stripRepeatedQuestionFromAnswer = (answer = "", question = "") => {
  let cleaned = String(answer || "").trim();
  const prompt = String(question || "").trim();
  if (!cleaned || !prompt) {
    return cleaned;
  }

  const escapedPrompt = prompt.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  cleaned = cleaned.replace(
    new RegExp(`^\\s*(?:\\*\\*)?\\s*${escapedPrompt}\\s*(?:\\*\\*)?\\s*[:\\-]?\\s*`, "i"),
    ""
  );
  return cleaned.replace(/^\*{1,2}|\*{1,2}$/g, "").trim();
};

const getSuggestionText = (item) => {
  if (typeof item === "string") {
    return item;
  }
  if (!item || typeof item !== "object") {
    return "";
  }
  return item.description || item.suggestion || item.coach_tip || item.title || "";
};

const CV_SECTION_MARKERS = [
  "CONTATTI",
  "LINGUE",
  "HARD SKILLS",
  "SOFT SKILLS",
  "CHI SONO",
  "PROFILO",
  "PROFILO PROFESSIONALE",
  "FORMAZIONE",
  "ESPERIENZE PROFESSIONALI",
  "ESPERIENZA PROFESSIONALE",
];

const normalizeSuggestionText = (value = "") =>
  String(value).toLowerCase().replace(/\s+/g, " ").trim();

const countSuggestionSectionMarkers = (value = "") => {
  const normalized = normalizeSuggestionText(value);
  return CV_SECTION_MARKERS.filter((marker) => normalized.includes(normalizeSuggestionText(marker))).length;
};

const previewSuggestionText = (value = "", expanded = false) => {
  const text = String(value || "").trim();
  if (expanded || text.length <= 300) {
    return text;
  }
  return `${text.slice(0, 300).trim()}...`;
};

const USELESS_KEYWORD_LABELS = new Set([
  "game",
  "design",
  "management",
  "business",
  "project",
  "projects",
  "team",
  "analysis",
  "developer",
  "engineer",
  "manager",
  "skill",
  "skills",
  "software",
  "data",
]);

const filterUsefulKeywords = (values = []) =>
  (Array.isArray(values) ? values : [])
    .map((item) => String(item || "").trim())
    .filter(Boolean)
    .filter((item) => {
      const normalized = item.toLowerCase();
      return normalized.length >= 3 && !USELESS_KEYWORD_LABELS.has(normalized);
    })
    .filter((item, index, list) =>
      list.findIndex((candidate) => candidate.toLowerCase() === item.toLowerCase()) === index
    );

const getApiErrorDetail = (data, fallback = "Si è verificato un errore.") =>
  typeof data?.detail === "string"
    ? data.detail
    : data?.detail?.message
      || data?.detail?.reason
      || data?.detail?.error
      || (data?.detail ? JSON.stringify(data.detail) : null)
      || fallback;

const getFriendlyApiErrorMessage = (message, status = 0) => {
  const detail = String(message || "").trim();
  if (!detail) {
    return "Si è verificato un errore.";
  }

  if (status === 401 || /sessione mancante/i.test(detail)) {
    return "La sessione non è più valida. Accedi di nuovo per continuare.";
  }
  if (status === 403 || /sessione non autorizzata/i.test(detail)) {
    return "Questo contenuto appartiene a un altro account oppure la sessione non è più autorizzata. Accedi di nuovo.";
  }
  if (/sembra appartenere a un'altra persona/i.test(detail)) {
    return `${detail} Per proseguire carica il CV corretto o aggiorna il profilo con il nome giusto.`;
  }
  if (/non coincide in modo chiaro con quello del profilo/i.test(detail)) {
    return `${detail} Se il CV è tuo, controlla nome e cognome indicati nel profilo prima di continuare.`;
  }

  return detail;
};

const normalizeCoachSuggestion = (item, index, fallbackCategory = "phrases") => {
  if (!item) {
    return null;
  }
  const category = item.category || fallbackCategory;
  const label = item.category_label || CV_COACH_CATEGORY_LABELS[category] || CV_COACH_CATEGORY_LABELS.phrases;
  const title = item.title || item.section || label;
  const description = getSuggestionText(item);
  if (!description && !title) {
    return null;
  }
  const idSource = item.id || `${category}-${title}-${description}-${index}`;
  return {
    id: String(idSource).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
    type: item.type || "",
    category,
    category_label: label,
    title,
    description,
    action: item.action || item.coach_tip || item.suggestion || "",
    section: item.section || "",
    original_text: item.original_text || item.original || "",
    proposed_text: item.proposed_text || item.replacement || "",
    reason: item.reason || item.description || "",
    supported_by_cv: item.supported_by_cv !== false,
    keywords_added: filterUsefulKeywords(item.keywords_added),
    requires_confirmation: Boolean(item.requires_confirmation),
  };
};

const normalizeConfirmationName = (value) => {
  if (typeof value === "string") {
    return value;
  }
  return value?.name || value?.label || value?.keyword || value?.title || "";
};

const canonicalizeSkillName = (value = "") => {
  const normalized = String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9+#.]+/g, " ")
    .replace(/\b(programming|programmazione|language|linguaggio|framework|tool|strumento|skills?|competenze?)\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const aliases = {
    "team working": "collaborazione",
    teamwork: "collaborazione",
    collaboration: "collaborazione",
    "collaborazione in team": "collaborazione",
    "lavoro in team": "collaborazione",
    "lavoro di squadra": "collaborazione",
    "risoluzione dei problemi": "problem solving",
    "gestione delle priorita": "gestione priorita",
    "priority management": "gestione priorita",
    communication: "comunicazione",
    organization: "organizzazione",
    "attention to detail": "attenzione ai dettagli",
    "analytical thinking": "pensiero analitico",
    "data analysis": "analisi dati",
    "data analytics": "analisi dati",
    "analisi dei dati": "analisi dati",
    "data visualisation": "data visualization",
    "visualizzazione dati": "data visualization",
    "visualizzazione dei dati": "data visualization",
    "version control": "controllo versione",
    "controllo di versione": "controllo versione",
    "rest api": "api rest",
    "restful api": "api rest",
    powerbi: "power bi",
  };
  return aliases[normalized] || normalized;
};

const isSkillSemanticallyPresent = (cvText = "", skillName = "") => {
  const identity = canonicalizeSkillName(skillName);
  if (!identity) {
    return true;
  }
  const normalizedCv = String(cvText)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  const knownVariants = {
    collaborazione: ["team working", "teamwork", "collaboration", "collaborazione in team", "lavoro in team", "lavoro di squadra"],
    "problem solving": ["problem solving", "risoluzione dei problemi"],
    "gestione priorita": ["gestione priorita", "gestione delle priorita", "priority management"],
    "attenzione ai dettagli": ["attenzione ai dettagli", "attention to detail"],
    "pensiero analitico": ["pensiero analitico", "analytical thinking"],
    "analisi dati": ["analisi dati", "analisi dei dati", "data analysis", "data analytics"],
    "data visualization": ["data visualization", "data visualisation", "visualizzazione dati", "visualizzazione dei dati"],
    "controllo versione": ["controllo versione", "controllo di versione", "version control"],
    "api rest": ["api rest", "rest api", "restful api"],
  };
  return [identity, ...(knownVariants[identity] || [])].some((variant) => {
    const escaped = variant.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`(^|[^a-z0-9])${escaped}([^a-z0-9]|$)`, "i").test(normalizedCv);
  });
};

const normalizeSkillConfirmationItem = (value, index, fallback = {}) => {
  const name = normalizeConfirmationName(value).trim();
  if (!name) {
    return null;
  }
  const category = value?.category || fallback.category || "hard_skill";
  const alreadyPresent = value?.already_present !== undefined
    ? Boolean(value.already_present)
    : value?.status === "present" || Boolean(fallback.already_present);
  const id = String(value?.id || `skill-${category}-${name}-${index}`)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  return {
    id,
    type: value?.type || fallback.type || "skillConfirmation",
    name,
    category,
    reason: value?.reason || fallback.reason || "Competenza utile per questa candidatura, da inserire solo se reale e non già presente nel CV.",
    already_present: alreadyPresent,
    requires_confirmation: Boolean(value?.requires_confirmation ?? !alreadyPresent),
    status: "pending",
    user_example: "",
    target_section: value?.target_section || fallback.target_section || (category === "soft_skill" ? "SOFT SKILLS" : "HARD SKILLS"),
  };
};

const getConfirmationCategoryLabel = (category = "") => {
  const labels = {
    hard_skill: "Hard skill",
    soft_skill: "Soft skill",
    tool: "Strumento",
    language: "Linguaggio",
  };
  return labels[category] || String(category || "Suggerimento").replaceAll("_", " ");
};

const isActionableCoachSuggestion = (item) =>
  item?.type === "actionableEdit" &&
  Boolean(item.section?.trim()) &&
  Boolean(item.original_text?.trim()) &&
  Boolean(item.proposed_text?.trim()) &&
  item.original_text.trim().length <= 1000 &&
  item.proposed_text.trim().length <= 1000 &&
  countSuggestionSectionMarkers(item.original_text) <= 1 &&
  countSuggestionSectionMarkers(item.proposed_text) === 0 &&
  !(
    ["chi sono", "profilo", "profilo professionale"].includes(normalizeSuggestionText(item.section)) &&
    ["contatti", "lingue", "hard skills", "soft skills", "formazione", "esperienze professionali"].some((marker) =>
      normalizeSuggestionText(`${item.original_text} ${item.proposed_text}`).includes(marker)
    )
  );

const getPendingCoachSuggestionStatuses = (suggestions = []) =>
  suggestions.reduce((selected, suggestion) => ({
    ...selected,
    [suggestion.id]: "pending",
  }), {});

const getCoachSuggestionsFromAnalysis = (analysis) => {
  if (!analysis) {
    return [];
  }
  if (Array.isArray(analysis.coach_suggestions) && analysis.coach_suggestions.length) {
    return analysis.coach_suggestions
      .map((item, index) => normalizeCoachSuggestion(item, index, item.category || "phrases"))
      .filter(isActionableCoachSuggestion);
  }

  const generated = [
    ...(analysis.weaknesses || []).map((item) => ({ item, category: "phrases" })),
    ...(analysis.relevant_skills_found || []).map((item) => ({ item: { title: item, description: "Rendi questa competenza piu visibile dove e gia supportata dal CV." }, category: "skills" })),
    ...(analysis.relevant_experiences || []).map((item) => ({ item, category: "experiences" })),
    ...(analysis.missing_skills_for_role || []).map((item) => ({ item: { title: item, description: "Informazione da aggiungere solo se confermata con un esempio reale.", requires_confirmation: true }, category: "missing_info" })),
    ...((analysis.sections_to_improve || analysis.ats_analysis?.sections_to_improve || []).map((item) => ({ item, category: "sections" }))),
    ...(analysis.suggestions || []).map((item) => ({ item, category: "phrases" })),
  ];

  const seen = new Set();
  return generated
    .map(({ item, category }, index) => normalizeCoachSuggestion(item, index, category))
    .filter((item) => {
      if (!isActionableCoachSuggestion(item) || seen.has(item.id)) {
        return false;
      }
      seen.add(item.id);
      return true;
    });
};

const normalizeCvErrorReference = (value = "") =>
  String(value)
    .trim()
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\s+/g, " ");

const getCvRejectedFieldReference = (value = "") => {
  const normalized = normalizeCvErrorReference(value);
  const adaptationMatch = normalized.match(/risposta domanda (\d+)/);

  if (adaptationMatch) {
    return {
      type: "adaptation",
      index: Number(adaptationMatch[1]) - 1,
    };
  }

  const matchedField = CV_ADDITIONAL_DATA_FIELDS.find((field) =>
    normalizeCvErrorReference(field.key) === normalized ||
    normalizeCvErrorReference(field.label) === normalized
  );

  return matchedField
    ? { type: "additional", key: matchedField.key }
    : null;
};

const wait = (duration) =>
  new Promise((resolve) => {
    setTimeout(resolve, duration);
  });

async function fetchWithTimeout(url, options = {}, timeout = 30000) {
  const controller = new AbortController();
  const headers = new Headers(options.headers || {});
  const storedToken =
    typeof window !== "undefined" ? localStorage.getItem(AUTH_TOKEN_KEY) || "" : "";

  if (storedToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${storedToken}`);
  }

  const timeoutId = setTimeout(() => {
    controller.abort();
  }, timeout);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

async function fetchWithApiFallbacks(path, options = {}, timeout = 30000) {
  const attempts = [...new Set(API_URL_FALLBACKS)];
  let lastError = null;

  for (const baseUrl of attempts) {
    try {
      const response = await fetchWithTimeout(`${baseUrl}${path}`, options, timeout);
      const contentType = response.headers.get("content-type") || "";
      if (baseUrl === "/api" && (response.status === 404 || contentType.includes("text/html"))) {
        continue;
      }
      return response;
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("Impossibile contattare il backend.");
}

function analyzeSpeech(text, durationSeconds) {
  const cleanText = text.toLowerCase();
  const words = cleanText.split(/\s+/).filter(Boolean);

  const fillerList = [
    "ehm",
    "mmm",
    "cioè",
    "allora",
    "praticamente",
    "tipo",
    "diciamo",
    "appunto",
    "ok",
    "quindi"
  ];

  const fillerWords = words.filter((word) =>
    fillerList.includes(word.replace(/[.,!?;:]/g, ""))
  );

  const wordsPerMinute =
    durationSeconds > 0 ? Math.round((words.length / durationSeconds) * 60) : 0;

  return {
    duration_seconds: durationSeconds,
    words_count: words.length,
    words_per_minute: wordsPerMinute,
    filler_words_count: fillerWords.length,
    filler_words: fillerWords
  };
}

function isProfileComplete(profile) {
  return Boolean(profile.cv_uploaded || profile.cv_filename);
}

function normalizeInstagramHandle(value = "") {
  return value
    .trim()
    .replace("https://www.instagram.com/", "")
    .replace("https://instagram.com/", "")
    .split("?")[0]
    .replaceAll("/", "")
    .replace(/^@/, "")
    .toLowerCase();
}

function normalizeProfileUrl(value = "") {
  const trimmed = value.trim();

  if (!trimmed) {
    return "";
  }

  const withProtocol = trimmed.startsWith("http://") || trimmed.startsWith("https://")
    ? trimmed
    : `https://${trimmed}`;

  return withProtocol.replace(/\/$/, "").toLowerCase();
}

function normalizeDigitalAnalysis(analysis) {
  const deterministicStatuses = new Set(["allineato", "da_migliorare", "da_risolvere"]);
  if (
    analysis?.findings?.length
    && analysis.findings.every((finding) => deterministicStatuses.has(finding.status))
  ) {
    return analysis;
  }
  if (!analysis?.findings || analysis.analysis_evidence?.instagram_media_analyzed === true) {
    return analysis;
  }

  const mediaAnalysis = analysis.analysis_evidence?.visual_media_analysis;
  const instagramMessage = mediaAnalysis?.message || (
    analysis.analysis_evidence?.instagram_metadata_found
      ? "Il profilo Instagram risulta rintracciabile sul web. Questa versione analizza solo metadati testuali indicizzati: foto, video e post non sono stati analizzati, anche se il profilo e pubblico."
      : "Instagram e stato collegato, ma non risultano contenuti pubblici accessibili. Se il profilo e privato, foto, bio e post non possono essere analizzati."
  );

  return {
    ...analysis,
    findings: analysis.findings.map((finding) => {
      const title = String(finding.title || "").toLowerCase();
      if (!title.includes("instagram") && !title.includes("foto") && !title.includes("contenuti pubblici")) {
        return finding;
      }

      return {
        ...finding,
        status: "warning",
        description: instagramMessage,
      };
    }),
  };
}

function getDigitalFindingMeta(finding = {}) {
  const status = String(finding.status || "warning").toLowerCase();
  const title = String(finding.title || "").toLowerCase();

  if (status === "success" || status === "allineato") {
    return { tone: "success", label: "Allineato" };
  }
  if (status === "da_migliorare") {
    return { tone: "warning", label: "Da migliorare" };
  }
  if (status === "da_risolvere" || title.includes("linkedin") || title.includes("coerenza cv")) {
    return { tone: "danger", label: "Da risolvere" };
  }
  return { tone: "warning", label: "Da migliorare" };
}

function getDigitalFindingTitle(title = "") {
  const normalized = String(title).trim().toLowerCase();
  const titleMap = {
    "coerenza linkedin": "LinkedIn",
    "coerenza cv e profili": "Coerenza CV / Profili social",
    "coerenza cv/profili": "Coerenza CV / Profili social",
    "foto e contenuti pubblici": "Impatto recruiter",
    "screenshot caricati": "Verifica screenshot",
    "verifica screenshot": "Verifica screenshot",
  };

  return titleMap[normalized] || title;
}

function getCanonicalProfileKey(value = "") {
  try {
    const url = new URL(normalizeProfileUrl(value));
    return `${url.hostname.replace(/^www\./, "")}${url.pathname.replace(/\/+$/, "").toLowerCase()}`;
  } catch {
    return normalizeProfileUrl(value).split("?")[0].replace(/\/+$/, "");
  }
}

function normalizeStrategyItem(item, fallbackTitle = "Elemento rilevante") {
  const cleanGenericTitle = (title = "") => {
    const cleanTitle = String(title || "").trim();
    const normalized = cleanTitle.toLowerCase();
    return ["punto debole", "punto di forza", "elemento rilevante"].includes(normalized)
      ? ""
      : cleanTitle;
  };

  if (typeof item === "string") {
    return {
      title: "",
      description: item,
      coach_tip: "",
    };
  }

  return {
    title: cleanGenericTitle(item?.title || fallbackTitle || ""),
    description: item?.description || String(item || ""),
    coach_tip: item?.coach_tip || "",
  };
}

function getAdaptationQuestion(item, index) {
  const text = `${item?.title || ""} ${item?.description || ""} ${item?.coach_tip || ""}`.toLowerCase();

  if (text.includes("python") || text.includes("react") || text.includes("competen")) {
    return "Quali esperienze, progetti o attività dimostrano questa competenza?";
  }

  if (text.includes("risultat") || text.includes("metric") || text.includes("quantific")) {
    return "Quali risultati concreti o misurabili puoi aggiungere?";
  }

  if (text.includes("progett")) {
    return "Quali progetti reali vuoi valorizzare in questa versione del CV?";
  }

  if (text.includes("certific") || text.includes("cors")) {
    return "Quali corsi, certificazioni o percorsi formativi pertinenti hai completato?";
  }

  if (text.includes("azienda") || text.includes("ruolo")) {
    return "Quali informazioni specifiche su azienda e ruolo vuoi usare per rendere il CV più mirato?";
  }

  if (text.includes("soft") || text.includes("comunic") || text.includes("team")) {
    return "Quali soft skills puoi dimostrare con esempi concreti?";
  }

  return `Quali informazioni reali puoi aggiungere per migliorare questo punto ${index + 1}?`;
}

function looksMostlyEnglish(text = "") {
  const normalized = text.toLowerCase();
  const englishHits = [
    " is ", " are ", " should ", " improve ", " skills ", " experience ",
    " portfolio ", " role ", " candidate ", " company ", " coursework ",
    " highly ", " strong ", " seeks "
  ].filter((word) => normalized.includes(word)).length;
  return englishHits >= 2;
}

function getItalianCvIntroSummary(analysis, role, company) {
  const summary = analysis?.summary || "";
  if (summary && !looksMostlyEnglish(summary)) {
    return summary;
  }

  const score = analysis?.overall_score || analysis?.score || 0;
  const targetRole = role || "ruolo indicato";
  const targetCompany = company || "azienda indicata";
  return `Il CV è stato valutato rispetto al ruolo ${targetRole} presso ${targetCompany}. Il punteggio complessivo è ${score}/100: consulta punteggi, punti di forza, aree da migliorare e suggerimenti per adattarlo meglio alla candidatura.`;
}

function downloadOptimizedCvFile(optimizedCvFile) {
  if (!optimizedCvFile?.file_base64) {
    return;
  }

  const link = document.createElement("a");
  link.href = `data:${optimizedCvFile.content_type};base64,${optimizedCvFile.file_base64}`;
  link.download = optimizedCvFile.filename || "cv-ottimizzato.pdf";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function SplashScreen({
  slogan = "Allenati oggi, conquista il colloquio di domani",
  mode = "intro",
}) {
  const isLoadingMode = mode === "loading";

  return (
    <section className={`splash-page splash-page-${mode}`} aria-label="CareerCoach">
      <div className="splash-brand">
        <img
          className="auth-logo splash-logo"
          src={logoCareerCoach}
          alt="Logo Career Coach"
        />
        <p className="auth-app-title splash-title">CareerCoach</p>
        {isLoadingMode ? (
          <>
            <div className="splash-spinner" aria-label="Caricamento" />
            {slogan && <p className="splash-slogan">{slogan}</p>}
          </>
        ) : (
          <p className="splash-slogan">{slogan}</p>
        )}
      </div>
    </section>
  );
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function FileDocumentIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 3h7l4 4v14H7z" />
      <path d="M14 3v5h5" />
      <path d="M9.5 13h5" />
      <path d="M9.5 16h5" />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="4" y="5" width="16" height="15" rx="2" />
      <path d="M8 3v4" />
      <path d="M16 3v4" />
      <path d="M4 10h16" />
      <path d="M8 14h.01" />
      <path d="M12 14h.01" />
      <path d="M16 14h.01" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3v12" />
      <path d="m7 10 5 5 5-5" />
      <path d="M5 21h14" />
    </svg>
  );
}

function MicrophoneIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0" />
      <path d="M12 18v3" />
    </svg>
  );
}

function ProfileIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="8" r="4" />
      <path d="M5 21a7 7 0 0 1 14 0" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M6 6l1 14h10l1-14" />
      <path d="M10 11v5" />
      <path d="M14 11v5" />
    </svg>
  );
}

function CvDocumentIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 3h7l4 4v14H7z" />
      <path d="M14 3v5h5" />
      <path d="M10 12h5" />
      <path d="M10 15h3" />
      <path d="M16.5 14.5l2 2" />
      <path d="M18.8 12.2a1.6 1.6 0 0 1 2.2 2.2l-4.8 4.8-2.5.5.5-2.5 4.6-5Z" />
    </svg>
  );
}

function InterviewIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 14a4 4 0 0 0 4-4V7a4 4 0 0 0-8 0v3a4 4 0 0 0 4 4Z" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <path d="M12 17v4" />
      <path d="M8.5 21h7" />
      <path d="M18 5.5h2.5v4H18" />
      <path d="M6 5.5H3.5v4H6" />
    </svg>
  );
}

function formatGeneratedDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat("it-IT", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [showTransition, setShowTransition] = useState(false);
  const [step, setStep] = useState("auth");
  const [authMode, setAuthMode] = useState("login");

  const [userId, setUserId] = useState(null);
  const [authToken, setAuthToken] = useState(() => localStorage.getItem(AUTH_TOKEN_KEY) || "");
  const [authMessage, setAuthMessage] = useState("");
  const [previewLink, setPreviewLink] = useState("");
  const [visiblePasswords, setVisiblePasswords] = useState({});

  const [authForm, setAuthForm] = useState({
    name: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
    identifier: "",
    newPassword: ""
  });

  const [profile, setProfile] = useState(getDefaultProfile);

  const [cvFile, setCvFile] = useState(null);
  const [cvPreview, setCvPreview] = useState(null);
  const [isCvDragging, setIsCvDragging] = useState(false);
  const cvFileInputRef = useRef(null);
  const linkedinFileInputRef = useRef(null);
  const chatContainerRef = useRef(null);
  const answerRef = useRef(null);
  const profileImageInputRef = useRef(null);
  const screenshotAnalysisQueueRef = useRef([]);
  const screenshotAnalysisRunningRef = useRef(false);
  const screenshotQueueGenerationRef = useRef(0);
  const screenshotFileInputRef = useRef(null);
  const selectedScreenshotFilesRef = useRef([]);
  const [linkedinUploadMessage, setLinkedinUploadMessage] = useState("");
  const [socialScreenshotMessages, setSocialScreenshotMessages] = useState({});
  const [selectedScreenshotFiles, setSelectedScreenshotFiles] = useState([]);
  const [screenshotAnalysisProgress, setScreenshotAnalysisProgress] = useState({
    active: false,
    fileCount: 0,
    queuedCount: 0,
    elapsedSeconds: 0,
    profileType: "",
  });
  const [cvValidation, setCvValidation] = useState({
    status: "idle",
    message: "",
    confidence: 0,
    detectedSections: [],
  });
  const [digitalPresence, setDigitalPresence] = useState({
    linkedin_url: "",
    portfolio_url: "",
    instagram_handle: "",
  });
  const [digitalAnalysis, setDigitalAnalysis] = useState(null);
  const [cvOptimizationAnalysis, setCvOptimizationAnalysis] = useState(null);
  const [cvOptimizationStage, setCvOptimizationStage] = useState(0);
  const [optimizedCv, setOptimizedCv] = useState(null);
  const [optimizedCvWarnings, setOptimizedCvWarnings] = useState([]);
  const [optimizedCvsList, setOptimizedCvsList] = useState([]);
  const [showOptimizedCvVersions, setShowOptimizedCvVersions] = useState(false);
  const [cvAdditionalData, setCvAdditionalData] = useState(getEmptyCvAdditionalData);
  const [cvAdaptationAnswers, setCvAdaptationAnswers] = useState({});
  const [selectedCoachSuggestions, setSelectedCoachSuggestions] = useState({});
  const [confirmedSkillDetails, setConfirmedSkillDetails] = useState({});
  const [expandedCoachSuggestionText, setExpandedCoachSuggestionText] = useState({});
  const [cvAdditionalDataError, setCvAdditionalDataError] = useState("");
  const [cvFieldErrors, setCvFieldErrors] = useState({
    additional: {},
    adaptation: {},
  });
  const [loadingMessage, setLoadingMessage] = useState("");
  const [jobValidation, setJobValidation] = useState({
    status: "idle",
    errors: {},
    warnings: [],
    message: "",
  });
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [profileImageSaving, setProfileImageSaving] = useState(false);
  const [profileImageMessage, setProfileImageMessage] = useState("");
  const [stepHistory, setStepHistory] = useState([]);

  const [interviewType, setInterviewType] = useState("conoscitive_motivazionali");
  const [difficulty, setDifficulty] = useState("intermedio");

  const [company, setCompany] = useState("Azienda Generica");
  const [personalizeIntent, setPersonalizeIntent] = useState("interview");
  const [personalizeForm, setPersonalizeForm] = useState({
    goal: "",
    company: "",
    role: "",
    role_level: "",
    sector: "",
    link: "",
  });
  const [questionMode] = useState("web");

  const [questions, setQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [allFeedbacks, setAllFeedbacks] = useState([]);

  const [questionId, setQuestionId] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  const [, setAnswerMode] = useState("text");
  const [isListening, setIsListening] = useState(false);
  const [speechMetrics, setSpeechMetrics] = useState(null);

  const [feedback, setFeedback] = useState(null);
  const [history, setHistory] = useState([]);
  const [expandedHistorySessions, setExpandedHistorySessions] = useState([]);
  const [expandedHistoryQuestions, setExpandedHistoryQuestions] = useState([]);
  const [progress, setProgress] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Stati per l'effetto typewriter e la voce AI
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    // Ogni volta che compare una nuova domanda o entriamo nello step "question"
    if (step === "question" && question && !showTransition) {
      window.speechSynthesis.cancel(); // Interrompi voci precedenti
      setDisplayedText("");
      setIsSpeaking(true);

      // Effetto Typewriter: rivela un carattere alla volta
      let i = 0;
      const typewriter = setInterval(() => {
        setDisplayedText(question.substring(0, i + 1));
        i++;
        if (i >= question.length) clearInterval(typewriter);
      }, 60); // Velocità di comparsa del testo

      // Sintesi Vocale (TTS)
      try {
        const utter = new SpeechSynthesisUtterance(question);
        utter.lang = "it-IT";
        utter.rate = 0.95; // Velocità naturale
        utter.onend = () => setIsSpeaking(false);
        window.speechSynthesis.speak(utter);
      } catch {
        setIsSpeaking(false);
      }

      return () => {
        clearInterval(typewriter);
        window.speechSynthesis.cancel();
      };
    } else if (step === "question" && showTransition) {
      setDisplayedText("");
      setIsSpeaking(false);
    }
  }, [question, step, showTransition]);

  useEffect(() => {
    if (step === "question" && chatContainerRef.current) {
      // Determiniamo se l'AI sta scrivendo per decidere se lo scroll deve essere fluido o immediato
      const isTyping = displayedText.length > 0 && displayedText.length < (question?.length || 0);
      
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: isTyping ? "auto" : "smooth"
      });
    }
  }, [allFeedbacks, question, displayedText, step, loading]);

  useEffect(() => {
    if (step === "question" && answerRef.current) {
      answerRef.current.style.height = "auto";
      answerRef.current.style.height = `${answerRef.current.scrollHeight}px`;
    }
  }, [answer, step]);

  useEffect(() => {
    const splashTimer = setTimeout(() => {
      setShowSplash(false);
    }, INTRO_SPLASH_DURATION_MS);

    return () => clearTimeout(splashTimer);
  }, []);

  useEffect(() => {
    let transitionTimer;

    if (loading) {
      setShowTransition(step !== "question" && step !== "interview-summary"); 
      return () => clearTimeout(transitionTimer);
    }

    transitionTimer = setTimeout(() => {
      setShowTransition(false);
    }, TRANSITION_DURATION_MS);

    return () => clearTimeout(transitionTimer);
  }, [loading]);

  useEffect(() => {
    if (!screenshotAnalysisProgress.active) {
      return undefined;
    }

    const timer = setInterval(() => {
      setScreenshotAnalysisProgress((current) => ({
        ...current,
        elapsedSeconds: current.elapsedSeconds + 1,
      }));
    }, 1000);

    return () => clearInterval(timer);
  }, [screenshotAnalysisProgress.active]);

  useEffect(() => {
    if (step === "cv-digital") {
      return;
    }

    screenshotQueueGenerationRef.current += 1;
    screenshotAnalysisQueueRef.current = [];
    setSelectedScreenshotFiles((current) => {
      current.forEach((item) => URL.revokeObjectURL(item.previewUrl));
      return [];
    });
    setSocialScreenshotMessages({});
    setScreenshotAnalysisProgress({
      active: false,
      fileCount: 0,
      queuedCount: 0,
      elapsedSeconds: 0,
      profileType: "",
    });
    if (screenshotFileInputRef.current) {
      screenshotFileInputRef.current.value = "";
    }
  }, [step]);

  useEffect(() => {
    selectedScreenshotFilesRef.current = selectedScreenshotFiles;
  }, [selectedScreenshotFiles]);

  useEffect(() => () => {
    selectedScreenshotFilesRef.current.forEach((item) => {
      URL.revokeObjectURL(item.previewUrl);
    });
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const verifyToken = params.get("verify");
    const resetToken = params.get("reset");
    const oauthToken = params.get("oauth_token");

    if (oauthToken) {
      localStorage.setItem(AUTH_TOKEN_KEY, oauthToken);
      setAuthToken(oauthToken);
      loadSession(oauthToken);
      window.history.replaceState({}, document.title, window.location.pathname);
      return;
    }

    if (verifyToken) {
      verifyEmail(verifyToken);
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    if (resetToken) {
      setAuthMode("reset");
      setAuthForm((current) => ({ ...current, resetToken }));
      setStep("auth");
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  useEffect(() => {
    if (!authToken) {
      return;
    }

    loadSession(authToken);
  }, []);

  useEffect(() => {
    if (step !== "cv-view" || !userId || !profile.cv_filename) {
      return;
    }

    const loadCvFile = async () => {
      resetError();

      try {
        const response = await fetchWithTimeout(`${API_URL}/users/${userId}/cv-file`, {}, 15000);
        const data = await response.json();

        if (!response.ok) {
          handleApiFailure(response, data, "CV non trovato.");
          return;
        }

        setCvPreview(data);
      } catch (err) {
        console.error(err);
        setError("Errore nel caricamento dell'anteprima del CV.");
      }
    };

    loadCvFile();
  }, [step, userId, profile.cv_filename]);

  useEffect(() => {
    if (!userId) {
      return;
    }
    loadOptimizedCvsList(userId);
  }, [userId]);

  useEffect(() => {
    const handleBrowserBack = (event) => {
      resetError();
      setIsProfileMenuOpen(false);
      setShowTransition(false);

      if (!authToken || !userId) {
        setStep("auth");
        return;
      }

      setStep(event.state?.careerCoachStep || "home");
    };

    window.addEventListener("popstate", handleBrowserBack);

    return () => window.removeEventListener("popstate", handleBrowserBack);
  }, [authToken, userId]);

  const updateAuthForm = (field, value) => {
    setAuthForm({
      ...authForm,
      [field]: value,
    });
  };

  const togglePasswordVisibility = (field) => {
    setVisiblePasswords((current) => ({
      ...current,
      [field]: !current[field],
    }));
  };

  const socialLogin = async (provider) => {
    resetError();
    setLoading(true);
    let isRedirecting = false;

    try {
      const frontendOrigin = typeof window !== "undefined" ? window.location.origin : "";
      const oauthUrl = `${API_URL}/auth/oauth/${provider}/url?frontend_origin=${encodeURIComponent(frontendOrigin)}`;
      const response = await fetchWithTimeout(oauthUrl, {}, 10000);
      const data = await response.json();

      if (!response.ok) {
        setError(
          typeof data.detail === "string"
            ? data.detail
            : "Accesso social non configurato."
        );
        return;
      }

      isRedirecting = true;
      await wait(TRANSITION_DURATION_MS);
      window.location.href = data.auth_url;
    } catch (err) {
      console.error(err);
      setError("Errore nell'avvio dell'accesso social. Controlla che il backend sia avviato.");
    } finally {
      if (!isRedirecting) {
        setLoading(false);
      }
    }
  };

  const resetError = () => {
    setError("");
    setAuthMessage("");
    setPreviewLink("");
  };

  const resetClientSession = (message = "") => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    setAuthToken("");
    setUserId(null);
    setProfile(getDefaultProfile());
    setDigitalPresence({ linkedin_url: "", portfolio_url: "", instagram_handle: "" });
    setDigitalAnalysis(null);
    setCvPreview(null);
    setOptimizedCvsList([]);
    setQuestions([]);
    setAllFeedbacks([]);
    setHistory([]);
    setProgress(null);
    window.history.replaceState({ careerCoachStep: "auth" }, "", window.location.pathname);
    setStep("auth");
    setError(message || "La sessione non è più valida. Accedi di nuovo per continuare.");
  };

  const handleApiFailure = (response, data, fallback = "Operazione non completata.") => {
    const detail = getFriendlyApiErrorMessage(getApiErrorDetail(data, fallback), response?.status || 0);
    if (response?.status === 401 || response?.status === 403) {
      resetClientSession(detail);
      return true;
    }
    setError(detail);
    return true;
  };

  const transitionToStep = (nextStep) => {
    resetError();
    setIsProfileMenuOpen(false);
    setShowTransition(true);
    window.history.pushState({ careerCoachStep: nextStep }, "", window.location.pathname);
    setStepHistory((current) =>
      current[current.length - 1] === step ? current : [...current, step].slice(-12)
    );

    setTimeout(() => {
      setStep(nextStep);
      setShowTransition(false);
    }, TRANSITION_DURATION_MS);
  };

  const goBack = () => {
    resetError();
    setIsProfileMenuOpen(false);
    const previousStep = stepHistory[stepHistory.length - 1];

    if (!previousStep) {
      const fallbackStep = isProfileComplete(profile) ? "home" : "cv-upload";
      window.history.pushState({ careerCoachStep: fallbackStep }, "", window.location.pathname);
      setStep(fallbackStep);
      return;
    }

    setStepHistory((current) => current.slice(0, -1));
    window.history.pushState({ careerCoachStep: previousStep }, "", window.location.pathname);
    setStep(previousStep);
  };

  const applyAuthenticatedUser = (token, user) => {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    setAuthToken(token);
    setUserId(user.id);
    setProfile({
      name: user.name || "",
      email: user.email || "",
      phone: user.phone || "",
      education: user.education || "",
      target_role: user.target_role || "",
      sector: user.sector || "",
      experience_level: user.experience_level || "Junior",
      interview_language: user.interview_language || "Italiano",
      cv_filename: user.cv_filename || "",
      cv_uploaded: Boolean(user.cv_uploaded),
      cv_text: user.cv_text || "",
      linkedin_url: user.linkedin_url || "",
      linkedin_profile_filename: user.linkedin_profile_filename || "",
      linkedin_profile_uploaded: Boolean(user.linkedin_profile_uploaded),
      portfolio_url: user.portfolio_url || "",
      instagram_handle: user.instagram_handle || "",
      auth_provider: user.auth_provider || "",
    });
    setDigitalPresence({
      linkedin_url: user.linkedin_url || "",
      portfolio_url: user.portfolio_url || "",
      instagram_handle: user.instagram_handle || "",
    });
    setDigitalAnalysis(normalizeDigitalAnalysis(user.digital_analysis || null));
    setPersonalizeForm({
      goal: "",
      company: "",
      role: "",
      role_level: "",
      sector: "",
      link: "",
    });
    setCompany("Azienda Generica");
    setCvOptimizationAnalysis(null);
    setOptimizedCv(null);
    setOptimizedCvWarnings([]);
    setSelectedCoachSuggestions({});
    setCvAdaptationAnswers({});
    setCvAdditionalData(getEmptyCvAdditionalData());
    setConfirmedSkillDetails({});
    setExpandedCoachSuggestionText({});
    setQuestions([]);
    setAllFeedbacks([]);
    setStepHistory([]);
    const firstStep = isProfileComplete(user) ? "home" : "cv-upload";
    window.history.replaceState({ careerCoachStep: firstStep }, "", window.location.pathname);
    setStep(firstStep);
  };

  const loadSession = async (token) => {
    try {
      const response = await fetchWithTimeout(`${API_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }, 15000);

      const data = await response.json();

      if (!response.ok) {
        resetClientSession(getFriendlyApiErrorMessage(getApiErrorDetail(data, "Sessione non valida."), response.status));
        return;
      }

      applyAuthenticatedUser(token, data.user);
    } catch (err) {
      console.error(err);
    }
  };

  const registerUser = async () => {
    resetError();

    if (!authForm.name.trim()) {
      setError("Inserisci il nome.");
      return;
    }

    if (!authForm.email.trim()) {
      setError("Inserisci l'email.");
      return;
    }

    if (authForm.password !== authForm.confirmPassword) {
      setError("Le password non coincidono.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          name: authForm.name,
          email: authForm.email,
          phone: authForm.phone,
          password: authForm.password
        })
      }, 15000);

      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nella registrazione.");
        return;
      }

      setAuthMessage(data.message || "Account creato. Controlla la tua email.");
      setPreviewLink(data.preview_link || "");
      setAuthMode("login");
    } catch (err) {
      console.error(err);
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const loginUser = async () => {
    resetError();

    if (!authForm.identifier.trim() || !authForm.password.trim()) {
      setError("Inserisci email/telefono e password.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          identifier: authForm.identifier,
          password: authForm.password
        })
      }, 15000);

      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nell'accesso.");
        return;
      }

      applyAuthenticatedUser(data.token, data.user);
    } catch (err) {
      console.error(err);
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const verifyEmail = async (token) => {
    resetError();
    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/auth/verify-email`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ token })
      }, 15000);

      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Verifica email non riuscita.");
        setStep("auth");
        return;
      }

      setAuthMessage(data.message || "Email verificata.");
      applyAuthenticatedUser(data.token, data.user);
    } catch (err) {
      console.error(err);
      setError("Errore durante la verifica email.");
      setStep("auth");
    } finally {
      setLoading(false);
    }
  };

  const requestPasswordReset = async () => {
    resetError();

    if (!authForm.identifier.trim()) {
      setError("Inserisci email o numero associato all'account.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/auth/forgot-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ identifier: authForm.identifier })
      }, 15000);

      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nel recupero password.");
        return;
      }

      setAuthMessage(data.message);
      setPreviewLink(data.preview_link || "");
    } catch (err) {
      console.error(err);
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const resetPassword = async () => {
    resetError();

    if (!authForm.newPassword.trim()) {
      setError("Inserisci una nuova password.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/auth/reset-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          token: authForm.resetToken,
          password: authForm.newPassword
        })
      }, 15000);

      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nel reset password.");
        return;
      }

      setAuthMessage(data.message);
      setAuthMode("login");
    } catch (err) {
      console.error(err);
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const logoutUser = async () => {
    const token = authToken;
    localStorage.removeItem(AUTH_TOKEN_KEY);
    setAuthToken("");
    setUserId(null);
    setIsProfileMenuOpen(false);
    setStepHistory([]);
    transitionToStep("auth");

    if (token) {
      try {
        await fetchWithTimeout(`${API_URL}/auth/logout`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ token })
        }, 10000);
      } catch (err) {
        console.error(err);
      }
    }
  };

  const updateProfileImage = (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    setProfileImageMessage("");

    if (!file) {
      return;
    }

    const allowedImageTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!allowedImageTypes.includes(file.type)) {
      setProfileImageMessage("Seleziona un'immagine JPG, PNG o WEBP valida.");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setProfileImageMessage("La foto profilo deve essere inferiore a 2 MB.");
      return;
    }

    const previousImage = profile.profile_image_data_url || null;
    const reader = new FileReader();
    reader.onload = async () => {
      const imageDataUrl = String(reader.result || "");
      setProfile((current) => ({ ...current, profile_image_data_url: imageDataUrl }));
      setProfileImageSaving(true);

      try {
        const response = await fetchWithApiFallbacks(`/users/${userId}/profile-image`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${authToken}`,
          },
          body: JSON.stringify({ image_data_url: imageDataUrl }),
        }, 15000);
        const responseText = await response.text();
        let data = {};
        try {
          data = responseText ? JSON.parse(responseText) : {};
        } catch {
          if (!response.ok) {
            throw new Error("Errore del server durante il salvataggio della foto profilo.");
          }
          throw new Error("Il server ha restituito una risposta non valida.");
        }
        if (!response.ok) {
          throw new Error(data.detail || "Impossibile salvare la foto profilo.");
        }
        setProfile((current) => ({
          ...current,
          profile_image_data_url: data.profile_image_data_url,
        }));
        setProfileImageMessage("Foto profilo aggiornata.");
      } catch (err) {
        setProfile((current) => ({ ...current, profile_image_data_url: previousImage }));
        const message = err?.message && /fetch/i.test(err.message)
          ? "Backend non raggiungibile. Verifica che FastAPI sia attivo su 8000."
          : err?.message || "Impossibile salvare la foto profilo.";
        setProfileImageMessage(message);
      } finally {
        setProfileImageSaving(false);
      }
    };
    reader.onerror = () => {
      setProfileImageMessage("Impossibile leggere l'immagine selezionata.");
    };
    reader.readAsDataURL(file);
  };

  const removeProfileImage = async () => {
    const previousImage = profile.profile_image_data_url;
    setProfileImageMessage("");
    setProfile((current) => ({ ...current, profile_image_data_url: null }));
    setProfileImageSaving(true);

    try {
      const response = await fetchWithApiFallbacks(`/users/${userId}/profile-image`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      }, 15000);
      const responseText = await response.text();
      let data = {};
      try {
        data = responseText ? JSON.parse(responseText) : {};
      } catch {
        if (!response.ok) {
          throw new Error("Errore del server durante la rimozione della foto profilo.");
        }
        throw new Error("Il server ha restituito una risposta non valida.");
      }
      if (!response.ok) {
        throw new Error(data.detail || "Impossibile rimuovere la foto profilo.");
      }
      setProfileImageMessage("Foto profilo rimossa.");
    } catch (err) {
      setProfile((current) => ({ ...current, profile_image_data_url: previousImage }));
      const message = err?.message && /fetch/i.test(err.message)
        ? "Backend non raggiungibile. Verifica che FastAPI sia attivo su 8000."
        : err?.message || "Impossibile rimuovere la foto profilo.";
      setProfileImageMessage(message);
    } finally {
      setProfileImageSaving(false);
    }
  };

  const deleteProfile = async () => {
    resetError();

    const confirmed = window.confirm(
      "Vuoi eliminare definitivamente il profilo? Verranno rimossi account, CV e storico colloqui."
    );

    if (!confirmed) {
      return;
    }

    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/users/${userId}`, {
        method: "DELETE",
      }, 15000);
      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nell'eliminazione del profilo.");
        return;
      }

      localStorage.removeItem(AUTH_TOKEN_KEY);
      setAuthToken("");
      setUserId(null);
      setProfile({
        name: "",
        email: "",
        phone: "",
        education: "",
        target_role: "",
        sector: "",
        experience_level: "Junior",
        interview_language: "Italiano",
        cv_filename: "",
        cv_uploaded: false,
        cv_text: "",
        linkedin_url: "",
        linkedin_profile_filename: "",
        linkedin_profile_uploaded: false,
        portfolio_url: "",
        instagram_handle: "",
      });
      setDigitalPresence({
        linkedin_url: "",
        portfolio_url: "",
        instagram_handle: "",
      });
      setDigitalAnalysis(null);
      setCvFile(null);
      setCvPreview(null);
      setHistory([]);
      setProgress(null);
      setStepHistory([]);
      window.history.replaceState({ careerCoachStep: "auth" }, "", window.location.pathname);
      setStep("auth");
    } catch (err) {
      console.error(err);
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const renderPasswordField = (field, value, placeholder, autoComplete) => (
    <div className="password-field">
      <input
        type={visiblePasswords[field] ? "text" : "password"}
        value={value}
        onChange={(e) => updateAuthForm(field, e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
      />
      <button type="button" onClick={() => togglePasswordVisibility(field)}>
        {visiblePasswords[field] ? "Nascondi" : "Mostra"}
      </button>
    </div>
  );

  const readCvText = (file) =>
    new Promise((resolve) => {
      if (!file || file.type !== "text/plain") {
        resolve("");
        return;
      }

      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ""));
      reader.onerror = () => resolve("");
      reader.readAsText(file);
    });

  const readFileBase64 = (file) =>
    new Promise((resolve) => {
      if (!file) {
        resolve("");
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        const result = String(reader.result || "");
        resolve(result.includes(",") ? result.split(",")[1] : result);
      };
      reader.onerror = () => resolve("");
      reader.readAsDataURL(file);
    });

  const resetCvValidation = () => {
    setCvValidation({
      status: "idle",
      message: "",
      confidence: 0,
      detectedSections: [],
    });
  };

  const selectCvFile = async (file) => {
    resetError();
    setCvFile(null);
    resetCvValidation();

    if (!file) {
      return;
    }

    const extension = file.name.split(".").pop()?.toLowerCase();
    const allowedExtensions = ["pdf", "docx"];

    if (!allowedExtensions.includes(extension)) {
      setError("Carica un file PDF o DOCX.");
      if (cvFileInputRef.current) {
        cvFileInputRef.current.value = "";
      }
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError("Il CV non puo superare 5MB.");
      if (cvFileInputRef.current) {
        cvFileInputRef.current.value = "";
      }
      return;
    }

    setCvValidation({
      status: "validating",
      message: "Verifica del CV in corso...",
      confidence: 0,
      detectedSections: [],
    });

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetchWithTimeout(`${API_URL}/validate-cv-file`, {
        method: "POST",
        body: formData,
      }, 45000);
      const data = await response.json();

      if (!response.ok) {
        const detail = typeof data.detail === "string"
          ? data.detail
          : "Il file caricato non sembra leggibile o non sembra essere un CV.";
        setCvValidation({
          status: "invalid",
          message: `Il file caricato non sembra leggibile o non sembra essere un CV. Dettaglio: ${detail}`,
          confidence: 0,
          detectedSections: [],
        });
        if (cvFileInputRef.current) {
          cvFileInputRef.current.value = "";
        }
        return;
      }

      if (!data.is_cv) {
        const detail = data.reason || "Carica un CV valido in formato PDF o DOCX.";
        setCvValidation({
          status: "invalid",
          message: `Il file caricato non sembra leggibile o non sembra essere un CV. Dettaglio: ${detail}`,
          confidence: data.confidence || 0,
          detectedSections: data.detected_sections || [],
        });
        if (cvFileInputRef.current) {
          cvFileInputRef.current.value = "";
        }
        return;
      }

      setCvFile(file);
      setCvOptimizationAnalysis(null);
      setOptimizedCv(null);
      setOptimizedCvWarnings([]);
      setSelectedCoachSuggestions({});
      setCvAdaptationAnswers({});
      setCvAdditionalData(getEmptyCvAdditionalData());
      setConfirmedSkillDetails({});
      setExpandedCoachSuggestionText({});
      setCvValidation({
        status: "valid",
        message: "CV riconosciuto correttamente.",
        confidence: data.confidence || 0,
        detectedSections: data.detected_sections || [],
      });
    } catch (err) {
      console.error(err);
      setCvValidation({
        status: "invalid",
        message: "Non siamo riusciti a verificare il contenuto del file. Riprova con un CV valido in formato PDF o DOCX.",
        confidence: 0,
        detectedSections: [],
      });
      if (cvFileInputRef.current) {
        cvFileInputRef.current.value = "";
      }
    }
  };

  const removeSelectedCvFile = () => {
    resetError();
    setCvFile(null);
    resetCvValidation();

    if (cvFileInputRef.current) {
      cvFileInputRef.current.value = "";
    }
  };

  const uploadCv = async () => {
    resetError();

    if (!cvFile || cvValidation.status !== "valid") {
      setError("Carica un CV valido prima di continuare.");
      return;
    }

    setLoading(true);

    try {
      const text = await readCvText(cvFile);
      const fileBase64 = await readFileBase64(cvFile);
      const response = await fetchWithTimeout(`${API_URL}/users/${userId}/cv`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          filename: cvFile.name,
          content_type: cvFile.type || "application/octet-stream",
          size: cvFile.size,
          text,
          file_base64: fileBase64
        })
      }, 15000);

      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nel caricamento del CV.");
        return;
      }

      const updatedUser = data.user;
      setProfile((current) => ({
        ...current,
        ...updatedUser,
        cv_uploaded: Boolean(updatedUser.cv_uploaded),
      }));
      setDigitalPresence({
        linkedin_url: updatedUser.linkedin_url || "",
        portfolio_url: updatedUser.portfolio_url || "",
        instagram_handle: updatedUser.instagram_handle || "",
      });
      setCvFile(null);
      setCvPreview(null);
      transitionToStep("cv-digital");
    } catch (err) {
      console.error(err);
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const updateDigitalPresence = (field, value) => {
    setDigitalPresence((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const uploadLinkedinProfile = async (file) => {
    resetError();
    setLinkedinUploadMessage("");

    if (!file) {
      return;
    }

    const extension = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "docx"].includes(extension)) {
      setError("Carica l'esportazione LinkedIn in formato PDF o DOCX.");
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetchWithTimeout(`${API_URL}/users/${userId}/linkedin-profile`, {
        method: "POST",
        body: formData,
      }, 45000);
      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nel caricamento del profilo LinkedIn.");
        return;
      }

      setProfile((current) => ({
        ...current,
        ...data.user,
      }));
      setLinkedinUploadMessage("Esportazione LinkedIn pronta per il confronto con il CV.");
    } catch (err) {
      console.error(err);
      setError("Errore nel caricamento dell'esportazione LinkedIn.");
    } finally {
      setLoading(false);
      if (linkedinFileInputRef.current) {
        linkedinFileInputRef.current.value = "";
      }
    }
  };

  const deleteLinkedinProfile = async () => {
    resetError();
    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/users/${userId}/linkedin-profile`, {
        method: "DELETE",
      }, 15000);
      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nella rimozione del profilo LinkedIn.");
        return;
      }

      setProfile((current) => ({
        ...current,
        ...data.user,
      }));
      setLinkedinUploadMessage("Esportazione LinkedIn rimossa.");
    } catch (err) {
      console.error(err);
      setError("Errore nella rimozione dell'esportazione LinkedIn.");
    } finally {
      setLoading(false);
    }
  };

  const analyzeDigitalPresence = async () => {
    resetError();

    if (!canAnalyzeDigitalPresence) {
      return;
    }

    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/users/${userId}/digital-presence`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          ...digitalPresence,
          target_role: personalizeForm.role.trim() || profile.target_role || "",
          linkedin_connected: isLinkedInConnected,
        })
      }, 60000);

      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nel salvataggio dei profili digitali.");
        return;
      }

      setProfile((current) => ({
        ...current,
        ...data.user,
      }));
      setDigitalAnalysis(normalizeDigitalAnalysis(data.analysis || data.user?.digital_analysis || null));
      transitionToStep("cv-analysis");
    } catch (err) {
      console.error(err);
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const processSocialScreenshotQueue = async () => {
    if (screenshotAnalysisRunningRef.current) {
      return;
    }

    const processGeneration = screenshotQueueGenerationRef.current;
    screenshotAnalysisRunningRef.current = true;
    while (screenshotAnalysisQueueRef.current.length) {
      const batch = screenshotAnalysisQueueRef.current.shift();
      const batchGeneration = batch.generation;
      if (batchGeneration !== screenshotQueueGenerationRef.current) {
        continue;
      }
      const queuedCount = screenshotAnalysisQueueRef.current.reduce(
        (total, queuedBatch) => total + queuedBatch.files.length,
        0
      );
      setScreenshotAnalysisProgress({
        active: true,
        fileCount: batch.files.length,
        queuedCount,
        elapsedSeconds: 0,
        profileType: batch.profileType,
      });

      try {
        const formData = new FormData();
        formData.append("profile_type", batch.profileType);
        formData.append("instagram_handle", batch.instagramHandle);
        batch.files.forEach((file) => formData.append("files", file));
        const response = await fetchWithTimeout(`${API_URL}/users/${userId}/social-screenshots`, {
          method: "POST",
          body: formData,
        }, 300000);
        const data = await response.json();
        if (batchGeneration !== screenshotQueueGenerationRef.current) {
          continue;
        }
        if (!response.ok) {
          setError(typeof data.detail === "string" ? data.detail : "Errore nell'analisi degli screenshot.");
          continue;
        }

        setProfile((current) => ({ ...current, ...data.user }));
        setDigitalAnalysis(normalizeDigitalAnalysis(data.analysis || data.user?.digital_analysis || null));
        setSocialScreenshotMessages((current) => ({
          ...current,
          [batch.profileType]: data.message || "Screenshot analizzati.",
        }));
      } catch (err) {
        if (batchGeneration !== screenshotQueueGenerationRef.current) {
          continue;
        }
        console.error(err);
        setError(
          err?.name === "AbortError"
            ? "L'analisi locale degli screenshot sta richiedendo troppo tempo. Prova con meno immagini."
            : "Errore di connessione durante l'analisi degli screenshot. Controlla che FastAPI e Ollama siano avviati."
        );
      }
    }

    screenshotAnalysisRunningRef.current = false;
    if (processGeneration !== screenshotQueueGenerationRef.current) {
      return;
    }
    setScreenshotAnalysisProgress({
      active: false,
      fileCount: 0,
      queuedCount: 0,
      elapsedSeconds: 0,
      profileType: "",
    });
  };

  const analyzeSocialScreenshots = (profileType, files) => {
    resetError();

    const selectedFiles = Array.from(files || []);
    if (!selectedFiles.length) {
      return;
    }

    screenshotAnalysisQueueRef.current.push({
      profileType,
      files: selectedFiles,
      instagramHandle: digitalPresence.instagram_handle.trim(),
      generation: screenshotQueueGenerationRef.current,
    });
    const queuedCount = screenshotAnalysisQueueRef.current.reduce(
      (total, batch) => total + batch.files.length,
      0
    );
    setScreenshotAnalysisProgress((current) => ({
      ...current,
      active: true,
      queuedCount: screenshotAnalysisRunningRef.current
        ? current.queuedCount + selectedFiles.length
        : Math.max(0, queuedCount - selectedFiles.length),
    }));
    setSocialScreenshotMessages((current) => ({
      ...current,
      [profileType]: screenshotAnalysisRunningRef.current
        ? `${selectedFiles.length} ${selectedFiles.length === 1 ? "immagine aggiunta" : "immagini aggiunte"} alla coda.`
        : "",
    }));
    processSocialScreenshotQueue();
  };

  const addSelectedScreenshotFiles = (files) => {
    resetError();
    const imageFiles = Array.from(files || []).filter((file) =>
      (file?.type || "").startsWith("image/")
    );
    if (!imageFiles.length) {
      setSocialScreenshotMessages((current) => ({
        ...current,
        instagram: "Seleziona immagini PNG, JPG o WebP.",
      }));
      return;
    }

    setSelectedScreenshotFiles((current) => {
      const existingKeys = new Set(
        current.map((item) => `${item.file.name}:${item.file.size}:${item.file.lastModified}`)
      );
      const availableSlots = Math.max(0, 8 - current.length);
      const additions = imageFiles
        .filter((file) => !existingKeys.has(`${file.name}:${file.size}:${file.lastModified}`))
        .slice(0, availableSlots)
        .map((file) => ({
          id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2)}`,
          file,
          previewUrl: URL.createObjectURL(file),
        }));
      return [...current, ...additions];
    });
    setSocialScreenshotMessages((current) => ({ ...current, instagram: "" }));
  };

  const removeSelectedScreenshotFile = (fileId) => {
    setSelectedScreenshotFiles((current) => {
      const removed = current.find((item) => item.id === fileId);
      if (removed) {
        URL.revokeObjectURL(removed.previewUrl);
      }
      return current.filter((item) => item.id !== fileId);
    });
  };

  const submitSelectedScreenshots = () => {
    if (!selectedScreenshotFiles.length) {
      return;
    }
    const files = selectedScreenshotFiles.map((item) => item.file);
    selectedScreenshotFiles.forEach((item) => URL.revokeObjectURL(item.previewUrl));
    setSelectedScreenshotFiles([]);
    if (screenshotFileInputRef.current) {
      screenshotFileInputRef.current.value = "";
    }
    analyzeSocialScreenshots("instagram", files);
  };

  const analyzeCvOptimization = async (profileOverride = profile, fileOverride = null, targetOverride = null) => {
    resetError();
    setOptimizedCv(null);

    if (!profileOverride.cv_uploaded && !profileOverride.cv_filename) {
      setError("Carica un CV prima di avviare l'analisi strategica.");
      transitionToStep("cv-upload");
      return;
    }

    setLoading(true);

    try {
      const requestPayload = {
        description: personalizeForm.goal.trim(),
        company: targetOverride?.company ?? (personalizeForm.company.trim() || (company === "Azienda Generica" ? "" : company)),
        role: targetOverride?.role ?? (personalizeForm.role.trim() || profileOverride.target_role || ""),
        role_level: personalizeForm.role_level.trim(),
        sector: personalizeForm.sector.trim() || profile.sector || "",
        link: personalizeForm.link.trim(),
      };

      let response;
      if (fileOverride) {
        const nameParts = getProfileNameParts();
        const formData = new FormData();
        formData.append("file", fileOverride);
        formData.append("user_first_name", nameParts.firstName);
        formData.append("user_last_name", nameParts.lastName);
        formData.append("description", requestPayload.description);
        formData.append("company", requestPayload.company);
        formData.append("role", requestPayload.role);
        formData.append("role_level", requestPayload.role_level);
        formData.append("sector", requestPayload.sector);
        formData.append("link", requestPayload.link);

        response = await fetchWithTimeout(`${API_URL}/cv/analyze-for-job`, {
          method: "POST",
          body: formData,
        }, 180000);
      } else {
        response = await fetchWithTimeout(`${API_URL}/users/${userId}/cv/analyze-for-job`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(requestPayload)
        }, 180000);
      }

      const data = await response.json();

      if (!response.ok) {
        handleApiFailure(response, data, "Errore nell'analisi del CV.");
        return;
      }

      const nextAnalysis = {
        ...(data.cv_evaluation || {}),
        cv_fingerprint: data.cv_fingerprint || "",
        target: {
          company: requestPayload.company,
          role: requestPayload.role,
        },
        identity_check: data.identity_check,
        job_validation: data.job_validation,
        warnings: (data.warnings || []).filter((warning) => !String(warning).toLowerCase().includes("verificare la coerenza")),
      };
      setCvOptimizationAnalysis(nextAnalysis);
      setCvOptimizationStage(0);
      const nextCoachSuggestions = getCoachSuggestionsFromAnalysis(nextAnalysis);
      setSelectedCoachSuggestions(getPendingCoachSuggestionStatuses(nextCoachSuggestions));
      setCvAdaptationAnswers({});
      setCvAdditionalData(getEmptyCvAdditionalData());
      setConfirmedSkillDetails({});
      setExpandedCoachSuggestionText({});
      transitionToStep("cv-strategy");
    } catch (err) {
      console.error(err);
      setError(
        err?.name === "AbortError"
          ? "L'analisi con Ollama sta richiedendo più tempo del previsto. Il backend potrebbe essere ancora attivo: riprova tra poco."
          : "Impossibile raggiungere il backend. Avvia FastAPI usando il virtual environment del progetto."
      );
    } finally {
      setLoading(false);
    }
  };

  const optimizeCv = async ({ skipAdditional = false } = {}) => {
    resetError();
    setCvAdditionalDataError("");
    setCvFieldErrors({ additional: {}, adaptation: {} });
    setOptimizedCvWarnings([]);

    if (!userId) {
      setError("Utente non autenticato. Riprova.");
      return;
    }

    if (!profile.cv_uploaded && !profile.cv_filename) {
      setError("Carica un CV prima di ottimizzarlo.");
      transitionToStep("cv-upload");
      return;
    }

    const selectedRole = personalizeForm.role.trim() || profile.target_role || "";
    if (!selectedRole || selectedRole.toLowerCase() === "da definire") {
      setError("Inserisci un ruolo target prima di ottimizzare il CV.");
      return;
    }

    const userAdditionalData = skipAdditional
      ? {}
      : {
        ...CV_ADDITIONAL_DATA_FIELDS.reduce((payload, item) => {
          const value = String(cvAdditionalData[item.key] || "").trim();
          if (!value) {
            return payload;
          }
          return {
            ...payload,
            [item.key]: value,
          };
        }, {}),
        adaptation_answers: cvOptimizationQuestions.map((question, index) => ({
          question: question.question,
          reason: question.reason,
          category: question.category,
          answer: stripRepeatedQuestionFromAnswer(
            cvAdaptationAnswers[index] || "",
            question.question
          ),
        })).filter((item) => item.answer.trim()),
      };
    const confirmedSkillPayload = acceptedSkillConfirmations.map((item) => ({
      id: item.id,
      type: item.type,
      name: item.name,
      category: item.category,
      reason: item.reason,
      already_present: item.already_present,
      requires_confirmation: item.requires_confirmation,
      status: "confirmed",
      user_example: item.user_example || "",
      detail: item.user_example || "",
      target_section: item.target_section,
    }));
    const rejectedSkillPayload = rejectedSkillConfirmations.map((item) => ({
      id: item.id,
      type: item.type,
      name: item.name,
      category: item.category,
      status: "rejected",
      target_section: item.target_section,
    }));
    const hasAdditionalInfo = (
      Object.entries(userAdditionalData).some(([key, value]) =>
        key === "adaptation_answers"
          ? Array.isArray(value) && value.length > 0
          : Boolean(String(value || "").trim())
      )
      || confirmedSkillPayload.length > 0
    );
    if (selectedCoachSuggestionItems.filter(isActionableCoachSuggestion).length === 0 && !hasAdditionalInfo) {
      setError("Non hai accettato modifiche da applicare.");
      return;
    }

    const candidateSources = cvOptimizationAnalysis?.sources || [];

    setLoading(true);
    setLoadingMessage("Sto generando il tuo CV ottimizzato...");

    try {
      const response = await fetchWithTimeout(`${API_URL}/users/${userId}/cv-optimize`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          original_cv_text: profile.cv_text || cvPreview?.text || "",
          cv_fingerprint: cvOptimizationAnalysis?.cv_fingerprint || "",
          company: personalizeForm.company.trim() || company,
          role: selectedRole,
          role_level: personalizeForm.role_level.trim(),
          goal: personalizeForm.goal.trim(),
          job_link: personalizeForm.link.trim(),
          job_data: {
            company: personalizeForm.company.trim() || company,
            role: selectedRole,
            role_level: personalizeForm.role_level.trim(),
            description: personalizeForm.goal.trim(),
            sector: personalizeForm.sector.trim() || profile.sector || "",
            application_sources: candidateSources,
          },
          cv_evaluation: cvOptimizationAnalysis,
          strategic_analysis: cvOptimizationAnalysis,
          recommended_adaptations: recommendedAdaptations,
          selected_suggestion_ids: selectedCoachSuggestionItems.filter(isActionableCoachSuggestion).map((item) => item.id),
          acceptedSuggestionIds: selectedCoachSuggestionItems.filter(isActionableCoachSuggestion).map((item) => item.id),
          rejected_suggestion_ids: rejectedCoachSuggestionItems.map((item) => item.id),
          accepted_suggestions: selectedCoachSuggestionItems.filter(isActionableCoachSuggestion),
          rejected_suggestions: rejectedCoachSuggestionItems,
          user_additional_data: userAdditionalData,
          answers: userAdditionalData.adaptation_answers || [],
          extraAnswers: userAdditionalData.adaptation_answers || [],
          confirmedSkills: confirmedSkillPayload,
          acceptedSkillConfirmations: confirmedSkillPayload,
          rejectedSkillConfirmations: rejectedSkillPayload,
        })
      }, 420000);

      const responseText = await response.text();
      let data = {};
      try {
        data = responseText ? JSON.parse(responseText) : {};
      } catch {
        data = {};
      }

      if (!response.ok) {
        const detail = typeof data.detail === "string"
          ? data.detail
          : data.detail?.message
            || data.detail?.error
            || responseText
            || "Non è stato possibile generare il CV. Controlla che il file originale sia ancora disponibile e riprova.";
        const rejectedFields = Array.isArray(data.detail?.rejected_fields)
          ? data.detail.rejected_fields
          : [];

        if (rejectedFields.length) {
          const nextFieldErrors = { additional: {}, adaptation: {} };
          rejectedFields.forEach((fieldName) => {
            const reference = getCvRejectedFieldReference(fieldName);
            if (reference?.type === "additional") {
              nextFieldErrors.additional[reference.key] = "Dettaglio troppo generico: aggiungi fatti concreti, contesto o un esempio reale.";
            }
            if (reference?.type === "adaptation") {
              nextFieldErrors.adaptation[reference.index] = "Risposta troppo generica: specifica attività, strumenti, risultati o un esempio verificabile.";
            }
          });
          setCvFieldErrors(nextFieldErrors);
          setCvAdditionalDataError("Controlla i campi evidenziati: alcuni dettagli sono troppo brevi o generici per creare un CV affidabile.");
          setCvOptimizationStage(1);
        } else {
          setError(detail);
        }
        return;
      }

      const nextOptimizedCv = data.optimizedCv || data.optimized_cv || null;
      const warningCandidates = [
        ...(data.hallucination_warnings || []),
        ...(data.format_warnings || []).map((message) => ({ claim: message, reason: "" })),
        ...(data.skipped_changes || []).map((item) => ({
          claim: item.reason || String(item),
          reason: item.applied_changes_count !== undefined ? "Modifica confermata non applicata" : "",
        })),
      ];
      const uniqueWarnings = Array.from(
        new Map(
          warningCandidates
            .filter((warning) => warning?.claim)
            .map((warning) => [`${warning.reason || ""}|${warning.claim}`, warning])
        ).values()
      );
      setOptimizedCv(nextOptimizedCv);
      setOptimizedCvWarnings(uniqueWarnings);
      if (data.optimized_analysis) {
        setCvOptimizationAnalysis((current) => ({
          ...(current || {}),
          ...data.optimized_analysis,
          sources: data.candidate_sources || current?.sources || [],
          score_comparison: data.score_comparison || null,
        }));
      }
      downloadOptimizedCvFile(nextOptimizedCv);
      await loadOptimizedCvsList(userId);
      transitionToStep("cv-optimized");
      if (data.candidate_sources?.length && !cvOptimizationAnalysis?.sources?.length) {
        setCvOptimizationAnalysis((current) => ({
          ...(current || {}),
          sources: data.candidate_sources,
        }));
      }
    } catch (err) {
      console.error(err);
      setError(
        err?.name === "AbortError"
          ? "La generazione del CV sta impiegando troppo tempo. Riprova: la richiesta è stata interrotta dopo 3 minuti e 30 secondi."
          : "Connessione al backend interrotta durante la generazione del CV. Controlla che FastAPI sia ancora avviato e riprova."
      );
    } finally {
      setLoading(false);
      setLoadingMessage("");
    }
  };

  const updateCvAdditionalData = (field, value) => {
    setCvAdditionalDataError("");
    setCvFieldErrors((current) => ({
      ...current,
      additional: {
        ...current.additional,
        [field]: "",
      },
    }));
    setCvAdditionalData((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const loadOptimizedCvsList = async (targetUserId = userId) => {
    if (!targetUserId) {
      return;
    }
    try {
      const response = await fetchWithTimeout(`${API_URL}/users/${targetUserId}/optimized-cvs`, {}, 15000);
      const data = await response.json();
      if (response.ok) {
        setOptimizedCvsList(data.optimized_cvs || []);
      } else if (response.status === 401 || response.status === 403) {
        handleApiFailure(response, data, "Non riesco a recuperare i CV ottimizzati.");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const deleteOptimizedCv = async (optimizedCvId) => {
    if (!userId || !optimizedCvId) {
      return;
    }
    setLoading(true);
    try {
      const response = await fetchWithTimeout(`${API_URL}/users/${userId}/optimized-cvs/${optimizedCvId}`, {
        method: "DELETE",
      }, 15000);
      if (response.ok) {
        await loadOptimizedCvsList(userId);
      } else {
        const data = await response.json().catch(() => ({}));
        handleApiFailure(response, data, "Non e stato possibile eliminare il CV ottimizzato.");
      }
    } catch (err) {
      console.error(err);
      setError("Errore di connessione durante l'eliminazione del CV ottimizzato.");
    } finally {
      setLoading(false);
    }
  };

  const updateCoachSuggestionStatus = (suggestionId, status) => {
    setCvAdditionalDataError("");
    setSelectedCoachSuggestions((current) => ({
      ...current,
      [suggestionId]: status,
    }));
  };

  const updateSkillConfirmation = (skillId, status) => {
    setConfirmedSkillDetails((current) => ({
      ...current,
      [skillId]: {
        ...(current[skillId] || {}),
        status,
      },
    }));
  };

  const updateSkillConfirmationDetail = (skillId, detail) => {
    setConfirmedSkillDetails((current) => ({
      ...current,
      [skillId]: {
        ...(current[skillId] || { status: "pending" }),
        user_example: detail,
      },
    }));
  };

  const toggleCoachSuggestionPreview = (suggestionId, field) => {
    const key = `${suggestionId}:${field}`;
    setExpandedCoachSuggestionText((current) => ({
      ...current,
      [key]: !current[key],
    }));
  };

  const generateQuestion = async () => {
    resetError();
    setLoading(true);

    setQuestion("");
    setAnswer("");
    setQuestionId(null);
    setFeedback(null);
    setSpeechMetrics(null);

    setQuestions([]);
    setCurrentQuestionIndex(0);
    setAllFeedbacks([]);

    const selectedCompany = personalizeForm.company.trim() || company || "Azienda Generica";
    const selectedRole = personalizeForm.role.trim() || profile.target_role || "";

    try {
      const response = await fetchWithTimeout(
        `${API_URL}/generate-question`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            user_id: userId,
            interview_type: interviewType,
            difficulty: difficulty,
            company: selectedCompany,
            goal: personalizeForm.goal.trim(),
            role: selectedRole,
            job_link: personalizeForm.link.trim(),
            question_mode: questionMode
          })
        },
        45000
      );

      let data;
      try {
        data = await response.json();
      } catch (jsonError) {
        console.error("Errore parsing JSON:", jsonError);
        setError("Il backend ha risposto, ma non ha restituito un JSON valido.");
        return;
      }

      if (!response.ok) {
        console.log("Errore backend:", data);
        setError(
          typeof data.detail === "string"
            ? data.detail
            : "Errore nella generazione della domanda."
        );
        return;
      }

      const receivedQuestions = data.questions || [
        {
          question_id: data.question_id,
          question: data.question
        }
      ];

      console.log("Domande ricevute:", receivedQuestions);

      if (!receivedQuestions.length || !receivedQuestions[0].question) {
        setError("Il backend non ha restituito domande valide.");
        return;
      }

      setQuestions(receivedQuestions);
      setCurrentQuestionIndex(0);
      setAllFeedbacks([]);

      setQuestionId(receivedQuestions[0].question_id);
      setQuestion(receivedQuestions[0].question);
      setAnswer("");
      setFeedback(null);
      setStep("question");

    } catch (err) {
      console.error("Errore generateQuestion:", err);

      if (err.name === "AbortError") {
        setError(
          "La generazione delle domande sta impiegando troppo tempo. Riprova tra poco."
        );
      } else {
        setError(
          "Errore di connessione al backend. Controlla che FastAPI sia avviato su http://127.0.0.1:8000."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const evaluateAnswer = async () => {
    resetError();

    // Disattiva il microfono se è ancora attivo al momento dell'invio
    if (isListening) {
      stopVoiceAnswer();
    }

    if (!answer.trim()) {
      setError("Scrivi o registra una risposta prima di inviarla.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/evaluate-answer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question_id: questionId,
          answer: answer,
          speech_metrics: speechMetrics
        })
      }, 30000);

      const data = await response.json();

      if (!response.ok) {
        setError(
          typeof data.detail === "string"
            ? data.detail
            : "Errore nella valutazione della risposta."
        );
        console.log(data);
        return;
      }

      setFeedback(data);

      setAllFeedbacks((prev) => [
        ...prev,
        {
          question_id: questionId,
          question: question,
          answer: answer,
          feedback: data
        }
      ]);

      // Se ci sono altre domande, passa alla prossima, altrimenti vai al riepilogo finale
      if (currentQuestionIndex < questions.length - 1) {
        const nextIndex = currentQuestionIndex + 1;
        const nextQuestion = questions[nextIndex];
        
        if (!nextQuestion) return;

        setCurrentQuestionIndex(nextIndex);
        setQuestionId(nextQuestion.question_id);
        setQuestion(nextQuestion.question);
        setAnswer("");
        setFeedback(null);
        setSpeechMetrics(null);
        setAnswerMode("text");
        // Restiamo nello step "question"
      } else {
        transitionToStep("interview-summary");
      }
    } catch (err) {
      console.error(err);

      if (err.name === "AbortError") {
        setError("La valutazione sta impiegando troppo tempo. Riprova.");
      } else {
        setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
      }
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async (navigateToHistory = true) => {
    resetError();
    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/history/${userId}`, {}, 15000);
      const data = await response.json();

      if (!response.ok) {
        setError("Errore nel caricamento dello storico.");
        console.log(data);
        return;
      }

      setHistory(data);
      if (navigateToHistory) {
        setStep("history");
      }
    } catch (err) {
      console.error(err);

      if (err.name === "AbortError") {
        setError("Il caricamento dello storico sta impiegando troppo tempo.");
      } else {
        setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (step !== "gym" || !userId || history.length > 0) {
      return;
    }

    loadHistory(false);
  }, [step, userId]);

  const startVoiceAnswer = () => {
    resetError();

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError("Il riconoscimento vocale non è supportato da questo browser. Prova con Chrome o Edge.");
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang =
      profile.interview_language === "Inglese" ? "en-US" : "it-IT";

    recognition.continuous = true;
    recognition.interimResults = true;

    let finalTranscript = answer;
    const startTime = Date.now();

    recognition.onstart = () => {
      setIsListening(true);
      // Riporta il focus sulla textarea appena il microfono si attiva.
      // Questo garantisce che il tasto Invio sulla tastiera funzioni immediatamente.
      answerRef.current?.focus();
    };

    recognition.onresult = (event) => {
      let interimTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;

        if (event.results[i].isFinal) {
          finalTranscript += " " + transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      setAnswer((finalTranscript + " " + interimTranscript).trim());
    };

    recognition.onerror = (event) => {
      setError(`Errore microfono: ${event.error}`);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);

      const endTime = Date.now();
      const duration = Math.round((endTime - startTime) / 1000);

      const metrics = analyzeSpeech(finalTranscript, duration);
      setSpeechMetrics(metrics);
    };

    recognition.start();
    window.currentRecognition = recognition;
  };

  const stopVoiceAnswer = () => {
    if (window.currentRecognition) {
      window.currentRecognition.stop();
    }
  };

  const goToNextQuestion = () => {
    resetError();

    const nextIndex = currentQuestionIndex + 1;

    if (nextIndex >= questions.length) {
      loadHistory();
      return;
    }

    const nextQuestion = questions[nextIndex];

    setCurrentQuestionIndex(nextIndex);
    setQuestionId(nextQuestion.question_id);
    setQuestion(nextQuestion.question);
    setAnswer("");
    setFeedback(null);
    setSpeechMetrics(null);
    setAnswerMode("text");
    transitionToStep("question");
  };

  const startNewTraining = () => {
    resetError();
    setQuestion("");
    setAnswer("");
    setQuestionId(null);
    setFeedback(null);
    setSpeechMetrics(null);
    setAnswerMode("text");

    setQuestions([]);
    setCurrentQuestionIndex(0);
    setAllFeedbacks([]);

    transitionToStep("gym");
  };


  const resetPersonalizationContext = () => {
    setPersonalizeForm({
      goal: "",
      company: "",
      role: "",
      role_level: "",
      sector: "",
      link: "",
    });
    setCompany("Azienda Generica");
    setJobValidation({
      status: "idle",
      errors: {},
      warnings: [],
      message: "",
    });
  };

  const resetCvOptimizationContext = () => {
    setCvOptimizationAnalysis(null);
    setCvOptimizationStage(0);
    setOptimizedCv(null);
    setOptimizedCvWarnings([]);
    setSelectedCoachSuggestions({});
    setCvAdaptationAnswers({});
    setCvAdditionalData(getEmptyCvAdditionalData());
    setConfirmedSkillDetails({});
    setExpandedCoachSuggestionText({});
  };

  const startCvPath = () => {
    resetPersonalizationContext();
    resetCvOptimizationContext();
    setPersonalizeIntent("cv");
    transitionToStep("personalize");
  };

  const updatePersonalizeForm = (field, value) => {
    setJobValidation({
      status: "idle",
      errors: {},
      warnings: [],
      message: "",
    });
    setPersonalizeForm((current) => ({
      ...current,
      [field]: value,
    }));
    if (["role", "company", "goal", "role_level", "sector", "link"].includes(field)) {
      setCvOptimizationAnalysis(null);
      setOptimizedCv(null);
      setSelectedCoachSuggestions({});
      setConfirmedSkillDetails({});
    }
  };

  const validatePersonalizeForm = async () => {
    setJobValidation((current) => ({
      ...current,
      status: "validating",
      message: "Validazione dei dati in corso...",
    }));

    let response;
    try {
      response = await fetchWithTimeout(`${API_URL}/job/validate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          description: personalizeForm.goal.trim(),
          company: personalizeForm.company.trim(),
          role: personalizeForm.role.trim(),
          role_level: personalizeForm.role_level.trim(),
          sector: personalizeForm.sector.trim(),
          link: personalizeForm.link.trim(),
        })
      }, 30000);
    } catch (err) {
      console.error(err);
      setJobValidation({
        status: "invalid",
        errors: {},
        warnings: [],
        message: err?.name === "AbortError"
          ? "La validazione dei dati sta impiegando troppo tempo. Riprova."
          : "Errore di connessione al backend durante la validazione. Controlla che FastAPI sia avviato.",
      });
      return null;
    }

    let data;
    try {
      data = await response.json();
    } catch (err) {
      console.error(err);
      setJobValidation({
        status: "invalid",
        errors: {},
        warnings: [],
        message: "Il backend ha risposto ma non ha restituito un JSON valido.",
      });
      return null;
    }

    if (!response.ok || !data.is_valid) {
      const detail = data.detail && typeof data.detail === "object" ? data.detail : data;
      setJobValidation({
        status: "invalid",
        errors: detail.errors || {},
        warnings: detail.warnings || [],
        message: detail.message || "Correggi i campi evidenziati prima di continuare.",
      });
      return null;
    }

    setJobValidation({
      status: "valid",
      errors: {},
      warnings: data.warnings || [],
      message: data.message || "I dati inseriti sono validi.",
    });
    return data;
  };

  const getProfileNameParts = () => {
    const parts = (profile.name || "").trim().split(/\s+/).filter(Boolean);
    return {
      firstName: parts[0] || "",
      lastName: parts.slice(1).join(" "),
    };
  };

  const continuePersonalizedPath = async (event) => {
    event.preventDefault();
    resetError();

    const hasInterviewContext = Boolean(
      personalizeForm.goal.trim() ||
      personalizeForm.company.trim() ||
      (personalizeForm.role.trim() && personalizeForm.role.trim().toLowerCase() !== "da definire") ||
      personalizeForm.sector.trim() ||
      personalizeForm.link.trim()
    );

    if (!hasInterviewContext) {
      return;
    }

    let validationResult;
    try {
      validationResult = await validatePersonalizeForm();
      if (!validationResult) {
        return;
      }
    } catch (err) {
      console.error(err);
      setJobValidation({
        status: "invalid",
        errors: {},
        warnings: [],
        message: "Errore durante la validazione dei dati. Controlla che FastAPI sia avviato.",
      });
      return;
    }

    const nextCompany = validationResult.normalized_company || "";
    const nextRole = validationResult.normalized_role || "";

    if (personalizeIntent === "cv" && !nextRole) {
      setJobValidation({
        status: "invalid",
        errors: {
          role: "Inserisci almeno un ruolo target, ad esempio 'Data Analyst', 'Project Manager' o 'Computer Vision Engineer'. L'azienda è opzionale.",
        },
        warnings: [],
        message: "Inserisci almeno un ruolo target. L'azienda è opzionale.",
      });
      return;
    }

    setCompany(nextCompany || "Azienda Generica");
    setPersonalizeForm((current) => ({
      ...current,
      role: nextRole,
      company: nextCompany,
    }));

    if (nextRole) {
      setProfile((current) => ({
        ...current,
        target_role: nextRole,
      }));
    }

    if (personalizeIntent === "cv") {
      if (!isProfileComplete(profile)) {
        transitionToStep("cv-upload");
        return;
      }

      await analyzeCvOptimization(profile, null, {
        role: nextRole,
        company: nextCompany,
      });
      return;
    }

    transitionToStep("gym");
  };

  const goToMainDashboard = () => {
    if (step === "home") {
      resetError();
      setIsProfileMenuOpen(false);
      return;
    }

    transitionToStep("home");
  };

  if (showSplash) {
    return <SplashScreen />;
  }

  const canGoBack = userId && step !== "auth" && stepHistory.length > 0;
  const profileInitial = (profile.name || profile.email || "U").trim().charAt(0).toUpperCase();
  const displayedDigitalAnalysis = normalizeDigitalAnalysis(digitalAnalysis);
  const digitalCoherenceScore = displayedDigitalAnalysis?.score ?? 0;
  const isLinkedInConnected = profile.auth_provider === "linkedin";
  const hasAnyDigitalProfile = Boolean(
    digitalPresence.linkedin_url.trim() ||
    digitalPresence.portfolio_url.trim() ||
    digitalPresence.instagram_handle.trim()
  );
  const canAnalyzeDigitalPresence = isLinkedInConnected || hasAnyDigitalProfile;
  const exactInstagramHandle = normalizeInstagramHandle(digitalPresence.instagram_handle || profile.instagram_handle || "");
  const linkedinProfileUrl = digitalPresence.linkedin_url || profile.linkedin_url || "";
  const portfolioProfileUrl = digitalPresence.portfolio_url || profile.portfolio_url || "";
  const connectedDigitalProfiles = [
    linkedinProfileUrl ? { title: "Link LinkedIn pubblico", url: normalizeProfileUrl(linkedinProfileUrl) } : null,
    exactInstagramHandle ? { title: `Instagram @${exactInstagramHandle}`, url: `https://www.instagram.com/${exactInstagramHandle}/` } : null,
    portfolioProfileUrl ? {
      title: normalizeProfileUrl(portfolioProfileUrl).includes("github.com") ? "Profilo GitHub" : "Profilo collegato",
      url: normalizeProfileUrl(portfolioProfileUrl),
    } : null,
  ].filter(Boolean);
  const cvStrategyTargetRole = cvOptimizationAnalysis?.target?.role || personalizeForm.role || profile.target_role || "ruolo target";
  const cvStrategyTargetCompany = cvOptimizationAnalysis?.target?.company || company || "azienda target";
  const cvStrategyOverallScore = cvOptimizationAnalysis?.overall_score || cvOptimizationAnalysis?.score || 0;
  const cvScoreComparison = cvOptimizationAnalysis?.score_comparison || optimizedCv?.score_comparison || null;
  const cvStrategyScoreItems = [
    { label: "Generale", value: cvStrategyOverallScore },
    { label: "ATS simulato", value: cvOptimizationAnalysis?.ats_score || cvOptimizationAnalysis?.ats_analysis?.ats_score || 0 },
    { label: "Formato", value: cvOptimizationAnalysis?.format_score || cvOptimizationAnalysis?.ats_analysis?.format_score || 0 },
    { label: "Ruolo", value: cvOptimizationAnalysis?.job_match_score || cvOptimizationAnalysis?.role_match_score || cvOptimizationAnalysis?.role_score || 0 },
    { label: "Azienda", value: cvOptimizationAnalysis?.company_fit_score || cvOptimizationAnalysis?.company_score || 0 },
    { label: "Completezza", value: cvOptimizationAnalysis?.completeness_score || 0 },
  ];
  const suggestedSkills = cvOptimizationAnalysis?.suggested_skills || {};
  const rawSkillConfirmationItems = [
    ...(suggestedSkills.confirmation_items || []),
  ]
    .filter(Boolean)
    .filter((item) =>
      item.type === "skillConfirmation"
      && ["hard_skill", "soft_skill", "tool", "language"].includes(item.category)
      && !item.already_present
    );
  const skillConfirmationItems = rawSkillConfirmationItems
    .map((item, index) => normalizeSkillConfirmationItem(item, index))
    .filter(Boolean)
    .filter((item) => !isSkillSemanticallyPresent(profile.cv_text || cvPreview?.text || "", item.name))
    .filter((item, index, list) =>
      list.findIndex((candidate) => canonicalizeSkillName(candidate.name) === canonicalizeSkillName(item.name)) === index
    )
    .map((item) => {
      const saved = confirmedSkillDetails[item.id] || {};
      return {
        ...item,
        status: saved.status || (item.already_present ? item.status : "pending"),
        user_example: saved.user_example || "",
      };
    });
  const proposedSkillConfirmationItems = skillConfirmationItems.filter((item) => {
    const name = item.name.trim();
    const normalized = name.toLowerCase();
    const placeholders = [
      "competenza specializzata",
      "competenza tecnica primaria",
      "competenza tecnica secondaria",
      "strumento principale",
      "strumento ausiliario",
    ];
    return (
      !item.already_present
      && name.length >= 3
      && !placeholders.includes(normalized)
      && !normalized.endsWith(" analu")
      && normalized !== "analu"
    );
  });
  const acceptedSkillConfirmations = proposedSkillConfirmationItems.filter((item) => item.status === "confirmed" || item.status === "accepted");
  const rejectedSkillConfirmations = proposedSkillConfirmationItems.filter((item) => item.status === "rejected");
  const latestOptimizedCv = optimizedCvsList[0] || null;
  const hasMeaningfulProfileValue = (value) => {
    const normalized = String(value || "").trim().toLowerCase();
    return Boolean(normalized && !["da definire", "Azienda Generica", "settore"].includes(normalized));
  };
  const preferredCompanies = [
    personalizeForm.company,
    company,
    ...history.map((item) => item.company),
    ...optimizedCvsList.map((item) => item.target_company),
  ]
    .map((item) => String(item || "").trim())
    .filter((item) => item && item.toLowerCase() !== "azienda generica")
    .filter((item, index, list) =>
      list.findIndex((candidate) => candidate.toLowerCase() === item.toLowerCase()) === index
    );
  const hasMasterCv = Boolean(profile.cv_filename);
  const hasTargetRole = hasMeaningfulProfileValue(profile.target_role);
  const hasTargetCompany = preferredCompanies.length > 0;
  const hasOptimizedCv = optimizedCvsList.length > 0;
  const hasProfileDetails = Boolean(
    profile.name &&
    hasMeaningfulProfileValue(profile.sector)
  );
  const hasCvAnalysis = Boolean(digitalAnalysis || cvOptimizationAnalysis);
  const hasInterviewPreparation = Boolean((progress?.total_answers || 0) > 0 || history.length > 0);
  const careerPathItems = [
    { label: "CV caricato", complete: hasMasterCv },
    { label: "Ruolo target", complete: hasTargetRole },
    { label: "Azienda target", complete: hasTargetCompany },
    { label: "Analisi CV", complete: hasCvAnalysis },
    { label: "CV ottimizzato", complete: hasOptimizedCv },
    { label: "Preparazione colloquio", complete: hasInterviewPreparation },
  ];
  const totalProfileSteps = careerPathItems.length;
  const completedProfileSteps = careerPathItems.filter((item) => item.complete).length;
  const profileCompletionPercentage = Math.round(
    (completedProfileSteps / totalProfileSteps) * 100
  );

  // Calcolo delle medie per il riepilogo finale della sessione
  const sessionSummary = {
    totalScore: allFeedbacks.length > 0 ? Math.round(allFeedbacks.reduce((acc, f) => acc + f.feedback.total_score, 0) / allFeedbacks.length) : 0,
    clarity: allFeedbacks.length > 0 ? Math.round(allFeedbacks.reduce((acc, f) => acc + f.feedback.clarity_score, 0) / allFeedbacks.length) : 0,
    completeness: allFeedbacks.length > 0 ? Math.round(allFeedbacks.reduce((acc, f) => acc + f.feedback.completeness_score, 0) / allFeedbacks.length) : 0,
    relevance: allFeedbacks.length > 0 ? Math.round(allFeedbacks.reduce((acc, f) => acc + f.feedback.relevance_score, 0) / allFeedbacks.length) : 0,
    professionalism: allFeedbacks.length > 0 ? Math.round(allFeedbacks.reduce((acc, f) => acc + f.feedback.professionalism_score, 0) / allFeedbacks.length) : 0,
    synthesis: allFeedbacks.length > 0 ? Math.round(allFeedbacks.reduce((acc, f) => acc + f.feedback.synthesis_score, 0) / allFeedbacks.length) : 0,
    speaking: allFeedbacks.length > 0 ? Math.round(allFeedbacks.reduce((acc, f) => acc + f.feedback.speaking_score, 0) / allFeedbacks.length) : 0,
  };

  const previousInterviewTargetsFromHistory = history
    .filter((item) => item.company || item.role)
    .map((item) => ({
      company: item.company || "Azienda Generica",
      role: item.role || "Ruolo da definire",
      id: `${(item.company || "Azienda Generica").trim().toLowerCase()}::${(item.role || "").trim().toLowerCase()}`,
    }))
    .filter((item, index, list) => list.findIndex((target) => target.id === item.id) === index);

  const previousInterviewTargetsFromOptimizedCv = optimizedCvsList
    .filter((item) => item.target_company || item.target_role)
    .map((item) => ({
      company: item.target_company || "Azienda Generica",
      role: item.target_role || "Ruolo da definire",
      id: `${(item.target_company || "Azienda Generica").trim().toLowerCase()}::${(item.target_role || "").trim().toLowerCase()}`,
    }))
    .filter((item, index, list) => list.findIndex((target) => target.id === item.id) === index);

  const previousInterviewTargets = [
    ...previousInterviewTargetsFromHistory,
    ...previousInterviewTargetsFromOptimizedCv,
  ].filter((item, index, list) => list.findIndex((target) => target.id === item.id) === index);

  const difficultyOptions = [
    { value: "base", label: "Base", description: "Domande dirette, perfette per iniziare con ritmo tranquillo." },
    { value: "intermedio", label: "Intermedio", description: "Domande realistiche e professionali su competenze e motivazione." },
    { value: "avanzato", label: "Avanzato", description: "Domande sfidanti, tecniche e situazionali per un vero test di preparazione." },
  ];
  const currentDifficulty = difficultyOptions.find((option) => option.value === difficulty) || difficultyOptions[1];
  const coachSuggestions = getCoachSuggestionsFromAnalysis(cvOptimizationAnalysis);
  const selectedCoachSuggestionItems = coachSuggestions.filter((item) => selectedCoachSuggestions[item.id] === "accepted" || selectedCoachSuggestions[item.id] === true);
  const rejectedCoachSuggestionItems = coachSuggestions.filter((item) => selectedCoachSuggestions[item.id] === "rejected");
  const decidedCoachSuggestions = coachSuggestions.filter((item) => ["accepted", "rejected"].includes(selectedCoachSuggestions[item.id]));
  const currentCoachSuggestion = coachSuggestions.find((item) => !["accepted", "rejected"].includes(selectedCoachSuggestions[item.id])) || null;
  const decidedSkillConfirmations = proposedSkillConfirmationItems.filter((item) => ["accepted", "confirmed", "rejected"].includes(item.status));
  const currentSkillConfirmation = proposedSkillConfirmationItems.find((item) => !["accepted", "confirmed", "rejected"].includes(item.status)) || null;
  const allCoachSuggestionsReviewed = !currentCoachSuggestion;
  const allSkillConfirmationsReviewed = !currentSkillConfirmation;
  const recommendedAdaptations = [
    ...(cvOptimizationAnalysis?.suggestions || []),
    ...(cvOptimizationAnalysis?.improvements || []),
    ...(cvOptimizationAnalysis?.weaknesses || []),
  ]
    .map((item) => normalizeStrategyItem(item, "Adattamento consigliato"))
    .filter((item) => item.description || item.title);
  const cvOptimizationQuestions = (cvOptimizationAnalysis?.optimization_questions || []).length > 0
    ? cvOptimizationAnalysis.optimization_questions
    : recommendedAdaptations.map((item, index) => ({
      id: `fallback_${index}`,
      question: getAdaptationQuestion(item, index),
      reason: item.description || item.coach_tip || "",
      category: "approfondimento",
    }));
  const formatHistoryDate = (value) => {
    if (!value) return "";
    const normalized = String(value).trim().replace(" ", "T");
    const date = new Date(normalized);
    if (!Number.isNaN(date.getTime())) {
      return new Intl.DateTimeFormat("it-IT", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      }).format(date);
    }
    return String(value);
  };

  const displayInterviewType = (type) => {
    if (!type) return "Generale";
    const labels = {
      conoscitive_motivazionali: "Conoscitive motivazionali",
      tecniche: "Tecniche",
      logica: "Logica",
    };
    const key = String(type).toLowerCase();
    if (labels[key]) return labels[key];
    const label = type.replace(/_/g, " ");
    return label.charAt(0).toUpperCase() + label.slice(1).toLowerCase();
  };

  const displayDifficulty = (difficulty) => {
    if (!difficulty) return "—";
    return difficulty.charAt(0).toUpperCase() + difficulty.slice(1).toLowerCase();
  };

  const groupedHistory = Object.values(history.reduce((groups, item) => {
    const sessionId = item.session_id;
    if (!groups[sessionId]) {
      groups[sessionId] = {
        session_id: sessionId,
        company: item.company || "Azienda Generica",
        role: item.role || "Ruolo non specificato",
        interview_type: item.interview_type || "",
        difficulty: item.difficulty || "",
        created_at: item.created_at,
        total_score: item.total_score,
        questions: [],
      };
    }

    groups[sessionId].questions.push({
      question_id: `${sessionId}-${groups[sessionId].questions.length}`,
      question: item.question,
      user_answer: item.user_answer,
      feedback: item.feedback,
      speaking_feedback: item.speaking_feedback,
      improved_answer: item.improved_answer,
      solution_explanation: item.solution_explanation,
      clarity_score: item.clarity_score,
      completeness_score: item.completeness_score,
      relevance_score: item.relevance_score,
      professionalism_score: item.professionalism_score,
      synthesis_score: item.synthesis_score,
      speaking_score: item.speaking_score,
      question_mode: item.question_mode,
    });

    return groups;
  }, {})).sort((a, b) => {
    const aDate = new Date(String(a.created_at).trim().replace(" ", "T"));
    const bDate = new Date(String(b.created_at).trim().replace(" ", "T"));
    return bDate - aDate;
  });

  const toggleHistorySession = (sessionId) => {
    setExpandedHistorySessions((current) => {
      if (current.includes(sessionId)) {
        return current.filter((id) => id !== sessionId);
      }
      return [...current, sessionId];
    });
  };

  const toggleHistoryQuestion = (questionId) => {
    setExpandedHistoryQuestions((current) => {
      if (current.includes(questionId)) {
        return current.filter((id) => id !== questionId);
      }
      return [...current, questionId];
    });
  };

  const cvSummaryAcceptedSkillGroups = {
    hard: [
      ...acceptedSkillConfirmations.filter((item) => !["soft_skill", "tool"].includes(item.category)).map((item) => item.name),
      ...acceptedSkillConfirmations.filter((item) => item.category === "tool").map((item) => item.name),
    ],
    soft: [
      ...acceptedSkillConfirmations.filter((item) => item.category === "soft_skill").map((item) => item.name),
    ],
  };
  Object.keys(cvSummaryAcceptedSkillGroups).forEach((key) => {
    cvSummaryAcceptedSkillGroups[key] = cvSummaryAcceptedSkillGroups[key].filter((item, index, list) =>
      item && list.findIndex((candidate) => candidate.toLowerCase() === item.toLowerCase()) === index
    );
  });
  const cvSummarySkillExampleItems = acceptedSkillConfirmations
    .filter((item) => String(item.user_example || "").trim())
    .map((item) => ({
      title: item.name,
      detail: String(item.user_example).trim(),
    }));
  const cvSummaryAdditionalItems = [
    ...CV_ADDITIONAL_DATA_FIELDS
      .filter((field) => !["additional_notes", "technical_skills", "soft_skills", "tools"].includes(field.key))
      .map((field) => ({
        title: field.label,
        detail: String(cvAdditionalData[field.key] || "").trim(),
      }))
      .filter((item) => item.detail),
    ...(cvAdditionalData.additional_notes?.trim() ? [{
      title: "Note generali",
      detail: cvAdditionalData.additional_notes.trim(),
    }] : []),
    ...Object.entries(cvAdaptationAnswers)
      .filter(([, answer]) => String(answer || "").trim())
      .map(([index, answer]) => ({
        title: cvOptimizationQuestions[Number(index)]?.question || "Risposta extra",
        detail: stripRepeatedQuestionFromAnswer(
          answer,
          cvOptimizationQuestions[Number(index)]?.question || ""
        ),
      })),
  ];
  const cvSummaryExtraItems = [
    ...cvSummarySkillExampleItems,
    ...cvSummaryAdditionalItems,
  ];
  const cvSummaryAcceptedSuggestionCount = selectedCoachSuggestionItems.length;
  const cvSummaryReviewedSuggestionCount = decidedCoachSuggestions.length || coachSuggestions.length;
  const cvSummaryApplicationStatus = cvSummaryReviewedSuggestionCount > 0
    ? `${cvSummaryAcceptedSuggestionCount} su ${cvSummaryReviewedSuggestionCount}`
    : "0 su 0";
  return (
    <div className={step === "auth" ? "page auth-page page-auth" : `page page-${step}`}>
      {step !== "auth" && (
        <header className="app-navbar">
          <div className="navbar-left">
            <button
              className="navbar-back-btn"
              onClick={goBack}
              disabled={!canGoBack}
              aria-label="Torna indietro"
              title="Torna indietro"
            >
              <strong>Indietro</strong>
            </button>

            <button
              type="button"
              className="navbar-brand"
              onClick={goToMainDashboard}
              aria-label="Torna alla dashboard principale"
              title="Torna alla dashboard principale"
            >
              <img
                className="navbar-logo"
                src={logoCareerCoach}
                alt="Logo CareerCoach"
              />
              <span className="navbar-title">CareerCoach</span>
            </button>
          </div>

          {userId && (
            <div className="profile-menu navbar-user">
              <button
                className="profile-trigger"
                onClick={() => setIsProfileMenuOpen((current) => !current)}
                aria-expanded={isProfileMenuOpen}
                aria-label="Apri profilo"
              >
                <span>{profileInitial}</span>
                <strong>{profile.name || "Profilo"}</strong>
              </button>

              {isProfileMenuOpen && (
                <div className="profile-popover">
                  <div className="profile-popover-header">
                    <span>{profileInitial}</span>
                    <div>
                      <strong>{profile.name || "Il tuo profilo"}</strong>
                      <p>{profile.email || "Account CareerCoach"}</p>
                    </div>
                  </div>
                  <button onClick={() => transitionToStep("profile")}>Dettagli Profilo</button>
                  <button className="logout-menu-button" onClick={logoutUser}>Logout</button>
                </div>
              )}
            </div>
          )}
        </header>
      )}

      {showTransition && !showSplash && (
        <SplashScreen
          mode="loading"
          slogan={loadingMessage}
        />
      )}
      {error && <div className="error">{error}</div>}
      {authMessage && <div className="success-message">{authMessage}</div>}
      {previewLink && (
        <div className="info-box">
          Email non configurata in sviluppo. Apri questo link di test:{" "}
          <a href={previewLink}>{previewLink}</a>
        </div>
      )}

      {step === "home" && (
        <section className="home-page">
          <div className="home-heading">
            <h2>
              Cosa vuoi fare oggi
              {userId && profile?.name?.trim() ? (
                <span>, {profile.name.trim().split(/\s+/)[0]}</span>
              ) : ""}?
            </h2>
            <p>Scegli un'attività per continuare il tuo percorso.</p>
          </div>

          <div className="activity-cards-grid">
            <div
              className="home-action-card"
              onClick={startCvPath}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  startCvPath();
                }
              }}
            >
              <span className="recommended-badge">Consigliato</span>
              <div className="home-action-icon action-card-icon cv-action-icon">
                <CvDocumentIcon />
              </div>
              <div className="action-card-content">
                <h3 className="action-card-title">Ottimizza il tuo CV</h3>
                <p className="action-card-description">
                  Suggerimenti personalizzati su struttura,
                  competenze e coerenza con gli annunci.
                </p>
                <button className="action-card-button" onClick={startCvPath}>
                  <span>Inizia</span>
                </button>
              </div>
            </div>

            <div
              className="home-action-card"
              onClick={() => transitionToStep("gym")}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  transitionToStep("gym");
                }
              }}
            >
              <div className="home-action-icon action-card-icon interview interview-action-icon">
                <InterviewIcon />
              </div>
              <div className="action-card-content">
                <h3 className="action-card-title">Preparati al Colloquio</h3>
                <p className="action-card-description">
                  Allenati con domande realistiche e ricevi feedback su contenuto e
                  chiarezza.
                </p>
                <button className="action-card-button" onClick={() => transitionToStep("gym")}>
                  <span>Avvia simulazione</span>
                </button>
              </div>
            </div>
          </div>

          <p className="activity-footer-note">
            Puoi cambiare attività in qualsiasi momento.
          </p>
        </section>
      )}

      {step === "personalize" && (
        <PersonalizeExperience
          company={personalizeForm.company}
          goal={personalizeForm.goal}
          link={personalizeForm.link}
          role={personalizeForm.role}
          roleLevel={personalizeForm.role_level}
          sector={personalizeForm.sector}
          onBack={() => transitionToStep("home")}
          onChange={updatePersonalizeForm}
          onSubmit={continuePersonalizedPath}
          validation={jobValidation}
          isValidating={jobValidation.status === "validating"}
          requireRole={personalizeIntent === "cv"}
          submitLabel={personalizeIntent === "cv" ? "Continua" : "Continua alla simulazione"}
        />
      )}

      {step === "auth" && (
        <section className="auth-shell">
          <div className="auth-brand-top">
            <img
              className="auth-logo"
              src={logoCareerCoach}
              alt="Logo Career Coach"
            />
            <p className="auth-app-title">CareerCoach</p>
          </div>
          <div className="auth-panel">
            <div className="auth-card">
              <h3>
                {authMode === "register"
                  ? "Crea il tuo account"
                  : authMode === "forgot"
                    ? "Recupera la password"
                    : authMode === "reset"
                      ? "Scegli una nuova password"
                      : "Accedi"}
              </h3>
              <p className="auth-intro">
                Accedi con email, Gmail o LinkedIn.
              </p>

              <div className="oauth-grid">
                <button onClick={() => socialLogin("google")} disabled={loading}>
                  <span>G</span>
                  Google
                </button>
                <button onClick={() => socialLogin("linkedin")} disabled={loading}>
                  <span>in</span>
                  LinkedIn
                </button>
              </div>

              <div className="auth-divider">oppure</div>

              <div className="auth-tabs">
                <button
                  className={authMode === "login" ? "active" : ""}
                  onClick={() => {
                    resetError();
                    setAuthMode("login");
                  }}
                >
                  Accedi
                </button>
                <button
                  className={authMode === "register" ? "active" : ""}
                  onClick={() => {
                    resetError();
                    setAuthMode("register");
                  }}
                >
                  Registrati
                </button>
              </div>

              {authMode === "login" && (
                <div className="auth-form">
                  <label>Email o cellulare</label>
                  <input
                    value={authForm.identifier}
                    onChange={(e) => updateAuthForm("identifier", e.target.value)}
                    placeholder="tua.email@esempio.it"
                    autoComplete="username"
                  />

                  <label>Password</label>
                  {renderPasswordField("password", authForm.password, "Almeno 8 caratteri", "current-password")}

                  <button
                    className="link-button"
                    onClick={() => {
                      resetError();
                      setAuthMode("forgot");
                    }}
                  >
                    Password dimenticata?
                  </button>

                  <button className="auth-submit" onClick={loginUser} disabled={loading}>
                    Accedi
                  </button>
                </div>
              )}

              {authMode === "register" && (
                <div className="auth-form">
                  <label>Nome e Cognome</label>
                  <input
                    value={authForm.name}
                    onChange={(e) => updateAuthForm("name", e.target.value)}
                    placeholder="Il tuo nome"
                    autoComplete="name"
                  />

                  <label>Email</label>
                  <input
                    type="email"
                    value={authForm.email}
                    onChange={(e) => updateAuthForm("email", e.target.value)}
                    placeholder="tua.email@esempio.it"
                    autoComplete="email"
                  />

                  <label>Cellulare opzionale</label>
                  <input
                    type="tel"
                    value={authForm.phone}
                    onChange={(e) => updateAuthForm("phone", e.target.value)}
                    placeholder="+39 333 123 4567"
                    autoComplete="tel"
                  />

                  <label>Password</label>
                  {renderPasswordField("password", authForm.password, "Almeno 8 caratteri, lettere e numeri", "new-password")}

                  <label>Conferma password</label>
                  {renderPasswordField("confirmPassword", authForm.confirmPassword, "Ripeti la password", "new-password")}

                  <button className="auth-submit" onClick={registerUser} disabled={loading}>
                    Crea account
                  </button>
                </div>
              )}

              {authMode === "forgot" && (
                <div className="auth-form">
                  <label>Email o cellulare associato</label>
                  <input
                    value={authForm.identifier}
                    onChange={(e) => updateAuthForm("identifier", e.target.value)}
                    placeholder="tua.email@esempio.it"
                    autoComplete="username"
                  />

                  <button className="auth-submit" onClick={requestPasswordReset} disabled={loading}>
                    Invia link di recupero
                  </button>

                  <button
                    className="link-button centered"
                    onClick={() => {
                      resetError();
                      setAuthMode("login");
                    }}
                  >
                    Torna all'accesso
                  </button>
                </div>
              )}

              {authMode === "reset" && (
                <div className="auth-form">
                  <label>Nuova password</label>
                  {renderPasswordField("newPassword", authForm.newPassword, "Almeno 8 caratteri, lettere e numeri", "new-password")}

                  <button className="auth-submit" onClick={resetPassword} disabled={loading}>
                    Aggiorna password
                  </button>
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {step === "cv-upload" && (
        <section className="cv-onboarding">
          <div className="cv-onboarding-copy">
            <h2>Costruiamo il tuo profilo professionale</h2>
            <p>
              Carica il tuo CV: CareerCoach analizzerà esperienze, competenze e coerenza con il ruolo che vuoi raggiungere.
            </p>
          </div>

          <div className="cv-hero-graphic" aria-hidden="true">
            <div className="cv-graphic-document">
              <span className="cv-graphic-badge">AI</span>
              <span className="cv-graphic-line wide" />
              <span className="cv-graphic-line" />
              <span className="cv-graphic-line short" />
              <div className="cv-graphic-growth">
                <span />
                <span />
                <span />
              </div>
            </div>
            <div className="cv-graphic-sparkle one" />
            <div className="cv-graphic-sparkle two" />
          </div>

          <div
            className={isCvDragging ? "cv-upload-card active" : "cv-upload-card"}
            onDragOver={(event) => {
              event.preventDefault();
              setIsCvDragging(true);
            }}
            onDragLeave={() => setIsCvDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setIsCvDragging(false);
              selectCvFile(event.dataTransfer.files?.[0]);
            }}
          >
            {isCvDragging && (
              <div className="cv-drop-overlay" aria-hidden="true">
                <div className="cv-drop-overlay-inner">
                  <strong>Rilascia per caricare</strong>
                  <span>PDF o DOCX fino a 5MB</span>
                </div>
              </div>
            )}
            <div className="cv-upload-icon">CV</div>
            <h3>Trascina qui il tuo CV</h3>
            <p>PDF o DOCX fino a 5 MB</p>
            <div className="cv-divider"><span>oppure</span></div>
            <input
              id="cv-file-input"
              ref={cvFileInputRef}
              type="file"
              accept=".pdf,.docx"
              onChange={(event) => selectCvFile(event.target.files?.[0])}
            />
            <div className="cv-file-choose-row">
              <label className="browse-file-btn" htmlFor="cv-file-input">
                Scegli file
              </label>
              <span className="cv-file-choose-hint">oppure trascina qui il CV</span>
            </div>
          </div>

          <div className="cv-format-note">
            <strong>Formato consigliato</strong>
              <p>
              Per ottenere un CV ottimizzato identico nello stile, carica il file Word originale.
              Con un DOCX l'app prova a mantenere struttura, font e formattazione del documento; con un PDF
              può analizzarlo, ma il layout potrebbe non essere preservato perfettamente.
            </p>
          </div>

          {cvFile && (
            <div className="uploaded-file-preview">
              <div className="uploaded-file-icon" aria-hidden="true">CV</div>
              <div className="uploaded-file-copy">
                <strong>{cvFile.name}</strong>
                <p>File caricato correttamente</p>
              </div>
              <button
                type="button"
                className="remove-file-btn"
                onClick={removeSelectedCvFile}
                aria-label="Rimuovi file caricato"
                title="Rimuovi file"
              >
                ×
              </button>
            </div>
          )}

          {cvValidation.status !== "idle" && (
            <div className={`cv-validation-message ${cvValidation.status}`}>
              <span aria-hidden="true">
                {cvValidation.status === "validating" ? "i" : cvValidation.status === "valid" ? "✓" : "!"}
              </span>
              <p>{cvValidation.message}</p>
            </div>
          )}

          <div className="cv-edit-info">
            <span className="cv-edit-info-icon" aria-hidden="true">✓</span>
            <span>Potrai sempre modificare le informazioni estratte prima di continuare.</span>
          </div>

          <button
            className={`analyze-cv-btn ${cvFile && cvValidation.status === "valid" ? "active" : "disabled"}`}
            onClick={uploadCv}
            disabled={loading || !cvFile || cvValidation.status !== "valid"}
          >
            {cvFile ? "Analizza il mio CV" : "Prosegui con l'analisi"}
          </button>
        </section>
      )}

      {step === "cv-digital" && (
        <section className="cv-flow-page digital-profile-page digital-redesign-page">

          <div className="digital-redesign-cards">
            {/* Card 1: LinkedIn + extra URL + export + Instagram */}
            <div className="digital-card digital-card--main">
              <h3 className="digital-card-title">Collega i tuoi profili online</h3>
              <p className="digital-card-subtitle">Permettici di confrontare il tuo CV con la tua presenza digitale</p>

              {isLinkedInConnected && (
                <div className="linkedin-connected-badge digital-compact-badge">
                  <span aria-hidden="true">✓</span>
                  <div>
                    <strong>LinkedIn collegato</strong>
                    <p>Accesso effettuato tramite LinkedIn.</p>
                  </div>
                </div>
              )}

              <div className="digital-fields">
                <label className="digital-field-label">
                  <span className="digital-field-icon" aria-hidden="true">
                    <LinkedInIcon />
                  </span>
                  LinkedIn
                </label>
                <input
                  className="digital-input"
                  value={digitalPresence.linkedin_url}
                  onChange={(event) => updateDigitalPresence("linkedin_url", event.target.value)}
                  placeholder="https://linkedin.com/in/tuonome"
                  autoComplete="off"
                />

                <div
                  className="digital-export-dropzone digital-export-dropzone--linkedin"
                  onDragOver={(event) => {
                    event.preventDefault();
                  }}
                  onDrop={(event) => {
                    event.preventDefault();
                    if (loading) return;
                    uploadLinkedinProfile(event.dataTransfer.files?.[0]);
                  }}
                >
                  <label className="digital-export-zone-copy" htmlFor="linkedin-profile-file">
                    <span className="digital-export-icon" aria-hidden="true">
                      <ExportIcon size={18} />
                    </span>
                    <div>
                      <strong>Esportazione LinkedIn</strong>
                      <p>Carica il PDF del tuo profilo (o DOCX) per il confronto con il CV.</p>
                      <small className="digital-export-drop-hint">oppure trascina qui il file</small>
                    </div>
                  </label>

                  <input
                    id="linkedin-profile-file"
                    className="digital-file-input"
                    ref={linkedinFileInputRef}
                    type="file"
                    accept=".pdf,.docx"
                    onChange={(event) => uploadLinkedinProfile(event.target.files?.[0])}
                  />

                  {profile.linkedin_profile_uploaded ? (
                    <div className="linkedin-export-status">
                      <span>
                        File pronto: <strong>{profile.linkedin_profile_filename}</strong>
                      </span>
                      <button type="button" onClick={deleteLinkedinProfile} disabled={loading}>
                        Rimuovi
                      </button>
                    </div>
                  ) : (
                    <label className="digital-export-button" htmlFor="linkedin-profile-file">
                      Carica esportazione
                    </label>
                  )}

                  {linkedinUploadMessage && <p className="linkedin-upload-message">{linkedinUploadMessage}</p>}
                </div>



                <label className="digital-field-label">
                  <span className="digital-field-icon" aria-hidden="true">
                    <InstagramIcon />
                  </span>
                  Instagram <span className="optional-pill">opzionale</span>
                </label>
                <input
                  className="digital-input"
                  value={digitalPresence.instagram_handle}
                  onChange={(event) => updateDigitalPresence("instagram_handle", event.target.value)}
                  placeholder="@tuo_handle"
                  autoComplete="off"
                />

                <label className="digital-field-label">
                  <span className="digital-field-icon" aria-hidden="true">
                    <GitHubIcon />
                  </span>
                  GitHub <span className="optional-pill">opzionale</span>
                </label>
                <input
                  className="digital-input"
                  value={digitalPresence.portfolio_url}
                  onChange={(event) => updateDigitalPresence("portfolio_url", event.target.value)}
                  placeholder="https://github.com/tuonome"
                  autoComplete="off"
                />

                {!canAnalyzeDigitalPresence && (
                  <p className="digital-profile-help">
                    Inserisci almeno un profilo online oppure salta questo passaggio.
                  </p>
                )}
              </div>
            </div>

            {/* Card 2: screenshots */}
            <div className="digital-card digital-card--screens">
              <h3 className="digital-card-title">Screenshot del profilo</h3>
              <p className="digital-card-subtitle">
                Fino a 8 immagini · controlliamo solo la presenza di contenuti sensibili e non le salviamo
              </p>

              <div
                className={`screenshot-dropzone digital-screenshot-dropzone ${screenshotAnalysisProgress.active ? "disabled" : ""}`}
                onDragOver={(event) => {
                  event.preventDefault();
                }}
                onDrop={(event) => {
                  event.preventDefault();

                  if (screenshotAnalysisProgress.active) {
                    return;
                  }

                  const dt = event.dataTransfer;

                  const filesFromList = dt?.files ? Array.from(dt.files) : [];
                  const filesFromItems = dt?.items
                    ? Array.from(dt.items)
                        .map((item) => item?.getAsFile?.())
                        .filter(Boolean)
                    : [];

                  const files = [...filesFromList, ...filesFromItems];

                  if (!files.length) {
                    setSocialScreenshotMessages((current) => ({
                      ...current,
                      instagram:
                        "Non sono riuscito a riconoscere file immagine dal trascinamento. Usa “Scegli file” oppure trascina un PNG/JPG/WebP dal file system.",
                    }));
                    return;
                  }

                  const imageFiles = files.filter((f) =>
                    (f?.type || "").startsWith("image/")
                  );

                  if (!imageFiles.length) {
                    setSocialScreenshotMessages((current) => ({
                      ...current,
                      instagram:
                        "Formato non supportato: trascina immagini (PNG/JPG/WebP) oppure usa “Scegli file”.",
                    }));
                    return;
                  }

                  addSelectedScreenshotFiles(imageFiles);
                }}
              >
                <div className="screenshot-dropzone-content">
                  <h4>Trascina le screenshot qui</h4>
                  <p>Oppure usa “Scegli file”.</p>

                  <input
                    id="social-screenshot-files"
                    ref={screenshotFileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    multiple
                    disabled={screenshotAnalysisProgress.active}
                    onChange={(event) => {
                      addSelectedScreenshotFiles(event.target.files);
                      event.target.value = "";
                    }}
                  />
                  <label
                    className="digital-upload-button"
                    htmlFor="social-screenshot-files"
                  >
                    {screenshotAnalysisProgress.active ? "Analisi in corso" : "Scegli file"}
                  </label>

                  {selectedScreenshotFiles.length > 0 && (
                    <>
                      <div className="screenshot-selection-grid">
                        {selectedScreenshotFiles.map((item) => (
                          <div className="screenshot-selection-item" key={item.id}>
                            <img src={item.previewUrl} alt={`Anteprima ${item.file.name}`} />
                            <button
                              type="button"
                              onClick={() => removeSelectedScreenshotFile(item.id)}
                              aria-label={`Rimuovi ${item.file.name}`}
                              title="Rimuovi immagine"
                            >
                              ×
                            </button>
                            <span>{item.file.name}</span>
                          </div>
                        ))}
                      </div>
                      <button
                        className="digital-analyze-screenshots-button"
                        type="button"
                        onClick={submitSelectedScreenshots}
                        disabled={screenshotAnalysisProgress.active}
                      >
                        Analizza {selectedScreenshotFiles.length}{" "}
                        {selectedScreenshotFiles.length === 1 ? "screenshot selezionato" : "screenshot selezionati"}
                      </button>
                    </>
                  )}

                  {screenshotAnalysisProgress.active && (
                    <div className="screenshot-analysis-progress" role="status">
                      <div className="screenshot-analysis-spinner" />
                      <div>
                        <strong>
                          Controllo contenuti sensibili su {screenshotAnalysisProgress.fileCount}{" "}
                          {screenshotAnalysisProgress.fileCount === 1 ? "immagine" : "immagini"}
                        </strong>
                        <p>Tempo trascorso: {screenshotAnalysisProgress.elapsedSeconds}s.</p>
                        {screenshotAnalysisProgress.queuedCount > 0 && (
                          <p>
                            {screenshotAnalysisProgress.queuedCount}{" "}
                            {screenshotAnalysisProgress.queuedCount === 1 ? "immagine in attesa" : "immagini in attesa"}.
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {socialScreenshotMessages.instagram && (
                    <p className="linkedin-upload-message">{socialScreenshotMessages.instagram}</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* bottom text + CTA */}
          <p className="privacy-note digital-privacy-bottom">
            <span aria-hidden="true">i</span>
            I profili inseriti verranno usati solo per valutare la coerenza professionale del tuo percorso.
          </p>

          <button
            className="digital-cta-button"
            onClick={analyzeDigitalPresence}
            disabled={loading || !canAnalyzeDigitalPresence}
          >
            <span className="digital-cta-sparkle" aria-hidden="true">
              <SparkleIcon size={18} />
            </span>
            Analizza coerenza digitale
          </button>

          <a
            className="digital-skip-link"
            onClick={() => transitionToStep("home")}
          >
            Salta per ora
          </a>
        </section>
      )}

      {step === "cv-analysis" && (
        <section className="cv-flow-page digital-profile-page digital-results-page">
          <div className="digital-results-heading">
            <span>Risultato analisi</span>
            <h2>Analisi coerenza digitale</h2>
            <p>Confronto tra il tuo CV e i profili online: cosa è allineato e cosa migliorare.</p>
          </div>

          <div className="digital-results-overview">
            <article className="digital-results-panel digital-score-panel">
              <h3>Score di coerenza</h3>
              <div
                className="digital-results-score"
                style={{
                  background: `radial-gradient(circle at center, #ffffff 59%, transparent 61%), conic-gradient(#139ff2 0 ${digitalCoherenceScore}%, #dfe8ef ${digitalCoherenceScore}% 100%)`,
                }}
              >
                <span>{digitalCoherenceScore}%</span>
              </div>
              <h4>
                {displayedDigitalAnalysis?.headline || (
                  digitalCoherenceScore >= 75
                    ? "Allineamento forte"
                    : digitalCoherenceScore >= 45
                      ? "Buona base, margine di crescita"
                      : "Coerenza da migliorare"
                )}
              </h4>
              <p>
                {displayedDigitalAnalysis?.summary ||
                  "Abbiamo confrontato solo i profili digitali inseriti per stimare l'impatto sulla presenza professionale."}
              </p>
            </article>

            {digitalAnalysis?.analysis_evidence && (
              <article className="digital-results-panel digital-evidence-panel">
                <h3>Cosa abbiamo confrontato</h3>
                <div className="digital-evidence-table">
                  <div>
                    <span>CV</span>
                    <strong className={digitalAnalysis.analysis_evidence.cv_profile_loaded ? "is-good" : "is-bad"}>
                      {digitalAnalysis.analysis_evidence.cv_profile_loaded
                        ? `Caricato · ${digitalAnalysis.analysis_evidence.cv_filename || profile.cv_filename || "CV"}`
                        : "Non disponibile"}
                    </strong>
                  </div>
                  <div>
                    <span>LinkedIn export</span>
                    <strong className={digitalAnalysis.analysis_evidence.linkedin_export_compared ? "is-good" : "is-bad"}>
                      {digitalAnalysis.analysis_evidence.linkedin_export_compared
                        ? `Caricato · ${digitalAnalysis.analysis_evidence.linkedin_export_filename || profile.linkedin_profile_filename || "PDF LinkedIn"}`
                        : "Non caricato"}
                    </strong>
                  </div>

                  <div>
                    <span>Instagram</span>
                    <strong className={digitalAnalysis.analysis_evidence.instagram_slug_verification?.matched ? "is-good" : "is-warning"}>
                      {digitalAnalysis.analysis_evidence.instagram_slug_verification?.matched
                        ? "Nome e cognome corrispondono all'handle"
                        : "Nome e cognome non corrispondono all'handle"}
                    </strong>
                  </div>
                  <div>
                    <span>GitHub</span>
                    <strong className={digitalAnalysis.analysis_evidence.cv_github_name_match?.status === "matched" ? "is-good" : "is-warning"}>
                      {digitalAnalysis.analysis_evidence.github_link_provided
                        ? digitalAnalysis.analysis_evidence.cv_github_name_match?.message || "Profilo inserito"
                        : "Non inserito"}
                    </strong>
                  </div>
                  <div>
                    <span>Screenshot Instagram</span>
                    <strong className={
                      (digitalAnalysis.analysis_evidence.instagram_screenshots_summary?.sensitive_flagged_count || 0) > 0
                        ? "is-bad"
                        : (digitalAnalysis.analysis_evidence.instagram_screenshots_summary?.count || 0) > 0
                          ? "is-good"
                          : "is-warning"
                    }>
                      {(digitalAnalysis.analysis_evidence.instagram_screenshots_summary?.sensitive_flagged_count || 0) > 0
                        ? "Contenuti sensibili rilevati"
                        : (digitalAnalysis.analysis_evidence.instagram_screenshots_summary?.count || 0) > 0
                          ? "Nessun contenuto sensibile rilevato"
                          : "Non caricati"}
                    </strong>
                  </div>
                </div>
              </article>
            )}
          </div>

          <section className="digital-results-panel digital-findings-panel">
            <h3>Risultati &amp; coach tips</h3>
            <p>Le aree più rilevanti per aumentare la coerenza</p>
            <div className="digital-findings-list">
              {(displayedDigitalAnalysis?.findings || []).map((finding, index) => {
                const meta = getDigitalFindingMeta(finding);
                return (
                  <article className={`digital-finding digital-finding--${meta.tone}`} key={`${finding.title}-${index}`}>
                    <header>
                      <h4><span />{getDigitalFindingTitle(finding.title)}</h4>
                      <span className="digital-status-pill">{meta.label}</span>
                    </header>
                    <div className="digital-finding-body">
                      <p>{finding.description}</p>
                      {finding.coach_tip && (
                        <div className="digital-coach-tip">
                          <span aria-hidden="true" />
                          <div>
                            <strong>Consiglio del coach</strong>
                            <p>{finding.coach_tip}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </article>
                );
              })}

              {["provider_not_configured", "provider_unavailable"].includes(
                digitalAnalysis?.analysis_evidence?.visual_media_analysis?.status
              ) && (
                <article className="digital-finding digital-finding--warning">
                  <header>
                    <h4><span />Analisi visuale da configurare</h4>
                    <span className="digital-status-pill">Da migliorare</span>
                  </header>
                  <div className="digital-finding-body">
                    <p>
                      Per analizzare le immagini in locale, installa Ollama, esegui
                      <strong> ollama pull moondream</strong> e assicurati che il servizio sia avviato.
                    </p>
                  </div>
                </article>
              )}
            </div>
          </section>

          {connectedDigitalProfiles.length > 0 && (
            <section className="digital-results-panel digital-connected-panel">
              <h3>Profili collegati</h3>
              <div>
                {connectedDigitalProfiles.map((source) => (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    key={getCanonicalProfileKey(source.url)}
                  >
                    {source.title || source.url}
                  </a>
                ))}
              </div>
            </section>
          )}

          <button className="digital-results-home-button" onClick={() => transitionToStep("home")}>
            Torna alla home ↗
          </button>
        </section>
      )}


      {step === "cv-strategy" && (
        <section className="cv-strategy-page">
          <div className="cv-strategy-heading">
            <h2>Analisi CV</h2>
            <p>
              {cvStrategyTargetRole} presso {cvStrategyTargetCompany}
            </p>
          </div>

          <div className="cv-strategy-score-card">
            <div
              className="cv-score-ring"
              style={{
                background: `radial-gradient(circle at center, #ffffff 58%, transparent 60%), conic-gradient(#248269 0 ${cvStrategyOverallScore}%, #dfe8ef ${cvStrategyOverallScore}% 100%)`,
              }}
            >
              <span>{cvStrategyOverallScore}%</span>
            </div>
            <h3>Punteggio complessivo</h3>
            <p>
              {getItalianCvIntroSummary(cvOptimizationAnalysis, cvStrategyTargetRole, cvStrategyTargetCompany)}
            </p>
          </div>

          {cvOptimizationAnalysis?.identity_check?.matches_user == null
            && cvOptimizationAnalysis?.identity_check?.message ? (
              <div className="cv-strategy-item warning" style={{ marginBottom: 18 }}>
                <span aria-hidden="true">!</span>
                <div>
                  <strong>Controllo nome CV</strong>
                  <p>{cvOptimizationAnalysis.identity_check.message}</p>
                  {cvOptimizationAnalysis?.identity_check?.detected_name ? (
                    <small>
                      Nome rilevato nel CV: {cvOptimizationAnalysis.identity_check.detected_name}. Se il documento è corretto puoi continuare, ma conviene verificare che il profilo e il CV riportino lo stesso nominativo.
                    </small>
                  ) : (
                    <small>
                      Non sono riuscito a leggere il nominativo in modo affidabile: controlla che nel CV compaiano nome e cognome corretti.
                    </small>
                  )}
                </div>
              </div>
            ) : null}

          <div className="cv-strategy-section">
            <div
              className="scores-grid cv-job-scores"
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                gap: 12,
              }}
            >
              {cvStrategyScoreItems.map((item) => {
                const scoreRaw = Number(item.value);
                const score = Number.isFinite(scoreRaw) ? scoreRaw : 0;

                const numberColor =
                  score < 50
                    ? "#ff3b3b" // rosso (50 escluso)
                    : score < 70
                      ? "#ff9f1a" // arancione (70 escluso)
                      : "#22c55e"; // verde (70-100)

                return (
                  <div className="cv-score-tile" key={item.label}>
                    <strong style={{ color: numberColor }}>{score}</strong>
                    <p>{item.label}</p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="cv-strategy-section">
            <div className="cv-strategy-section-title">
              <span className="success">+</span>
              <h3>Punti di Forza</h3>
            </div>

            {(cvOptimizationAnalysis?.strengths || []).map((item, index) => {
              const normalizedItem = normalizeStrategyItem(item);
              return (
                <div className="cv-strategy-item success" key={`${normalizedItem.description}-${index}`}>
                  <span aria-hidden="true" style={{ display: "grid", placeItems: "center" }}>
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M6 9l4 7 8-14" />
                    </svg>
                  </span>
                  <div>
                    {normalizedItem.title && <strong>{normalizedItem.title}</strong>}
                    <p>{normalizedItem.description}</p>
                    {normalizedItem.coach_tip && <small>{normalizedItem.coach_tip}</small>}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="cv-strategy-section">
            <div className="cv-strategy-section-title">
              <span className="warning">~</span>
              <h3>Miglioramenti consigliati</h3>
            </div>

            {(cvOptimizationAnalysis?.weaknesses || cvOptimizationAnalysis?.improvements || []).map((item, index) => {
              const normalizedItem = normalizeStrategyItem(item);
              return (
                <div className="cv-strategy-item warning" key={`${normalizedItem.description}-${index}`}>
                  <span aria-hidden="true" style={{ display: "grid", placeItems: "center" }}>
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M12 16v.01" />
                      <path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2-3 4" />
                    </svg>
                  </span>
                  <div>
                    {normalizedItem.title && <strong>{normalizedItem.title}</strong>}
                    <p>{normalizedItem.description}</p>
                    {normalizedItem.coach_tip && <small>{normalizedItem.coach_tip}</small>}
                  </div>
                </div>
              );
            })}
          </div>



          <div className="cv-strategy-section">
            <div className="cv-strategy-section-title">
              <span>i</span>
              <h3>Fonti Utili</h3>
            </div>
            {(cvOptimizationAnalysis?.sources || []).length > 0 ? (
              <div className="source-list">
                {cvOptimizationAnalysis.sources.slice(0, 4).map((source, index) => (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    key={`${source.url}-${index}`}
                  >
                    {source.title || source.url}
                  </a>
                ))}
              </div>
            ) : (
              <p className="cv-strategy-note">
                Nessuna fonte candidatura attendibile trovata. Inserisci un annuncio specifico per un'analisi più precisa.
              </p>
            )}
          </div>

          <button className="cv-next-button" onClick={() => transitionToStep("cv-optimize-details")}>
            Continua con l'ottimizzazione
          </button>
        </section>
      )}

      {step === "cv-optimize-details" && (
        <section className={`cv-strategy-page cv-optimize-details-page cv-optimize-details-page--stage-${cvOptimizationStage}`}>
          <div className="cv-strategy-heading">
            <h2>
              {[
                "Valuta skill suggerite",
                "Modifiche accettate",
                "Genera CV ottimizzato",
              ][cvOptimizationStage]}
            </h2>
            <p>
              {[
                "Conferma solo le competenze che possiedi davvero. Puoi aggiungere un contesto reale per renderle più credibili.",
                "Controlla le modifiche e completa qui le informazioni che saranno integrate nel nuovo CV.",
                "Genera il nuovo documento mantenendo stile e struttura del CV originale, ampliandolo solo quando necessario.",
              ][cvOptimizationStage]}
            </p>
          <div className="cv-stage-progress" aria-label="Avanzamento ottimizzazione CV">
              {["Skill", "Riepilogo", "Generazione"].map((label, index) => (
                <span
                  className={index <= cvOptimizationStage ? "active" : ""}
                  key={label}
                >
                  {index === 0 ? (
                    <span className="cv-stage-progress-bulb" aria-hidden="true">
                      💡
                    </span>
                  ) : index === 1 ? (
                    <span className="cv-stage-progress-pentagon" aria-hidden="true" />
                  ) : index === 2 ? (
                    <span className="cv-stage-progress-summary-icon" aria-hidden="true">
                      <span />
                      <span />
                      <span />
                    </span>
                  ) : index === 3 ? (
                    <span className="cv-stage-progress-sparkle" aria-hidden="true">
                      <SparkleIcon size={12} />
                    </span>
                  ) : (
                    <span className="cv-stage-progress-number" aria-hidden="true">
                      {index + 1}.
                    </span>
                  )}
                  <span className={index === 0 ? "cv-stage-progress-label" : ""}>
                    {label}
                  </span>
                </span>
              ))}
            </div>
          </div>

          {cvOptimizationStage === -2 && (
            <>
              <div className="cv-strategy-section cv-optimize-details-page__suggestions">
                <div className="cv-strategy-section-title">
                  <span>i</span>
                  <h3>Modifiche consigliate</h3>
                </div>
                {currentCoachSuggestion ? (
                  <div className="ai-suggestion-card-list">
                    {[currentCoachSuggestion].map((suggestion) => {
                      const index = coachSuggestions.findIndex((item) => item.id === suggestion.id);
                      const suggestionStatus = selectedCoachSuggestions[suggestion.id] || "pending";
                      const isAccepted = suggestionStatus === "accepted";
                      const isRejected = suggestionStatus === "rejected";

                      return (
                        <div className={`coach-suggestion-option ai-suggestion-card ${suggestionStatus}`} key={suggestion.id}>
                          <span className="suggestion-state-icon" aria-hidden="true">{isAccepted ? "✓" : isRejected ? "✖" : "i"}</span>
                          <span>
                            <small>Suggerimento {index + 1} di {coachSuggestions.length}</small>
                            <b>{suggestion.title}</b>
                            <small><b>Categoria:</b> {suggestion.category_label}</small>
                            <small><b>Sezione:</b> {suggestion.section}</small>
                            <small>{suggestion.reason || suggestion.description}</small>
                            <small><b>Testo originale:</b> {previewSuggestionText(suggestion.original_text, Boolean(expandedCoachSuggestionText[`${suggestion.id}:original`]))}</small>
                            {suggestion.original_text.length > 300 && (
                              <button className="inline-link-button" type="button" onClick={() => toggleCoachSuggestionPreview(suggestion.id, "original")}>
                                {expandedCoachSuggestionText[`${suggestion.id}:original`] ? "Mostra meno" : "Mostra di piu"}
                              </button>
                            )}
                            <small><b>Modifica proposta:</b> {previewSuggestionText(suggestion.proposed_text, Boolean(expandedCoachSuggestionText[`${suggestion.id}:proposed`]))}</small>
                            {suggestion.proposed_text.length > 300 && (
                              <button className="inline-link-button" type="button" onClick={() => toggleCoachSuggestionPreview(suggestion.id, "proposed")}>
                                {expandedCoachSuggestionText[`${suggestion.id}:proposed`] ? "Mostra meno" : "Mostra di piu"}
                              </button>
                            )}
                            {suggestion.keywords_added.length > 0 && (
                              <small><b>Competenze valorizzate:</b> {suggestion.keywords_added.join(", ")}</small>
                            )}
                            <small className={`suggestion-status-pill ${suggestionStatus}`}>
                              Stato: {isAccepted ? "accettato" : isRejected ? "rifiutato" : "in attesa"}
                            </small>
                            <div className="suggestion-choice-actions" aria-label={`Scelta per ${suggestion.title}`}>
                              <button
                                className={`suggestion-choice-button accept ${isAccepted ? "active" : ""}`}
                                type="button"
                                aria-pressed={isAccepted}
                                onClick={() => updateCoachSuggestionStatus(suggestion.id, "accepted")}
                              >
                                <span aria-hidden="true">✓</span>
                                Accetta
                              </button>
                              <button
                                className={`suggestion-choice-button reject ${isRejected ? "active" : ""}`}
                                type="button"
                                aria-pressed={isRejected}
                                onClick={() => updateCoachSuggestionStatus(suggestion.id, "rejected")}
                              >
                                <span aria-hidden="true">✖</span>
                                Rifiuta
                              </button>
                            </div>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="cv-strategy-note">
                    Nessun suggerimento applicabile generato. Puoi continuare aggiungendo informazioni extra reali.
                  </p>
                )}
                {decidedCoachSuggestions.length > 0 && (
                  <div className="reviewed-choice-list">
                    {decidedCoachSuggestions.map((item) => {
                      const status = selectedCoachSuggestions[item.id];
                      return (
                        <div className={`reviewed-choice ${status}`} key={`reviewed-${item.id}`}>
                          <span>{status === "accepted" ? "✓" : "×"}</span>
                          <strong>{item.title}</strong>
                          <small>{status === "accepted" ? "Accettato" : "Rifiutato"}</small>
                          <button
                            className="reviewed-choice-edit"
                            type="button"
                            onClick={() => updateCoachSuggestionStatus(item.id, "pending")}
                          >
                            Modifica
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <button
                className="cv-next-button"
                type="button"
                onClick={() => setCvOptimizationStage(1)}
                disabled={!allCoachSuggestionsReviewed}
              >
                {allCoachSuggestionsReviewed ? "Continua con le skill suggerite" : "Valuta tutti i suggerimenti per continuare"}
              </button>

              <button
                className="cv-next-button cv-return-analysis-button"
                type="button"
                onClick={() => {
                  setCvOptimizationStage(0);
                  transitionToStep("cv-strategy");
                }}
              >
                Torna all'analisi
              </button>
            </>
          )}

          {cvOptimizationStage === 0 && (
            <>
          <div className="cv-strategy-section">
            <div className="cv-strategy-section-title">
              <span>?</span>
              <h3>Hard skill e soft skill</h3>
            </div>
            {currentSkillConfirmation ? (
              <div className="ai-suggestion-card-list">
                {[currentSkillConfirmation].map((item) => {
                  const index = proposedSkillConfirmationItems.findIndex((candidate) => candidate.id === item.id);
                  const itemStatus = item.status === "confirmed" ? "accepted" : item.status;
                  const isAccepted = itemStatus === "accepted";
                  const isRejected = itemStatus === "rejected";

                  return (
                    <div className={`coach-suggestion-option skill-confirmation-card ai-suggestion-card ${itemStatus}`} key={item.id}>
                      <span className="suggestion-state-icon" aria-hidden="true">{isAccepted ? "✓" : isRejected ? "✖" : "i"}</span>
                      <span>
                        <small>Skill {index + 1} di {proposedSkillConfirmationItems.length}</small>
                        <b>{item.name}</b>
                        <small><b>Categoria:</b> {getConfirmationCategoryLabel(item.category)}</small>

                        <label className="cv-additional-field">
                          <span>Contesto reale d'uso (facoltativo)</span>
                          <textarea
                            value={item.user_example}
                            onChange={(event) => updateSkillConfirmationDetail(item.id, event.target.value)}
                            placeholder={
                              item.category === "soft_skill"
                                ? "Descrivi una situazione reale in cui hai dimostrato questa competenza, senza inventare nuove skill..."
                                : "Descrivi un progetto, corso o esperienza reale in cui hai usato questa competenza..."
                            }
                            rows={2}
                          />
                        </label>
                        <small className={`suggestion-status-pill ${itemStatus}`}>
                          Stato: {isAccepted ? "accettato" : isRejected ? "rifiutato" : "in attesa"}
                        </small>
                        <div className="suggestion-choice-actions" aria-label={`Scelta per ${item.name}`}>
                          <button
                            className={`suggestion-choice-button accept ${isAccepted ? "active" : ""}`}
                            type="button"
                            aria-pressed={isAccepted}
                            onClick={() => updateSkillConfirmation(item.id, "accepted")}
                          >
                            <span aria-hidden="true">✓</span>
                            Accetta
                          </button>
                          <button
                            className={`suggestion-choice-button reject ${isRejected ? "active" : ""}`}
                            type="button"
                            aria-pressed={isRejected}
                            onClick={() => updateSkillConfirmation(item.id, "rejected")}
                          >
                            <span aria-hidden="true">✖</span>
                            Rifiuta
                          </button>
                        </div>
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="cv-strategy-note">Nessuna nuova skill specifica da valutare.</p>
            )}
            {decidedSkillConfirmations.length > 0 && (
              <div className="reviewed-choice-list">
                {decidedSkillConfirmations.map((item) => {
                  const status = item.status === "confirmed" ? "accepted" : item.status;
                  return (
                    <div className={`reviewed-choice ${status}`} key={`reviewed-skill-${item.id}`}>
                      <span>{status === "accepted" ? "✓" : "×"}</span>
                      <strong>{item.name}</strong>
                      <small>{status === "accepted" ? "Accettato" : "Rifiutato"}</small>
                      <button
                        className="reviewed-choice-edit"
                        type="button"
                        onClick={() => updateSkillConfirmation(item.id, "pending")}
                      >
                        Modifica
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <button
            className="cv-next-button"
            type="button"
            onClick={() => setCvOptimizationStage(1)}
            disabled={!allSkillConfirmationsReviewed}
          >
            {allSkillConfirmationsReviewed ? "Continua al riepilogo" : "Valuta tutte le skill per continuare"}
          </button>
            </>
          )}

          {cvOptimizationStage === 1 && (
            <>
          <div className="cv-review-summary">
            <section className="cv-review-card">
              <header className="cv-review-card-header">
                <div className="cv-review-card-title">
                  <span className="cv-review-icon target">⊙</span>
                  <h3>Candidatura</h3>
                </div>
                <button className="cv-review-edit-button" type="button" onClick={() => transitionToStep("personalize")}>
                  Modifica
                </button>
              </header>
              <div className="cv-review-fields">
                <div>
                  <span>Azienda</span>
                  <strong>{cvStrategyTargetCompany}</strong>
                </div>
                <div>
                  <span>Ruolo</span>
                  <strong>{cvStrategyTargetRole}</strong>
                </div>
              </div>
            </section>

            <section className="cv-review-card" hidden>
              <header className="cv-review-card-header">
                <div className="cv-review-card-title">
                  <span className="cv-review-icon idea">✧</span>
                  <h3>Suggerimenti</h3>
                </div>
                <button className="cv-review-edit-button" type="button" onClick={() => setCvOptimizationStage(0)}>
                  Modifica
                </button>
              </header>
              <div className="cv-review-status-row">
                <span>Applicati</span>
                <strong>✓ {cvSummaryApplicationStatus}</strong>
              </div>
              {selectedCoachSuggestionItems.length > 0 && (
                <div className="cv-review-compact-list">
                  {selectedCoachSuggestionItems.slice(0, 4).map((item, index) => (
                    <span key={`review-suggestion-${item.id || index}`}>{item.title}</span>
                  ))}
                </div>
              )}
            </section>

            <section className="cv-review-card">
              <header className="cv-review-card-header">
                <div className="cv-review-card-title">
                  <span className="cv-review-icon star">☆</span>
                  <h3>Skill accettate</h3>
                </div>
                <button className="cv-review-edit-button" type="button" onClick={() => setCvOptimizationStage(0)}>
                  Modifica
                </button>
              </header>
              {[
                ["HARD", cvSummaryAcceptedSkillGroups.hard],
                ["SOFT", cvSummaryAcceptedSkillGroups.soft],
              ].map(([label, items]) => (
                <div className="cv-review-skill-row" key={`review-skill-${label}`}>
                  <div className="cv-review-divider">
                    <span>{label}</span>
                  </div>
                  {items.length > 0 ? (
                    <div className="cv-review-tags">
                      {items.map((item) => (
                        <span key={`${label}-${item}`}>{item}</span>
                      ))}
                    </div>
                  ) : (
                    <p>Nessuna skill confermata.</p>
                  )}
                </div>
              ))}
            </section>

            <section className="cv-review-card">
              <header className="cv-review-card-header">
                <div className="cv-review-card-title">
                  <span className="cv-review-icon plus">+</span>
                  <h3>Informazioni extra</h3>
                </div>
              </header>
              <div className="cv-review-extra-editor">
                <p className="cv-strategy-note">
                  Aggiungi solo informazioni vere e utili: verranno riscritte e inserite nelle sezioni più adatte del CV, senza creare doppioni.
                </p>

                {CV_ADDITIONAL_DATA_FIELDS
                  .map((field) => (
                    <label
                      className={[
                        "cv-additional-field",
                        cvFieldErrors.additional[field.key] ? "has-error" : "",
                      ].filter(Boolean).join(" ")}
                      key={field.key}
                    >
                      <span>{field.label}</span>
                      <textarea
                        value={cvAdditionalData[field.key] || ""}
                        onChange={(event) => updateCvAdditionalData(field.key, event.target.value)}
                        placeholder="Descrivi fatti, contesto, strumenti utilizzati e risultati reali."
                        rows={field.key === "additional_notes" ? 4 : 3}
                      />
                      {cvFieldErrors.additional[field.key] && (
                        <small className="cv-field-error">{cvFieldErrors.additional[field.key]}</small>
                      )}
                    </label>
                  ))}

            

                {cvAdditionalDataError && (
                  <p className="cv-additional-error">{cvAdditionalDataError}</p>
                )}
              </div>

              {cvSummarySkillExampleItems.length > 0 && (
                <div className="cv-review-extra-list">
                  <strong>Esempi scritti nelle skill accettate</strong>
                  {cvSummarySkillExampleItems.map((item, index) => (
                    <div key={`review-skill-example-${index}`}>
                      <strong>{item.title}</strong>
                      <p>{item.detail}</p>
                    </div>
                  ))}
                </div>
              )}

              {cvSummaryAdditionalItems.length > 0 && (
                <div className="cv-review-extra-list">
                  <strong>Informazioni aggiuntive compilate</strong>
                  {cvSummaryAdditionalItems.map((item, index) => (
                    <div key={`review-extra-${index}`}>
                      <strong>{item.title}</strong>
                      <p>{item.detail}</p>
                    </div>
                  ))}
                </div>
              )}

              {cvSummaryExtraItems.length === 0 && (
                <p className="cv-review-empty">Nessuna informazione extra aggiunta.</p>
              )}
            </section>
          </div>

          <div className="cv-stage-actions">
            <button className="cv-next-button" type="button" onClick={() => setCvOptimizationStage(2)}>
              Continua alla generazione
            </button>
            <button className="secondary-button" type="button" onClick={() => setCvOptimizationStage(0)}>
              Torna alle skill
            </button>
          </div>
            </>
          )}

          {cvOptimizationStage === 2 && (
          <div className="cv-generation-card">
            <div className="cv-generation-copy">
              <h3>Cosa verrà generato</h3>
              <p>
                Un CV ottimizzato per <strong>{cvStrategyTargetRole}</strong> presso <strong>{cvStrategyTargetCompany}</strong>, mantenendo stile e struttura originali.
              </p>
            </div>

            <div className="cv-generation-summary">
              <div>
                <span aria-hidden="true">✓</span>
                <p><strong>{acceptedSkillConfirmations.length}</strong> competenze confermate per il CV</p>
              </div>
              <div>
                <span aria-hidden="true">✓</span>
                <p><strong>{rejectedSkillConfirmations.length}</strong> competenze escluse</p>
              </div>
              <div>
                <span aria-hidden="true">✓</span>
                <p>
                  {cvSummaryExtraItems.length > 0
                    ? `${cvSummaryExtraItems.length} informazioni extra aggiunte`
                    : "Nessuna informazione extra aggiunta"}
                </p>
              </div>
            </div>

            <div className="cv-generation-actions">
              <button
                className="cv-generation-button"
                type="button"
                onClick={optimizeCv}
                disabled={loading}
              >
                <SparkleIcon size={14} />
                {loading ? "Sto generando il tuo CV ottimizzato..." : "Genera CV ottimizzato"}
              </button>
            </div>
          </div>
          )}
        </section>
      )}

      {step === "cv-optimized" && (
        <section className="cv-ready-page">
          <div className="cv-ready-heading">
            <span>CV ottimizzato generato</span>
            <h2>Il tuo CV è pronto</h2>
            <p>Ottimizzato per {optimizedCv?.target_role || cvStrategyTargetRole} presso {optimizedCv?.target_company || cvStrategyTargetCompany}.</p>
          </div>

          <div className="cv-ready-card">
            {optimizedCv && (
              <>
                <div className="cv-ready-file">
                  <span className="cv-ready-file-icon">
                    <FileDocumentIcon />
                  </span>
                  <div>
                    <strong>{optimizedCv.filename || "CV ottimizzato"}</strong>
                    <p>Nome file</p>
                  </div>
                </div>

                <div className="cv-ready-metrics">
                  <div>
                    <strong>{optimizedCv.analysis_score || cvStrategyOverallScore || 0}</strong>
                    <span>Punteggio CV</span>
                  </div>
                  <div>
                    <strong>{optimizedCv.applied_changes_count ?? 0}</strong>
                    <span>Modifiche applicate</span>
                  </div>
                </div>

                {cvScoreComparison?.before && cvScoreComparison?.after && (
                  <div className="cv-score-comparison">
                    <strong>Confronto punteggi prima e dopo</strong>
                    <div>
                      {[
                        ["Generale", "overall_score"],
                        ["ATS", "ats_score"],
                        ["Ruolo", "role_match_score"],
                        ["Completezza", "completeness_score"],
                      ].map(([label, key]) => {
                        const delta = cvScoreComparison.delta?.[key] || 0;
                        return (
                          <span className={delta > 0 ? "improved" : delta < 0 ? "reduced" : ""} key={key}>
                            <b>{label}</b>
                            {cvScoreComparison.before[key]} → {cvScoreComparison.after[key]}
                            <small>{delta > 0 ? `+${delta}` : delta}</small>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="cv-ready-date">
                  <span>
                    <CalendarIcon />
                    Generato il
                  </span>
                  <strong>{formatGeneratedDate(optimizedCv.generated_at || optimizedCv.created_at)}</strong>
                </div>
              </>
            )}

            {optimizedCv?.quality_review?.local_checks_completed && (
              <div className="cv-ready-checks">
                <CheckCircleIcon size={20} />
                <div>
                  <strong>Controlli finali completati</strong>
                  <p>
                    {optimizedCv.quality_review.review_provider === "llm"
                      ? "Qualità, struttura e modifiche applicate sono state verificate."
                      : "Struttura, contenuti e modifiche applicate sono stati verificati localmente."}
                  </p>
                </div>
              </div>
            )}

            <div className="cv-ready-checks">
              <CheckCircleIcon size={20} />
              <div>
                <strong>Controllo finale consigliato</strong>
                <p>
                  Il CV è stato ottimizzato. Stile e formattazione non sono garantiti al 100%: ti consigliamo di controllare il file finale prima di inviarlo.
                </p>
              </div>
            </div>

            {optimizedCv?.file_base64 ? (
              <a
                className="cv-ready-download"
                href={`data:${optimizedCv.content_type};base64,${optimizedCv.file_base64}`}
                download={optimizedCv.filename || "cv-ottimizzato.pdf"}
              >
                <DownloadIcon />
                Scarica {optimizedCv.content_type?.includes("wordprocessingml") ? "DOCX" : "PDF"}
              </a>
            ) : (
              <button className="cv-ready-download" type="button" onClick={() => transitionToStep("cv-optimize-details")}>
                Torna alla generazione
              </button>
            )}

            {(optimizedCv?.alternatives || []).length > 0 && (
              <div className="cv-ready-alternatives">
                {optimizedCv.alternatives.map((file) => (
                  <a
                    href={`data:${file.content_type};base64,${file.file_base64}`}
                    download={file.filename || "cv-ottimizzato.docx"}
                    key={file.filename}
                  >
                    <DownloadIcon />
                    Scarica anche {file.filename?.toLowerCase().endsWith(".docx") ? "DOCX" : "file alternativo"}
                  </a>
                ))}
              </div>
            )}

            {optimizedCvWarnings.length > 0 && (
              <div className="cv-ready-warnings">
                <h3>Avvisi di verifica</h3>
                <p>
                  Alcune frasi potrebbero richiedere un controllo manuale prima dell'invio.
                </p>
                {optimizedCvWarnings.map((warning, index) => (
                  <div className="cv-strategy-item warning" key={`${warning.claim}-${index}`}>
                    <span>!</span>
                    <div>
                      <strong>{warning.reason || "Possibile informazione non verificata"}</strong>
                      <p>{warning.claim}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="cv-ready-actions">
            <button type="button" onClick={startCvPath}>
              <SparkleIcon size={17} />
              Crea un altro CV ottimizzato
            </button>
            <button type="button" onClick={() => transitionToStep("gym")}>
              <MicrophoneIcon />
              Vai al colloquio
            </button>
            <button type="button" onClick={() => transitionToStep("profile")}>
              <ProfileIcon />
              Vai al profilo
            </button>
          </div>
        </section>
      )}

      {/* Old CV strategy markup removed
        <section>
            <div
              className="cv-score-ring"
              style={{
                background: `radial-gradient(circle at center, #ffffff 58%, transparent 60%), conic-gradient(#248269 0 ${cvOptimizationAnalysis?.score || 0}%, #dfe8ef ${cvOptimizationAnalysis?.score || 0}% 100%)`,
              }}
            >
              <span>{cvOptimizationAnalysis?.score || 0}%</span>
            </div>
            <h3>{cvOptimizationAnalysis?.headline || "Analisi completata"}</h3>
            <p>
              {cvOptimizationAnalysis?.summary ||
                "Abbiamo confrontato il tuo CV con ruolo, azienda e dati dell'annuncio per individuare priorita di ottimizzazione."}
            </p>
            {cvOptimizationAnalysis?.score_explanation?.summary && (
              <p className="cv-strategy-note">{cvOptimizationAnalysis.score_explanation.summary}</p>
            )}
          </div>

          <div className="cv-strategy-section">
            <div className="cv-strategy-section-title">
              <span className="success">+</span>
              <h3>Punti di Forza</h3>
            </div>

            {(cvOptimizationAnalysis?.strengths || []).map((item, index) => (
              <div className="cv-strategy-item success" key={`${item.title}-${index}`}>
                <span>✓</span>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.description}</p>
                  {item.coach_tip && <small>{item.coach_tip}</small>}
                </div>
              </div>
            ))}
          </div>

          <div className="cv-strategy-section">
            <div className="cv-strategy-section-title">
              <span className="warning">~</span>
              <h3>Miglioramenti consigliati</h3>
            </div>

            {(cvOptimizationAnalysis?.improvements || []).map((item, index) => (
              <div className="cv-strategy-item warning" key={`${item.title}-${index}`}>
                <span>!</span>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.description}</p>
                  {item.coach_tip && <small>{item.coach_tip}</small>}
                </div>
              </div>
            ))}
          </div>

          {(cvOptimizationAnalysis?.sources || []).length > 0 && (
            <div className="cv-strategy-section">
              <div className="cv-strategy-section-title">
                <span>i</span>
                <h3>Fonti candidatura</h3>
              </div>
              <div className="source-list">
                {cvOptimizationAnalysis.sources.slice(0, 4).map((source, index) => (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    key={`${source.url}-${index}`}
                  >
                    {source.title || source.url}
                  </a>
                ))}
              </div>
            </div>
          )}

          <button className="cv-next-button" onClick={() => transitionToStep("home")}>
            Torna alla home
            <span>-&gt;</span>
          </button>
        </section>
      */}

      {step === "cv-view" && (
        <section className="cv-flow-page">
          <div className="cv-analysis-heading">
            <h2>CV Master</h2>
            <p>{profile.cv_filename || "Nessun CV caricato"}</p>
          </div>

          <div className="cv-view-card">
            <div className="cv-view-header">
              <span>CV</span>
              <div>
                <strong>{cvPreview?.filename || profile.cv_filename || "CV non caricato"}</strong>
                <p>{cvPreview?.uploaded_at || profile.cv_uploaded_at ? `Caricato il ${cvPreview?.uploaded_at || profile.cv_uploaded_at}` : "Carica il tuo CV master."}</p>
              </div>
            </div>

            {cvPreview?.file_base64 && /\.(pdf|docx)$/i.test(cvPreview?.filename || "") ? (
              <div className="cv-word-preview">
                <strong>Documento {cvPreview.filename.toLowerCase().endsWith(".pdf") ? "PDF" : "Word"} caricato</strong>
                <p>
                  Il CV e salvato come file master. Aprilo per visualizzarlo nel programma associato.
                </p>
                <a
                  href={`data:${cvPreview.content_type};base64,${cvPreview.file_base64}`}
                  download={cvPreview.filename}
                >
                  Apri CV
                </a>
              </div>
            ) : cvPreview?.previewFinalCvContent && Object.keys(cvPreview.previewFinalCvContent).length > 0 ? (
              <div className="cv-preview-structured" style={{ textAlign: 'left' }}>
                {Object.entries(cvPreview.previewFinalCvContent).map(([section, content]) => (
                  <div key={section} className="cv-preview-section" style={{ marginBottom: '1rem' }}>
                    <h3 style={{ textTransform: 'uppercase', fontSize: '1.1em', borderBottom: '1px solid #ddd', paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>{section}</h3>
                    <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', margin: 0, fontSize: '0.95em' }}>{content}</pre>
                  </div>
                ))}
              </div>
            ) : cvPreview?.text || profile.cv_text ? (
              <pre className="cv-preview-text">{cvPreview?.text || profile.cv_text}</pre>
            ) : (
              <div className="empty-message">
                Caricamento anteprima CV in corso oppure file non disponibile.
              </div>
            )}

            <div className="actions">
              <button className="primary-button" onClick={() => transitionToStep("cv-upload")}>
                Sostituisci CV
              </button>
              <button className="secondary-button" onClick={() => transitionToStep("profile")}>
                Torna al profilo
              </button>
            </div>
          </div>
        </section>
      )}

      {step === "profile" && (
        <section className="profile-dashboard">
          <div className="profile-page-title">
            <div>
              <span>Area personale</span>
              <h2>Il tuo profilo</h2>
              <p>Monitora i progressi e completa il tuo percorso professionale.</p>
            </div>
          </div>

          <div className="profile-hero-card">
            <div className="profile-hero-main">
              <div className="profile-avatar-large">
                <input
                  ref={profileImageInputRef}
                  className="profile-image-input"
                  type="file"
                  accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                  onChange={updateProfileImage}
                />
                <button
                  className="profile-avatar-button"
                  type="button"
                  onClick={() => profileImageInputRef.current?.click()}
                  disabled={profileImageSaving}
                  aria-label={profile.profile_image_data_url ? "Cambia foto profilo" : "Aggiungi foto profilo"}
                >
                  {profile.profile_image_data_url ? (
                    <img src={profile.profile_image_data_url} alt="Foto profilo" />
                  ) : (
                    <span>{profileInitial}</span>
                  )}
                </button>
                <button
                  className="profile-avatar-add"
                  type="button"
                  onClick={() => profileImageInputRef.current?.click()}
                  disabled={profileImageSaving}
                  aria-label={profile.profile_image_data_url ? "Cambia foto profilo" : "Aggiungi foto profilo"}
                  title={profile.profile_image_data_url ? "Cambia foto" : "Aggiungi foto"}
                >
                  +
                </button>
              </div>
              <div className="profile-hero-copy">
                <span className="profile-status-label">
                  {hasProfileDetails ? "Profilo professionale" : "Profilo professionale"}
                </span>
                <h2>{profile.name || "Il tuo profilo"}</h2>
                <p>{hasTargetRole ? profile.target_role : "Ruolo target non impostato"}</p>
                <div className="profile-image-controls">
                  {profile.profile_image_data_url && (
                    <button type="button" onClick={removeProfileImage} disabled={profileImageSaving}>
                      Rimuovi
                    </button>
                  )}
                  {profileImageMessage && <span role="status">{profileImageMessage}</span>}
                </div>
              </div>
            </div>
            <button className="profile-analysis-button" type="button" onClick={() => transitionToStep("cv-digital")}>
              <SparkleIcon size={20} />
              Analisi digitale
            </button>
          </div>

          <div className="profile-overview-grid">
            <div className="profile-progress-card">
              <div className="profile-card-heading">
                <div>
                  <span>Completamento profilo</span>
                  <strong>{profileCompletionPercentage}% completato</strong>
                </div>
                <span className="profile-completion-score">{profileCompletionPercentage}%</span>
              </div>
              <div
                className="profile-progress-track"
                role="progressbar"
                aria-label="Completamento profilo"
                aria-valuemin="0"
                aria-valuemax="100"
                aria-valuenow={profileCompletionPercentage}
              >
                <span style={{ width: `${profileCompletionPercentage}%` }} />
              </div>
              <p>
                {completedProfileSteps} di {totalProfileSteps} elementi completati.
              </p>
            </div>

            <div className="profile-path-card">
              <div className="profile-card-heading">
                <div>
                  <span>Percorso CareerCoach</span>
                  <strong>I prossimi passi</strong>
                </div>
                <span className="profile-path-count">
                  {careerPathItems.filter((item) => item.complete).length}/{careerPathItems.length}
                </span>
              </div>
              <div className="profile-checklist">
                {careerPathItems.map((item) => (
                  <div className={item.complete ? "complete" : ""} key={item.label}>
                    <span aria-hidden="true" />
                    <p>{item.label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="profile-content-grid">
            <div className="profile-dashboard-section">
              <div className="profile-section-title">
                <div>
                  <span>Target professionali</span>
                  <h3>Aziende preferite</h3>
                </div>
              </div>

              {preferredCompanies.length > 0 ? (
                <div className="favorite-company-grid">
                  {preferredCompanies.map((item) => (
                    <div className="favorite-company-card" key={item}>
                      <span>{item.charAt(0).toUpperCase()}</span>
                      <div>
                        <strong>{item}</strong>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="profile-empty-state">
                  <span className="profile-empty-icon" aria-hidden="true">A</span>
                  <div>
                    <strong>Nessuna azienda preferita rilevata</strong>
                    <p>Le aziende compariranno automaticamente quando le inserirai in Personalizza la tua esperienza.</p>
                  </div>
                </div>
              )}
            </div>

            <div className="profile-dashboard-section profile-documents-section">
              <div className="profile-section-title">
                <div>
                  <span>Archivio personale</span>
                  <h3>I tuoi documenti</h3>
                </div>
              </div>

              <div className="document-group">
                <div className="document-group-heading">
                  <strong>CV Master</strong>
                  <span>Documento principale</span>
                </div>
                <div className="document-item">
                  <span>CV</span>
                  <div>
                    <strong>{profile.cv_filename || "CV Master non caricato"}</strong>
                    <p>{profile.cv_filename ? "File principale usato per analisi e ottimizzazioni." : "Carica il tuo CV per iniziare il percorso."}</p>
                  </div>
                  <div className="document-actions">
                    <button className="secondary-button change-cv-button" type="button" onClick={() => transitionToStep("cv-upload")}
                      aria-label={profile.cv_filename ? "Cambia CV" : "Carica CV"}
                      title={profile.cv_filename ? "Cambia CV" : "Carica CV"}
                    >
                      {profile.cv_filename ? "Cambia CV" : "Carica CV"}
                    </button>
                  </div>
                </div>
              </div>

              <div className="document-group">
                <div className="document-group-heading">
                  <strong>CV ottimizzati</strong>
                  <span>{optimizedCvsList.length} {optimizedCvsList.length === 1 ? "versione" : "versioni"}</span>
                </div>
                {latestOptimizedCv ? (
                  <div className="document-item document-item-optimized">
                    <span>AI</span>
                    <div>
                      <strong>{latestOptimizedCv.target_role || "CV Ottimizzato"}</strong>
                      <p>{`${latestOptimizedCv.target_company || "Azienda"}${latestOptimizedCv.created_at ? ` - ${latestOptimizedCv.created_at}` : ""}`}</p>
                    </div>
                    <div className="document-actions">
                      {latestOptimizedCv.has_docx && (
                        <a href={`${API_URL}${latestOptimizedCv.docx_download_url}`} download aria-label="Scarica DOCX" title="Scarica DOCX">DOCX</a>
                      )}
                      {latestOptimizedCv.has_pdf && (
                        <a href={`${API_URL}${latestOptimizedCv.pdf_download_url}`} download aria-label="Scarica PDF" title="Scarica PDF">PDF</a>
                      )}
                      {optimizedCvsList.length > 1 && (
                        <button className="document-text-button" type="button" onClick={() => setShowOptimizedCvVersions((current) => !current)}>
                          {showOptimizedCvVersions ? "Chiudi" : "Tutte"}
                        </button>
                      )}
                      <button className="danger-icon-button" type="button" onClick={() => deleteOptimizedCv(latestOptimizedCv.id)} disabled={loading} aria-label="Elimina ultimo CV ottimizzato" title="Elimina ultimo CV ottimizzato">
                        <TrashIcon />
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="profile-empty-state document-empty-state">
                    <span className="profile-empty-icon" aria-hidden="true">AI</span>
                    <div>
                      <strong>Nessun CV ottimizzato</strong>
                      <p>Genera una versione mirata per il ruolo e l'azienda che vuoi raggiungere.</p>
                    </div>
                    <button type="button" onClick={() => transitionToStep(hasMasterCv ? "home" : "cv-upload")}>
                      {hasMasterCv ? "Vai agli strumenti CV" : "Carica CV Master"}
                    </button>
                  </div>
                )}
                {showOptimizedCvVersions && optimizedCvsList.slice(1).map((item) => (
                  <div className="document-item document-item-version" key={`profile-optimized-${item.id}`}>
                    <span>CV</span>
                    <div>
                      <strong>{item.target_role || "Ruolo"} - {item.target_company || "Azienda"}</strong>
                      <p>{item.created_at || ""}{item.generation_status ? ` - ${item.generation_status}` : ""}</p>
                    </div>
                    <div className="document-actions">
                      {item.has_docx && (
                        <a href={`${API_URL}${item.docx_download_url}`} download aria-label="Scarica DOCX" title="Scarica DOCX">DOCX</a>
                      )}
                      {item.has_pdf && (
                        <a href={`${API_URL}${item.pdf_download_url}`} download aria-label="Scarica PDF" title="Scarica PDF">PDF</a>
                      )}
                      <button type="button" onClick={() => { setOptimizedCv(item); transitionToStep("cv-optimized"); }} aria-label="Visualizza dettagli" title="Visualizza dettagli">
                        <EyeIcon />
                      </button>
                      <button className="danger-icon-button" type="button" onClick={() => deleteOptimizedCv(item.id)} disabled={loading} aria-label="Elimina CV ottimizzato" title="Elimina CV ottimizzato">
                        <TrashIcon />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="profile-danger-zone">
            <div>
              <span>Zona pericolosa</span>
              <strong>Elimina definitivamente il profilo</strong>
              <p>Questa azione rimuove account, CV e storico salvato in CareerCoach.</p>
            </div>
            <button type="button" onClick={deleteProfile} disabled={loading}>
              Elimina profilo
            </button>
          </div>

        </section>
      )}

      {step === "gym" && (
        <section className="card">
          <h2>Palestra dei colloqui</h2>
          <p className="section-description">
            Scegli tipologia di colloquio e livello di difficoltà.
            L’app genererà 10 domande realistiche e personalizzate per simulare un colloquio completo.
          </p>

          <div className="interview-context interview-context-form">
            <div className="field-card">
              <label htmlFor="gym-company">Azienda</label>
              <input
                id="gym-company"
                type="text"
                value={personalizeForm.company}
                placeholder={company || "Azienda Generica"}
                onChange={(event) => updatePersonalizeForm("company", event.target.value)}
              />
            </div>
            <div className="field-card">
              <label htmlFor="gym-role">Candidatura</label>
              <input
                id="gym-role"
                type="text"
                value={personalizeForm.role}
                placeholder={profile.target_role || "Ruolo da definire"}
                onChange={(event) => updatePersonalizeForm("role", event.target.value)}
              />
            </div>
            {personalizeForm.goal && (
              <div className="field-card full">
                <label>Obiettivo</label>
                <input
                  type="text"
                  value={personalizeForm.goal}
                  placeholder="Obiettivo specifico della candidatura"
                  onChange={(event) => updatePersonalizeForm("goal", event.target.value)}
                />
              </div>
            )}
          </div>

          {previousInterviewTargets.length > 0 && (
            <div className="previous-targets-card">
              <label>Usa un'azienda e candidatura già ottimizzate</label>
              <div className="previous-target-list">
                {previousInterviewTargets.map((target) => {
                  const isActive = target.company === (personalizeForm.company.trim() || company) && target.role === (personalizeForm.role.trim() || profile.target_role);
                  return (
                    <button
                      key={target.id}
                      type="button"
                      className={isActive ? "target-chip active" : "target-chip"}
                      onClick={() => {
                        updatePersonalizeForm("company", target.company);
                        updatePersonalizeForm("role", target.role);
                      }}
                    >
                      <strong>{target.company}</strong>
                      <span>{target.role}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <h3 className="sub-title">Tipo di allenamento</h3>

          <div className="choice-grid three-columns">
            <button
              className={interviewType === "conoscitive_motivazionali" ? "choice active" : "choice"}
              onClick={() => setInterviewType("conoscitive_motivazionali")}
            >
              <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span
                  aria-hidden="true"
                  style={{
                    width: 40,
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <BrainIcon size={24} />
                </span>
                Conoscitive e motivazionali
              </h3>
              <p>
                Domande su chi sei, obiettivi, aspettative, motivazione,
                azienda, percorso personale e lavoro di gruppo.
              </p>
            </button>

            <button
              className={interviewType === "tecniche" ? "choice active" : "choice"}
              onClick={() => setInterviewType("tecniche")}
            >
              <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span
                  aria-hidden="true"
                  style={{
                    width: 40,
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <HammerIcon size={24} />
                </span>
                Tecniche
              </h3>
              <p>
                Domande specifiche sul ruolo scelto, sulle competenze richieste,
                sugli strumenti e sulle capacità operative.
              </p>
            </button>

            <button
              className={interviewType === "logica" ? "choice active" : "choice"}
              onClick={() => setInterviewType("logica")}
            >
              <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span
                  aria-hidden="true"
                  style={{
                    width: 40,
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <PuzzleIcon size={24} />
                </span>
                Logica e ragionamento
              </h3>
              <p>
                Domande a trabocchetto, serie numeriche o alfabetiche,
                stime, problem solving e ragionamento.
              </p>
            </button>
          </div>

          <label>Difficoltà</label>
          <div className="difficulty-grid">
            {difficultyOptions.map((option) => {
              const starsByDifficulty = {
                base: { stars: "★" },
                intermedio: { stars: "★★" },
                avanzato: { stars: "★★★" },
              };

              const starSpec = starsByDifficulty[option.value] || { stars: "★" };

              return (
                <button
                  key={option.value}
                  type="button"
                  className={difficulty === option.value ? "difficulty-pill active" : "difficulty-pill"}
                  onClick={() => setDifficulty(option.value)}
                >
                  <span
                    aria-hidden="true"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      marginRight: 8,
                      verticalAlign: "middle",
                      color: "#f5c400",
                      fontWeight: 900,
                      fontSize: 18,
                      lineHeight: 1,
                    }}
                  >
                    {starSpec.stars}
                  </span>
                  {option.label}
                </button>
              );
            })}
          </div>
          <p className="difficulty-description">{currentDifficulty.description}</p>

          <div className="actions" style={{ display: "flex", gap: 12, alignItems: "stretch" }}>
            <button
              className="digital-cta-button gym-cta-shape"
              onClick={generateQuestion}
              disabled={loading}
              type="button"
              style={{
                flex: 1,
                minWidth: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
              }}
            >
              <span className="digital-cta-sparkle" aria-hidden="true" style={{ display: "inline-flex" }}>
                <SparkleIcon size={18} />
              </span>
              Genera 10 domande
            </button>

              <button
                className="secondary-button gym-cta-shape"
                onClick={loadHistory}
                disabled={loading}
                type="button"
                style={{
                  width: "100%",
                  flex: "unset",
                  minWidth: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  paddingLeft: 8,
                  paddingRight: 8,
                  fontSize: 14,
                  minHeight: 46,
                }}
              >
              Vedi storico
            </button>
          </div>
        </section>
      )}

      {step === "question" && (
        <section className="card chat-simulation-container" style={{ display: 'flex', flexDirection: 'column', height: '75vh', padding: 0, overflow: 'hidden', backgroundColor: 'var(--bg-light)' }}>
          <div className="chat-header" style={{ padding: '1rem 1.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#fff', zIndex: 10 }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Simulazione Colloquio</h2>
              <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Domanda {currentQuestionIndex + 1} di {questions.length || 10}
              </p>
            </div>
            <button 
              className="secondary-button" 
              onClick={() => transitionToStep("gym")} 
              style={{ margin: 0, padding: '6px 12px', fontSize: '0.85rem' }}
            >
              Esci
            </button>
          </div>

          <div className="chat-messages-scroll" ref={chatContainerRef} style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem', background: '#f8faff' }}>
            {allFeedbacks.map((item, index) => (
              <React.Fragment key={`turn-${index}`}>
                <div className="interviewer-container" style={{ margin: 0, justifyContent: 'flex-start' }}>
                  <div className="avatar-wrapper" style={{ width: '36px', height: '36px', minWidth: '36px' }}>
                    <div className="interviewer-avatar" style={{ padding: '3px' }}>
                      <img src={logoCareerCoach} alt="AI" className="avatar-logo" />
                    </div>
                  </div>
                  <div className="interviewer-content" style={{ maxWidth: '85%' }}>
                    <div className="question-bubble" style={{ background: '#fff', color: 'var(--text-primary)', borderRadius: '4px 16px 16px 16px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', padding: '12px 16px' }}>{item.question}</div>
                  </div>
                </div>
                <div className="user-chat-turn" style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <div className="user-bubble" style={{ background: 'var(--primary)', color: 'white', padding: '12px 16px', borderRadius: '16px 16px 4px 16px', maxWidth: '80%', fontSize: '0.95rem', boxShadow: '0 2px 8px rgba(36, 130, 105, 0.2)' }}>
                    {item.answer}
                  </div>
                </div>
              </React.Fragment>
            ))}

            {/* Turno corrente dell'intervistatore */}
            <div className="interviewer-container" style={{ margin: 0, justifyContent: 'flex-start', opacity: loading ? 0.6 : 1 }}>
              <div className="avatar-wrapper" style={{ width: '40px', height: '40px', minWidth: '40px' }}>
                <div className={`interviewer-avatar ${isSpeaking ? 'speaking' : ''}`}>
                  <img src={logoCareerCoach} alt="Logo" className="avatar-logo" />
                </div>
              </div>
              <div className="interviewer-content" style={{ maxWidth: '85%' }}>
                <div className="question-bubble" aria-live="polite" style={{ background: '#fff', borderRadius: '4px 18px 18px 18px', boxShadow: '0 2px 5px rgba(0,0,0,0.06)', padding: '14px 18px' }}>
                  {displayedText}
                  {displayedText.length < (question?.length || 0) && !loading && <span className="cursor">|</span>}
                </div>
              </div>
            </div>

            {loading && (
              <div className="interviewer-container" style={{ margin: '10px 0' }}>
                <div className="typing-indicator" style={{ fontStyle: 'italic', color: 'var(--text-secondary)', paddingLeft: '50px', fontSize: '0.9rem' }}>
                  Il coach sta valutando la risposta...
                </div>
              </div>
            )}
          </div>

          <div className="chat-input-bar" style={{ padding: '1.2rem 1.5rem', background: '#fff', borderTop: '1px solid var(--border-color)', boxShadow: '0 -4px 12px rgba(0,0,0,0.03)' }}>
            <div className="textarea-wrapper" style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', background: '#f0f2f5', padding: '8px 16px', borderRadius: '28px', border: '1px solid transparent', transition: 'border-color 0.2s' }}>
              <textarea
                id="answer"
                ref={answerRef}
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    // Permettiamo la chiamata anche se il testo è vuoto (sarà validato internamente)
                    if (!loading) evaluateAnswer();
                  }
                }}
                placeholder="Scrivi la tua risposta..."
                rows={1}
                style={{ flex: 1, border: 'none', background: 'transparent', padding: '10px 4px', resize: 'none', outline: 'none', fontSize: '1rem', minHeight: '40px' }}
              />
              <div style={{ display: 'flex', gap: '8px', paddingBottom: '4px', flexShrink: 0 }}>
              <button
                type="button"
                  className="chat-mic-button" 
                  style={{ position: 'static', margin: 0, background: isListening ? '#ff4d4d' : 'transparent', color: isListening ? '#fff' : 'var(--text-secondary)', width: '38px', height: '38px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', border: 'none', cursor: 'pointer' }}
                onClick={() => {
                  if (isListening) {
                    stopVoiceAnswer();
                  } else {
                    setAnswerMode("voice");
                    startVoiceAnswer();
                  }
                }}
                title="Usa il microfono"
                aria-label="Usa il microfono"
              >
                  <svg viewBox="0 0 24 24" aria-hidden="true" width="22" height="22" fill="currentColor">
                  <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 14 0h-2Zm-5 9a7 7 0 0 0 7-7h2a9 9 0 0 1-18 0h2a7 7 0 0 0 7 7Zm-1 2h2v2h-2v-2Z"/>
                </svg>
              </button>
              <button 
                className="send-message-btn" 
                onClick={evaluateAnswer} 
                disabled={loading || !answer.trim()}
                  style={{ position: 'static', margin: 0, background: 'var(--primary)', color: '#fff', border: 'none', width: '38px', height: '38px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', opacity: (loading || !answer.trim()) ? 0.6 : 1 }}
              >
                  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
              </button>
              </div>
            </div>
          </div>
        </section>
      )}

      {step === "feedback" && feedback && (
        <section className="card">
          <h2>Feedback del coach</h2>

          <div className="progress-question">
            Feedback domanda {currentQuestionIndex + 1} di {questions.length || 10}
          </div>

          <div className="score-main">
            <span>{feedback.total_score}</span>
            <p>Punteggio totale su 100</p>
          </div>

          <div className="scores-grid">
            <div>
              <strong>{feedback.clarity_score}</strong>
              <p>Chiarezza</p>
            </div>

            <div>
              <strong>{feedback.completeness_score}</strong>
              <p>Completezza</p>
            </div>

            <div>
              <strong>{feedback.relevance_score}</strong>
              <p>Pertinenza</p>
            </div>

            <div>
              <strong>{feedback.professionalism_score}</strong>
              <p>Professionalità</p>
            </div>

            <div>
              <strong>{feedback.synthesis_score}</strong>
              <p>Sintesi</p>
            </div>

            <div>
              <strong>{feedback.speaking_score}</strong>
              <p>Parlato</p>
            </div>
          </div>

          <div className="feedback-block">
            <h3>Valutazione del contenuto</h3>
            <p>{feedback.feedback}</p>
          </div>

          {feedback.speaking_feedback && (
            <div className="feedback-block">
              <h3>Valutazione del modo di parlare</h3>
              <p>{feedback.speaking_feedback}</p>
            </div>
          )}

          <div className="improved-answer">
            <h3>Risposta modello / migliorata</h3>
            <p>{feedback.improved_answer}</p>
          </div>

          {feedback.solution_explanation && (
            <div className="solution-block">
              <h3>Soluzione / ragionamento corretto</h3>
              <p>{feedback.solution_explanation}</p>
            </div>
          )}

          <div className="actions">
            {currentQuestionIndex < questions.length - 1 ? (
              <button className="primary-button" onClick={goToNextQuestion}>
                Prossima domanda
              </button>
            ) : (
              <button className="primary-button" onClick={loadHistory}>
                Concludi simulazione
              </button>
            )}

            <button className="secondary-button" onClick={startNewTraining}>
              Nuovo allenamento
            </button>
          </div>
        </section>
      )}

      {step === "interview-summary" && (
        <section className="card">
          <h2>Riepilogo Simulazione</h2>
          <p className="section-description" style={{ marginBottom: '2rem' }}>
            Ottimo lavoro! Hai completato tutte le domande
            {profile.target_role && profile.target_role !== "Da definire" && (
              <> per il ruolo di <strong>{profile.target_role}</strong></>
            )}
            {company && company !== "Azienda Generica" && (
              <> in <strong>{company}</strong></>
            )}.
          </p>

          <div className="score-main">
            <span>{sessionSummary.totalScore}</span>
            <p>Punteggio Medio Sessione</p>
          </div>

          <div className="scores-grid">
            <div>
              <strong>{sessionSummary.clarity}</strong>
              <p>Chiarezza</p>
            </div>
            <div>
              <strong>{sessionSummary.completeness}</strong>
              <p>Completezza</p>
            </div>
            <div>
              <strong>{sessionSummary.relevance}</strong>
              <p>Pertinenza</p>
            </div>
            <div>
              <strong>{sessionSummary.professionalism}</strong>
              <p>Professionalità</p>
            </div>
            <div>
              <strong>{sessionSummary.synthesis}</strong>
              <p>Sintesi</p>
            </div>
            <div>
              <strong>{sessionSummary.speaking}</strong>
              <p>Parlato</p>
            </div>
          </div>

          <h3 className="sub-title">Dettaglio Domande</h3>
          <div className="history-question-list" style={{ borderTop: 'none' }}>
            {allFeedbacks.map((item, index) => {
              const isQuestionExpanded = expandedHistoryQuestions.includes(`summary-${index}`);
              return (
                <div className="history-item" key={`summary-${index}`} style={{ background: '#fff' }}>
                  <div className="history-header">
                    <div style={{ flex: 1 }}>
                      <p style={{ margin: 0, fontWeight: 'bold', color: 'var(--primary)' }}>
                        Domanda {index + 1}
                      </p>
                      <p style={{ margin: '4px 0', fontSize: '1.1rem' }}>{item.question}</p>
                    </div>
                    <div className="score-pill" style={{ 
                      background: 'var(--primary-light)', 
                      padding: '8px 12px', 
                      borderRadius: '12px',
                      fontWeight: 'bold',
                      color: 'var(--primary)'
                    }}>
                      {item.feedback.total_score}/100
                    </div>
                  </div>

                  <button
                    type="button"
                    className="history-question-toggle"
                    onClick={() => toggleHistoryQuestion(`summary-${index}`)}
                  >
                    {isQuestionExpanded ? "Nascondi analisi" : "Vedi analisi e consigli"}
                  </button>

                  {isQuestionExpanded && (
                    <div className="history-question-details" style={{ marginTop: '1rem' }}>
                      {item.answer && (
                        <div className="feedback-block">
                          <h3>La tua risposta</h3>
                          <p>{item.answer}</p>
                        </div>
                      )}
                      <div className="feedback-block" style={{ marginTop: 0 }}>
                        <h3>Feedback</h3>
                        <p>{item.feedback.feedback}</p>
                      </div>

                      {item.feedback.speaking_feedback && (
                        <div className="feedback-block">
                          <h3>Parlato</h3>
                          <p>{item.feedback.speaking_feedback}</p>
                        </div>
                      )}

                      <div className="improved-answer">
                        <h3>Risposta Modello</h3>
                        <p>{item.feedback.improved_answer}</p>
                      </div>

                      {item.feedback.solution_explanation && (
                        <div className="solution-block">
                          <h3>Logica / Soluzione</h3>
                          <p>{item.feedback.solution_explanation}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="actions">
            <button className="primary-button" onClick={startNewTraining}>
              Nuovo Allenamento
            </button>
            <button className="secondary-button" onClick={() => transitionToStep("home")}>
              Torna alla Home
            </button>
          </div>
        </section>
      )}

      {step === "history" && (
        <section className="card">
          <h2>Storico allenamenti</h2>

          {history.length === 0 && (
            <p className="empty-message">Non ci sono ancora allenamenti salvati.</p>
          )}

          {groupedHistory.map((session) => {
            const isExpanded = expandedHistorySessions.includes(session.session_id);
            return (
              <div className="history-item" key={session.session_id}>
                <div className="history-header">
                  <div>
                    <h3>{session.company}</h3>
                    <p className="history-session-subtitle">
                      {session.role}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="history-toggle-button"
                    onClick={() => toggleHistorySession(session.session_id)}
                  >
                    {isExpanded ? "Chiudi" : "Apri"}
                  </button>
                </div>

                <div className="history-session-meta">
                  <span>{formatHistoryDate(session.created_at)}</span>
                  <span>{displayInterviewType(session.interview_type)}</span>
                  <span>Difficoltà: {displayDifficulty(session.difficulty)}</span>
                  <span>Punteggio: {session.total_score !== null ? `${session.total_score}/100` : "Non valutato"}</span>
                </div>

                {isExpanded && (
                  <div className="history-question-list">
                    {session.questions.map((item, index) => {
                      const questionKey = `${session.session_id}-${index}`;
                      const hasDetails = item.user_answer || item.feedback || item.speaking_feedback || item.improved_answer || item.solution_explanation;
                      const isQuestionExpanded = expandedHistoryQuestions.includes(questionKey);

                      return (
                        <div className="history-question-item" key={questionKey}>
                          <p>
                            <strong>Domanda {index + 1}:</strong> {item.question}
                          </p>

                          {hasDetails && (
                            <button
                              type="button"
                              className="history-question-toggle"
                              onClick={() => toggleHistoryQuestion(questionKey)}
                            >
                              {isQuestionExpanded ? "Nascondi dettagli" : "Mostra dettagli"}
                            </button>
                          )}

                          {isQuestionExpanded && (
                            <div className="history-question-details">
                              {item.user_answer && (
                                <p>
                                  <strong>Risposta:</strong> {item.user_answer}
                                </p>
                              )}

                              {item.feedback && (
                                <p>
                                  <strong>Feedback:</strong> {item.feedback}
                                </p>
                              )}

                              {item.speaking_feedback && (
                                <p>
                                  <strong>Feedback parlato:</strong> {item.speaking_feedback}
                                </p>
                              )}

                              {item.improved_answer && (
                                <div className="mini-improved">
                                  <strong>Risposta modello / migliorata:</strong>
                                  <p>{item.improved_answer}</p>
                                </div>
                              )}

                              {item.solution_explanation && (
                                <div className="mini-solution">
                                  <strong>Soluzione:</strong>
                                  <p>{item.solution_explanation}</p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}

          <button className="primary-button" onClick={() => transitionToStep("gym")}>
            Torna alla palestra
          </button>
        </section>
      )}

      {step === "progress" && (
        <section className="card">
          <h2>Progressi</h2>

          {!progress || progress.total_answers === 0 ? (
            <p className="empty-message">
              Non ci sono ancora risposte valutate. Fai almeno un allenamento per
              vedere i progressi.
            </p>
          ) : (
            <>
              <div className="progress-summary">
                <div>
                  <strong>{progress.total_answers}</strong>
                  <p>Risposte valutate</p>
                </div>

                <div>
                  <strong>{progress.average_total_score}</strong>
                  <p>Punteggio medio</p>
                </div>
              </div>

              <div className="scores-grid">
                <div>
                  <strong>{progress.average_clarity_score}</strong>
                  <p>Chiarezza media</p>
                </div>

                <div>
                  <strong>{progress.average_completeness_score}</strong>
                  <p>Completezza media</p>
                </div>

                <div>
                  <strong>{progress.average_relevance_score}</strong>
                  <p>Pertinenza media</p>
                </div>

                <div>
                  <strong>{progress.average_professionalism_score}</strong>
                  <p>Professionalità media</p>
                </div>

                <div>
                  <strong>{progress.average_synthesis_score}</strong>
                  <p>Sintesi media</p>
                </div>

                <div>
                  <strong>{progress.average_speaking_score}</strong>
                  <p>Parlato medio</p>
                </div>
              </div>
            </>
          )}

          <button className="primary-button" onClick={() => transitionToStep("gym")}>
            Torna alla palestra
          </button>
        </section>
      )}
    </div>
  );
}

export default App;
