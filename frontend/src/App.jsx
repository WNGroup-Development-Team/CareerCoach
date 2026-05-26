import { useEffect, useState } from "react";
import "./App.css";
import logoCareerCoach from "./assets/career-coach-logo.png";

const API_URL = "http://127.0.0.1:8000";
const AUTH_TOKEN_KEY = "careercoach_auth_token";
const INTRO_SPLASH_DURATION_MS = 3000;
const TRANSITION_DURATION_MS = 2000;

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
  return Boolean(
    profile.name.trim() &&
      profile.education.trim() &&
      profile.target_role.trim() &&
      profile.sector.trim()
  );
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
  });

  const [interviewType, setInterviewType] = useState("conoscitive_motivazionali");
  const [difficulty, setDifficulty] = useState("intermedio");

  const [company, setCompany] = useState("Generica");
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
    setShowTransition(true);

    setTimeout(() => {
      setStep(nextStep);
      setShowTransition(false);
    }, TRANSITION_DURATION_MS);
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
    });
    setStep(isProfileComplete({
      name: user.name || "",
      education: user.education || "",
      target_role: user.target_role || "",
      sector: user.sector || "",
      email: user.email || "",
      phone: user.phone || "",
      experience_level: user.experience_level || "Junior",
      interview_language: user.interview_language || "Italiano",
    }) ? "gym" : "profile");
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
            company: company,
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

  if (showSplash) {
    return <SplashScreen />;
  }

  return (
    <div className={step === "auth" ? "page auth-page" : "page"}>
      {step !== "auth" && (
        <header className="header">
          <div className="brand">
            <img
              className="app-logo"
              src={logoCareerCoach}
              alt="Logo Career Coach"
            />

            <div className="brand-copy">
              <h1 className="brand-title" aria-label="CareerCoach">
                <span className="brand-title-career">Career</span>
                <span className="brand-title-coach">Coach</span>
              </h1>
              <p>La palestra intelligente per simulare colloqui reali</p>
            </div>
          </div>
        </header>
      )}

      {userId && (
        <nav className="navbar">
          <button onClick={() => transitionToStep("gym")}>Palestra colloqui</button>
          <button onClick={loadHistory}>Storico</button>
          <button onClick={loadProgress}>Progressi</button>
          <button onClick={logoutUser}>Esci</button>
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

      {step === "profile" && (
        <section className="card">
          <h2>Personalizza la tua esperienza</h2>
          <p className="section-description">
            Inserisci il tuo profilo candidato. Queste informazioni verranno usate
            per generare domande realistiche, adattarle al tuo ruolo e simulare un colloquio completo.
          </p>

          <div className="form-grid">
            <div>
              <label>Nome</label>
              <input
                value={profile.name}
                onChange={(e) => updateProfile("name", e.target.value)}
                placeholder="Es. Silvia"
              />
            </div>

            <div>
              <label>Email</label>
              <input
                type="email"
                value={profile.email}
                onChange={(e) => updateProfile("email", e.target.value)}
                placeholder="Es. silvia@email.com"
              />
            </div>

            <div>
              <label>Cellulare</label>
              <input
                type="tel"
                value={profile.phone}
                onChange={(e) => updateProfile("phone", e.target.value)}
                placeholder="Es. +39 333 123 4567"
              />
            </div>

            <div className="full">
              <label>Percorso di studi</label>
              <input
                value={profile.education}
                onChange={(e) => updateProfile("education", e.target.value)}
                placeholder="Es. Laurea magistrale in Ingegneria Informatica"
              />
            </div>

            <div>
              <label>Ruolo target</label>
              <input
                value={profile.target_role}
                onChange={(e) => updateProfile("target_role", e.target.value)}
                placeholder="Es. Junior Data Analyst"
              />
            </div>

            <div>
              <label>Settore</label>
              <input
                value={profile.sector}
                onChange={(e) => updateProfile("sector", e.target.value)}
                placeholder="Es. AI e Data Science"
              />
            </div>

            <div>
              <label>Livello esperienza</label>
              <select
                value={profile.experience_level}
                onChange={(e) => updateProfile("experience_level", e.target.value)}
              >
                <option>Junior</option>
                <option>Intermedio</option>
                <option>Senior</option>
              </select>
            </div>

            <div>
              <label>Lingua colloquio</label>
              <select
                value={profile.interview_language}
                onChange={(e) => updateProfile("interview_language", e.target.value)}
              >
                <option>Italiano</option>
                <option>Inglese</option>
              </select>
            </div>
          </div>

          <button className="primary-button" onClick={createProfile} disabled={loading}>
            Salva profilo e continua
          </button>
        </section>
      )}

      {step === "gym" && (
        <section className="card">
          <h2>Palestra dei colloqui</h2>
          <p className="section-description">
            Scegli azienda, tipologia di colloquio e livello di difficoltà.
            L’app genererà 10 domande realistiche e personalizzate per simulare un colloquio completo.
          </p>

          <div className="form-grid">
            <div>
              <label>Azienda target</label>
              <input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Es. Amazon, Google, Deloitte, Reply, TIM..."
              />
            </div>
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
