def generate_post_processing_prompt(input_problem: str):
    return f"""You are a specialized extraction system for physics problems with complete solutions.

TASK: Extract fully solved physics problems from the provided content.

EXTRACTION CRITERIA:
A valid extraction requires BOTH components:
1. Problem Statement: Clear, complete question or scenario
2. Complete Solution: Multi-step worked solution with mathematical derivations

EXCLUSIONS:
- Problems with only final answers or brief explanations
- Multiple choice, true/false, or fill-in-the-blank questions
- Incomplete solutions or solution fragments
- Problems requiring you to fill in missing steps

OUTPUT FORMAT:
For each valid problem-solution pair found:

**Problem Statement:**
[Exact copy of original problem text, preserving all formatting and LaTeX]

**Solution Steps:**
Step 1: [Clear description of this step's purpose]
Equation: $$ [Original LaTeX equation] $$
SymPy: [Valid SymPy Python code for this equation]

Step 2: [Description of next step]
Equation: $$ [Next equation] $$
SymPy: [Corresponding SymPy code]

[Continue for all solution steps...]

**Final Answer:**
$$ [Final result with proper formatting] $$

---

IMPORTANT NOTES:
- Preserve all original LaTeX formatting exactly
- Convert equations to valid SymPy syntax (use proper Python variable names, operators, and functions)
- Maintain logical flow between solution steps
- Include units in final answers when present
- If multiple problems exist, separate each with "---"

If no valid problem-solution pairs are found, respond with:
```
No complete problem-solution pairs found in the provided content.
```

INPUT CONTENT:

{input_problem}
"""
