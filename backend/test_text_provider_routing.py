import unittest
from unittest.mock import patch

import main


class TextProviderRoutingTests(unittest.TestCase):
    def test_call_groq_ignores_ollama_provider_when_text_ollama_disabled(self):
        with patch.object(main, "LLM_PROVIDER", "ollama"), \
             patch.object(main, "OLLAMA_TEXT_ENABLED", False), \
             patch.object(main, "_call_groq_impl", return_value="groq-result") as groq_impl, \
             patch.object(main, "call_ollama", return_value="ollama-result") as ollama_call:
            result = main.call_groq("test prompt")

        self.assertEqual(result, "groq-result")
        groq_impl.assert_called_once()
        ollama_call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
