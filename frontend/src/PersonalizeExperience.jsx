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
  validation = { status: "idle", errors: {}, warnings: [], message: "" },
  isValidating = false,
  submitLabel = "Continua",
}) {
  const normalizedGoal = goal.trim();
  const normalizedCompany = company.trim();
  const normalizedRole = role.trim();
  const normalizedLink = link.trim();
  const hasRole = normalizedRole && normalizedRole.toLowerCase() !== "da definire";
  const linkLooksValid = !normalizedLink || /^https?:\/\/\S+\.\S+$/i.test(normalizedLink) || /^[\w.-]+\.[a-z]{2,}/i.test(normalizedLink);
  const localErrors = {
    description: normalizedGoal.length > 19 ? "" : "Descrivi il colloquio o l'annuncio con almeno qualche dettaglio concreto.",
    company: normalizedCompany.length > 2 ? "" : "Inserisci il nome dell'azienda.",
    role: hasRole && normalizedRole.length > 3 ? "" : "Inserisci un ruolo lavorativo reale.",
    link: linkLooksValid ? "" : "Inserisci un URL valido oppure lascia il campo vuoto.",
  };
  const fieldErrors = {
    ...Object.fromEntries(Object.entries(localErrors).filter(([, value]) => value)),
    ...(validation.errors || {}),
  };
  const hasLocalValidFields = !localErrors.description && !localErrors.company && !localErrors.role && !localErrors.link;
  const canSubmit = hasLocalValidFields && !isValidating;

  const handleSubmit = (event) => {
    if (!canSubmit) {
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
        {fieldErrors.description && <p className="field-error">{fieldErrors.description}</p>}

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
        {fieldErrors.company && <p className="field-error">{fieldErrors.company}</p>}

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
        {fieldErrors.role && <p className="field-error">{fieldErrors.role}</p>}
        {fieldErrors.coherence && <p className="field-error">{fieldErrors.coherence}</p>}

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
        {fieldErrors.link && <p className="field-error">{fieldErrors.link}</p>}
        <p className="personalize-hint form-helper-text">
          Facoltativo: se inserisci l'annuncio, le domande saranno piu aderenti alla posizione.
        </p>
        {validation.message && (
          <p className={`job-validation-message ${validation.status}`}>
            {validation.message}
          </p>
        )}
        {(validation.warnings || []).map((warning, index) => (
          <p className="field-warning" key={`${warning}-${index}`}>{warning}</p>
        ))}

        <div className="personalize-actions">
          <button type="button" className="secondary-button card-back-btn" onClick={onBack}>
            <span aria-hidden="true">&larr;</span>
            Indietro
          </button>
          <button
            type="submit"
            className={`primary-button continue-cv-btn ${canSubmit ? "active" : "disabled"}`}
            disabled={!canSubmit}
          >
            {isValidating ? "Validazione..." : submitLabel}
          </button>
        </div>
        {!hasLocalValidFields && (
          <p className="continue-helper-text">
            Completa descrizione, azienda e ruolo con dati coerenti per continuare.
          </p>
        )}
      </form>
    </section>
  );
}
