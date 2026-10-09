import unittest
from types import SimpleNamespace

from merlin_bot.generation import ContentGenerator
from merlin_bot.prompts import WORKPLACE_ENGLISH_PROMPT


class FakeCompletions:
    def __init__(self) -> None:
        self.messages = []

    def parse(self, **kwargs):
        self.messages = kwargs["messages"]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(parsed=object()))]
        )


class GenerationTests(unittest.TestCase):
    def test_workplace_user_prompt_is_not_empty(self) -> None:
        completions = FakeCompletions()
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        generator = ContentGenerator(client, "deployment")

        generator.generate_workplace_lesson(WORKPLACE_ENGLISH_PROMPT)

        user_message = completions.messages[1]["content"]
        self.assertTrue(user_message)
        self.assertIn("exactly 10 expressions", user_message)
        self.assertNotIn("{today}", user_message)


if __name__ == "__main__":
    unittest.main()
