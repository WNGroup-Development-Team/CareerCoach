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

    def test_classifies_cv_like_screenshot_as_invalid(self):
        result = main.classify_social_screenshot_text(
            "Curriculum Vitae\nEsperienze professionali\nFormazione\nCompetenze tecniche\nEmail"
        )

        self.assertFalse(result["valid"])
        self.assertEqual(result["kind"], "cv_or_document")
        self.assertIn("CV o di un documento", result["reason"])

    def test_classifies_professional_profile_screenshot_as_valid(self):
        result = main.classify_social_screenshot_text(
            "LinkedIn\nSilvia Mucci\nData Analyst\nPortfolio\nGitHub\nFollowers"
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["kind"], "social_profile")

    def test_classifies_generic_non_professional_screenshot_as_invalid(self):
        result = main.classify_social_screenshot_text(
            "Vacanza estate\nSelfie al mare\nWeekend con amici"
        )

        self.assertFalse(result["valid"])
        self.assertIn(result["kind"], {"unknown", "unreadable"})

    def test_social_screenshot_score_is_cumulative(self):
        score = main.calculate_social_screenshot_score_adjustment([
            {"valid": True, "flagged_count": 2, "sensitive_flagged_count": 1},
            {"valid": True, "flagged_count": 1, "sensitive_flagged_count": 0},
            {"valid": False, "flagged_count": 8, "sensitive_flagged_count": 8},
        ])

        self.assertEqual(score, -14)

    def test_github_link_is_identified_as_github_platform(self):
        result = main.classify_additional_link(
            "https://github.com/silviamucci",
            [{
                "title": "GitHub Silvia Mucci",
                "url": "https://github.com/silviamucci",
                "content": "Repositories Python Data Analyst",
                "kind": "other_profile_public_snippet",
            }],
            {"status": "matched"},
        )

        self.assertEqual(result["platform"], "github")
        self.assertIn("GitHub", result["message"])

    def test_instagram_private_visibility_is_reported(self):
        result = main.infer_instagram_visibility(
            {"instagram_handle": "@silvia"},
            [],
            {"social_screenshot_batches": []},
        )

        self.assertEqual(result["status"], "private")
        self.assertIn("privato", result["message"])

    def test_cv_and_github_name_match_is_reported_without_blocking(self):
        result = main.evaluate_cv_profile_name_match(
            "Silvia Mucci\nData Analyst\nEsperienze professionali",
            [{
                "title": "GitHub silviamucci",
                "url": "https://github.com/silviamucci",
                "content": "Python repositories",
                "kind": "other_profile_public_snippet",
            }],
            {"other_profile_public_snippet"},
            "il profilo GitHub",
            fallback_values=["silviamucci"],
        )

        self.assertIn(result["status"], {"similar", "matched"})

    def test_name_match_summary_lists_each_platform_explicitly(self):
        evidence = {
            "instagram_link_provided": True,
            "cv_linkedin_name_match": {
                "status": "matched",
                "detected_name": "Silvia Mucci",
                "profile_name_candidate": "Silvia Mucci",
            },
            "instagram_slug_verification": {
                "matched": True,
                "message": "Il nome e cognome corrispondono allo slug del link Instagram.",
            },
        }

        summary = main.describe_cv_profile_name_matches(evidence)

        self.assertIn("Nome CV ↔ LinkedIn: coerente.", summary)
        self.assertIn("Nome CV ↔ Instagram: coerente.", summary)

    def test_name_match_summary_omits_instagram_when_not_provided(self):
        summary = main.describe_cv_profile_name_matches({
            "cv_linkedin_name_match": {"status": "unverified"},
            "instagram_slug_verification": {
                "matched": False,
                "message": "Link o handle Instagram non presente.",
            },
        })

        self.assertNotIn("Instagram", summary)

    def test_instagram_slug_requires_name_and_surname(self):
        matched = main.verify_instagram_slug(
            {"name": "Silvia Mucci", "cv_text": ""},
            "https://instagram.com/silvia.mucci/",
        )
        mismatch = main.verify_instagram_slug(
            {"name": "Silvia Mucci", "cv_text": ""},
            "https://instagram.com/travel_daily/",
        )

        self.assertTrue(matched["matched"])
        self.assertFalse(mismatch["matched"])
        self.assertIn("username riconoscibile", mismatch["coach_tip"])

    def test_instagram_slug_accepts_flexible_personal_brand_variants(self):
        valid_variants = [
            "zerellaluca",
            "zerella_luca",
            "lzerella",
            "luc.zerella",
            "lu_zerella",
            "lucazer",
            "l.zer",
            "luca__zerella",
            "luca.zerella.official",
            "iamlucazerella",
            "real_lucazerella",
            "lzerella00",
            "luca98zerella",
            "lucazerella_26",
            "l_zerella_99",
            "luquid_zerella",
        ]

        for username in valid_variants:
            with self.subTest(username=username):
                result = main.verify_instagram_slug(
                    {"name": "Luca Zerella", "cv_text": ""},
                    f"https://instagram.com/{username}/",
                )
                self.assertTrue(result["matched"], result)
                self.assertGreaterEqual(result["confidence"], 0.6)

    def test_instagram_slug_rejects_abstract_nickname(self):
        result = main.verify_instagram_slug(
            {"name": "Luca Zerella", "cv_text": ""},
            "https://instagram.com/darkknight_99/",
        )

        self.assertFalse(result["matched"])
        self.assertEqual(result["method"], "no_identity_signal")

    def test_linkedin_cv_coherence_compares_skills_roles_and_dates(self):
        result = main.evaluate_linkedin_cv_coherence(
            "Data Analyst dal 2023. Competenze: Python, SQL e Power BI.",
            "Data Analyst | 2023 - presente | Python, SQL, Power BI",
        )

        self.assertEqual(result["status"], "success")
        self.assertGreater(result["score_adjustment"], 0)
        self.assertEqual(result["matched_years"], ["2023"])

    def test_safe_screenshots_are_explicitly_summarized(self):
        summary = main.summarize_screenshot_evidence({
            "social_screenshot_batches": [{
                "valid": True,
                "profile_type": "instagram",
                "analyzed_count": 2,
                "flagged_count": 0,
                "sensitive_flagged_count": 0,
            }],
        })

        self.assertTrue(summary["safe_content"])
        self.assertEqual(summary["count"], 2)


if __name__ == "__main__":
    unittest.main()
