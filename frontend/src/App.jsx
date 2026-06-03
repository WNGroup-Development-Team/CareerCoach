import { useEffect, useRef, useState } from "react";
import "./App.css";

import logoCareerCoach from "./assets/career-coach-logo.png";
import PersonalizeExperience from "./PersonalizeExperience";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const AUTH_TOKEN_KEY = "careercoach_auth_token";
const INTRO_SPLASH_DURATION_MS = 3000;
const TRANSITION_DURATION_MS = 2000;
const CV_FLOW_STEPS = [
  { id: "cv-upload", label: "CV" },
  { id: "cv-digital", label: "Digitale" },
  { id: "cv-analysis", label: "Analisi" },
  { id: "gym", label: "Percorso" },
];

const wait = (duration) =>
  new Promise((resolve) => {
    setTimeout(resolve, duration);
  });

async function fetchWithTimeout(url, options = {}, timeout = 30000) {
  const controller = new AbortController();

  const timeoutId = setTimeout(() => {
    controller.abort();
  }, timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
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

function getProfilePath(value = "") {
  try {
    return new URL(normalizeProfileUrl(value)).pathname.replace(/^\/|\/$/g, "").toLowerCase();
  } catch {
    return "";
  }
}

function getCanonicalProfileKey(value = "") {
  try {
    const url = new URL(normalizeProfileUrl(value));
    return `${url.hostname.replace(/^www\./, "")}${url.pathname.replace(/\/+$/, "").toLowerCase()}`;
  } catch {
    return normalizeProfileUrl(value).split("?")[0].replace(/\/+$/, "");
  }
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
          <div className="splash-spinner" aria-label="Caricamento" />
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

function PencilIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 20h4.2L19.4 8.8a2 2 0 0 0 0-2.8L18 4.6a2 2 0 0 0-2.8 0L4 15.8V20Z" />
      <path d="M14 6l4 4" />
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

function CvFlowProgress({ currentStep, onStepSelect }) {
  const activeIndex = Math.max(
    CV_FLOW_STEPS.findIndex((flowStep) => flowStep.id === currentStep),
    0
  );
  const progress = (activeIndex / (CV_FLOW_STEPS.length - 1)) * 100;

  return (
    <nav className="progress-steps" aria-label="Avanzamento percorso CV">
      <div className="progress-steps-track" aria-hidden="true">
        <span style={{ width: `${progress}%` }} />
      </div>

      <ol>
        {CV_FLOW_STEPS.map((flowStep, index) => {
          const isActive = index === activeIndex;
          const isComplete = index < activeIndex;
          const canReturnToStep = isComplete && typeof onStepSelect === "function";
          const stepContent = (
            <>
              <span aria-hidden="true">{isComplete ? "✓" : ""}</span>
              <strong>{flowStep.label}</strong>
            </>
          );

          return (
            <li
              className={[
                "progress-step",
                isActive ? "active" : "",
                isComplete ? "complete" : "",
              ].filter(Boolean).join(" ")}
              aria-current={isActive ? "step" : undefined}
              key={flowStep.id}
            >
              {canReturnToStep ? (
                <button type="button" onClick={() => onStepSelect(flowStep.id)}>
                  {stepContent}
                </button>
              ) : (
                stepContent
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
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

  const [profile, setProfile] = useState({
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

  const [cvFile, setCvFile] = useState(null);
  const [cvPreview, setCvPreview] = useState(null);
  const [isCvDragging, setIsCvDragging] = useState(false);
  const cvFileInputRef = useRef(null);
  const linkedinFileInputRef = useRef(null);
  const [linkedinUploadMessage, setLinkedinUploadMessage] = useState("");
  const [socialScreenshotMessages, setSocialScreenshotMessages] = useState({});
  const [screenshotAnalysisProgress, setScreenshotAnalysisProgress] = useState({
    active: false,
    fileCount: 0,
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
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [stepHistory, setStepHistory] = useState([]);

  const [interviewType, setInterviewType] = useState("conoscitive_motivazionali");
  const [difficulty, setDifficulty] = useState("intermedio");

  const [company, setCompany] = useState("Generica");
  const [personalizeIntent, setPersonalizeIntent] = useState("interview");
  const [personalizeForm, setPersonalizeForm] = useState({
    goal: "",
    company: "",
    role: "",
    link: "",
  });
  const [questionMode] = useState("web");

  const [questions, setQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [allFeedbacks, setAllFeedbacks] = useState([]);

  const [questionId, setQuestionId] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  const [answerMode, setAnswerMode] = useState("text");
  const [isListening, setIsListening] = useState(false);
  const [speechMetrics, setSpeechMetrics] = useState(null);

  const [feedback, setFeedback] = useState(null);
  const [history, setHistory] = useState([]);
  const [progress, setProgress] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const splashTimer = setTimeout(() => {
      setShowSplash(false);
    }, INTRO_SPLASH_DURATION_MS);

    return () => clearTimeout(splashTimer);
  }, []);

  useEffect(() => {
    let transitionTimer;

    if (loading) {
      setShowTransition(true);
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
          setError(typeof data.detail === "string" ? data.detail : "CV non trovato.");
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
      const response = await fetchWithTimeout(`${API_URL}/auth/oauth/${provider}/url`, {}, 10000);
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

  const updateProfile = (field, value) => {
    setProfile({
      ...profile,
      [field]: value,
    });
  };

  const resetError = () => {
    setError("");
    setAuthMessage("");
    setPreviewLink("");
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
        localStorage.removeItem(AUTH_TOKEN_KEY);
        setAuthToken("");
        setUserId(null);
        setStep("auth");
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

  const deleteCv = async () => {
    resetError();

    if (!profile.cv_filename) {
      setError("Non c'e nessun CV da eliminare.");
      return;
    }

    const confirmed = window.confirm(
      "Vuoi eliminare il CV caricato? Potrai caricarne uno nuovo dal profilo."
    );

    if (!confirmed) {
      return;
    }

    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/users/${userId}/cv`, {
        method: "DELETE",
      }, 15000);
      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nell'eliminazione del CV.");
        return;
      }

      setProfile((current) => ({
        ...current,
        ...data.user,
        cv_uploaded: false,
        cv_filename: "",
        cv_text: "",
      }));
      setCvFile(null);
      setCvPreview(null);
      setDigitalAnalysis(null);
    } catch (err) {
      console.error(err);
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
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
    const allowedExtensions = ["pdf", "docx", "txt"];

    if (!allowedExtensions.includes(extension)) {
      setError("Carica un file PDF, DOCX o TXT.");
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
        const detail = data.reason || "Carica un CV valido in formato PDF, DOCX o TXT.";
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
        message: "Non siamo riusciti a verificare il contenuto del file. Riprova con un CV valido in formato PDF, DOCX o TXT.",
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
      if (personalizeIntent === "cv") {
        await analyzeCvOptimization(updatedUser);
        return;
      }
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
    if (!["pdf", "docx", "txt"].includes(extension)) {
      setError("Carica l'esportazione LinkedIn in formato PDF, DOCX o TXT.");
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

  const analyzeSocialScreenshots = async (profileType, files) => {
    resetError();
    setSocialScreenshotMessages((current) => ({ ...current, [profileType]: "" }));

    const selectedFiles = Array.from(files || []);
    if (!selectedFiles.length) {
      return;
    }

    setScreenshotAnalysisProgress({
      active: true,
      fileCount: selectedFiles.length,
      elapsedSeconds: 0,
      profileType,
    });
    try {
      const formData = new FormData();
      formData.append("profile_type", profileType);
      selectedFiles.forEach((file) => formData.append("files", file));
      const response = await fetchWithTimeout(`${API_URL}/users/${userId}/social-screenshots`, {
        method: "POST",
        body: formData,
      }, 300000);
      const data = await response.json();
      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nell'analisi degli screenshot.");
        return;
      }

      setProfile((current) => ({ ...current, ...data.user }));
      setDigitalAnalysis(normalizeDigitalAnalysis(data.analysis || data.user?.digital_analysis || null));
      setSocialScreenshotMessages((current) => ({
        ...current,
        [profileType]: data.message || "Screenshot analizzati.",
      }));
    } catch (err) {
      console.error(err);
      setError(
        err?.name === "AbortError"
          ? "L'analisi locale degli screenshot sta richiedendo troppo tempo. Prova con meno immagini."
          : "Errore di connessione durante l'analisi degli screenshot. Controlla che FastAPI e Ollama siano avviati."
      );
    } finally {
      setScreenshotAnalysisProgress({
        active: false,
        fileCount: 0,
        elapsedSeconds: 0,
        profileType: "",
      });
    }
  };

  const analyzeCvOptimization = async (profileOverride = profile) => {
    resetError();

    if (!profileOverride.cv_uploaded && !profileOverride.cv_filename) {
      setError("Carica un CV prima di avviare l'analisi strategica.");
      transitionToStep("cv-upload");
      return;
    }

    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/users/${userId}/cv-optimization-analysis`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          company: personalizeForm.company.trim() || company,
          role: personalizeForm.role.trim() || profileOverride.target_role || "",
          goal: personalizeForm.goal.trim(),
          job_link: personalizeForm.link.trim(),
        })
      }, 60000);

      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nell'analisi del CV.");
        return;
      }

      setCvOptimizationAnalysis(data.analysis);
      transitionToStep("cv-strategy");
    } catch (err) {
      console.error(err);
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const createProfile = async () => {
    resetError();

    if (!profile.name.trim()) {
      setError("Inserisci il nome.");
      return;
    }

    if (!profile.education.trim()) {
      setError("Inserisci il percorso di studi.");
      return;
    }

    if (!profile.target_role.trim()) {
      setError("Inserisci il ruolo target.");
      return;
    }

    if (!profile.sector.trim()) {
      setError("Inserisci il settore.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/users${userId ? `/${userId}` : ""}`, {
        method: userId ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(profile)
      }, 15000);

      const data = await response.json();

      if (!response.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Errore nella creazione del profilo.");
        return;
      }

      const updatedUser = data.user;
      if (updatedUser) {
        setUserId(updatedUser.id);
        setProfile({
          name: updatedUser.name || "",
          email: updatedUser.email || "",
          phone: updatedUser.phone || "",
          education: updatedUser.education || "",
          target_role: updatedUser.target_role || "",
          sector: updatedUser.sector || "",
          experience_level: updatedUser.experience_level || "Junior",
          interview_language: updatedUser.interview_language || "Italiano",
        });
      } else {
        setUserId(data.user_id);
      }
      setStep("gym");
    } catch (err) {
      console.error(err);

      if (err.name === "AbortError") {
        setError("Il backend non risponde. Controlla che FastAPI sia avviato.");
      } else {
        setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
      }
    } finally {
      setLoading(false);
    }
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

    const selectedCompany = personalizeForm.company.trim() || company || "Generica";
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

      let data = null;

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

      setStep("feedback");
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

  const loadHistory = async () => {
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
      setStep("history");
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

  const loadProgress = async () => {
    resetError();
    setLoading(true);

    try {
      const response = await fetchWithTimeout(`${API_URL}/progress/${userId}`, {}, 15000);
      const data = await response.json();

      if (!response.ok) {
        setError("Errore nel caricamento dei progressi.");
        console.log(data);
        return;
      }

      setProgress(data);
      setStep("progress");
    } catch (err) {
      console.error(err);

      if (err.name === "AbortError") {
        setError("Il caricamento dei progressi sta impiegando troppo tempo.");
      } else {
        setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
      }
    } finally {
      setLoading(false);
    }
  };

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


  const preparePersonalizeForm = () => {
    setPersonalizeForm((current) => ({
      goal: current.goal,
      company: current.company || (company === "Generica" ? "" : company),
      role: current.role.toLowerCase() === "da definire" ? "" : current.role,
      link: current.link,
    }));
  };

  const startCvPath = () => {
    preparePersonalizeForm();
    setPersonalizeIntent("cv");
    transitionToStep("personalize");
  };

  const startInterviewPath = () => {
    preparePersonalizeForm();
    setPersonalizeIntent("interview");
    transitionToStep("personalize");
  };

  const updatePersonalizeForm = (field, value) => {
    setPersonalizeForm((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const continuePersonalizedPath = async (event) => {
    event.preventDefault();
    resetError();

    const hasInterviewContext = Boolean(
      personalizeForm.goal.trim() ||
      personalizeForm.company.trim() ||
      (personalizeForm.role.trim() && personalizeForm.role.trim().toLowerCase() !== "da definire") ||
      personalizeForm.link.trim()
    );

    if (!hasInterviewContext) {
      return;
    }

    const nextCompany = personalizeForm.company.trim() || "Generica";
    const nextRole = personalizeForm.role.trim();

    setCompany(nextCompany);

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

      await analyzeCvOptimization();
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
  const firstName = (profile.name || "Silvia").trim().split(/\s+/)[0];
  const interviewPreparationScore = progress?.average_total_score ?? 0;
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
  const otherProfileUrl = digitalPresence.portfolio_url || profile.portfolio_url || "";
  const connectedDigitalProfiles = [
    linkedinProfileUrl ? { title: "Link LinkedIn pubblico", url: normalizeProfileUrl(linkedinProfileUrl) } : null,
    exactInstagramHandle ? { title: `Instagram @${exactInstagramHandle}`, url: `https://www.instagram.com/${exactInstagramHandle}/` } : null,
    otherProfileUrl ? { title: "Link aggiuntivo", url: normalizeProfileUrl(otherProfileUrl) } : null,
  ].filter(Boolean);
  const screenshotUploadBoxes = [
    {
      type: "instagram",
      title: "Screenshot Instagram",
      description: "Carica schermate del profilo, della bio o dei post pubblici visibili.",
    },
    {
      type: "facebook",
      title: "Screenshot Facebook",
      description: "Utile quando Facebook richiede il login e impedisce il recupero automatico.",
    },
    {
      type: "other",
      title: "Screenshot di un altro profilo",
      description: "Puoi caricare schermate di TikTok, GitHub, portfolio o altri profili pubblici.",
    },
  ];

  return (
    <div className={step === "auth" ? "page auth-page" : "page"}>
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
              <span aria-hidden="true">←</span>
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

      {userId && !["home", "personalize", "cv-upload", "cv-digital", "cv-analysis"].includes(step) && (
        <nav className="navbar">
          <button onClick={() => transitionToStep("home")}>Home</button>
          <button onClick={() => transitionToStep("gym")}>Palestra colloqui</button>
          <button onClick={loadHistory}>Storico</button>
          <button onClick={loadProgress}>Progressi</button>
        </nav>
      )}

      {showTransition && !showSplash && (
        <SplashScreen
          mode="loading"
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
            <h2>Cosa vuoi fare oggi?</h2>
            <p>Seleziona un’attività per continuare il tuo percorso.</p>
            <p className="activity-orientation-text">
              Puoi iniziare migliorando il CV oppure allenarti subito con una simulazione personalizzata.
            </p>
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
                  Ricevi suggerimenti personalizzati per migliorare struttura,
                  competenze e coerenza con gli annunci.
                </p>
                <button className="action-card-button" onClick={startCvPath}>
                  <span>Inizia Ottimizzazione</span>
                  <span className="button-arrow" aria-hidden="true">→</span>
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
                  Allenati con domande realistiche e ricevi feedback su contenuto,
                  chiarezza e modo di parlare.
                </p>
                <button className="action-card-button" onClick={() => transitionToStep("gym")}>
                  <span>Avvia simulazione</span>
                  <span className="button-arrow" aria-hidden="true">→</span>
                </button>
              </div>
            </div>
          </div>

          <p className="activity-footer-note">
            Potrai modificare il tuo percorso in qualsiasi momento.
          </p>
        </section>
      )}

      {step === "personalize" && (
        <PersonalizeExperience
          company={personalizeForm.company}
          goal={personalizeForm.goal}
          link={personalizeForm.link}
          role={personalizeForm.role}
          onBack={() => transitionToStep("home")}
          onChange={updatePersonalizeForm}
          onSubmit={continuePersonalizedPath}
          submitLabel={personalizeIntent === "cv" ? "Continua al CV" : "Continua alla simulazione"}
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
                  <label>Nome</label>
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
          <CvFlowProgress currentStep={step} onStepSelect={transitionToStep} />

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
            <div className="cv-upload-icon">CV</div>
            <h3>Trascina qui il tuo CV</h3>
            <p>PDF, DOCX o TXT fino a 5 MB</p>
            <div className="cv-divider"><span>oppure</span></div>
            <input
              id="cv-file-input"
              ref={cvFileInputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(event) => selectCvFile(event.target.files?.[0])}
            />
            <label className="browse-file-btn" htmlFor="cv-file-input">
              Sfoglia file
            </label>
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
        <section className="cv-flow-page digital-profile-page">
          <CvFlowProgress currentStep={step} onStepSelect={transitionToStep} />

          <div className="cv-loaded-card">
            <span className="cv-loaded-check" aria-hidden="true">✓</span>
            <div>
              <h2>CV caricato correttamente</h2>
              <p>
                <strong>{profile.cv_filename || "CV"}</strong> è pronto per l'analisi.
              </p>
            </div>
          </div>

          <div className="cv-analysis-card digital-profile-card">
            <h3 className="digital-profile-title">Collega i tuoi profili online</h3>
            <p>
              Rafforza la tua candidatura. Collega i tuoi profili social per permettere
              all'AI di analizzare la coerenza tra il tuo CV e la tua presenza online.
            </p>

            <label>LinkedIn Profile Link</label>
            {isLinkedInConnected && (
              <div className="linkedin-connected-badge">
                <span aria-hidden="true">✓</span>
                <div>
                  <strong>LinkedIn collegato</strong>
                  <p>Accesso effettuato tramite LinkedIn.</p>
                </div>
              </div>
            )}
            <input
              value={digitalPresence.linkedin_url}
              onChange={(event) => updateDigitalPresence("linkedin_url", event.target.value)}
              placeholder="https://linkedin.com/in/tuonome"
            />
            <p className="linkedin-access-note">
              Dal link pubblico possiamo verificare il profilo e leggere solo dati base o
              snippet pubblici. Le sezioni complete di LinkedIn richiedono autorizzazioni dedicate.
            </p>

            <div className="linkedin-export-box">
              <div>
                <strong>Confronto completo con LinkedIn</strong>
                <p>
                  Carica l'esportazione PDF del tuo profilo LinkedIn per confrontare
                  esperienze, formazione e competenze con il CV.
                </p>
              </div>

              <input
                id="linkedin-profile-file"
                ref={linkedinFileInputRef}
                type="file"
                accept=".pdf,.docx,.txt"
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
                <label className="linkedin-export-button" htmlFor="linkedin-profile-file">
                  Carica esportazione LinkedIn
                </label>
              )}

              {linkedinUploadMessage && <p className="linkedin-upload-message">{linkedinUploadMessage}</p>}
            </div>

            <label>Link aggiuntivo <span>(opzionale)</span></label>
            <input
              value={digitalPresence.portfolio_url}
              onChange={(event) => updateDigitalPresence("portfolio_url", event.target.value)}
              placeholder="https://..."
            />
            <p className="linkedin-access-note">
              Puoi inserire qualsiasi URL pubblico: un altro profilo social, un sito
              personale o una pagina professionale. Se il contenuto non e accessibile,
              viene segnalato senza inventare un'analisi.
            </p>

            <label>Instagram <span>(opzionale)</span></label>
            <input
              value={digitalPresence.instagram_handle}
              onChange={(event) => updateDigitalPresence("instagram_handle", event.target.value)}
              placeholder="@tuo_handle"
            />
            <p className="linkedin-access-note">
              Proviamo automaticamente a recuperare i media visibili dal link pubblico.
              Se Instagram blocca il recupero o il profilo e privato, potrai caricare
              screenshot nella schermata successiva.
            </p>

            <p className="privacy-note">
              <span aria-hidden="true">i</span>
              I profili inseriti verranno usati solo per valutare la coerenza professionale del tuo percorso.
            </p>

            {!canAnalyzeDigitalPresence && (
              <p className="digital-profile-help">
                Inserisci almeno un profilo online oppure salta questo passaggio.
              </p>
            )}
          </div>

          <button
            className="cv-next-button digital-analyze-btn"
            onClick={analyzeDigitalPresence}
            disabled={loading || !canAnalyzeDigitalPresence}
          >
            <span>Analizza Coerenza Digitale</span>
            <span className="button-arrow" aria-hidden="true">→</span>
          </button>

          <button className="cv-skip-button" onClick={() => transitionToStep("profile")}>
            Salta per ora e aggiorna dal profilo
          </button>
        </section>
      )}

      {step === "cv-analysis" && (
        <section className="cv-flow-page">
          <CvFlowProgress currentStep={step} onStepSelect={transitionToStep} />

          <div className="cv-analysis-heading">
            <h2>Analisi Coerenza Digitale</h2>
            <p>Confronto tra il tuo CV e i profili online.</p>
          </div>

          <div className="cv-score-card">
            <div
              className="cv-score-ring"
              style={{
                background: `radial-gradient(circle at center, #ffffff 58%, transparent 60%), conic-gradient(#3d735e 0 ${digitalAnalysis?.score || 0}%, #dfe8ef ${digitalAnalysis?.score || 0}% 100%)`,
              }}
            >
              <span>{digitalAnalysis?.score || 0}%</span>
            </div>
            <h3>{digitalAnalysis?.headline || "Analisi completata"}</h3>
            <p>
              {digitalAnalysis?.summary ||
                "Abbiamo confrontato CV, LinkedIn e profili inseriti per stimare l'impatto sul tuo profilo professionale."}
            </p>
          </div>

          <h3 className="cv-detail-title">Dettagli Analisi</h3>

          {digitalAnalysis?.analysis_evidence && (
            <div className="cv-analysis-card linkedin-basic-card">
              <h3>Cosa abbiamo confrontato davvero</h3>
              <p>
                CV del profilo:{" "}
                {digitalAnalysis.analysis_evidence.cv_profile_loaded
                  ? `caricato (${digitalAnalysis.analysis_evidence.cv_filename || profile.cv_filename || "CV"})`
                  : "non disponibile"}
              </p>
              <p>
                PDF LinkedIn:{" "}
                {digitalAnalysis.analysis_evidence.linkedin_export_compared
                  ? `caricato e confrontato (${digitalAnalysis.analysis_evidence.linkedin_export_filename || profile.linkedin_profile_filename || "PDF LinkedIn"})`
                  : "non caricato"}
              </p>
              <p>
                Link LinkedIn pubblico: {digitalAnalysis.analysis_evidence.linkedin_public_identity?.message}
              </p>
              <p>
                Fonti API/OAuth ufficiali:{" "}
                {(digitalAnalysis.analysis_evidence.official_profile_source_count || 0) > 0 ? (
                  <>
                    <strong>{digitalAnalysis.analysis_evidence.official_profile_source_count}</strong>
                    {digitalAnalysis.analysis_evidence.linkedin_official_identity?.message
                      ? ` - ${digitalAnalysis.analysis_evidence.linkedin_official_identity.message}`
                      : ""}
                  </>
                ) : (
                  "non collegate"
                )}
              </p>
              <p>
                Profili pubblici verificati:{" "}
                <strong>{digitalAnalysis.analysis_evidence.verified_profile_count || 0}</strong>
              </p>
              {!digitalAnalysis.analysis_evidence.can_compare_with_cv && (
                <p>
                  {digitalAnalysis.analysis_evidence.zero_score_reason}
                </p>
              )}
              <p>
                Instagram:{" "}
                {digitalAnalysis.analysis_evidence.instagram_media_analyzed
                  ? "screenshot o contenuti caricati analizzati"
                  : digitalAnalysis.analysis_evidence.public_preview_analyzed
                    ? "analizzata solo un'anteprima pubblica del profilo; foto e post non sono stati analizzati"
                  : digitalAnalysis.analysis_evidence.instagram_metadata_found
                    ? "profilo rintracciabile sul web: foto, video e post non sono stati analizzati"
                    : "profilo non accessibile: foto e post non sono stati analizzati"}
              </p>
              <p>
                Anteprime pubbliche analizzate:{" "}
                <strong>
                  {digitalAnalysis.analysis_evidence.visual_media_analysis?.analyzed_preview_count || 0}
                </strong>
                {" "}· Screenshot/contenuti caricati:{" "}
                <strong>
                  {digitalAnalysis.analysis_evidence.visual_media_analysis?.analyzed_content_count || 0}
                </strong>
              </p>
              <p>
                Impatto delle analisi visuali sul punteggio:{" "}
                <strong>
                  {(digitalAnalysis.analysis_evidence.visual_score_adjustment || 0) > 0 ? "+" : ""}
                  {digitalAnalysis.analysis_evidence.visual_score_adjustment || 0}
                </strong>
              </p>
              <p>
                Link aggiuntivo:{" "}
                {digitalAnalysis.analysis_evidence.additional_link?.message}
              </p>
            </div>
          )}

          {(displayedDigitalAnalysis?.findings || []).map((finding, index) => (
            <div
              className={`cv-detail-card ${finding.status === "warning" ? "warning" : "success"}`}
              key={`${finding.title}-${index}`}
            >
              <h4>{finding.title}</h4>
              <p>{finding.description}</p>
              {finding.coach_tip && (
                <div className="coach-tip">
                  <strong>Il consiglio del coach</strong>
                  <p>{finding.coach_tip}</p>
                </div>
              )}
            </div>
          ))}

          {["provider_not_configured", "provider_unavailable"].includes(
            digitalAnalysis?.analysis_evidence?.visual_media_analysis?.status
          ) && (
            <div className="cv-analysis-card linkedin-basic-card">
              <h3>Analisi visuale da configurare</h3>
              <p>
                Per analizzare gratuitamente le immagini in locale, installa Ollama, esegui
                <strong> ollama pull moondream</strong> e assicurati che il servizio
                Ollama sia avviato.
              </p>
              {digitalAnalysis?.analysis_evidence?.visual_media_analysis?.message && (
                <p>{digitalAnalysis.analysis_evidence.visual_media_analysis.message}</p>
              )}
            </div>
          )}

          {!["provider_not_configured", "provider_unavailable"].includes(
              digitalAnalysis?.analysis_evidence?.visual_media_analysis?.status
            ) && (
            <div className="cv-analysis-card linkedin-basic-card">
              <h3>Completa il controllo delle immagini</h3>
              <p>
                Puoi caricare fino a 8 screenshot per ciascun profilo. Le immagini vengono
                analizzate senza essere salvate come file: eventuali contenuti sensibili
                possono ridurre il punteggio complessivo.
              </p>
              <div className="screenshot-upload-grid">
                {screenshotUploadBoxes.map((box) => {
                  const isCurrentAnalysis =
                    screenshotAnalysisProgress.active && screenshotAnalysisProgress.profileType === box.type;
                  return (
                    <div className="screenshot-upload-box" key={box.type}>
                      <h4>{box.title}</h4>
                      <p>{box.description}</p>
                      <input
                        id={`social-screenshot-files-${box.type}`}
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        multiple
                        disabled={screenshotAnalysisProgress.active}
                        onChange={(event) => {
                          analyzeSocialScreenshots(box.type, event.target.files);
                          event.target.value = "";
                        }}
                      />
                      <label
                        className={`linkedin-export-button ${screenshotAnalysisProgress.active ? "disabled" : ""}`}
                        htmlFor={`social-screenshot-files-${box.type}`}
                      >
                        {isCurrentAnalysis ? "Analisi in corso..." : "Carica screenshot"}
                      </label>
                      {isCurrentAnalysis && (
                        <div className="screenshot-analysis-progress" role="status">
                          <div className="screenshot-analysis-spinner" />
                          <div>
                            <strong>
                              Analisi locale di {screenshotAnalysisProgress.fileCount}{" "}
                              {screenshotAnalysisProgress.fileCount === 1 ? "immagine" : "immagini"}
                            </strong>
                            <p>Tempo trascorso: {screenshotAnalysisProgress.elapsedSeconds}s.</p>
                          </div>
                        </div>
                      )}
                      {socialScreenshotMessages[box.type] && (
                        <p className="linkedin-upload-message">{socialScreenshotMessages[box.type]}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {connectedDigitalProfiles.length > 0 && (
            <div className="cv-analysis-card">
              <h3>Profili collegati</h3>
              <div className="source-list">
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
            </div>
          )}

          <button className="cv-next-button" onClick={() => transitionToStep("gym")}>
            Avanti
            
          </button>
        </section>
      )}

      {step === "cv-strategy" && (
        <section className="cv-strategy-page">
          <div className="cv-strategy-heading">
            <h2>Analisi Strategica CV</h2>
            <p>
              {(cvOptimizationAnalysis?.target?.role || personalizeForm.role || profile.target_role || "Ruolo target")} presso{" "}
              {cvOptimizationAnalysis?.target?.company || company || "azienda target"}
            </p>
          </div>

          <div className="cv-strategy-score-card">
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
              <h3>Aree di Sviluppo</h3>
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
      )}

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
            <h2>Profilo</h2>
          </div>

          <div className="profile-hero-card">
            <button className="profile-settings" type="button" aria-label="Impostazioni profilo">
              ...
            </button>
            <div className="profile-avatar-large">
              <span>{profileInitial}</span>
              <button type="button" aria-label="Modifica immagine profilo">+</button>
            </div>
            <h2>{profile.name || "Il tuo profilo"}</h2>
            <p>{profile.target_role || "Ruolo target da definire"}</p>
            <div className="profile-chip-row">
              <span>{profile.sector || "Settore"}</span>
              <span>{profile.experience_level || "Junior"}</span>
            </div>
            <button className="profile-analysis-button" type="button" onClick={() => transitionToStep("cv-digital")}>
              Analisi digitale
            
            </button>
          </div>

          <div className="profile-section-title">
            <h3>Traguardi Colloqui</h3>
          </div>

          <div className="profile-progress-card">
            <div>
              <strong>Preparazione Generale</strong>
              <span>{interviewPreparationScore}%</span>
            </div>
            <div className="profile-progress-track">
              <span style={{ width: `${interviewPreparationScore}%` }} />
            </div>
            <p>
              {progress?.total_answers
                ? `${progress.total_answers} risposte valutate finora.`
                : "Pronta per iniziare i colloqui tecnici."}
            </p>
          </div>

          <div className="profile-stats-grid">
            <div>
              <span className="profile-stat-icon">^</span>
              <strong>{progress?.total_answers || 0}</strong>
              <p>Colloqui Superati</p>
            </div>
            <div>
              <span className="profile-stat-icon">*</span>
              <strong>{digitalCoherenceScore}%</strong>
              <p>Coerenza Digitale</p>
            </div>
          </div>

          <div className="profile-section-title">
            <h3>Aziende Preferite</h3>
            <button type="button" onClick={() => transitionToStep("gym")}>Vedi tutte</button>
          </div>

          <div className="favorite-company-grid">
            {[company || "TechCorp", "GlobalNet", "EcoInnovate"].map((item) => (
              <div key={item}>
                <span>{item.charAt(0).toUpperCase()}</span>
                <strong>{item}</strong>
              </div>
            ))}
          </div>

          <div className="profile-section-title">
            <h3>I Tuoi Documenti</h3>
          </div>

          <div className="document-list">
            <div className="document-item">
              <span>CV</span>
              <div>
                <strong>CV Master Caricato</strong>
                <p>{profile.cv_filename || "Carica il tuo CV per iniziare"}</p>
              </div>
              <div className="document-actions">
                <button
                  type="button"
                  onClick={() => transitionToStep("cv-view")}
                  disabled={!profile.cv_filename}
                  aria-label="Vedi CV caricato"
                  title="Vedi CV caricato"
                >
                  <EyeIcon />
                </button>
                <button
                  type="button"
                  onClick={() => transitionToStep("cv-upload")}
                  aria-label="Modifica CV"
                  title="Modifica CV"
                >
                  <PencilIcon />
                </button>
                <button
                  className="danger-icon-button"
                  type="button"
                  onClick={deleteCv}
                  disabled={!profile.cv_filename || loading}
                  aria-label="Elimina CV"
                  title="Elimina CV"
                >
                  <TrashIcon />
                </button>
              </div>
            </div>
            <div>
              <span>AI</span>
              <div>
                <strong>CV Ottimizzato</strong>
                <p>{digitalAnalysis ? `Versione per ${company || "il tuo ruolo"}` : "Analisi da completare"}</p>
              </div>
              <button type="button" onClick={() => transitionToStep("cv-digital")} aria-label="Apri analisi digitale">v</button>
            </div>
          </div>

          <div className="profile-danger-zone">
            <div>
              <strong>Elimina profilo</strong>
              <p>Rimuove account, CV e storico salvato in CareerCoach.</p>
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

          <div className="interview-context">
            <div>
              <span>Azienda</span>
              <strong>{company || "Generica"}</strong>
            </div>
            <div>
              <span>Candidatura</span>
              <strong>{personalizeForm.role || profile.target_role || "Ruolo da definire"}</strong>
            </div>
            {personalizeForm.goal && (
              <div className="full">
                <span>Obiettivo</span>
                <strong>{personalizeForm.goal}</strong>
              </div>
            )}
          </div>

          <h3 className="sub-title">Tipo di allenamento</h3>

          <div className="choice-grid three-columns">
            <button
              className={interviewType === "conoscitive_motivazionali" ? "choice active" : "choice"}
              onClick={() => setInterviewType("conoscitive_motivazionali")}
            >
              <h3>Conoscitive e motivazionali</h3>
              <p>
                Domande su chi sei, obiettivi, aspettative, motivazione,
                azienda, percorso personale e lavoro di gruppo.
              </p>
            </button>

            <button
              className={interviewType === "tecniche" ? "choice active" : "choice"}
              onClick={() => setInterviewType("tecniche")}
            >
              <h3>Tecniche</h3>
              <p>
                Domande specifiche sul ruolo scelto, sulle competenze richieste,
                sugli strumenti e sulle capacità operative.
              </p>
            </button>

            <button
              className={interviewType === "logica" ? "choice active" : "choice"}
              onClick={() => setInterviewType("logica")}
            >
              <h3>Logica e ragionamento</h3>
              <p>
                Domande a trabocchetto, serie numeriche o alfabetiche,
                stime, problem solving e ragionamento.
              </p>
            </button>
          </div>

          <label>Difficoltà</label>
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
          >
            <option value="base">Base</option>
            <option value="intermedio">Intermedio</option>
            <option value="avanzato">Avanzato</option>
          </select>

          <div className="actions">
            <button className="primary-button" onClick={generateQuestion} disabled={loading}>
              Genera 10 domande
            </button>

            <button className="secondary-button" onClick={loadHistory} disabled={loading}>
              Vedi storico
            </button>
          </div>
        </section>
      )}

      {step === "question" && (
        <section className="card">
          <h2>Simulazione colloquio</h2>

          <div className="progress-question">
            Domanda {currentQuestionIndex + 1} di {questions.length || 10}
          </div>

          <div className="tag-row">
            <span>{company}</span>
            <span>{interviewType}</span>
            <span>{difficulty}</span>
          </div>

          <div className="question-box">{question}</div>

          <div className="info-box">
            La domanda è stata generata in base al tuo profilo, al ruolo scelto, all’azienda e al livello di difficoltà.
            Le eventuali fonti usate sono salvate nel database dell’app.
          </div>

          <div className="mode-switch">
            <button
              className={answerMode === "text" ? "mode active" : "mode"}
              onClick={() => setAnswerMode("text")}
            >
              Risposta scritta
            </button>

            <button
              className={answerMode === "voice" ? "mode active" : "mode"}
              onClick={() => setAnswerMode("voice")}
            >
              Risposta con microfono
            </button>
          </div>

          {answerMode === "voice" && (
            <div className="voice-panel">
              <h3>Allenamento vocale</h3>
              <p>
                Parla come se fossi davanti a un recruiter. L’app trascrive la tua
                risposta e analizza il modo di parlare, senza mostrare numeri tecnici a schermo.
              </p>

              {!isListening ? (
                <button className="primary-button" onClick={startVoiceAnswer}>
                  Avvia microfono
                </button>
              ) : (
                <button className="danger-button" onClick={stopVoiceAnswer}>
                  Ferma registrazione
                </button>
              )}
            </div>
          )}

          <label>La tua risposta</label>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Scrivi qui la tua risposta oppure usa il microfono e poi correggi la trascrizione..."
            rows={9}
          />

          <div className="actions">
            <button className="primary-button" onClick={evaluateAnswer} disabled={loading}>
              Invia risposta
            </button>

            <button className="secondary-button" onClick={() => transitionToStep("gym")}>
              Torna alla palestra
            </button>
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

      {step === "history" && (
        <section className="card">
          <h2>Storico allenamenti</h2>

          {history.length === 0 && (
            <p className="empty-message">Non ci sono ancora allenamenti salvati.</p>
          )}

          {history.map((item) => (
            <div className="history-item" key={`${item.session_id}-${item.question}`}>
              <div className="history-header">
                <h3>{item.company || "Azienda generica"}</h3>
                <span>{item.interview_type}</span>
              </div>

              <p className="date">{item.created_at}</p>

              <p>
                <strong>Difficoltà:</strong> {item.difficulty}
              </p>

              <p>
                <strong>Punteggio:</strong>{" "}
                {item.total_score !== null ? `${item.total_score}/100` : "Non valutato"}
              </p>

              <p>
                <strong>Domanda:</strong> {item.question}
              </p>

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
          ))}

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
