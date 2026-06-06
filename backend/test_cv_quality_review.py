import unittest

from main import review_generated_cv_quality_locally
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


if __name__ == "__main__":
    unittest.main()
