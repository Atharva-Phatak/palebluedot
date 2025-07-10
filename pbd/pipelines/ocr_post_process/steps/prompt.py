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
