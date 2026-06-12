import unittest
from unittest.mock import patch

import main


class SocialProfileTextTests(unittest.TestCase):
    def test_clean_ocr_text_removes_duplicate_lines(self):
        result = main.clean_social_ocr_text("Data Analyst\nData Analyst\n  Python e SQL  ")

        self.assertEqual(result, "Data Analyst\nPython e SQL")

    def test_profile_text_is_aligned_with_target_role(self):
        result = main.evaluate_social_profile_text(
            "Silvia Mucci\nData Analyst\nPython, SQL e Power BI\nlinkedin.com/in/silvia",
            "instagram",
            {"target_role": "Data Analyst"},
        )

        self.assertEqual(result["status"], "aligned")
        self.assertEqual(result["matched_role_terms"], ["data", "analyst"])
        self.assertIn("Data Analyst", result["bio_candidate"])

    def test_generic_bio_generates_role_suggestions(self):
        result = main.evaluate_social_profile_text(
            "Viaggi, musica e fotografia",
            "instagram",
            {"target_role": "Software Engineer"},
        )

        self.assertEqual(result["status"], "review")
        self.assertTrue(any("Software Engineer" in item for item in result["suggestions"]))
        self.assertTrue(any("identità professionale" in item for item in result["suggestions"]))

    def test_ocr_failure_does_not_raise(self):
        with (
            patch.object(main, "VISION_PROVIDER", "ollama"),
            patch.object(
                main,
                "extract_social_text_with_rapidocr",
                side_effect=RuntimeError("rapidocr unavailable"),
            ),
            patch.object(
                main,
                "extract_social_text_with_ollama",
                side_effect=RuntimeError("timeout"),
            ),
        ):
            result = main.extract_social_screenshot_texts([{"image_url": {"url": "data:image/png;base64,AA=="}}])

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["extracted_text"], "")


if __name__ == "__main__":
    unittest.main()
