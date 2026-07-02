import unittest
from unittest.mock import MagicMock, patch

from backend.app.llm import (
    MIND_MAP_MAX_CHILDREN,
    MIND_MAP_MAX_DEPTH,
    MIND_MAP_MAX_NODES,
    extract_json_object,
    generate_mind_map,
    normalize_mind_map_tree,
)


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, str]:
        return {"response": self.content}


def make_large_tree(depth: int) -> dict[str, object]:
    return {
        "title": f"Level {depth}",
        "detail": "A useful detail",
        "children": [make_large_tree(depth + 1) for _ in range(7)]
        if depth < 6
        else [],
    }


def tree_depth(node: dict[str, object]) -> int:
    children = node["children"]
    if not isinstance(children, list) or not children:
        return 1
    return 1 + max(tree_depth(child) for child in children)


class MindMapGenerationTests(unittest.TestCase):
    def test_extracts_json_object_from_code_fence(self) -> None:
        data = extract_json_object(
            '```json\n{"title":"Networks","detail":"","children":[]}\n```'
        )
        self.assertEqual(data["title"], "Networks")

    def test_normalizes_and_counts_a_valid_tree(self) -> None:
        tree, node_count = normalize_mind_map_tree(
            {
                "title": "Security Models",
                "detail": "Main topic",
                "children": [
                    {"title": "BLP", "detail": "Confidentiality", "children": []},
                    {"title": "Biba", "detail": "Integrity", "children": []},
                ],
            }
        )

        self.assertEqual(tree["title"], "Security Models")
        self.assertEqual(node_count, 3)

    def test_enforces_tree_size_limits(self) -> None:
        tree, node_count = normalize_mind_map_tree(make_large_tree(1))

        self.assertLessEqual(node_count, MIND_MAP_MAX_NODES)
        self.assertLessEqual(tree_depth(tree), MIND_MAP_MAX_DEPTH)
        self.assertLessEqual(len(tree["children"]), MIND_MAP_MAX_CHILDREN)

    def test_rejects_nodes_without_titles(self) -> None:
        with self.assertRaises(ValueError):
            normalize_mind_map_tree({"detail": "Missing title", "children": []})

    @patch("backend.app.llm.httpx.post")
    def test_generates_and_validates_model_output(self, mock_post: MagicMock) -> None:
        mock_post.return_value = FakeResponse(
            '{"title":"AODV","detail":"Routing protocol",'
            '"children":[{"title":"Discovery","detail":"On demand","children":[]}]}'
        )

        tree, node_count = generate_mind_map("AODV discovers routes on demand.")

        self.assertEqual(tree["title"], "AODV")
        self.assertEqual(node_count, 2)
        self.assertEqual(mock_post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
