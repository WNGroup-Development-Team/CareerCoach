import { useState } from "react";

export default function TagInput({ label, placeholder, value, onChange, error }) {
  const [inputValue, setInputValue] = useState("");

  const tags = value ? value.split(",").map((t) => t.trim()).filter(Boolean) : [];

  const handleKeyDown = (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag();
    }
  };

  const addTag = () => {
    const newTag = inputValue.trim();
    if (newTag && !tags.includes(newTag)) {
      const newTags = [...tags, newTag];
      onChange(newTags.join(", "));
    }
    setInputValue("");
  };

  const removeTag = (indexToRemove) => {
    const newTags = tags.filter((_, index) => index !== indexToRemove);
    onChange(newTags.join(", "));
  };

  return (
    <label className={`cv-additional-field tag-input-container ${error ? "has-error" : ""}`}>
      {label && <span>{label}</span>}
      <div className="tag-input-box">
        {tags.map((tag, index) => (
          <span key={index} className="tag-pill">
            {tag}
            <button type="button" onClick={() => removeTag(index)} title="Rimuovi">
              &times;
            </button>
          </span>
        ))}
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={addTag}
          placeholder={tags.length === 0 ? placeholder : "Aggiungi un altro..."}
          className="tag-input-field"
        />
      </div>
      <small className="tag-help-text">Premi Invio o la virgola per aggiungere.</small>
      {error && <small className="cv-field-error">{error}</small>}
    </label>
  );
}
