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
  roleLevel = "",
  sector = "",
  validation = { status: "idle", errors: {}, warnings: [], message: "" },
  isValidating = false,
  submitLabel = "Continua",
}) {
  const normalizedGoal = goal.trim();
  const normalizedCompany = company.trim();
  const normalizedRole = role.trim();
  const normalizedRoleLevel = roleLevel.trim();
  const normalizedLink = link.trim();
  const hasRole = normalizedRole && normalizedRole.toLowerCase() !== "da definire";
  const hasQuickMethod = normalizedGoal.length > 19;
  const hasSpecificDetails = normalizedCompany.length > 2 && hasRole && normalizedRole.length > 3;
  const linkLooksValid = !normalizedLink || /^https?:\/\/\S+\.\S+$/i.test(normalizedLink) || /^[\w.-]+\.[a-z]{2,}/i.test(normalizedLink);
  const hasLink = normalizedLink.length > 5 && linkLooksValid;
  const localErrors = {
    description: hasQuickMethod || hasSpecificDetails || hasLink ? "" : "Compila il metodo rapido, i dettagli dell'azienda, oppure il link dell'annuncio.",
    company: hasQuickMethod || hasLink || !normalizedCompany || normalizedCompany.length > 2 ? "" : "Inserisci un nome azienda valido.",
    role: hasQuickMethod || hasLink || !normalizedRole || (hasRole && normalizedRole.length > 3) ? "" : "Inserisci un ruolo lavorativo reale.",
    role_level: !normalizedRoleLevel || normalizedRoleLevel.length >= 2 ? "" : "Inserisci un livello riconoscibile oppure lascia il campo vuoto.",
    link: !normalizedLink || linkLooksValid ? "" : "Inserisci un URL valido oppure lascia il campo vuoto.",
  };
  const fieldErrors = {
    ...Object.fromEntries(Object.entries(localErrors).filter(([, value]) => value)),
    ...(validation.errors || {}),
  };
  const hasLocalValidFields = (hasQuickMethod || hasSpecificDetails || hasLink) && !localErrors.company && !localErrors.role && !localErrors.role_level && !localErrors.link;
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
          className={`interview-textarea ${fieldErrors.description ? "input-error" : ""}`}
          value={goal}
          onChange={(event) => onChange("goal", event.target.value)}
          placeholder="Es. Voglio prepararmi per un colloquio da Data Analyst in Google."
        />
        {fieldErrors.description && <p className="field-error">{fieldErrors.description}</p>}

        <div className="personalize-divider details-section-label">Dettagli specifici</div>

        <label htmlFor="personalize-company">Nome Azienda</label>
        <div className={`personalize-field ${fieldErrors.company ? "input-error" : ""}`}>
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
        <div className={`personalize-field ${fieldErrors.role || fieldErrors.coherence ? "input-error" : ""}`}>
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

        <label htmlFor="personalize-role-level">Livello ruolo</label>
        <div className={`personalize-field ${fieldErrors.role_level ? "input-error" : ""}`}>
          <BriefcaseIcon />
          <input
            id="personalize-role-level"
            value={roleLevel}
            onChange={(event) => onChange("role_level", event.target.value)}
            placeholder="Es. Stage, Junior, Senior"
          />
        </div>
        {fieldErrors.role_level && <p className="field-error">{fieldErrors.role_level}</p>}

        <label htmlFor="personalize-link">Link all'annuncio o all'azienda</label>
        <div className={`personalize-field ${fieldErrors.link ? "input-error" : ""}`}>
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
          Inserendo tutti i campi la simulazione e l'ottimizzazione CV saranno molto più specifiche.
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
            Usa il metodo rapido, compila azienda e ruolo, oppure inserisci un link per continuare.
          </p>
        )}
      </form>
    </section>
  );
}
