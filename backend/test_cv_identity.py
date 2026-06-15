import unittest

import main


class CvIdentityTests(unittest.TestCase):
    def test_blocks_cv_that_clearly_belongs_to_another_person(self):
        cv_text = "Mario Rossi\nData Analyst\nEsperienze professionali\nFormazione"

        result = main.check_cv_identity(cv_text, "Silvia", "Mucci")

        self.assertFalse(result["matches_user"])
        self.assertIn("un'altra persona", result["message"])

    def test_keeps_ambiguous_name_mismatch_as_warning_only(self):
        cv_text = "Silvia Rossi\nData Analyst\nEsperienze professionali\nFormazione"

        result = main.check_cv_identity(cv_text, "Silvia", "Mucci")

        self.assertIsNone(result["matches_user"])
        self.assertGreaterEqual(result["confidence"], 0.3)

    def test_matches_user_when_full_name_is_present_anywhere_in_cv(self):
        cv_text = (
            "PROFILO PROFESSIONALE\n"
            "Data Analyst orientata al reporting.\n"
            "Silvia Mucci\n"
            "Esperienze professionali\n"
        )

        result = main.check_cv_identity(cv_text, "Silvia", "Mucci")

        self.assertTrue(result["matches_user"])
        self.assertEqual(result["confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()
