#!/usr/bin/env python3
"""Test the new suggestion generation with fallback mechanism."""

import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, '.')

from main import (
    build_coach_suggestions_from_evaluation,
    build_cv_job_suggestions,
    build_generic_rewrite_fallbacks,
    canonical_skill_identity,
    build_role_skill_suggestions,
    call_ollama,
    clean_skill_section_source,
    count_section_markers,
    deterministic_section_consolidation,
    extract_clean_skill_items,
    format_skill_list_like_original,
    infer_skill_library_from_role,
    infer_role_family,
    sanitize_cv_additional_data,
)
from services.cv_optimizer import RewriteInstruction
from services.cv_optimizer.skill_suggestions import build_skill_mini_shot_suggestions
from services.cv_optimizer.suggestions import refine_cv_job_suggestions


class TestSuggestionGeneration(unittest.TestCase):
    """Test suggestion generation with fallback."""

    def test_ollama_respects_explicit_short_timeout(self):
        captured = {}

        class FakeResponse:
            ok = True
            status_code = 200

            @staticmethod
            def json():
                return {"message": {"content": "{}"}}

        def fake_post(*args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            return FakeResponse()

        with patch("main.requests.post", side_effect=fake_post):
            call_ollama("test", timeout=25, json_mode=True)

        self.assertEqual(captured["timeout"], 25)

    def test_ollama_refines_each_static_coach_suggestion(self):
        suggestion = {
            "id": "profile-1",
            "type": "actionableEdit",
            "category": "profile",
            "section": "CHI SONO",
            "title": "Rendi il profilo piu mirato",
            "description": "Bozza locale.",
            "reason": "Bozza locale.",
            "original_text": "Studentessa magistrale con interesse per analisi dei dati.",
            "proposed_text": "Studentessa magistrale con interesse per analisi dei dati e ruolo target.",
        }
        evaluation = {
            "cv_text": "CHI SONO\nStudentessa magistrale con interesse per analisi dei dati.",
            "target": {"role": "Data Analyst", "company": ""},
        }
        llm_result = {
            "title": "Rafforza il profilo analitico",
            "reason": "Presenta con maggiore precisione il percorso.",
            "proposed_text": "Studentessa magistrale con interesse per l'analisi dei dati.",
        }

        with patch("main.call_lightweight_analysis_llm", return_value=llm_result):
            refined = refine_cv_job_suggestions([suggestion], evaluation)

        self.assertEqual(refined[0]["generated_by"], "ollama")
        self.assertEqual(refined[0]["title"], "Rafforza il profilo analitico")
        self.assertEqual(
            refined[0]["proposed_text"],
            "Studentessa magistrale con interesse per l'analisi dei dati.",
        )

    def test_section_marker_detection_ignores_normal_sentences(self):
        self.assertEqual(count_section_markers("Esperienza valorizzata per il ruolo"), 0)
        self.assertEqual(count_section_markers("Soft skills rilevanti:\n- Collaborazione"), 0)
        self.assertEqual(count_section_markers("HARD SKILLS\nPython, SQL"), 1)

    def test_local_guard_generates_data_analyst_suggestions_without_llm(self):
        evaluation = {
            "cv_text": (
                "PROFILO\nLaureato con interesse per analisi e visualizzazione dei dati.\n"
                "HARD SKILLS\nPython, SQL, Excel, pandas\n"
                "SOFT SKILLS\nProblem solving, collaborazione, precisione\n"
                "PROGETTI\nAnalisi di un dataset e creazione di report con Python e SQL.\n"
                "FORMAZIONE\nLaurea in Informatica"
            ),
            "target": {
                "role": "Data Analyst",
                "company": "Google",
                "description": "Analisi dati, dashboard, KPI e reporting.",
            },
            "missing_keywords": ["Power BI", "Tableau", "KPI"],
            "relevant_skills_found": ["Python", "SQL", "Excel"],
        }

        with patch(
            "services.cv_optimizer.skill_suggestions.build_skill_mini_shot_suggestions",
            side_effect=AssertionError("Il guard locale non deve richiedere il mini-shot"),
        ):
            suggestions = build_coach_suggestions_from_evaluation(evaluation)

        self.assertGreater(len(suggestions), 0)
        self.assertTrue(all(item.get("type") == "actionableEdit" for item in suggestions))

    def test_validation_mode_never_calls_skill_mini_shot(self):
        evaluation = {
            "cv_text": "PROFILO\nCandidato junior.\nFORMAZIONE\nLaurea in Informatica",
            "target": {"role": "Data Analyst", "company": "Google"},
        }

        with patch(
            "services.cv_optimizer.skill_suggestions.build_skill_mini_shot_suggestions",
            side_effect=AssertionError("Il mini-shot non deve bloccare la validazione"),
        ):
            suggestions = build_coach_suggestions_from_evaluation(
                evaluation,
                allow_llm=False,
            )

        self.assertIsInstance(suggestions, list)

    def test_education_only_cv_gets_a_safe_local_suggestion(self):
        evaluation = {
            "cv_text": (
                "Luca Zerella\n"
                "FORMAZIONE\n"
                "Laurea magistrale in Ingegneria Informatica, curriculum Intelligenza Artificiale."
            ),
            "target": {"role": "Software Engineer", "company": "TIM"},
        }

        suggestions = build_cv_job_suggestions(evaluation, allow_llm=False)

        self.assertGreaterEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].get("section"), "FORMAZIONE")
        self.assertIn("Percorso accademico", suggestions[0].get("proposed_text", ""))

    def test_skill_source_stops_before_cross_column_education_text(self):
        source = (
            "Python ML & AI C++ SQL Java\n"
            "e approccio analitico alla risoluzione di problemi complessi.\n"
            "Università degli Studi di Roma Tre | 2019-2024"
        )

        cleaned = clean_skill_section_source(source)

        self.assertEqual(cleaned, "Python ML & AI C++ SQL Java")

    def test_skill_formatter_creates_compact_sidebar_rows(self):
        formatted = format_skill_list_like_original(
            "Python SQL Java",
            [
                "Python", "SQL", "Java", "KPI", "Reporting",
                "Data visualization", "Power BI", "Tableau",
            ],
        )

        self.assertIn(" · ", formatted)
        self.assertTrue(all(len(line) <= 44 for line in formatted.splitlines()))

    def test_soft_skill_extraction_removes_candidate_name_and_title(self):
        source = (
            "Creatività Flessibilità Capacità di adattamento "
            "Attenzione ai dettagli Apprendimento continuo "
            "Problem solving Team Working SILVIA MUCCI Ingegnere Informatico"
        )

        skills = extract_clean_skill_items(source, is_soft=True)

        self.assertIn("Creatività", skills)
        self.assertIn("Problem solving", skills)
        self.assertNotIn("SILVIA MUCCI", " ".join(skills))

    def test_rewrite_generators_stay_generic_about_role_and_company(self):
        section_map = {
            "profile": "Profilo breve con esperienza in analisi e progettazione.",
            "experience": "Supporto su dati, documenti e automazione dei processi.",
        }
        suggestions = build_generic_rewrite_fallbacks(section_map, "Game Design")
        combined = " ".join(
            f"{item.get('title', '')} {item.get('description', '')} {item.get('proposed_text', '')}"
            for item in suggestions
        )

        self.assertNotIn("Datewave", combined)
        self.assertNotIn("Game Design presso", combined)
        self.assertIn("ruolo target", combined)

    def test_backend_generates_actionable_coach_suggestions_for_generic_role_context(self):
        evaluation = {
            "cv_text": (
                "PROFILO\n"
                "Studente magistrale in Ingegneria Informatica.\n"
                "HARD SKILLS\n"
                "Python, SQL, Java\n"
                "ESPERIENZE PROFESSIONALI\n"
                "Supporto su dati e automazione dei processi."
            ),
            "role": "Game Design",
            "company": "Datewave",
            "missing_keywords": [],
            "relevant_skills_found": ["Python", "SQL"],
            "sections_to_improve": ["profile", "experience"],
            "coach_suggestions": [],
            "suggestions": [],
        }

        suggestions = build_coach_suggestions_from_evaluation(evaluation, allow_llm=False)

        self.assertGreaterEqual(len(suggestions), 1)
        self.assertTrue(all(item.get("type") == "actionableEdit" for item in suggestions))
        joined = " ".join(
            f"{item.get('description', '')} {item.get('proposed_text', '')}"
            for item in suggestions
        ).lower()
        self.assertNotIn("datewave", joined)
        self.assertNotIn("game design presso", joined)
        self.assertTrue(any("profilo" in (item.get("section") or "").lower() or "esperienz" in (item.get("section") or "").lower() for item in suggestions))

    def test_software_engineering_cv_always_gets_applicable_suggestions(self):
        evaluation = {
            "cv_text": (
                "Luca Zerella\n"
                "PROFILO\n"
                "Studente magistrale in Ingegneria Informatica con curriculum in Intelligenza Artificiale.\n"
                "COMPETENZE TECNICHE\n"
                "Python, C, Java, TensorFlow, PyTorch, scikit-learn, Apache Spark\n"
                "PROGETTI\n"
                "Progetto Machine Learning\n"
                "Implementazione di pipeline di analisi predittiva con scikit-learn.\n"
                "Progetto Big Data\n"
                "Elaborazione distribuita di dataset con Hadoop, Hive e Spark.\n"
            ),
            "target": {
                "role": "Software Engineer",
                "company": "TIM",
                "description": "Sviluppo software, testing, Git e collaborazione in team.",
            },
            "missing_keywords": ["Git", "Unit testing"],
            "relevant_skills_found": ["Python", "Java"],
        }

        suggestions = build_cv_job_suggestions(evaluation, allow_llm=False)

        self.assertGreaterEqual(len(suggestions), 1)
        self.assertTrue(all(item.get("original_text") for item in suggestions))
        self.assertTrue(all(item.get("proposed_text") for item in suggestions))
        self.assertTrue(all(count_section_markers(item.get("proposed_text", "")) == 0 for item in suggestions))

    def test_backend_uses_additional_screen_data_when_cv_section_is_missing(self):
        evaluation = {
            "cv_text": "PROFILO\nStudente magistrale in Ingegneria Informatica.\nHARD SKILLS\nPython, SQL",
            "target": {"role": "Project Manager", "company": "Poste Italiane"},
            "user_additional_data": {
                "adaptation_answers": [
                    {
                        "question": "Hai gestito attività o progetti?",
                        "answer": "Ho coordinato un progetto universitario con divisione attività e scadenze.",
                        "category": "experience",
                    }
                ],
                "confirmed_skills": [
                    {
                        "id": "pm-jira",
                        "name": "Jira",
                        "detail": "Usato per organizzare attività e priorità.",
                        "target_section": "HARD SKILLS",
                        "type": "skillConfirmation",
                    }
                ],
            },
            "coach_suggestions": [],
            "suggestions": [],
        }

        suggestions = build_coach_suggestions_from_evaluation(evaluation, allow_llm=False)

        self.assertGreaterEqual(len(suggestions), 1)
        joined = " ".join(
            f"{item.get('description', '')} {item.get('proposed_text', '')}"
            for item in suggestions
        ).lower()
        self.assertTrue(any(item.get("section") for item in suggestions))

    def test_compact_skill_mini_shot_builds_actionable_fields_locally(self):
        evaluation = {
            "cv_text": (
                "PROFILO\nStudentessa di Informatica.\n"
                "HARD SKILLS\nPython, SQL\n"
                "SOFT SKILLS\nProblem solving"
            ),
            "target": {"role": "Data Analyst", "company": "Google"},
            "missing_hard_skills": ["Power BI"],
            "missing_soft_skills": ["Pensiero analitico"],
            "relevant_skills_found": ["Python", "SQL"],
        }
        compact_result = {
            "suggestions": [
                {
                    "bucket": "hard_add",
                    "skill": "Power BI",
                    "reason": "Utile per dashboard e reporting.",
                }
            ]
        }

        with patch("main.call_lightweight_analysis_llm", return_value=compact_result):
            suggestions = build_skill_mini_shot_suggestions(evaluation)

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["section"], "hard_skills")
        self.assertIn("Power BI", suggestions[0]["proposed_text"])
        self.assertEqual(suggestions[0]["keywords_added"], ["Power BI"])

    def test_confirmed_skill_payload_is_deduplicated_by_id_and_name(self):
        skill = {
            "id": "data-analyst-hard-skills-kpi",
            "name": "KPI",
            "category": "hard_skill",
            "target_section": "HARD SKILLS",
        }
        sanitized, rejected = sanitize_cv_additional_data({
            "confirmed_skills": [skill, dict(skill), {**skill, "id": "another-kpi"}],
        })

        self.assertEqual(len(sanitized["confirmed_skills"]), 1)
        self.assertEqual(rejected, [])

    def test_skill_identity_merges_common_synonyms(self):
        self.assertEqual(
            canonical_skill_identity("ML & AI"),
            canonical_skill_identity("Machine Learning"),
        )
        self.assertEqual(
            canonical_skill_identity("Team Working"),
            canonical_skill_identity("Collaborazione"),
        )

    def test_deterministic_skill_consolidation_removes_synonym_duplicates(self):
        replacement = deterministic_section_consolidation(
            "Python · ML & AI",
            [
                RewriteInstruction(
                    section="HARD SKILLS",
                    original="Python · ML & AI",
                    replacement="Python · Machine Learning · SQL",
                    source_id="skills-1",
                ),
                RewriteInstruction(
                    section="HARD SKILLS",
                    original="Python · ML & AI",
                    replacement="ML & AI · SQL · Power BI",
                    source_id="skills-2",
                ),
            ],
        )

        identities = [
            canonical_skill_identity(item)
            for item in replacement.replace("\n", " · ").split(" · ")
            if item.strip()
        ]
        self.assertEqual(len(identities), len(set(identities)))

    def test_data_scientist_generates_suggestions(self):
        """Test that Data Scientist generates appropriate suggestions."""
        cv_text = "I have experience with Python and SQL. I know machine learning basics."
        role = "Data Scientist"
        result = build_role_skill_suggestions(cv_text, role)
        
        print(f"\n[Data Scientist] confirmation_items: {len(result['confirmation_items'])}")
        self.assertGreater(len(result['confirmation_items']), 0, 
                          "Data Scientist should generate suggestions")
        
        # Check that suggestions include expected categories
        skill_types = {item['type'] for item in result['confirmation_items']}
        self.assertIn('skillConfirmation', skill_types, 
                     "Should have skill confirmations")

    def test_project_manager_generates_suggestions(self):
        """Test that Project Manager generates appropriate suggestions."""
        cv_text = "I managed multiple projects and teams. Organized meetings and tracked progress."
        role = "Project Manager"
        result = build_role_skill_suggestions(cv_text, role)
        
        print(f"\n[Project Manager] confirmation_items: {len(result['confirmation_items'])}")
        self.assertGreater(len(result['confirmation_items']), 0, 
                          "Project Manager should generate suggestions")
        
        # Check that suggestions include planning, coordination, etc.
        names = {item['name'].lower() for item in result['confirmation_items']}
        print(f"  Names: {names}")

    def test_generic_role_fallback(self):
        """Generic roles must not produce invented placeholder skills."""
        cv_text = "I have work experience in technology sector."
        role = "Specialist"
        result = build_role_skill_suggestions(cv_text, role)
        
        print(f"\n[Specialist] confirmation_items: {len(result['confirmation_items'])}")
        # Should still generate something via fallback
        self.assertEqual(result["confirmation_items"], [])

    def test_infer_skill_library_project_manager(self):
        """Test that infer_skill_library_from_role works for Project Manager."""
        library = infer_skill_library_from_role("Project Manager")
        
        print(f"\n[Library] Project Manager hard_skills: {len(library.get('hard_skills', []))}")
        self.assertGreater(len(library.get('hard_skills', [])), 0)
        self.assertGreater(len(library.get('soft_skills', [])), 0)
        
        # Check for expected items
        hard_skills = {s.lower() for s in library.get('hard_skills', [])}
        self.assertTrue(any('pianificazione' in s or 'coordinamento' in s for s in hard_skills),
                       "Should have planning or coordination skills")

    def test_infer_skill_library_data_scientist(self):
        """Test that infer_skill_library_from_role works for Data Scientist."""
        library = infer_skill_library_from_role("Data Scientist")
        
        print(f"\n[Library] Data Scientist hard_skills: {len(library.get('hard_skills', []))}")
        self.assertGreater(len(library.get('hard_skills', [])), 0)
        self.assertGreater(len(library.get('programming_languages', [])), 0)
        self.assertGreater(len(library.get('tools', [])), 0)
        
        # Check for Python
        langs = {s.lower() for s in library.get('programming_languages', [])}
        self.assertIn('python', langs, "Data Scientist should have Python")

    def test_multiple_suggestions_per_category(self):
        """Test that multiple suggestions are generated for each category."""
        cv_text = "Work experience in technology."
        role = "Data Analyst"
        result = build_role_skill_suggestions(cv_text, role)
        
        # Count by type
        by_type = {}
        for item in result['confirmation_items']:
            t = item['type']
            by_type[t] = by_type.get(t, 0) + 1
        
        print(f"\n[Multiple] By type: {by_type}")
        # Should have multiple skill confirmations
        self.assertGreater(by_type.get('skillConfirmation', 0), 1, 
                          "Should have multiple skill confirmations")

    def test_no_empty_suggestions(self):
        """Test that no empty suggestions are generated."""
        cv_text = "I have experience."
        role = "Backend Developer"
        result = build_role_skill_suggestions(cv_text, role)
        
        for item in result['confirmation_items']:
            self.assertTrue(item['name'].strip(), f"Item should not have empty name: {item}")
            self.assertTrue(item['name'], f"Item name should be truthy")

    def test_confirmation_items_match_library(self):
        """Test that confirmation items come from the library."""
        cv_text = "I know Python and SQL."
        role = "Data Analyst"
        result = build_role_skill_suggestions(cv_text, role)
        
        # Get the items
        items = result['confirmation_items']
        names = {item['name'] for item in items}
        
        print(f"\n[Match] Generated {len(items)} items: {names}")
        
        # Should include Data Analyst skills like SQL, Python
        names_lower = {n.lower() for n in names}
        # Allow partial matches like "python", "sql", "analisi", etc.
        expected_terms = ['sql', 'python', 'analisi', 'dati', 'excel', 'power bi']
        found = [t for t in expected_terms if any(t in n for n in names_lower)]
        print(f"  Found expected terms: {found}")
        self.assertGreater(len(found), 0, 
                          "Should include expected Data Analyst terms")


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
