import io
import unittest

from docx import Document

from services.cv_optimizer.pipeline import DocxPreserver, ResumeParser, RewriteInstruction


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


if __name__ == "__main__":
    unittest.main()
