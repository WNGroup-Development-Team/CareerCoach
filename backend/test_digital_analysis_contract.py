import unittest

import main


class DigitalAnalysisContractTests(unittest.TestCase):
    def test_fully_aligned_profiles_score_100(self):
        user = {
            "cv_text": "Mario Rossi\nData Analyst 2024\nPython SQL\nGitHub",
            "linkedin_url": "https://www.linkedin.com/in/mario-rossi",
            "linkedin_profile_text": "Mario Rossi\nData Analyst 2024\nPython SQL",
            "instagram_handle": "@mario.rossi",
            "portfolio_url": "https://github.com/mariorossi",
        }
        sources = [{
            "kind": "instagram_public_metadata",
            "url": "https://www.instagram.com/mario.rossi/",
            "title": "Instagram Mario Rossi",
            "content": "Mario Rossi",
        }]
        evidence = {
            "cv_detected_name": {"name": "Mario Rossi"},
            "linkedin_cv_coherence": {"status": "success", "details": ["Data Analyst"]},
            "github_profile": {
                "is_github_link": True,
                "username_match": {"matched": True},
            },
            "social_screenshot_batches": [
                {
                    "valid": True,
                    "profile_type": "instagram",
                    "analyzed_count": 2,
                    "sensitive_flagged_count": 0,
                },
            ],
        }

        result = main.build_deterministic_digital_analysis(user, sources, evidence)

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["headline"], "Profilo digitale eccellente")
        self.assertEqual(
            [finding["status"] for finding in result["findings"]],
            ["allineato", "allineato", "allineato"],
        )
        self.assertEqual(result["sources"]["linkedin_export"], "caricato")
        self.assertEqual(result["sources"]["instagram_screenshots"], "caricati")
        self.assertNotIn("github_screenshots", result["sources"])

    def test_missing_profiles_use_exact_weighted_score(self):
        user = {
            "cv_text": "Mario Rossi\nData Analyst",
            "linkedin_url": "https://www.linkedin.com/in/mario-rossi",
            "linkedin_profile_text": "",
            "instagram_handle": "",
            "portfolio_url": "",
        }
        evidence = {
            "cv_detected_name": {"name": "Mario Rossi"},
            "linkedin_cv_coherence": {"status": "unverified", "details": []},
            "github_profile": {"is_github_link": False},
            "social_screenshot_batches": [],
        }

        result = main.build_deterministic_digital_analysis(user, [], evidence)

        self.assertEqual(result["score"], 20)
        self.assertEqual(result["headline"], "Profilo digitale molto incompleto")
        self.assertEqual(
            [finding["title"] for finding in result["findings"]],
            ["LinkedIn", "Instagram", "GitHub"],
        )
        github = next(item for item in result["findings"] if item["title"] == "GitHub")
        self.assertEqual(github["status"], "da_risolvere")
        self.assertEqual(result["sources"]["linkedin_url"], "caricato")
        self.assertEqual(result["sources"]["linkedin_export"], "non caricato")
        self.assertEqual(result["sources"]["github"], "non caricato")

    def test_sensitive_instagram_screenshot_is_da_migliorare(self):
        user = {
            "cv_text": "Mario Rossi",
            "linkedin_url": "",
            "linkedin_profile_text": "",
            "instagram_handle": "@mario.rossi",
            "portfolio_url": "",
        }
        sources = [{
            "kind": "instagram_public_metadata",
            "url": "https://instagram.com/mario.rossi/",
        }]
        evidence = {
            "cv_detected_name": {"name": "Mario Rossi"},
            "linkedin_cv_coherence": {"status": "unverified", "details": []},
            "github_profile": {"is_github_link": False},
            "social_screenshot_batches": [{
                "valid": True,
                "profile_type": "instagram",
                "analyzed_count": 1,
                "sensitive_flagged_count": 1,
            }],
        }

        result = main.build_deterministic_digital_analysis(user, sources, evidence)
        instagram = next(item for item in result["findings"] if item["title"] == "Instagram")

        self.assertEqual(instagram["status"], "da_migliorare")
        self.assertIn(
            "Il nome e cognome corrispondono all'handle Instagram.",
            instagram["description"],
        )
        self.assertEqual(
            result["sources"]["instagram_screenshots"],
            "caricati con contenuti sensibili",
        )

    def test_payload_contract_returns_only_required_keys(self):
        result = main.build_digital_analysis_from_payload(
            main.DigitalCoherenceInput(
                cv_name="Mario",
                cv_surname="Rossi",
                linkedin_url="https://www.linkedin.com/in/mario-rossi",
                linkedin_export_name="Mario",
                linkedin_export_surname="Rossi",
                linkedin_export_role="Data Analyst",
                linkedin_export_companies=["Acme"],
                instagram_handle="@mario.rossi",
                instagram_handle_from_profile="@mario.rossi",
                instagram_screenshots_analysis="Nessun contenuto sensibile rilevato",
                github_url="https://github.com/mariorossi",
                github_username_from_url="mariorossi",
            )
        )

        self.assertEqual(
            set(result),
            {"score", "headline", "summary", "sources", "findings"},
        )
        self.assertEqual(result["score"], 100)
        self.assertEqual(len(result["findings"]), 3)

    def test_instagram_always_reports_name_mismatch(self):
        result = main.build_digital_analysis_from_payload(
            main.DigitalCoherenceInput(
                cv_name="Mario",
                cv_surname="Rossi",
                instagram_handle="@darkknight",
                instagram_handle_from_profile="@darkknight",
                instagram_screenshots_analysis="Nessun contenuto sensibile rilevato",
            )
        )
        instagram = next(item for item in result["findings"] if item["title"] == "Instagram")

        self.assertEqual(instagram["status"], "da_migliorare")
        self.assertIn(
            "Il nome e cognome non corrispondono all'handle Instagram.",
            instagram["description"],
        )

    def test_github_is_aligned_without_screenshots(self):
        result = main.build_digital_analysis_from_payload(
            main.DigitalCoherenceInput(
                cv_name="Mario",
                cv_surname="Rossi",
                github_url="https://github.com/mariorossi",
                github_username_from_url="mariorossi",
            )
        )
        github = next(item for item in result["findings"] if item["title"] == "GitHub")

        self.assertEqual(github["status"], "allineato")
        self.assertNotIn("screenshot", github["description"].lower())
        self.assertNotIn("github_screenshots", result["sources"])

    def test_matching_instagram_handle_without_screenshots_is_da_migliorare(self):
        result = main.build_digital_analysis_from_payload(
            main.DigitalCoherenceInput(
                cv_name="Mario",
                cv_surname="Rossi",
                instagram_handle="@mario.rossi",
                instagram_handle_from_profile="@mario.rossi",
            )
        )
        instagram = next(item for item in result["findings"] if item["title"] == "Instagram")

        self.assertEqual(instagram["status"], "da_migliorare")
        self.assertIn(
            "Il nome e cognome corrispondono all'handle Instagram.",
            instagram["description"],
        )

    def test_instagram_ignores_screenshot_text_when_images_are_safe(self):
        result = main.build_digital_analysis_from_payload(
            main.DigitalCoherenceInput(
                cv_name="Mario",
                cv_surname="Rossi",
                instagram_handle="@mario.rossi",
                instagram_screenshots_analysis=(
                    "Curriculum vitae, numeri di telefono e molto testo visibile. "
                    "Nessun contenuto sensibile rilevato."
                ),
            )
        )
        instagram = next(item for item in result["findings"] if item["title"] == "Instagram")

        self.assertEqual(instagram["status"], "allineato")
        self.assertIn("non mostrano contenuti sensibili", instagram["description"])
        self.assertEqual(result["sources"]["instagram"], "caricato")
        self.assertEqual(result["sources"]["instagram_screenshots"], "caricati")

    def test_visual_check_ignores_text_only_flags(self):
        result = main.build_visual_analysis_result(
            "uploaded_screenshots",
            1,
            [{
                "flagged": True,
                "categories": ["linguaggio offensivo visibile"],
            }],
            0,
        )

        self.assertEqual(result["flagged_count"], 0)
        self.assertEqual(result["sensitive_flagged_count"], 0)

    def test_visual_check_counts_sensitive_images(self):
        result = main.build_visual_analysis_result(
            "uploaded_screenshots",
            1,
            [{
                "flagged": True,
                "categories": ["violenza"],
            }],
            0,
        )

        self.assertEqual(result["flagged_count"], 1)
        self.assertEqual(result["sensitive_flagged_count"], 1)

    def test_github_mismatch_is_da_migliorare_and_missing_is_da_risolvere(self):
        mismatch = main.build_digital_analysis_from_payload(
            main.DigitalCoherenceInput(
                cv_name="Mario",
                cv_surname="Rossi",
                github_url="https://github.com/darkknight",
                github_username_from_url="darkknight",
            )
        )
        missing = main.build_digital_analysis_from_payload(
            main.DigitalCoherenceInput(
                cv_name="Mario",
                cv_surname="Rossi",
                github_url=None,
            )
        )

        github_mismatch = next(item for item in mismatch["findings"] if item["title"] == "GitHub")
        self.assertEqual(github_mismatch["status"], "da_migliorare")
        github_missing = next(item for item in missing["findings"] if item["title"] == "GitHub")
        self.assertEqual(github_missing["status"], "da_risolvere")


if __name__ == "__main__":
    unittest.main()
