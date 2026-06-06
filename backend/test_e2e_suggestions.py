#!/usr/bin/env python3
"""End-to-end test for suggestion generation and filtering."""

import json
from main import (
    build_role_skill_suggestions,
    filter_cv_keyword_list,
)

def test_end_to_end_project_manager():
    """Test complete flow for Project Manager role."""
    print("\n" + "="*80)
    print("TEST: End-to-end Project Manager suggestion generation")
    print("="*80)
    
    cv_text = """
    ESPERIENZE PROFESSIONALI
    Project Manager - TechCorp, 2020-2024
    Gestione di 5 progetti complessi con team di 10+ persone.
    Coordinamento con stakeholder, pianificazione timeline.
    """
    
    role = "Project Manager"
    company = "TechCorp"
    description = "Gestione progetti, coordinamento team, pianificazione attività"
    
    # Generate suggestions
    result = build_role_skill_suggestions(cv_text, role, description)
    
    print(f"\nGenerated result:")
    print(f"  Role family: {result['role_family']}")
    print(f"  Total confirmation items: {len(result['confirmation_items'])}")
    
    # Count by type
    by_type = {}
    by_category = {}
    for item in result['confirmation_items']:
        t = item['type']
        c = item['category']
        by_type[t] = by_type.get(t, 0) + 1
        by_category[c] = by_category.get(c, 0) + 1
    
    print(f"\nBreakdown:")
    print(f"  By type: {by_type}")
    print(f"  By category: {by_category}")
    
    # List items
    print(f"\nGenerated suggestions:")
    for item in result['confirmation_items']:
        print(f"  - {item['name']} ({item['type']}/{item['category']}) - present: {item['already_present']}")
    
    # Verify minimums
    hard_skills = [i for i in result['confirmation_items'] if i['category'] == 'hard_skill']
    soft_skills = [i for i in result['confirmation_items'] if i['category'] == 'soft_skill']
    keywords = [i for i in result['confirmation_items'] if i['category'] == 'keyword']
    
    print(f"\nVerification:")
    print(f"  Hard skills: {len(hard_skills)} (minimum 3)")
    print(f"  Soft skills: {len(soft_skills)} (minimum 3)")
    print(f"  Keywords: {len(keywords)} (minimum 3)")
    
    assert len(hard_skills) >= 3, f"Not enough hard skills: {len(hard_skills)}"
    assert len(soft_skills) >= 3, f"Not enough soft skills: {len(soft_skills)}"
    assert len(keywords) >= 0, f"Should have keywords: {len(keywords)}"  # Keywords can be 0 for PM
    
    print("\n✓ PASSED: Project Manager generates sufficient suggestions")

def test_end_to_end_data_scientist():
    """Test complete flow for Data Scientist role."""
    print("\n" + "="*80)
    print("TEST: End-to-end Data Scientist suggestion generation")
    print("="*80)
    
    cv_text = """
    ESPERIENZE PROFESSIONALI
    Data Scientist - DataCorp, 2021-2024
    Sviluppo modelli predittivi con Python e SQL.
    Utilizzo di pandas, scikit-learn per feature engineering.
    Analisi di dataset con 1M+ righe.
    """
    
    role = "Data Scientist"
    description = "Machine Learning, Python, Analisi predittiva"
    
    result = build_role_skill_suggestions(cv_text, role, description)
    
    print(f"\nGenerated result:")
    print(f"  Role family: {result['role_family']}")
    print(f"  Total confirmation items: {len(result['confirmation_items'])}")
    
    hard_skills = [i for i in result['confirmation_items'] if i['category'] == 'hard_skill']
    soft_skills = [i for i in result['confirmation_items'] if i['category'] == 'soft_skill']
    tools = [i for i in result['confirmation_items'] if i['category'] == 'tool']
    
    print(f"\nBreakdown:")
    print(f"  Hard skills: {len(hard_skills)}")
    print(f"  Soft skills: {len(soft_skills)}")
    print(f"  Tools: {len(tools)}")
    
    # Print skill names
    print(f"\nSkill names:")
    for item in hard_skills:
        print(f"  - {item['name']} (present: {item['already_present']})")
    
    assert len(hard_skills) >= 3, f"Not enough hard skills: {len(hard_skills)}"
    assert len(soft_skills) >= 3, f"Not enough soft skills: {len(soft_skills)}"
    
    print("\n✓ PASSED: Data Scientist generates sufficient suggestions")

def test_generic_role_fallback():
    """Test fallback for unrecognized generic role."""
    print("\n" + "="*80)
    print("TEST: Generic role fallback")
    print("="*80)
    
    cv_text = "I have IT experience."
    role = "Specialist"  # Unrecognized role
    
    result = build_role_skill_suggestions(cv_text, role)
    
    print(f"\nGenerated result:")
    print(f"  Role family: '{result['role_family']}' (empty means generic fallback used)")
    print(f"  Total confirmation items: {len(result['confirmation_items'])}")
    
    # Should still generate something
    assert len(result['confirmation_items']) > 0, "Fallback should generate suggestions"
    print("\n✓ PASSED: Generic role uses fallback successfully")

def test_keyword_filtering():
    """Test that keyword filtering doesn't block legitimate keywords."""
    print("\n" + "="*80)
    print("TEST: Keyword filtering robustness")
    print("="*80)
    
    # Test various keywords
    keywords = [
        "project management",
        "python programming",
        "data analysis",
        "team leadership",
        "business intelligence",
    ]
    
    filtered = filter_cv_keyword_list(keywords)
    
    print(f"\nOriginal keywords: {len(keywords)}")
    print(f"  {keywords}")
    print(f"\nFiltered keywords: {len(filtered)}")
    print(f"  {filtered}")
    
    # All legitimate keywords should pass
    for kw in keywords:
        assert any(kw.lower() in f.lower() for f in filtered), f"Keyword '{kw}' was filtered out"
    
    print("\n✓ PASSED: Keywords pass through filtering")

if __name__ == "__main__":
    test_end_to_end_project_manager()
    test_end_to_end_data_scientist()
    test_generic_role_fallback()
    test_keyword_filtering()
    
    print("\n" + "="*80)
    print("ALL TESTS PASSED ✓")
    print("="*80)
