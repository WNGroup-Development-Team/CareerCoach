import unittest

from main import (
    build_deterministic_cv_scorecard,
    build_fallback_cv_job_evaluation,
    compare_cv_scorecards,
    compute_digital_presence_score,
    normalize_cv_job_evaluation,
)


class CvScoringTests(unittest.TestCase):
    def test_incomplete_cv_cannot_receive_high_scores(self):
        scorecard = build_deterministic_cv_scorecard(
            "Mario Rossi\nPython",
            "",
            "Data Analyst",
            "Analisi dati, SQL, dashboard e reporting.",
        )

        self.assertLessEqual(scorecard["overall_score"], 50)
        self.assertLessEqual(scorecard["completeness_score"], 48)
        self.assertLessEqual(scorecard["ats_score"], 50)

    def test_relevant_real_content_improves_multiple_components(self):
        before_text = (
            "Mario Rossi\nmario@example.com\n"
            "FORMAZIONE\nLaurea in Informatica\n"
            "HARD SKILLS\nPython"
        )
        after_text = (
            "Mario Rossi\nmario@example.com\n+39 333 1234567\n"
            "PROFILO PROFESSIONALE\n"
            "Data Analyst con esperienza in analisi dati, reporting e dashboard.\n"
            "ESPERIENZE PROFESSIONALI\n"
            "- Analizzato 120000 record con Python e SQL.\n"
            "- Creato dashboard Power BI e KPI riducendo del 25% i tempi di reporting.\n"
            "PROGETTI\n"
            "- Pipeline di data cleaning e visualizzazione dei dati.\n"
            "FORMAZIONE\nLaurea in Informatica, 2024\n"
            "HARD SKILLS\nPython, SQL, Power BI, Data visualization, KPI, Reporting\n"
            "SOFT SKILLS\nPensiero analitico, Comunicazione dei risultati\n"
            "LINGUE\nItaliano, Inglese B2"
        )
        target = {
            "company": "Acme",
            "role": "Data Analyst",
            "description": "Analisi dati, SQL, Power BI, dashboard, KPI e reporting.",
        }
        before = build_deterministic_cv_scorecard(before_text, **target)
        after = build_deterministic_cv_scorecard(after_text, **target)
        comparison = compare_cv_scorecards(before, after)

        self.assertGreater(comparison["delta"]["overall_score"], 0)
        self.assertGreater(comparison["delta"]["ats_score"], 0)
        self.assertGreater(comparison["delta"]["keyword_score"], 0)
        self.assertGreater(comparison["delta"]["role_match_score"], 0)
        self.assertGreater(comparison["delta"]["completeness_score"], 0)

    def test_role_change_changes_match_score(self):
        cv_text = (
            "PROFILO PROFESSIONALE\nData Analyst orientato al reporting.\n"
            "ESPERIENZE PROFESSIONALI\nAnalisi dataset e creazione dashboard.\n"
            "HARD SKILLS\nPython, SQL, Power BI, KPI, Data visualization\n"
            "FORMAZIONE\nLaurea in Informatica"
        )

        data_score = build_deterministic_cv_scorecard(
            cv_text, "", "Data Analyst", "SQL, dashboard e reporting"
        )
        frontend_score = build_deterministic_cv_scorecard(
            cv_text, "", "Frontend Developer", "React, TypeScript e accessibilità"
        )

        self.assertGreater(
            data_score["role_match_score"],
            frontend_score["role_match_score"],
        )
        self.assertNotEqual(
            data_score["scoring_context"]["target_fingerprint"],
            frontend_score["scoring_context"]["target_fingerprint"],
        )

    def test_llm_scores_do_not_override_deterministic_scorecard(self):
        fallback = build_fallback_cv_job_evaluation(
            "FORMAZIONE\nLaurea\nHARD SKILLS\nPython",
            "",
            "Data Analyst",
            "SQL e dashboard",
            [],
        )
        normalized = normalize_cv_job_evaluation({
            "overall_score": 99,
            "ats_score": 99,
            "role_match_score": 99,
            "completeness_score": 99,
        }, fallback)

        self.assertEqual(normalized["overall_score"], fallback["overall_score"])
        self.assertEqual(normalized["ats_score"], fallback["ats_score"])
        self.assertEqual(normalized["role_match_score"], fallback["role_match_score"])
        self.assertEqual(normalized["completeness_score"], fallback["completeness_score"])

    def test_digital_score_uses_verified_evidence_and_penalties(self):
        evidence = {
            "can_compare_with_cv": True,
            "cv_profile_loaded": True,
            "linkedin_export_verified": True,
            "linkedin_public_verified": False,
            "linkedin_official_verified": False,
            "other_profile_identity": {"status": "unverified"},
            "verified_profile_count": 1,
            "social_text_analyses": {
                "instagram": {"evaluation": {"status": "aligned"}},
            },
            "visual_score_adjustment": -12,
        }

        self.assertEqual(compute_digital_presence_score(evidence), 29)
        self.assertEqual(
            compute_digital_presence_score({**evidence, "can_compare_with_cv": False}),
            0,
        )


if __name__ == "__main__":
    unittest.main()
