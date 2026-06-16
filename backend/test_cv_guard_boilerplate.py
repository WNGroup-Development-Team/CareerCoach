import unittest

from main import is_valid_actionable_suggestion
from services.cv_optimizer.safe_cv_guard import is_bad_suggestion


class CvGuardBoilerplateTests(unittest.TestCase):
    def test_central_validator_blocks_system_boilerplate(self):
        self.assertFalse(
            is_valid_actionable_suggestion(
                {
                    "type": "actionableEdit",
                    "category": "experience",
                    "section": "ESPERIENZE PROFESSIONALI",
                    "original_text": "Gestione fatture e prima nota.",
                    "proposed_text": (
                        "Esperienza valorizzata per il ruolo di Accountant, "
                        "evidenziando attivita gia presenti nel CV:\n"
                        "- Gestione fatture e prima nota."
                    ),
                }
            )
        )

    def test_guard_blocks_unsupported_boilerplate_claims(self):
        self.assertTrue(
            is_bad_suggestion(
                {
                    "type": "actionableEdit",
                    "category": "experience",
                    "section": "ESPERIENZE PROFESSIONALI",
                    "original_text": "Gestione fatture e prima nota.",
                    "proposed_text": (
                        "Esperienza valorizzata per il ruolo di Accountant, "
                        "evidenziando attivita gia presenti nel CV:\n"
                        "- Gestione fatture e prima nota."
                    ),
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
