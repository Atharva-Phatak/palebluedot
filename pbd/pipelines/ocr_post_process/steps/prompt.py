def get_segmentation_prompt(md_chunk: str) -> str:
    return f"""You are a Markdown segmenter and classifier for physics textbooks.

Your task is to split the given Markdown content into **logical content blocks**, and label each block with its **type**.

Return a list of JSON objects, where each object has:
- `"type"`: one of ["heading", "definition", "derivation", "example", "problem", "solution", "theory", "note", "caption", "other"]
- `"content"`: the full Markdown content for that block

---

### 💡 GUIDELINES FOR SEGMENTATION AND LABELING:

1. **Preserve continuation logic**:
   - If a block continues a solution, derivation, or example from the previous section **without a new heading**, treat it as part of that block’s continuation.

2. **What counts as a `solution`**:
   - A solution is any step-by-step worked answer to a problem, exercise, or example.
   - Clues: equations with substitutions, phrases like “Given”, “Therefore”, “So”, “Putting values”, “We get”, boxed answers, and final numeric values with units.
   - Solutions often directly follow problems or examples.

3. **What counts as a `derivation`**:
   - A formal, general mathematical development of a formula or law.
   - Often includes symbolic calculus, without being tied to a specific numeric problem.
   - May contain math, figures, and graph interpretations.

4. **What counts as `theory`**:
   - Conceptual or descriptive explanations of physics principles, often accompanied by a few math equations or graphs.
   - Does not solve a specific problem, and does not derive a new formula.
   - Use this when content is too broad or verbal to be a `derivation`.

5. **Headings**:
   - Use `"heading"` **only** for standalone section titles or chapter headings like `## Moment of Inertia`.
   - It must be short (1–2 lines), must **not contain LaTeX equations**, and must not be followed by a long explanation.
   - If the block contains multiple paragraphs or math, classify it as `"derivation"` or `"theory"` instead.

6. **Other block types**:
   - `"definition"`: Short boxed/inlined definitions of key terms (e.g. "Momentum is defined as...").
   - `"example"`: A labeled example like `Example 11.4`, usually with an associated `"solution"`.
   - `"exercise"`: A question to be solved by the student, often without a solution.
   - `"note"`: Side notes, clarifications, conceptual remarks.
   - `"caption"`: Descriptions of images, graphs, or tables.
   - `"other"`: Anything that doesn't fit into the above types.

---

Only return **valid JSON** — no explanations, no markdown formatting.

Markdown content:
{md_chunk}
"""
