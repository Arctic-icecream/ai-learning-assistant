import unittest
from unittest.mock import MagicMock, patch

from backend.app.llm import generate_document_summary, group_items


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, str]:
        return {"response": self.content}


class SummaryGenerationTests(unittest.TestCase):
    def test_group_items_preserves_order(self) -> None:
        self.assertEqual(
            group_items(["one", "two", "three", "four", "five"], 2),
            [["one", "two"], ["three", "four"], ["five"]],
        )

    @patch("backend.app.llm.httpx.post")
    def test_short_document_uses_one_model_call(self, mock_post: MagicMock) -> None:
        mock_post.return_value = FakeResponse("# Brief summary")

        content, model_call_count = generate_document_summary(
            ["First chunk", "Second chunk"], "brief"
        )

        self.assertEqual(content, "# Brief summary")
        self.assertEqual(model_call_count, 1)
        self.assertEqual(mock_post.call_count, 1)

    @patch("backend.app.llm.httpx.post")
    def test_long_document_maps_batches_before_final_reduce(
        self, mock_post: MagicMock
    ) -> None:
        mock_post.return_value = FakeResponse("Generated notes")
        chunks = [f"Chunk content {index}" for index in range(13)]

        content, model_call_count = generate_document_summary(chunks, "detailed")

        self.assertEqual(content, "Generated notes")
        self.assertEqual(model_call_count, 4)
        self.assertEqual(mock_post.call_count, 4)

    def test_rejects_invalid_mode(self) -> None:
        with self.assertRaises(ValueError):
            generate_document_summary(["Content"], "medium")


if __name__ == "__main__":
    unittest.main()
