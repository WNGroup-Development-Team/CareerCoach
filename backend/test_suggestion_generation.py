#!/usr/bin/env python3
"""Test the new suggestion generation with fallback mechanism."""

import sys
import unittest
sys.path.insert(0, '.')

from main import (
    build_role_skill_suggestions,
    infer_skill_library_from_role,
    infer_role_family,
)


class TestSuggestionGeneration(unittest.TestCase):
    """Test suggestion generation with fallback."""

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
        """Test that generic role gets fallback suggestions."""
        cv_text = "I have work experience in technology sector."
        role = "Specialist"
        result = build_role_skill_suggestions(cv_text, role)
        
        print(f"\n[Specialist] confirmation_items: {len(result['confirmation_items'])}")
        # Should still generate something via fallback
        self.assertGreater(len(result['confirmation_items']), 0, 
                          "Generic role should generate fallback suggestions")

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
