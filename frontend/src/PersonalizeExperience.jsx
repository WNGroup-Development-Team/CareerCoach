import "./App.css";

function isPlausibleRole(value) {
  const normalized = value.trim().toLowerCase().replace(/\s+/g, " ");
  const words = normalized.match(/[a-zà-ÿ0-9+#.-]+/gi) || [];
  const genericValues = new Set([
    "lavoro",
    "ruolo",
    "impiego",
    "posto",
    "qualsiasi lavoro",
    "lavoro qualunque",
    "da definire",
  ]);
  const sentenceTerms = /\b(voglio|vorrei|prepararmi|colloquio|intervista|candidarmi|cerco|azienda|presso)\b/i;

  return (
    normalized.length >= 4
    && words.length >= 1
    && words.length <= 6
    && !genericValues.has(normalized)
    && !sentenceTerms.test(normalized)
  );
}

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
  link, // kept for backend compatibility (not used in UI anymore)
  onBack,
  onChange,
  onSubmit,
  role,
  roleLevel, // kept for backend compatibility (not used in UI anymore)
  sector = "",
  validation = { status: "idle", errors: {}, warnings: [], message: "" },
  isValidating = false,
  requireRole = false,
  submitLabel = "Continua",
}) {
  const normalizedGoal = goal.trim();
  const normalizedCompany = company.trim();
  const normalizedRole = role.trim();
  const hasQuickMethod = normalizedGoal.length > 19;
  const hasPlausibleRole = isPlausibleRole(normalizedRole);
  const hasSpecificDetails = normalizedCompany.length > 2 && hasPlausibleRole;

  const localErrors = {
    description: hasQuickMethod || hasSpecificDetails ? "" : "Descrivi la candidatura o compila i dettagli specifici.",
    company: hasQuickMethod || (!normalizedCompany || normalizedCompany.length > 2) ? "" : "Inserisci un nome azienda valido.",
    role: requireRole && !hasPlausibleRole
      ? "Inserisci un ruolo professionale specifico, ad esempio Data Analyst o Software Engineer."
      : (!normalizedRole || hasPlausibleRole)
        ? ""
        : "Inserisci solo il titolo del ruolo, non una frase sul colloquio.",
  };

  const fieldErrors = {
    ...Object.fromEntries(Object.entries(localErrors).filter(([, value]) => value)),
    ...(validation.errors || {}),
  };

  const hasRequiredContext = requireRole
    ? hasPlausibleRole && (hasQuickMethod || normalizedCompany.length > 2)
    : hasQuickMethod || hasSpecificDetails;
  const hasLocalValidFields = hasRequiredContext && !localErrors.company && !localErrors.role;
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
        <h2>A quale ruolo stai puntando?</h2>
        <p>Queste informazioni verranno usate per ottimizzare il tuo CV e personalizzare la simulazione del colloquio.</p>
      </div>

      <div className="personalize-layout">
        <form className="personalize-card" onSubmit={handleSubmit}>
          <div className="quick-method-label">Metodo rapido</div>
          <label htmlFor="goal">Descrivilo in una frase</label>
          <textarea
            id="goal"
            className={`interview-textarea ${fieldErrors.description ? "input-error" : ""}`}
            value={goal}
            onChange={(event) => onChange("goal", event.target.value)}
            placeholder="Es. Voglio prepararmi per un colloquio da Data Analyst in Google."
          />
          {fieldErrors.description && <p className="field-error">{fieldErrors.description}</p>}

          <div className="personalize-divider details-section-label">Dettagli specifici</div>

          {fieldErrors.company && <p className="field-error">{fieldErrors.company}</p>}

          <label htmlFor="personalize-role">Ruolo</label>
          <div className={`personalize-field ${fieldErrors.role || fieldErrors.coherence ? "input-error" : ""}`}>
            <BriefcaseIcon />
            <input
              id="personalize-role"
              value={role}
              onChange={(event) => onChange("role", event.target.value)}
              placeholder="Es. UX Designer, Data Analyst, Software Engineer"
            />
          </div>

          <label htmlFor="personalize-company">Azienda</label>
          <div className={`personalize-field ${fieldErrors.company ? "input-error" : ""}`}>
            <BuildingIcon />
            <input
              id="personalize-company"
              value={company}
              onChange={(event) => onChange("company", event.target.value)}
              placeholder="es. Google, TechFlow"
            />
          </div>
          
          {fieldErrors.role && <p className="field-error">{fieldErrors.role}</p>}
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
        </form>

        <aside className="personalize-sidebar">
          <div className="personalize-sidebar-card">
            <span className="personalize-sidebar-kicker">Come funziona</span>
            <h3>Più dettagli, migliore sarà il risultato</h3>
            <ol>
              <li>Indica un ruolo professionale specifico.</li>
              <li>Aggiungi l'azienda per rendere l'analisi più mirata.</li>
              <li>Usa la frase libera per raccontare il tuo obiettivo.</li>
            </ol>
          </div>

          <div className="personalize-sidebar-card personalize-live-summary">
            <span className="personalize-sidebar-kicker">Riepilogo</span>
            <div>
              <BriefcaseIcon />
              <span>
                <small>Ruolo</small>
                <strong>{normalizedRole || "Da definire"}</strong>
              </span>
            </div>
            <div>
              <BuildingIcon />
              <span>
                <small>Azienda</small>
                <strong>{normalizedCompany || "Da definire"}</strong>
              </span>
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
