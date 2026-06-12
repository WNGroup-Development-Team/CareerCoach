import io
import unittest

from docx import Document
from docx.shared import Pt

from main import build_confirmed_skill_rewrite_instructions
from services.cv_optimizer.structured_cv_engine import build_optimized_cv_text
from services.cv_optimizer.pipeline import (
    DocxPreserver,
    ResumeDocxOptimizationPipeline,
    ResumeParser,
    ResumeRewriter,
    RewriteInstruction,
    StructuredRewriteInstruction,
)


class ResumeParserLayoutTests(unittest.TestCase):
    def test_parse_text_recovers_inline_section_headings(self):
        text = (
            "Mario Rossi CHI SONO Profilo breve orientato ai dati "
            "HARD SKILLS Python SQL Power BI FORMAZIONE Laurea in Informatica "
            "ESPERIENZE PROFESSIONALI Analisi dati in progetto universitario"
        )

        sections = {section.name: section.text for section in ResumeParser().parse_text(text)}

        self.assertIn("profilo", sections)
        self.assertIn("hard_skills", sections)
        self.assertIn("formazione", sections)
        self.assertIn("esperienze", sections)
        self.assertEqual(sections["hard_skills"], "Python SQL Power BI")


class ResumeRewriterTests(unittest.TestCase):
    def test_applies_generated_instructions_to_optimized_text(self):
        original = (
            "PROFILO\n"
            "Analista con esperienza in reportistica.\n\n"
            "COMPETENZE\n"
            "Excel e SQL"
        )

        optimized = ResumeRewriter().apply_to_text(
            original,
            [
                RewriteInstruction(
                    section="profilo",
                    original="Analista con esperienza in reportistica.",
                    replacement="Analista orientato ai dati con esperienza in reportistica.",
                    source_id="generated-profile",
                )
            ],
        )

        self.assertIn(
            "Analista orientato ai dati con esperienza in reportistica.",
            optimized,
        )
        self.assertNotEqual(optimized, original)

    def test_build_optimized_cv_text_applies_accepted_edits(self):
        original = (
            "SILVIA MUCCI\n"
            "CHI SONO\n"
            "Sono una studentessa magistrale in Ingegneria Informatica.\n\n"
            "HARD SKILLS\n"
            "Python SQL Java\n\n"
            "ESPERIENZE PROFESSIONALI\n"
            "Supporto all'analisi legislativa tramite LLM."
        )

        accepted = [
            {
                "id": "profile-1",
                "type": "actionableEdit",
                "section": "CHI SONO",
                "original_text": "Sono una studentessa magistrale in Ingegneria Informatica.",
                "proposed_text": "Sono una studentessa magistrale in Ingegneria Informatica orientata all'analisi dei dati e allo sviluppo di soluzioni digitali.",
            },
            {
                "id": "skills-1",
                "type": "actionableEdit",
                "section": "HARD SKILLS",
                "original_text": "Python SQL Java",
                "proposed_text": "Python, SQL, Java, Machine Learning",
            },
        ]

        optimized = build_optimized_cv_text(
            original,
            accepted,
            user_additional_data={},
            role="Data Analyst",
            company="Google",
            use_llm=False,
        )

        self.assertNotEqual(optimized, original)
        self.assertIn("orientata all'analisi dei dati", optimized)
        self.assertIn("Machine Learning", optimized)


