import "./App.css";

function BuildingIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 21V7l8-4 8 4v14" />
      <path d="M9 21v-4h6v4" />
      <path d="M8 9h.01M12 9h.01M16 9h.01M8 13h.01M12 13h.01M16 13h.01" />
    </svg>
  );
}

function BriefcaseIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M10 6V5a2 2 0 0 1 2-2h0a2 2 0 0 1 2 2v1" />
      <path d="M4 7h16v12H4z" />
      <path d="M4 12h16" />
    </svg>
  );
}

function LinkIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M10 13a5 5 0 0 0 7.07 0l2-2a5 5 0 0 0-7.07-7.07l-1.14 1.14" />
      <path d="M14 11a5 5 0 0 0-7.07 0l-2 2A5 5 0 0 0 12 20.07l1.14-1.14" />
    </svg>
  );
}

export default function PersonalizeExperience({
  company,
  goal,
  link,
  onBack,
  onChange,
  onSubmit,
  role,
  submitLabel = "Continua",
}) {
  const normalizedRole = role.trim();
  const hasRole = normalizedRole && normalizedRole.toLowerCase() !== "da definire";
  const hasInterviewContext = Boolean(
    goal.trim() ||
    company.trim() ||
    hasRole ||
    link.trim()
  );

  const handleSubmit = (event) => {
    if (!hasInterviewContext) {
      event.preventDefault();
      return;
    }

    onSubmit(event);
  };

  return (
    <section className="personalize-page">
      <div className="personalize-heading">
        <h2>Personalizza la simulazione</h2>
        <p>Inserisci il ruolo o l'annuncio per ricevere domande e feedback piu mirati.</p>
      </div>

      <form className="personalize-card" onSubmit={handleSubmit}>
        <div className="quick-method-label">Metodo rapido</div>
        <label htmlFor="goal">Per quale colloquio vuoi prepararti?</label>
        <textarea
          id="goal"
          className="interview-textarea"
          value={goal}
          onChange={(event) => onChange("goal", event.target.value)}
          placeholder="Es. Voglio prepararmi per un colloquio da Data Analyst in Google."
        />

        <div className="personalize-divider details-section-label">Dettagli specifici</div>

        <label htmlFor="personalize-company">Nome Azienda</label>
        <div className="personalize-field">
          <BuildingIcon />
          <input
            id="personalize-company"
            value={company}
            onChange={(event) => onChange("company", event.target.value)}
            placeholder="es. Google, TechFlow"
          />
        </div>

        <label htmlFor="personalize-role">Ruolo desiderato</label>
        <div className="personalize-field">
          <BriefcaseIcon />
          <input
            id="personalize-role"
            value={role}
            onChange={(event) => onChange("role", event.target.value)}
            placeholder="Es. UX Designer, Data Analyst, Software Engineer"
          />
        </div>

        <label htmlFor="personalize-link">Link all'annuncio o all'azienda</label>
        <div className="personalize-field">
          <LinkIcon />
          <input
            id="personalize-link"
            value={link}
            onChange={(event) => onChange("link", event.target.value)}
            placeholder="https://..."
          />
        </div>
        <p className="personalize-hint form-helper-text">
          Facoltativo: se inserisci l'annuncio, le domande saranno piu aderenti alla posizione.
        </p>

        <div className="personalize-actions">
          <button type="button" className="secondary-button card-back-btn" onClick={onBack}>
            <span aria-hidden="true">&larr;</span>
            Indietro
          </button>
          <button
            type="submit"
            className={`primary-button continue-cv-btn ${hasInterviewContext ? "active" : "disabled"}`}
            disabled={!hasInterviewContext}
          >
            {submitLabel}
          </button>
        </div>
        {!hasInterviewContext && (
          <p className="continue-helper-text">
            Inserisci almeno una descrizione o un ruolo per continuare.
          </p>
        )}
      </form>
    </section>
  );
}
