import unittest

from backend.app.llm import format_chat_history


class ChatHistoryTests(unittest.TestCase):
    def test_empty_history_is_explicit(self) -> None:
        self.assertEqual(format_chat_history([]), "No previous conversation.")

    def test_formats_recent_messages_for_prompt_context(self) -> None:
        history = [
            {"role": "user", "content": "Explain AODV."},
            {"role": "assistant", "content": "AODV is a routing protocol."},
        ]

        self.assertEqual(
            format_chat_history(history),
            "User: Explain AODV.\nAssistant: AODV is a routing protocol.",
        )

    def test_limits_history_to_recent_messages(self) -> None:
        history = [
            {"role": "user", "content": f"Question {index}"}
            for index in range(10)
        ]

        formatted = format_chat_history(history)

        self.assertNotIn("Question 0", formatted)
        self.assertNotIn("Question 1", formatted)
        self.assertIn("Question 2", formatted)
        self.assertIn("Question 9", formatted)


if __name__ == "__main__":
    unittest.main()
