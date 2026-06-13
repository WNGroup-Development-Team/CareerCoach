import unittest
from unittest.mock import patch

from main import (
    build_additional_rewrite_instructions,
    build_confirmed_skill_rewrite_instructions,
    call_rewrite_llm,
    fallback_skill_detail_instruction,
    rewrite_preserves_instruction_content,
)
from services.cv_optimizer import RewriteInstruction


class CvGenerationHelperTests(unittest.TestCase):
    @patch("main.call_ollama")
    @patch("main.call_gemini")
    def test_rewrite_uses_gemini_then_falls_back_to_ollama(self, call_gemini, call_ollama):
        call_gemini.side_effect = RuntimeError("Gemini non disponibile")
        call_ollama.return_value = '{"text":"Riscrittura locale"}'

        result = call_rewrite_llm("Riscrivi il testo", context="test")

        self.assertEqual(result["text"], "Riscrittura locale")
        call_gemini.assert_called_once()
        call_ollama.assert_called_once()

    def test_additional_rewrite_instructions_returns_empty_list_without_data(self):
        self.assertEqual(build_additional_rewrite_instructions({}, "Data Analyst"), [])

    def test_language_level_from_certification_box_updates_languages(self):
        instructions = build_additional_rewrite_instructions(
            {"certifications": "B2"},
            "Data Analyst",
            "LINGUE\nItaliano\nInglese",
        )

        self.assertEqual(len(instructions), 1)
        self.assertEqual(instructions[0].section, "LINGUE")
        self.assertIn("Inglese B2", instructions[0].replacement)

    def test_all_confirmed_hard_skills_are_kept_without_truncation(self):
        names = [
            "KPI", "Reporting", "Data visualization", "Database", "Statistica",
            "Dashboard", "Excel avanzato", "Power BI", "Tableau", "BigQuery",
            "Google Analytics",
        ]
        instructions = build_confirmed_skill_rewrite_instructions(
            "HARD SKILLS\nPython | SQL | Java | C++ | ML & AI",
            {
                "confirmed_skills": [
                    {"name": name, "category": "hard_skill", "target_section": "HARD SKILLS"}
                    for name in names
                ],
            },
            "Data Analyst",
        )

        replacement = next(
            item.replacement for item in instructions
            if item.source_id == "confirmed_hard_skills"
        )
        for name in names:
            self.assertIn(name, replacement)

    def test_consolidation_guard_detects_dropped_confirmed_detail(self):
        instruction = RewriteInstruction(
            section="PROFILO",
            original="Studentessa magistrale.",
            replacement=(
                "Studentessa magistrale.\n"
                "Comunicazione dei risultati curata durante progetti universitari."
            ),
        )

        self.assertFalse(
            rewrite_preserves_instruction_content(
                "Studentessa magistrale orientata all'analisi dei dati.",
                instruction,
            )
        )

    @patch("main.build_professional_extra_text")
    def test_soft_skill_detail_is_kept_in_list_and_added_to_existing_profile(self, build_text):
        build_text.return_value = "Approccio analitico alla risoluzione di problemi complessi."

        instruction = fallback_skill_detail_instruction({
            "name": "Pensiero analitico",
            "category": "hard_skill",
            "detail": "Uso un approccio analitico per risolvere problemi complessi.",
        }, 0, "PROFILO\nData analyst orientata alla qualita dei dati.")

        self.assertEqual(instruction.section, "PROFILO")
        self.assertEqual(instruction.category, "profile")
        self.assertIn("Data analyst orientata alla qualita dei dati", instruction.replacement)
        self.assertIn("Approccio analitico applicato", instruction.replacement)
        self.assertNotIn("Pensiero analitico:", instruction.replacement)

    @patch("main.build_professional_extra_text")
    def test_soft_skill_detail_creates_profile_when_missing(self, build_text):
        build_text.return_value = "Collaborazione durante un progetto universitario."

        instruction = fallback_skill_detail_instruction({
            "name": "Collaborazione",
            "category": "soft_skill",
            "detail": "Collaborazione durante un progetto universitario.",
        }, 0, "HARD SKILLS\nPython, SQL")

        self.assertEqual(instruction.section, "PROFILO")
        self.assertEqual(instruction.original, "")
        self.assertIn("Collaborazione", instruction.replacement)

    @patch("main.build_professional_extra_text")
    def test_hard_skill_without_context_stays_only_in_skill_list(self, build_text):
        build_text.return_value = "Utilizzo di Python."

        instruction = fallback_skill_detail_instruction({
            "name": "Python",
            "category": "hard_skill",
            "detail": "Utilizzo di Python.",
        }, 0, "HARD SKILLS\nSQL")

        self.assertIsNone(instruction)

    @patch("main.build_professional_extra_text")
    def test_additional_rewrite_instructions_rewrites_skill_notes(self, build_text):
        build_text.return_value = "Utilizzo di Excel per attivita di analisi dati."

        instructions = build_additional_rewrite_instructions(
            {"additional_notes": "Ho usato Excel per analisi dati."},
            "Data Analyst",
        )

        self.assertEqual(len(instructions), 1)
        self.assertEqual(instructions[0].section, "COMPETENZE TECNICHE")
        self.assertIn("Excel", instructions[0].replacement)
        self.assertIn("Analisi dati", instructions[0].replacement)
        self.assertNotIn("Ho usato", instructions[0].replacement)

    @patch("main.build_professional_extra_text")
    def test_additional_rewrite_instructions_classify_short_fragments(self, build_text):
        def fake_build_text(payload, role):
            note = str(payload.get("additional_notes") or "")
            lowered = note.lower()
            if "excel" in lowered:
                return "Ho utilizzato Excel per analisi dati in ambito universitario."
            if "progetto" in lowered:
                return "Ho collaborato a un progetto universitario di analisi dati."
            return note

        build_text.side_effect = fake_build_text

        instructions = build_additional_rewrite_instructions(
            {
                "additional_notes": "Ho usato Excel per analisi dati. Ho lavorato a un progetto universitario.",
            },
            "Data Analyst",
        )

        self.assertEqual(
            [item.section for item in instructions],
            ["COMPETENZE TECNICHE", "PROGETTI"],
        )
        self.assertIn("Excel", instructions[0].replacement)
        self.assertIn("Progetto universitario", instructions[1].replacement)
        self.assertNotIn("Ho lavorato", instructions[1].replacement)

    @patch("main.build_professional_extra_text")
    def test_all_user_boxes_are_transformed_into_cv_instructions(self, build_text):
        build_text.side_effect = lambda payload, role: str(payload.get("additional_notes") or "")

        instructions = build_additional_rewrite_instructions(
            {
                "technical_skills": "SQL e database relazionali",
                "soft_skills": "Problem solving",
                "projects": "Dashboard vendite con Power BI.",
                "certifications": "Certificazione cloud completata",
                "company_role_notes": "Interesse per il ruolo di Data Analyst",
            },
            "Data Analyst",
        )

        sections = [item.section for item in instructions]
        self.assertIn("COMPETENZE TECNICHE", sections)
        self.assertIn("SOFT SKILLS", sections)
        self.assertIn("PROGETTI", sections)
        self.assertIn("CERTIFICAZIONI", sections)
        self.assertIn("PROFILO", sections)
        project_instruction = next(item for item in instructions if item.section == "PROGETTI")
        self.assertIn("Progetto di data visualization", project_instruction.replacement)

    @patch("main.build_professional_extra_text")
    def test_confirmed_skill_detail_is_professionally_integrated(self, build_text):
        build_text.return_value = (
            "Applicazione in un progetto di sviluppo software per allineare requisiti e aspettative."
        )

        instructions = build_confirmed_skill_rewrite_instructions(
            "PROFILO\nStudente magistrale.\nPROGETTI\nProgetto Software\nSviluppo di un'applicazione Java.",
            {
                "confirmed_skills": [{
                    "name": "Gestione requisiti",
                    "category": "soft_skill",
                    "detail": "Usata in progetto di sviluppo software per allineare requisiti e aspettative.",
                }]
            },
            "Project Manager",
        )

        joined = "\n".join(item.replacement for item in instructions)
        self.assertIn("Gestione requisiti", joined)
        self.assertIn("Studente magistrale", joined)
        self.assertIn("Gestione dei requisiti svolta durante un progetto di sviluppo software", joined)
        self.assertNotIn("Usata in progetto", joined)


if __name__ == "__main__":
    unittest.main()
