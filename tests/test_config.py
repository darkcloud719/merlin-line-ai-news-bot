import os
import unittest
from unittest.mock import patch

from merlin_bot.config import Settings


class SettingsTests(unittest.TestCase):
    def test_reports_all_missing_settings(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "AZURE_OPENAI_API_KEY"):
                Settings.from_environment()


if __name__ == "__main__":
    unittest.main()

