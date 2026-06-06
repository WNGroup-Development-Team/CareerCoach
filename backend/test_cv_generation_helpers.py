import unittest
from unittest.mock import patch

from main import build_additional_rewrite_instructions


class CvGenerationHelperTests(unittest.TestCase):
    def test_additional_rewrite_instructions_returns_empty_list_without_data(self):
        self.assertEqual(build_additional_rewrite_instructions({}, "Data Analyst"), [])

    @patch("main.build_professional_extra_text")
    def test_additional_rewrite_instructions_returns_instruction(self, build_text):
        build_text.return_value = "Progetto di analisi dati confermato."

        instructions = build_additional_rewrite_instructions(
            {"additional_notes": "Ho realizzato un progetto di analisi dati."},
            "Data Analyst",
        )

        self.assertEqual(len(instructions), 1)
        self.assertEqual(instructions[0].section, "PROGETTI")
        self.assertEqual(instructions[0].replacement, "Progetto di analisi dati confermato.")


if __name__ == "__main__":
    unittest.main()
