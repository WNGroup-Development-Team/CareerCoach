import unittest
from unittest.mock import patch

from main import (
    build_fallback_cv_job_evaluation,
    normalize_cv_job_evaluation,
    review_generated_cv_quality,
    review_generated_cv_quality_locally,
)
from services.cv_optimizer import RewriteInstruction


class CvQualityReviewTests(unittest.TestCase):
    def test_local_review_passes_when_change_is_present(self):
        review = review_generated_cv_quality_locally(
            final_text="PROFILO\nProfilo aggiornato e orientato ai risultati.",
            accepted_instructions=[
                RewriteInstruction(
                    section="PROFILO",
                    original="Profilo precedente.",
                    replacement="Profilo aggiornato e orientato ai risultati.",
                    source_id="profile-change",
                )
            ],
        )

        self.assertTrue(review["ready_to_send"])
        self.assertEqual(review["review_provider"], "local")
        self.assertTrue(review["local_checks_completed"])

    def test_normalize_cv_job_evaluation_recovers_when_model_returns_empty_payload(self):
        fallback = build_fallback_cv_job_evaluation(
            cv_text="ESPERIENZE PROFESSIONALI\nSviluppatore software.",
            company="TIM",
            role="Software Engineering",
            description="Sviluppo software e collaborazione tecnica.",
            sources=[],
            required_skills="Python, Git",
        )

        normalized = normalize_cv_job_evaluation({}, fallback)

        self.assertIn("coach_suggestions", normalized)
        self.assertIsInstance(normalized["coach_suggestions"], list)
        self.assertEqual(normalized["coach_suggestions"], [])
        self.assertIn("questions_for_user", normalized)
        self.assertIsInstance(normalized["questions_for_user"], list)

    def test_local_review_blocks_when_change_is_missing(self):
        review = review_generated_cv_quality_locally(
            final_text="PROFILO\nProfilo precedente.",
            accepted_instructions=[
                RewriteInstruction(
                    section="PROFILO",
                    original="Profilo precedente.",
                    replacement="Profilo aggiornato.",
                    source_id="profile-change",
                )
            ],
        )

        self.assertFalse(review["ready_to_send"])
        self.assertTrue(review["issues"])

    def test_llm_false_critical_does_not_override_passing_local_review(self):
        instruction = RewriteInstruction(
            section="CERTIFICAZIONI",
            original="",
            replacement="Competenza linguistica in inglese certificata a livello B2.",
            source_id="user_box_certifications_0",
        )
        llm_review = {
            "ready_to_send": False,
            "score": 27,
            "issues": [{
                "severity": "critical",
                "section": "CERTIFICAZIONI",
                "description": "La certificazione non è stata accettata dall'azienda.",
            }],
            "revisions": [],
        }

        with patch("main.CV_QUALITY_LLM_ENABLED", True), patch(
            "main.call_analysis_llm",
            return_value=llm_review,
        ):
            review = review_generated_cv_quality(
                final_text=(
                    "PROFILO\nCandidata orientata all'analisi dei dati.\n"
                    "CERTIFICAZIONI\n"
                    "Competenza linguistica in inglese certificata a livello B2."
                ),
                original_cv_text="PROFILO\nCandidata orientata all'analisi dei dati.",
                role="Data Analyst",
                company="Google",
                accepted_instructions=[instruction],
            )

        self.assertTrue(review["ready_to_send"])
        self.assertTrue(review["llm_review_suspect"])
        self.assertTrue(all(item["severity"] == "minor" for item in review["issues"]))


if __name__ == "__main__":
    unittest.main()
