import io
import unittest
import zipfile

from services.cv_image_safety import extract_cv_images, validate_cv_images


class CvImageSafetyTests(unittest.TestCase):
    def _docx_with_image(self) -> bytes:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr("word/document.xml", "<document />")
            archive.writestr("word/media/image1.png", b"\x89PNG\r\n" + b"x" * 3000)
        return output.getvalue()

    def test_extracts_embedded_docx_images(self):
        images = extract_cv_images("curriculum.docx", self._docx_with_image())

        self.assertEqual(len(images), 1)
        self.assertTrue(images[0]["image_url"]["url"].startswith("data:image/png;base64,"))

    def test_blocks_cv_when_analyzer_detects_animal(self):
        result = validate_cv_images(
            "curriculum.docx",
            self._docx_with_image(),
            lambda _image: {
                "blocked": True,
                "categories": ["animale"],
                "summary": "A dog.",
            },
        )

        self.assertTrue(result["blocked"])
        self.assertEqual(result["blocked_categories"], ["animale"])

    def test_text_cv_does_not_invoke_visual_analyzer(self):
        calls = []
        result = validate_cv_images(
            "curriculum.txt",
            b"Profilo professionale",
            lambda image: calls.append(image),
        )

        self.assertFalse(result["blocked"])
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
