import io
import unittest
import zipfile

from PIL import Image

from services.cv_image_safety import extract_cv_images, validate_cv_images
import main


class CvImageSafetyTests(unittest.TestCase):
    def _png_bytes(self, width: int, height: int) -> bytes:
        output = io.BytesIO()
        Image.new("RGB", (width, height), color=(32, 64, 128)).save(output, format="PNG")
        return output.getvalue()

    def _large_png_bytes(self, width: int, height: int) -> bytes:
        return self._png_bytes(width, height) + (b"\0" * 2_500)

    def _docx_with_images(self, media_files) -> bytes:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr("word/document.xml", "<document />")
            for name, data in media_files:
                archive.writestr(name, data)
        return output.getvalue()

    def _docx_with_image(self) -> bytes:
        return self._docx_with_images([
            ("word/media/image1.png", self._large_png_bytes(200, 200)),
        ])

    def test_extracts_embedded_docx_images(self):
        images = extract_cv_images("curriculum.docx", self._docx_with_image())

        self.assertEqual(len(images), 1)
        self.assertTrue(images[0]["image_url"]["url"].startswith("data:image/png;base64,"))

    def test_ignores_small_docx_images(self):
        images = extract_cv_images(
            "curriculum.docx",
            self._docx_with_images([
                ("word/media/icon.png", self._png_bytes(48, 48)),
                ("word/media/photo.png", self._large_png_bytes(160, 160)),
            ]),
        )

        self.assertEqual(len(images), 1)
        self.assertIn("photo.png", images[0]["label"])

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

    def test_ignores_implausible_multi_category_visual_output(self):
        normalized = main.normalize_cv_image_result({
            "blocked": True,
            "categories": [
                "animale",
                "armi",
                "contenuto sessuale",
                "droghe",
                "nudita",
                "sangue o ferite",
                "violenza",
            ],
            "summary": "",
        })

        self.assertFalse(normalized["blocked"])
        self.assertEqual(normalized["categories"], [])

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
