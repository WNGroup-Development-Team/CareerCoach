import unittest
from unittest.mock import patch

import main


class DigitalPresenceResilienceTests(unittest.TestCase):
    def test_update_digital_presence_continues_when_external_steps_fail(self):
        existing_user = [None] * 22
        existing_user[18] = ""
        existing_user[19] = ""
        existing_user[21] = ""

        updated_user = [None] * 22

        with (
            patch.object(main, "require_user_session"),
            patch.object(main, "get_connection") as get_connection,
            patch.object(main, "fetch_user_by_id", side_effect=[existing_user, updated_user]),
            patch.object(main, "user_to_response", return_value={"target_role": "", "linkedin_url": "", "portfolio_url": "", "instagram_handle": ""}),
            patch.object(main, "recover_saved_cv_text", return_value=""),
            patch.object(main, "analyze_public_social_media", side_effect=RuntimeError("visual down")),
            patch.object(main, "search_public_profile_signals", side_effect=RuntimeError("tavily down")),
            patch.object(main, "analyze_digital_profile", return_value={"score": 0, "headline": "", "summary": "", "findings": [], "sources": [], "analysis_evidence": {}}),
        ):
            connection = get_connection.return_value
            cursor = connection.cursor.return_value
            result = main.update_digital_presence(
                1,
                main.DigitalPresenceUpdate(
                    linkedin_url="",
                    portfolio_url="",
                    instagram_handle="",
                    target_role="",
                ),
                authorization=None,
            )

        self.assertIn("warnings", result["analysis"])
        self.assertEqual(
            result["analysis"]["warnings"],
            [
                "Analisi media pubblici non disponibile al momento.",
                "Ricerca dei segnali pubblici dai link non disponibile al momento.",
            ],
        )
        cursor.execute.assert_called()
        connection.commit.assert_called()


if __name__ == "__main__":
    unittest.main()
