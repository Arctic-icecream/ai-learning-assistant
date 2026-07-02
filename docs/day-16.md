# Day 16 - Interactive Mind Maps

## Goal

Turn a saved document summary into a validated knowledge tree, store it in
PostgreSQL, and render it as an interactive node graph in the browser.

## End-to-End Flow

```text
latest detailed summary, or latest brief summary
  -> local model returns a JSON tree
  -> backend validates and limits the tree
  -> PostgreSQL stores it as JSONB
  -> React converts the tree to nodes and edges
  -> Dagre calculates positions
  -> React Flow renders the interactive canvas
```

Mind-map generation requires an existing summary. This keeps the prompt small
and makes the relationship between source material, summary, and visualization
explicit.

## Tree Contract

Every model-generated node has the same recursive shape:

```json
{
  "title": "Access Control Models",
  "detail": "Models define how subjects may access objects.",
  "children": []
}
```

The model produces semantic relationships only. It does not produce pixel
coordinates, colors, or other presentation details.

## Validation Limits

Model output is untrusted input. The backend parser:

- requires one JSON object
- requires every node to be an object with a non-empty title
- requires `children` to be an array
- limits titles to 80 characters
- limits details to 240 characters
- limits the tree to 4 levels including the root
- limits each node to 5 children
- limits the complete map to 40 nodes

These bounds make rendering predictable even if the model ignores part of the
prompt.

## Database

The new `document_mind_maps` table stores:

- `document_id`: source document
- `summary_id`: exact summary used for generation
- `tree`: validated PostgreSQL `JSONB`
- `model_name`: local model used
- `node_count`: number of stored nodes
- `created_at`: generation time

JSONB stores structured data that PostgreSQL understands, unlike JSON encoded
inside a text column. Reprocessing a document removes its old mind maps before
removing summaries and chunks because those artifacts no longer match the new
text.

## API

```text
GET  /documents/{document_id}/mind-maps
POST /documents/{document_id}/mind-maps/generate
```

Generation prefers the newest `detailed` summary and falls back to the newest
saved summary. If none exists, FastAPI returns HTTP 400 with a message asking
the user to generate a summary first.

## Tree to Graph

A tree node only knows its children. React Flow needs two flat arrays:

```text
nodes: id, label, position
edges: source id, target id
```

`MindMapView.tsx` recursively walks the tree. Its path in the tree becomes a
stable node ID, and every parent-child relationship becomes an edge.

## Dagre Layout

Dagre receives fixed node dimensions and graph direction `LR` (left to right).
It calculates non-overlapping center coordinates. The component converts those
centers to React Flow's top-left positions.

Keeping semantic generation and layout separate means the same saved tree can
later be rendered vertically, exported, or displayed with a different visual
theme without asking the model again.

## Interaction

React Flow provides:

- pan and zoom
- draggable nodes
- fit-to-view controls
- a minimap
- selectable nodes

Selecting a node shows its full detail below the canvas. A version menu switches
between saved mind-map generations.

## Component Folder

`frontend/src/components` contains reusable interface units. The mind-map
canvas belongs there because it receives data and manages graph interaction;
the page remains responsible for HTTP requests and choosing a saved version.

## Tests

`backend/tests/test_mind_map_generation.py` checks fenced JSON extraction,
normalization, node counting, invalid titles, all size limits, and one mocked
local-model generation.

Run all backend tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
```

## Manual Check

1. Start the stack with `start-dev.cmd`.
2. Open a parsed document and generate a summary if it has none.
3. Click the document's `Mind Maps` action.
4. Click `Generate Mind Map`.
5. Pan, zoom, drag nodes, use fit view, and select nodes to inspect details.
6. Generate another version and switch versions with the menu.
7. Refresh the browser and confirm both versions remain available.

PNG export is not part of this version. It can be added later without changing
the saved tree or generation API.
