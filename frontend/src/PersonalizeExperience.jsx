import { useEffect, useMemo, useState } from "react";

import "./App.css";
import { VALID_COMPANIES } from "./data/companies";
import { matchCompany } from "./utils/companyValidation";
import { VALID_ROLES, matchRole } from "./utils/roleValidation";

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

function ChevronDownIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

export default function PersonalizeExperience({
  company,
  onBack,
  onChange,
  onSubmit,
  role,
  validation = { status: "idle", errors: {}, warnings: [], message: "" },
  isValidating = false,
  submitLabel = "Continua",
}) {
  const [roleInput, setRoleInput] = useState(role || "");
  const [roleSelected, setRoleSelected] = useState(Boolean(role));
  const [isRoleFocused, setIsRoleFocused] = useState(false);
  const [roleTouched, setRoleTouched] = useState(false);
  const [isCompanyFocused, setIsCompanyFocused] = useState(false);

  useEffect(() => {
    setRoleInput(role || "");
    setRoleSelected(Boolean(role));
  }, [role]);

  const normalizedCompany = company.trim();
  const normalizedRole = roleInput.trim();
  const roleMatch = useMemo(() => matchRole(roleInput, VALID_ROLES), [roleInput]);
  const companyMatch = useMemo(() => matchCompany(company, VALID_COMPANIES), [company]);
  const showRoleSuggestions = isRoleFocused && roleMatch.minLengthReached && roleMatch.suggestions.length > 0;
  const showCompanySuggestions = isCompanyFocused && companyMatch.minLengthReached && companyMatch.suggestions.length > 0;

  const localErrors = {
    description: "",
    role: "",
    company: "",
  };

  if (!roleSelected) {
    if (roleTouched && normalizedRole) {
      localErrors.role = "Seleziona un ruolo dalla lista";
    } else if (roleTouched) {
      localErrors.role = "Inserisci e seleziona un ruolo dalla lista";
    } else {
      localErrors.description = "Seleziona un ruolo dalla lista e inserisci un'azienda reale.";
    }
  }

  if (!normalizedCompany) {
    localErrors.company = "Inserisci il nome di un'azienda reale";
  } else if (companyMatch.minLengthReached && !companyMatch.isValid) {
    localErrors.company = "Inserisci il nome di un'azienda reale";
  }

  const fieldErrors = {
    ...Object.fromEntries(Object.entries(localErrors).filter(([, value]) => value)),
    ...(validation.errors || {}),
  };

  const hasLocalValidFields = roleSelected && companyMatch.isValid && !localErrors.role && !localErrors.company;
  const canSubmit = hasLocalValidFields && !isValidating;

  const handleSubmit = (event) => {
    if (!canSubmit) {
      event.preventDefault();
      setRoleTouched(true);
      return;
    }

    onSubmit(event);
  };

  const handleRoleInput = (event) => {
    const value = event.target.value;
    setRoleInput(value);
    setRoleSelected(false);
    onChange("role", "");
  };

  const handleRoleSelect = (selectedRole) => {
    setRoleInput(selectedRole);
    setRoleSelected(true);
    setRoleTouched(false);
    setIsRoleFocused(false);
    onChange("role", selectedRole);
  };

  const handleRoleBlur = () => {
    window.setTimeout(() => {
      setIsRoleFocused(false);
      setRoleTouched(true);
    }, 120);
  };

  const handleCompanySuggestionClick = (selectedCompany) => {
    onChange("company", selectedCompany);
    setIsCompanyFocused(false);
  };

  return (
    <section className="personalize-page">
      <div className="personalize-heading">
        <h2>A quale ruolo stai puntando?</h2>
        <p>Queste informazioni verranno usate per ottimizzare il tuo CV e personalizzare la simulazione del colloquio.</p>
      </div>

      <div className="personalize-layout">
        <form className="personalize-card" onSubmit={handleSubmit}>
          <div className="personalize-divider details-section-label">Dettagli specifici</div>

          {fieldErrors.description && <p className="field-error">{fieldErrors.description}</p>}
          <p className="field-hint">
            Seleziona un ruolo dalla lista e inserisci un'azienda riconoscibile per procedere.
          </p>

          <label htmlFor="personalize-role">Ruolo</label>
          <div className={`personalize-field personalize-select-field ${fieldErrors.role ? "input-error" : ""}`}>
            <BriefcaseIcon />
            <input
              id="personalize-role"
              value={roleInput}
              onBlur={handleRoleBlur}
              onChange={handleRoleInput}
              onFocus={() => setIsRoleFocused(true)}
              placeholder="Es. UX Designer, Data Analyst, Software Engineer"
              autoComplete="off"
            />
            <span className="personalize-field-caret" aria-hidden="true">
              <ChevronDownIcon />
            </span>
            {showRoleSuggestions && (
              <div className="personalize-role-suggestions" role="listbox" aria-label="Suggerimenti ruolo">
                {roleMatch.suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    className="personalize-role-suggestion"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => handleRoleSelect(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
          {fieldErrors.role && <p className="field-error">{fieldErrors.role}</p>}

          <label htmlFor="personalize-company">Azienda</label>
          <div className={`personalize-field ${fieldErrors.company ? "input-error" : ""}`}>
            <BuildingIcon />
            <input
              id="personalize-company"
              value={company}
              onBlur={() => window.setTimeout(() => setIsCompanyFocused(false), 120)}
              onChange={(event) => onChange("company", event.target.value)}
              onFocus={() => setIsCompanyFocused(true)}
              placeholder="es. Google, TechFlow"
              autoComplete="off"
            />
            {showCompanySuggestions && (
              <div className="personalize-role-suggestions" role="listbox" aria-label="Suggerimenti azienda">
                {companyMatch.suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    className="personalize-role-suggestion"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => handleCompanySuggestionClick(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
          {fieldErrors.company && <p className="field-error">{fieldErrors.company}</p>}

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
            <h3>Piu dettagli, migliore sara il risultato</h3>
            <ul>
              <li>Seleziona un ruolo professionale dalla lista suggerita.</li>
              <li>Inserisci il nome di un'azienda reale per attivare la simulazione.</li>
            </ul>
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
