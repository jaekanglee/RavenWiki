# Graph Positions Policy

## BLUF
`.graph_positions.json` is a **user/machine-local graph layout sidecar**, not canonical knowledge. Raven may read and write it to preserve manual graph drag positions, but it is **not source-of-truth content** and should be treated as optional local state.

## Rules

1. **Purpose**
   - Stores manual graph node positions after drag in Dashboard graph views.
   - Lets future graph loads reuse the user's preferred layout instead of recomputing everything from forceatlas.

2. **Location**
   - Saved at vault root as:
     - `<vault>/.graph_positions.json`

3. **What it is not**
   - Not a page/content file
   - Not durable semantic knowledge
   - Not a cross-user collaboration artifact
   - Not a replacement for graph layout defaults

4. **Operational stance**
   - Missing file: OK
   - Corrupt file: ignore/fallback to computed layout
   - Partial entries: ignore invalid rows, keep valid ones
   - All-vault graph: persist fan-out is done per vault, not into a global merged sidecar

5. **Git policy**
   - This file is typically **machine/user-specific local state**.
   - Whether to gitignore it is a repo policy decision, not an automatic assumption inside graph code.
   - Current graph implementation should therefore behave correctly whether the file is tracked or ignored.

6. **Design constraint**
   - Graph UX should remain good even without this file.
   - `.graph_positions.json` is an override/cache-like convenience layer, not a correctness dependency.

## Related code
- `raven/core/graph.py`
- `raven/api/server.py`
- `tests/test_graph_positions.py`
- `dashboard/src/routes/GraphPage.tsx`
