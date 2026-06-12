import unittest
from unittest.mock import patch

from main import (
    build_additional_rewrite_instructions,
    build_confirmed_skill_rewrite_instructions,
)


class CvGenerationHelperTests(unittest.TestCase):
    def test_additional_rewrite_instructions_returns_empty_list_without_data(self):
        self.assertEqual(build_additional_rewrite_instructions({}, "Data Analyst"), [])

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
        self.assertIn("Progetto di sviluppo software", joined)
        self.assertIn("Collaborazione con il team", joined)
        self.assertNotIn("Usata in progetto", joined)


if __name__ == "__main__":
    unittest.main()
