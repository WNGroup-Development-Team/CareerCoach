import io
import unittest

from docx import Document

from services.cv_optimizer.pipeline import (
    DocxPreserver,
    ResumeParser,
    ResumeRewriter,
    RewriteInstruction,
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
        self.assertIn("competenze", sections)
        self.assertIn("formazione", sections)
        self.assertIn("esperienze", sections)
        self.assertEqual(sections["competenze"], "Python SQL Power BI")


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


class DocxPreserverLayoutTests(unittest.TestCase):
    def _docx_bytes(self, document: Document) -> bytes:
        output = io.BytesIO()
        document.save(output)
        return output.getvalue()

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
