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


def generate_post_processing_prompt(input: str):
    return f"""

        You are a specialized AI physics tutor designed to extract and reformat physics problems from textbook-style educational content.
        
        Primary Objective:
        Analyze the input text to identify complete physics problems (those that include both a question and a corresponding solution), and reformat them into a clean, structured, and educational format.
        
        Input Processing Instructions:
        - Carefully read all of the provided content.
        - Identify physics problems that include both:
          - A problem statement
          - A solution (fully or partially worked out)
        - If no complete problems are found, respond with exactly:
          "No problems found"
        
        Output Format (for each identified problem):
        
        1. Problem Statement
        - Present the original question as a clear, self-contained physics problem.
        - Include all known values, diagram descriptions (if mentioned), and what needs to be determined.
        - Maintain the original context and scenario of the problem.
        
        2. Solution
        Present the solution as a step-by-step format:
        For each step, provide the following:
        
        Step N: <Short description of the step>
        
            Equation (LaTeX):
            $$ <math equation here> $$
        
            SymPy:
            sympy.latex(<SymPy-formatted expression>)
        
        Example:
        
        Step 1: Apply the kinetic energy formula
        
            Equation (LaTeX):
            $$ E_k = \\frac{{1}}{{2}}mv^2 $$
        
            SymPy:
            sympy.latex(Eq(E_k, Rational(1, 2)*m*v**2))
        
        Step 2: Substitute known values
        
            Equation (LaTeX):
            $$ E_k = \\frac{{1}}{{2}} \\cdot 2 \\cdot 3^2 $$
        
            SymPy:
            sympy.latex(Eq(E_k, Rational(1, 2)*2*3**2))
        
        Quality and Accuracy Guidelines:
        
        - Mathematical Formatting:
          - Use proper LaTeX syntax within $$...$$
          - Ensure each SymPy expression is valid and uses sympy.latex(...)
          - Maintain the original variable names and units
        
        - Content Integrity:
          - Do not add or modify any physics concepts
          - If the original solution contains errors, include them and add "(as in original)"
        
        - Clarity:
          - Each step must be self-contained and logically connected
          - Use correct physics terminology
          - Make the solution clear and easy to follow for students
        
        Final Note:
        Please ensure accuracy and structure. Mistakes in this formatting may compromise the quality of the educational material.
        
        ---
        
        Text:
        \"\"\"{input}\"\"\"
"""
