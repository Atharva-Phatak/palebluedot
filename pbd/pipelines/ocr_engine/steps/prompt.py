def get_nanonets_ocr_prompt():
    ocr_prompt = (
        "<|im_start|>system\n"
        "Extract the text from the above document as if you were reading it naturally. Return the tables in html format. Return the equations in LaTeX representation. If there is an image in the document and image caption is not present, add a small description of the image inside the <img></img> tag; otherwise, add the image caption inside <img></img>. Watermarks should be wrapped in brackets. Ex: <watermark>OFFICIAL COPY</watermark>. Page numbers should be wrapped in brackets. Ex: <page_number>14</page_number> or <page_number>9/22</page_number>. Prefer using ☐ and ☑ for check boxes.\n\n"
        "EXTRACTION GUIDELINES:\n"
        "1. Mathematical content:\n"
        "   - Preserve all equations exactly as written, maintaining proper notation\n"
        "   - Use LaTeX formatting: \\frac{a}{b}, \\int_{a}^{b}, \\sum_{i=1}^{n}, \\sqrt{x}, x^{2}, H_{2}O\n"
        "   - Common physics notation: \\vec{F}, \\hat{n}, \\nabla, \\partial, \\Delta, \\omega, \\theta, \\phi\n"
        "   - Units: maintain proper spacing (5 m/s, not 5m/s) and formatting (kg⋅m/s²)\n"
        "   - Matrix/vector notation: use \\begin{bmatrix}...\\end{bmatrix} or \\begin{pmatrix}...\\end{pmatrix}\n\n"
        "2. Textual content:\n"
        "   - Maintain paragraph structure and indentation\n"
        "   - Preserve exact problem numbering (1.2, Problem 3, Exercise 4.5, etc.)\n"
        "   - Include ALL text: footnotes, margin notes, captions, annotations\n"
        "   - Preserve formatting: **bold**, *italics*, underlined text\n"
        "   - Keep definition boxes, highlighted concepts, and key terms\n\n"
        "3. Visual elements:\n"
        "   - Describe diagrams: [DIAGRAM: Force diagram showing mass m on inclined plane at angle θ]\n"
        "   - Include ALL labels, measurements, arrows, and annotations from figures\n"
        "   - Note coordinate systems (x-y axes, polar coordinates, etc.)\n"
        "   - Describe graphs with axis labels, scales, and data points\n"
        "   - Include circuit diagrams with component values and connections\n\n"
        "4. Problem extraction (CRITICAL):\n"
        "   - Extract complete problem statements with ALL given information\n"
        '   - Include problem numbers/labels exactly as shown (e.g., "Problem 2.3", "Exercise 4-7", "Q15")\n'
        "   - Include ALL numerical values, units, and given conditions\n"
        "   - Extract complete solution steps if provided:\n"
        "     * Given/Find/Solution format when present\n"
        "     * Step-by-step mathematical work\n"
        "     * Intermediate calculations and substitutions\n"
        "     * Final answers with proper units and significant figures\n"
        "   - Include answer keys, hints, or solution references\n"
        "   - Preserve worked example formatting and organization\n"
        "   - Note any accompanying diagrams or figures for each problem\n\n"
        "5. Page structure:\n"
        "   - Follow reading order (left-to-right, top-to-bottom for multi-column)\n"
        "   - Include headers, footers, page numbers, chapter/section titles\n"
        "   - Preserve hierarchical structure (# ## ### for headings)\n"
        "   - Note any special formatting (boxes, sidebars, examples)\n\n"
        "CRITICAL REQUIREMENTS:\n"
        "- Extract EVERYTHING visible - no content should be omitted\n"
        "- For problems: capture complete context including setup, given data, and questions asked\n"
        "- If text is partially obscured or unclear, indicate with [UNCLEAR: best guess]\n"
        "- For handwritten notes, transcribe as accurately as possible\n"
        "- Maintain the exact sequence and organization of content\n"
        "- Double-check all mathematical expressions and numerical values for accuracy\n"
        "- Preserve the logical flow from problem statement → solution → answer\n\n"
        "Begin extraction now, ensuring no content is missed."
        "<|im_end|>\n"
        "<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|><|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    return ocr_prompt


def generate_post_processing_prompt(input: str):
    return f"""
        You are a text extraction and formatting tool. Your ONLY job is to find existing solved problems and reformat them.

        STRICT RULES:
        1. NEVER solve any problems yourself
        2. NEVER add solution steps that aren't already in the text
        3. NEVER perform calculations or work out answers
        4. ONLY reformat text that already contains both a problem AND its complete solution
        5. If you see a problem without a solution, IGNORE it completely

        Task: Find text sections that contain BOTH a physics problem statement AND its already-worked solution, then reformat them.

        What to look for:
        - Problem statement (question asking for something)
        - Complete worked solution (showing steps and final answer)
        - Both must already exist in the input text

        What to SKIP entirely:
        - Multiple choice questions (MCQ) - even if they have answer keys
        - True/False questions
        - Fill-in-the-blank questions
        - Questions with only final answers but no worked solutions
        - Any question format that doesn't show step-by-step mathematical work

        If no such complete problem+solution pairs exist, respond with exactly: "No problems found"

        Reformatting Instructions (ONLY for problems that already have solutions):

        Extract and reformat in this structure:

        **Problem Statement:**
        [Copy the original question exactly as written]

        **Solution Steps:**
        [For each step that already exists in the original solution:]

        Step N: [Describe what this existing step does]
        Equation: $$ [LaTeX format of equation that was already shown] $$
        SymPy: [Convert the existing equation to SymPy format]

        **Final Answer:**
        [Copy the final answer that was already provided, in LaTeX box]

        CRITICAL: You are a copy-and-reformat tool, not a solver.
        If the original text shows:
        - "F = ma = 5 × 2 = 10 N"
        You reformat it as:
        Step 1: Apply Newton's second law with given values
        Equation: $ F = ma = 5 \times 2 = 10 \text N $
        SymPy: Eq(F, m*a).subs([(m, 5), (a, 2)])

        If the original text shows:
        - "Find the force when m=5kg and a=2m/s²" with no solution
        - "What is the acceleration? A) 2 m/s² B) 4 m/s² C) 6 m/s²" (MCQ format)
        - "True or False: Force equals mass times acceleration"
        You IGNORE these completely.

        Remember: Extract and reformat existing solutions only. Never solve anything yourself.

        ---
        Input Text:
        \"\"\"{input}\"\"\"
"""


# Code specific to OCRFlux model : https://github.com/chatdoc-com/OCRFlux/blob/main/ocrflux/prompts.py


def build_qwen2_5_vl_prompt(question: str) -> str:
    """Builds a prompt for the Qwen2.5 VL model."""
    return (
        "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n"
        f"<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>"
        f"{question}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def build_element_merge_detect_prompt(
    text_list_1: list[str], text_list_2: list[str]
) -> str:
    task = """Below are two consecutive pages in Markdown format, where each element of them is numbered. Identify pairs of elements which should be merged across the two pages, such as text paragraphs or tables that span across the two pages. Return pairs as [(element_index_of_page1, element_index_of_page2), ...] or [] if no elements should be merged.\n"""
    task += "Previous page:\n"
    for i, text in enumerate(text_list_1):
        task += f"{i}. {text}\n\n"
    task += "Next page:\n"
    for i, text in enumerate(text_list_2):
        task += f"{i}. {text}\n\n"
    return task


def build_html_table_merge_prompt(table1, table2) -> str:
    return (
        f"Below are two tables in HTML format, merge them into one table in HTML format.\n"
        f"TABLE 1:\n"
        f"{table1}\n"
        f"TABLE 2:\n"
        f"{table2}\n"
    )


def build_page_to_markdown_prompt() -> str:
    return (
        "Below is the image of one page of a document. "
        "Just return the plain text representation of this document as if you were reading it naturally.\n"
        "ALL tables should be presented in HTML format.\n"
        'If there are images or figures in the page, present them as "<Image>(left,top),(right,bottom)</Image>", (left,top,right,bottom) are the coordinates of the top-left and bottom-right corners of the image or figure.\n'
        "Present all titles and headings as H1 headings.\n"
        "Do not hallucinate.\n"
    )
