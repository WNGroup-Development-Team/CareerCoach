import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

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

  const [interviewType, setInterviewType] = useState("motivazionale");
  const [difficulty, setDifficulty] = useState("intermedio");

  const [questionId, setQuestionId] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

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
      const response = await fetch(`${API_URL}/users`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(profile),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.detail || "Errore nella creazione del profilo.");
        return;
      }

      setUserId(data.user_id);
      setStep("gym");
    } catch (err) {
      console.error(err);
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const generateQuestion = async () => {
    resetError();
    setLoading(true);
    setQuestion("");
    setAnswer("");
    setFeedback(null);

    try {
      const response = await fetch(`${API_URL}/generate-question`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,
          interview_type: interviewType,
          difficulty: difficulty,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(
          typeof data.detail === "string"
            ? data.detail
            : "Errore nella generazione della domanda."
        );
        console.log(data);
        return;
      }

      setQuestionId(data.question_id);
      setQuestion(data.question);
      setStep("question");
    } catch (err) {
      console.error(err);
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const evaluateAnswer = async () => {
    resetError();

    if (!answer.trim()) {
      setError("Scrivi una risposta prima di inviarla.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/evaluate-answer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question_id: questionId,
          answer: answer,
        }),
      });

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
      setStep("feedback");
    } catch (err) {
      console.error(err);
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    resetError();
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/history/${userId}`);
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
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const loadProgress = async () => {
    resetError();
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/progress/${userId}`);
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
      setError("Errore di connessione al backend. Controlla che FastAPI sia avviato.");
    } finally {
      setLoading(false);
    }
  };

  const startNewTraining = () => {
    resetError();
    setQuestion("");
    setAnswer("");
    setQuestionId(null);
    setFeedback(null);
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
          <p>La tua palestra intelligente per prepararti ai colloqui di lavoro</p>
        </div>
      </header>

      {userId && (
        <nav className="navbar">
          <button onClick={() => setStep("gym")}>Palestra</button>
          <button onClick={loadHistory}>Storico</button>
          <button onClick={loadProgress}>Progressi</button>
        </nav>
      )}

      {loading && <div className="loading">Caricamento...</div>}

      {error && <div className="error">{error}</div>}

      {step === "profile" && (
        <section className="card">
          <h2>Crea il tuo profilo candidato</h2>
          <p className="section-description">
            Queste informazioni verranno usate per generare domande di colloquio
            personalizzate e coerenti con il tuo obiettivo professionale.
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
            Salva profilo e inizia
          </button>
        </section>
      )}

      {step === "gym" && (
        <section className="card">
          <h2>Palestra dei colloqui</h2>
          <p className="section-description">
            Scegli il tipo di colloquio e il livello di difficoltà. L’app genererà
            una domanda realistica e poi valuterà la tua risposta.
          </p>

          <div className="choice-grid">
            <button
              className={interviewType === "conoscitivo" ? "choice active" : "choice"}
              onClick={() => setInterviewType("conoscitivo")}
            >
              <h3>Conoscitivo</h3>
              <p>Domande su percorso, presentazione e obiettivi.</p>
            </button>

            <button
              className={interviewType === "motivazionale" ? "choice active" : "choice"}
              onClick={() => setInterviewType("motivazionale")}
            >
              <h3>Motivazionale</h3>
              <p>Domande su interesse per ruolo, azienda e settore.</p>
            </button>

            <button
              className={interviewType === "comportamentale" ? "choice active" : "choice"}
              onClick={() => setInterviewType("comportamentale")}
            >
              <h3>Comportamentale</h3>
              <p>Domande su esperienze, teamwork, problemi e risultati.</p>
            </button>

            <button
              className={interviewType === "tecnico" ? "choice active" : "choice"}
              onClick={() => setInterviewType("tecnico")}
            >
              <h3>Tecnico</h3>
              <p>Domande legate al ruolo e alle competenze richieste.</p>
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
              Genera domanda
            </button>

            <button className="secondary-button" onClick={loadHistory} disabled={loading}>
              Vedi storico
            </button>
          </div>
        </section>
      )}

      {step === "question" && (
        <section className="card">
          <h2>Domanda del colloquio</h2>

          <div className="tag-row">
            <span>{interviewType}</span>
            <span>{difficulty}</span>
          </div>

          <div className="question-box">{question}</div>

          <label>La tua risposta</label>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Scrivi qui la tua risposta come se fossi davvero davanti a un recruiter..."
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
          </div>

          <div className="feedback-block">
            <h3>Commento</h3>
            <p>{feedback.feedback}</p>
          </div>

          <div className="improved-answer">
            <h3>Risposta migliorata</h3>
            <p>{feedback.improved_answer}</p>
          </div>

          <div className="actions">
            <button className="primary-button" onClick={startNewTraining}>
              Nuovo allenamento
            </button>

            <button className="secondary-button" onClick={loadHistory}>
              Vedi storico
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
            <div className="history-item" key={item.session_id}>
              <div className="history-header">
                <h3>{item.interview_type}</h3>
                <span>{item.difficulty}</span>
              </div>

              <p className="date">{item.created_at}</p>

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