class DocxPreserverLayoutTests(unittest.TestCase):
    def _docx_bytes(self, document: Document) -> bytes:
        output = io.BytesIO()
        document.save(output)
        return output.getvalue()

    def test_profile_rewrite_can_mention_skills_in_a_normal_sentence(self):
        pipeline = ResumeDocxOptimizationPipeline()
        instruction = StructuredRewriteInstruction(
            suggestion_id="profile-data-analyst",
            target_section="profilo",
            action="replace",
            old_text_hint="Studentessa magistrale in Ingegneria Informatica.",
            new_text=(
                "Studentessa magistrale orientata al ruolo di Data Analyst, "
                "con hard skills in Python e SQL e attenzione ai dettagli."
            ),
            items=[],
            reason="Profilo più mirato.",
            confidence=0.8,
        )

        self.assertTrue(pipeline._is_safe_target_text(instruction))

    def test_profile_rewrite_rejects_an_injected_section_heading(self):
        pipeline = ResumeDocxOptimizationPipeline()
        instruction = StructuredRewriteInstruction(
            suggestion_id="profile-injection",
            target_section="profilo",
            action="replace",
            old_text_hint="Profilo originale.",
            new_text="Profilo aggiornato.\nHARD SKILLS\nPython, SQL",
            items=[],
            reason="Test sicurezza.",
            confidence=0.8,
        )

        self.assertFalse(pipeline._is_safe_target_text(instruction))

    def test_structured_pipeline_applies_profile_and_skill_updates_together(self):
        document = Document()
        document.add_paragraph("CHI SONO")
        document.add_paragraph(
            "Sono una studentessa magistrale in Ingegneria Informatica."
        )
        document.add_paragraph("HARD SKILLS")
        document.add_paragraph("Python, SQL, Java")
        document.add_paragraph("SOFT SKILLS")
        document.add_paragraph("Creatività, flessibilità, problem solving")

        instructions = [
            StructuredRewriteInstruction(
                suggestion_id="profile-data-analyst",
                target_section="profilo",
                action="replace",
                old_text_hint="Sono una studentessa magistrale in Ingegneria Informatica.",
                new_text=(
                    "Studentessa magistrale orientata al ruolo di Data Analyst, "
                    "con hard skills in Python e SQL e approccio analitico."
                ),
                items=[],
                reason="Profilo più mirato.",
                confidence=0.8,
            ),
            StructuredRewriteInstruction(
                suggestion_id="confirmed-hard-skills",
                target_section="HARD SKILLS",
                action="replace",
                old_text_hint="Python, SQL, Java",
                new_text="Python, SQL, Java, analisi dei dati",
                items=[],
                reason="Competenze confermate.",
                confidence=0.8,
            ),
            StructuredRewriteInstruction(
                suggestion_id="confirmed-soft-skills",
                target_section="SOFT SKILLS",
                action="replace",
                old_text_hint="Creatività, flessibilità, problem solving",
                new_text="Problem solving, attenzione ai dettagli, flessibilità",
                items=[],
                reason="Soft skill confermate.",
                confidence=0.8,
            ),
        ]

        result = ResumeDocxOptimizationPipeline().apply_instructions_to_docx(
            self._docx_bytes(document),
            instructions,
        )

        self.assertEqual(result.validation_report["status"], "applied")
        self.assertEqual(len(result.applied_ids), 3)
        self.assertIn("Studentessa magistrale orientata", result.validation_report["final_text"])
        self.assertIn("CHI SONO", result.validation_report["final_text"])

    def test_structured_pipeline_copies_direct_run_format_to_inserted_lines(self):
        document = Document()
        document.add_paragraph("ESPERIENZE PROFESSIONALI")
        body = document.add_paragraph("Attività originale.")
        body.runs[0].font.name = "Open Sans"
        body.runs[0].font.size = Pt(10)

        instruction = StructuredRewriteInstruction(
            suggestion_id="formatted-experience",
            target_section="ESPERIENZE PROFESSIONALI",
            action="replace",
            old_text_hint="Attività originale.",
            new_text="Prima attività aggiornata.\nSeconda attività aggiornata.",
            items=[],
            reason="Test formattazione.",
            confidence=0.8,
        )

        result = ResumeDocxOptimizationPipeline().apply_instructions_to_docx(
            self._docx_bytes(document),
            [instruction],
        )
        updated = Document(io.BytesIO(result.file_bytes))
        inserted = next(
            paragraph
            for paragraph in updated.paragraphs
            if paragraph.text == "Seconda attività aggiornata."
        )

        self.assertEqual(inserted.runs[0].font.name, "Open Sans")
        self.assertEqual(inserted.runs[0].font.size.pt, 10)

    def test_structured_pipeline_minimizes_trailing_paragraph_after_table(self):
        document = Document()
        table = document.add_table(rows=1, cols=1)
        table.cell(0, 0).text = "HARD SKILLS"
        table.rows[0].height = Pt(700)
        document.add_paragraph("")

        result = ResumeDocxOptimizationPipeline().apply_instructions_to_docx(
            self._docx_bytes(document),
            [],
        )
        updated = Document(io.BytesIO(result.file_bytes))
        trailing = updated.paragraphs[-1]

        self.assertEqual(trailing.paragraph_format.space_after.pt, 0)
        self.assertEqual(trailing.runs[0].font.size.pt, 1)
        self.assertTrue(trailing.runs[0].font.hidden)
        row_xml = updated.tables[0].rows[0]._tr.xml
        self.assertNotIn("trHeight", row_xml)

    def test_replaces_text_inside_table_section(self):
        document = Document()
        table = document.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "CHI SONO"
        table.cell(0, 1).text = "Profilo originale"
        table.cell(1, 0).text = "HARD SKILLS"
        table.cell(1, 1).text = "Python, SQL"

        updated_bytes, applied = DocxPreserver().apply(
            self._docx_bytes(document),
            [
                RewriteInstruction(
                    section="HARD SKILLS",
                    original="Python, SQL",
                    replacement="Python · SQL · Power BI",
                    category="skills",
                    source_id="test",
                )
            ],
        )

        updated = Document(io.BytesIO(updated_bytes))
        self.assertEqual(applied, 1)
        self.assertEqual(updated.tables[0].cell(1, 1).text, "Python · SQL · Power BI")
        self.assertEqual(updated.tables[0].cell(0, 1).text, "Profilo originale")

    def test_does_not_replace_same_text_from_wrong_table_section(self):
        document = Document()
        table = document.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "CHI SONO"
        table.cell(0, 1).text = "Python, SQL"
        table.cell(1, 0).text = "HARD SKILLS"
        table.cell(1, 1).text = "Python, SQL"

        updated_bytes, applied = DocxPreserver().apply(
            self._docx_bytes(document),
            [
                RewriteInstruction(
                    section="HARD SKILLS",
                    original="Python, SQL",
                    replacement="Python · SQL · Power BI",
                    category="skills",
                    source_id="test",
                )
            ],
        )

        updated = Document(io.BytesIO(updated_bytes))
        self.assertEqual(applied, 1)
        self.assertEqual(updated.tables[0].cell(0, 1).text, "Python, SQL")
        self.assertEqual(updated.tables[0].cell(1, 1).text, "Python · SQL · Power BI")

    def test_table_column_with_own_headings_does_not_inherit_soft_skills(self):
        document = Document()
        table = document.add_table(rows=1, cols=2)
        left = table.cell(0, 0)
        left.text = "SOFT SKILLS"
        left.add_paragraph("Problem solving")
        right = table.cell(0, 1)
        right.text = "SILVIA MUCCI\nIngegnere Informatico"
        right.add_paragraph("CHI SONO")
        right.add_paragraph("Profilo professionale.")

        contexts = ResumeDocxOptimizationPipeline()._paragraph_contexts(document)
        name_context = next(
            context
            for context in contexts
            if "SILVIA MUCCI" in (context.paragraph.text or "")
        )

        self.assertEqual(name_context.section, "intestazione")

    def test_validation_rejects_education_content_inside_hard_skills(self):
        document = Document()
        document.add_paragraph("HARD SKILLS")
        document.add_paragraph("Python · SQL")
        document.add_paragraph("Università degli Studi | 2019-2024 Laurea")

        pipeline = ResumeDocxOptimizationPipeline()
        warnings = pipeline._skill_section_contamination_warnings(
            self._docx_bytes(document)
        )

        self.assertTrue(warnings)

    def test_validation_rejects_narrative_fragments_and_names_inside_skills(self):
        document = Document()
        document.add_paragraph("HARD SKILLS")
        document.add_paragraph("Python · SQL")
        document.add_paragraph("e approccio analitico alla risoluzione di problemi complessi.")
        document.add_paragraph("SOFT SKILLS")
        document.add_paragraph("Problem solving · SILVIA MUCCI Ingegnere Informatico")

        warnings = ResumeDocxOptimizationPipeline()._skill_section_contamination_warnings(
            self._docx_bytes(document)
        )

        self.assertEqual(len(warnings), 2)

    def test_appends_to_existing_section_without_page_break(self):
        document = Document()
        document.add_paragraph("PROGETTI")
        document.add_paragraph("Progetto esistente")

        updated_bytes, applied = DocxPreserver().apply(
            self._docx_bytes(document),
            [
                RewriteInstruction(
                    section="PROGETTI",
                    original="",
                    replacement="Nuovo progetto confermato",
                    category="project",
                    source_id="test-project",
                )
            ],
        )

        updated = Document(io.BytesIO(updated_bytes))
        texts = [paragraph.text for paragraph in updated.paragraphs]
        self.assertEqual(applied, 1)
        self.assertEqual(texts, ["PROGETTI", "Progetto esistente", "Nuovo progetto confermato"])

    def test_appends_inside_existing_table_section(self):
        document = Document()
        table = document.add_table(rows=1, cols=1)
        cell = table.cell(0, 0)
        cell.text = "PROGETTI"
        cell.add_paragraph("Progetto esistente")

        updated_bytes, applied = DocxPreserver().apply(
            self._docx_bytes(document),
            [
                RewriteInstruction(
                    section="PROGETTI",
                    original="",
                    replacement="Nuovo progetto confermato",
                    category="project",
                    source_id="test-table-project",
                )
            ],
        )

        updated = Document(io.BytesIO(updated_bytes))
        texts = [paragraph.text for paragraph in updated.tables[0].cell(0, 0).paragraphs]
        self.assertEqual(applied, 1)
        self.assertEqual(texts, ["PROGETTI", "Progetto esistente", "Nuovo progetto confermato"])

    def test_removes_redundant_profile_paragraph_after_rewrite(self):
        document = Document()
        document.add_paragraph("CHI SONO")
        document.add_paragraph("Profilo originale.")
        document.add_paragraph("Motivata a crescere professionalmente.")
        document.add_paragraph("FORMAZIONE")
        document.add_paragraph("Laurea")

        updated_bytes, applied = DocxPreserver().apply(
            self._docx_bytes(document),
            [
                RewriteInstruction(
                    section="CHI SONO",
                    original="Profilo originale.",
                    replacement="Profilo aggiornato. Motivata a crescere professionalmente.",
                    category="profile",
                    source_id="test-profile",
                )
            ],
        )

        updated = Document(io.BytesIO(updated_bytes))
        texts = [paragraph.text for paragraph in updated.paragraphs]
        self.assertEqual(applied, 1)
        self.assertEqual(texts[1], "Profilo aggiornato. Motivata a crescere professionalmente.")
        self.assertEqual(texts[2], "")
        self.assertEqual(texts[3], "FORMAZIONE")

    def test_replaces_original_text_split_across_multiple_paragraphs(self):
        document = Document()
        document.add_paragraph("ESPERIENZE PROFESSIONALI")
        document.add_paragraph("Prima parte dell'esperienza con attività principali.")
        document.add_paragraph("Seconda parte con strumenti e risultati.")
        document.add_paragraph("FORMAZIONE")
        document.add_paragraph("Corso di studio")

        replacement = "Esperienza riscritta in modo completo e professionale."
        updated_bytes, applied = DocxPreserver().apply(
            self._docx_bytes(document),
            [
                RewriteInstruction(
                    section="ESPERIENZE PROFESSIONALI",
                    original=(
                        "Prima parte dell'esperienza con attività principali. "
                        "Seconda parte con strumenti e risultati."
                    ),
                    replacement=replacement,
                    category="experience",
                    source_id="split-experience",
                )
            ],
        )

        updated = Document(io.BytesIO(updated_bytes))
        texts = [paragraph.text for paragraph in updated.paragraphs]
        self.assertEqual(applied, 1)
        self.assertEqual(texts[1], replacement)
        self.assertEqual(texts[2], "")
        self.assertEqual(texts[3], "FORMAZIONE")

    def test_distributes_multiline_section_rewrite_across_existing_paragraphs(self):
        document = Document()
        document.add_paragraph("ESPERIENZE PROFESSIONALI")
        first = document.add_paragraph("Attività iniziale.")
        first.runs[0].font.name = "Open Sans"
        second = document.add_paragraph("Risultato iniziale.")
        second.runs[0].font.name = "Open Sans"
        document.add_paragraph("FORMAZIONE")

        replacement = "Attività aggiornata.\nRisultato aggiornato.\nStrumento confermato."
        updated_bytes, applied = DocxPreserver().apply(
            self._docx_bytes(document),
            [
                RewriteInstruction(
                    section="ESPERIENZE PROFESSIONALI",
                    original="Attività iniziale. Risultato iniziale.",
                    replacement=replacement,
                    category="experience",
                    source_id="multiline-experience",
                )
            ],
        )

        updated = Document(io.BytesIO(updated_bytes))
        texts = [paragraph.text for paragraph in updated.paragraphs]
        self.assertEqual(applied, 1)
        self.assertEqual(
            texts,
            [
                "ESPERIENZE PROFESSIONALI",
                "Attività aggiornata.",
                "Risultato aggiornato.",
                "Strumento confermato.",
                "FORMAZIONE",
            ],
        )
        self.assertEqual(updated.paragraphs[3].runs[0].font.name, "Open Sans")

    def test_appends_accepted_change_when_target_section_has_no_editable_body(self):
        document = Document()
        document.add_paragraph("PROGETTI")

        updated_bytes, applied = DocxPreserver().apply(
            self._docx_bytes(document),
            [
                RewriteInstruction(
                    section="PROGETTI",
                    original="Testo non più individuabile",
                    replacement="Progetto confermato dall'utente.",
                    category="project",
                    source_id="missing-original",
                )
            ],
        )

        updated = Document(io.BytesIO(updated_bytes))
        texts = [paragraph.text for paragraph in updated.paragraphs if paragraph.text]
        self.assertEqual(applied, 1)
        self.assertEqual(texts, ["PROGETTI", "Progetto confermato dall'utente."])

    def test_appends_new_skill_section_without_new_page(self):
        document = Document()
        document.add_paragraph("FORMAZIONE")
        document.add_paragraph("Laurea in Economia")

        updated_bytes, applied = DocxPreserver().apply(
            self._docx_bytes(document),
            [
                RewriteInstruction(
                    section="COMPETENZE",
                    original="",
                    replacement="Python",
                    category="skills",
                    source_id="skill-end",
                )
            ],
        )

        updated = Document(io.BytesIO(updated_bytes))
        texts = [paragraph.text for paragraph in updated.paragraphs if paragraph.text]
        self.assertEqual(applied, 1)
        self.assertEqual(texts[-2:], ["COMPETENZE", "Python"])

    def test_skips_role_like_confirmed_skill(self):
        instructions = build_confirmed_skill_rewrite_instructions(
            "PROFILO\nCandidato interessato a Project Manager (stage)",
            {"confirmed_skills": [{"name": "Project Manager (stage)", "category": "keyword"}]},
            "Project Manager (stage)"
        )
        self.assertEqual(instructions, [])

    def test_reuses_new_section_for_multiple_additions(self):
        document = Document()
        document.add_paragraph("FORMAZIONE")
        document.add_paragraph("Laurea")

        updated_bytes, applied = DocxPreserver().apply(
            self._docx_bytes(document),
            [
                RewriteInstruction(
                    section="PROGETTI",
                    original="",
                    replacement="Primo progetto",
                    category="project",
                    source_id="first-project",
                ),
                RewriteInstruction(
                    section="PROGETTI",
                    original="",
                    replacement="Secondo progetto",
                    category="project",
                    source_id="second-project",
                ),
            ],
        )

        updated = Document(io.BytesIO(updated_bytes))
        texts = [paragraph.text for paragraph in updated.paragraphs if paragraph.text]
        self.assertEqual(applied, 2)
        self.assertEqual(texts.count("PROGETTI"), 1)
        self.assertEqual(texts[-2:], ["Primo progetto", "Secondo progetto"])

    def test_new_page_section_copies_direct_font_formatting(self):
        document = Document()
        heading = document.add_paragraph("FORMAZIONE")
        heading.runs[0].font.name = "Montserrat"
        heading.runs[0].font.bold = True
        body = document.add_paragraph("Laurea")
        body.runs[0].font.name = "Open Sans"

        updated_bytes, applied = DocxPreserver().apply(
            self._docx_bytes(document),
            [
                RewriteInstruction(
                    section="PROGETTI",
                    original="",
                    replacement="Progetto confermato",
                    category="project",
                    source_id="formatted-project",
                )
            ],
        )

        updated = Document(io.BytesIO(updated_bytes))
        project_heading = next(paragraph for paragraph in updated.paragraphs if paragraph.text == "PROGETTI")
        project_body = next(paragraph for paragraph in updated.paragraphs if paragraph.text == "Progetto confermato")
        self.assertEqual(applied, 1)
        self.assertEqual(project_heading.runs[0].font.name, "Montserrat")
        self.assertTrue(project_heading.runs[0].font.bold)
        self.assertEqual(project_body.runs[0].font.name, "Open Sans")


if __name__ == "__main__":
    unittest.main()
