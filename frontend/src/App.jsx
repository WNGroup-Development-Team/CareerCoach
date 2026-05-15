import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

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

function App() {
  const [step, setStep] = useState("profile");

  const [userId, setUserId] = useState(null);

  const [profile, setProfile] = useState({
    name: "",
    email: "",
    education: "",
    target_role: "",
    sector: "",
    experience_level: "Junior",
    interview_language: "Italiano",
  });

  const [interviewType, setInterviewType] = useState("conoscitive_motivazionali");
  const [difficulty, setDifficulty] = useState("intermedio");

  const [company, setCompany] = useState("Generica");
  const [questionMode, setQuestionMode] = useState("web");

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

  const updateProfile = (field, value) => {
    setProfile({
      ...profile,
      [field]: value,
    });
  };

  const resetError = () => {
    setError("");
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
      const response = await fetchWithTimeout(`${API_URL}/users`, {
        method: "POST",
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

      setUserId(data.user_id);
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
      console.log("Invio richiesta a /generate-question");

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

      console.log("Risposta ricevuta dal backend:", response.status);

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
          "La generazione delle domande sta impiegando troppo tempo. Prova con 'Solo AI senza ricerca web' oppure riprova tra poco."
        );
      } else {
        setError(
          "Errore di connessione al backend. Controlla che FastAPI sia avviato su http://127.0.0.1:8000."
        );
      }
    } finally {
      console.log("Fine caricamento generateQuestion");
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
  setStep("question");
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

    setStep("gym");
  };

  return (
    <div className="page">
      <header className="header">
        <div className="logo-box">
          <span className="logo-icon">CC</span>
        </div>

        <div>
          <h1>CareerCoach</h1>
          <p>La palestra intelligente per simulare colloqui reali</p>
        </div>
      </header>

      {userId && (
        <nav className="navbar">
          <button onClick={() => setStep("gym")}>Palestra colloqui</button>
          <button onClick={loadHistory}>Storico</button>
          <button onClick={loadProgress}>Progressi</button>
        </nav>
      )}

      {loading && <div className="loading">Caricamento...</div>}
      {error && <div className="error">{error}</div>}

      {step === "profile" && (
        <section className="card">
          <h2>Personalizza la tua esperienza</h2>
          <p className="section-description">
            Inserisci il tuo profilo candidato. Queste informazioni verranno usate
            per cercare domande online, adattarle al tuo ruolo e simulare un colloquio
            più realistico.
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
                value={profile.email}
                onChange={(e) => updateProfile("email", e.target.value)}
                placeholder="Es. silvia@email.com"
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
            Scegli azienda, tipo di colloquio e origine delle domande.
            Verranno generate 10 domande per simulare un colloquio completo.
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

            <div>
              <label>Origine domande</label>
              <select
                value={questionMode}
                onChange={(e) => setQuestionMode(e.target.value)}
              >
                <option value="web">Cerca online domande reali/simili</option>
                <option value="mixed">Web + personalizzazione AI</option>
                <option value="ai">Solo AI senza ricerca web</option>
              </select>
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
      Domande su chi sei, cosa ti aspetti, obiettivi, motivazioni,
      lavoro di gruppo, azienda e percorso personale.
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
      Domande a trabocchetto, indovinelli, casi di ragionamento,
      problem solving e pensiero critico.
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
            <span>{questionMode}</span>
          </div>

          <div className="question-box">{question}</div>

          {questionMode !== "ai" && (
            <div className="info-box">
              La domanda è stata generata usando una ricerca web e personalizzata sul tuo profilo.
              Le fonti sono state salvate nel database dell’app.
            </div>
          )}

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
                risposta e calcola alcune metriche gratuite sul modo di parlare.
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

              {speechMetrics && (
                <div className="speech-metrics">
                  <div>
                    <strong>{speechMetrics.duration_seconds}s</strong>
                    <p>Durata</p>
                  </div>

                  <div>
                    <strong>{speechMetrics.words_count}</strong>
                    <p>Parole</p>
                  </div>

                  <div>
                    <strong>{speechMetrics.words_per_minute}</strong>
                    <p>Parole/min</p>
                  </div>

                  <div>
                    <strong>{speechMetrics.filler_words_count}</strong>
                    <p>Riempitivi</p>
                  </div>
                </div>
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

            <button className="secondary-button" onClick={() => setStep("gym")}>
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
            <h3>Risposta migliorata</h3>
            <p>{feedback.improved_answer}</p>
          </div>

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
                <strong>Origine domanda:</strong> {item.question_mode}
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
                  <strong>Risposta migliorata:</strong>
                  <p>{item.improved_answer}</p>
                </div>
              )}
            </div>
          ))}

          <button className="primary-button" onClick={() => setStep("gym")}>
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

          <button className="primary-button" onClick={() => setStep("gym")}>
            Torna alla palestra
          </button>
        </section>
      )}
    </div>
  );
}

export default App;