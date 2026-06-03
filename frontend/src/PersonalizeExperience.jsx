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
  return (
    <section className="personalize-page">
      <div className="personalize-heading">
        <h2>Personalizza la tua esperienza</h2>
        <p>Fornisci i dettagli per permettere all'IA di supportarti al meglio.</p>
      </div>

      <form className="personalize-card" onSubmit={onSubmit}>
        <label htmlFor="goal">Cosa vuoi fare?</label>
        <textarea
          id="goal"
          value={goal}
          onChange={(event) => onChange("goal", event.target.value)}
          placeholder="Descrivi il lavoro per cui vuoi prepararti (es. 'Voglio prepararmi per un colloquio in Google come UX Designer')."
        />

        <div className="personalize-divider">OPPURE FORNISCI DETTAGLI SPECIFICI</div>

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
            placeholder="es. Junior UX Researcher"
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
        <p className="personalize-hint">Opzionale, ma aiuta a fornire risposte piu mirate.</p>

        <div className="personalize-actions">
          <button type="button" className="secondary-button" onClick={onBack}>Indietro</button>
          <button type="submit" className="primary-button">{submitLabel}</button>
        </div>
      </form>
    </section>
  );
}
