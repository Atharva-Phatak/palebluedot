import re
import logging
from sympy.parsing.latex import parse_latex
from bs4 import BeautifulSoup
logging.basicConfig(level=logging.WARNING)


def clean_latex_expr(expr: str) -> str:
    expr = expr.strip()

    # OCR artifact corrections
    expr = expr.replace(r'\pik', r'\pi k')
    expr = expr.replace(r'\pim', r'\pi m')
    expr = expr.replace(r'\cdotd', r'\cdot d')

    # Fix \frac{}{} structure if broken (e.g., \frac{\frac{p}{dt}}{} → \frac{p}{dt})
    expr = re.sub(r'\\frac\s*\{\\frac\{([^}]+)\}\{([^}]+)\}\}\{\}', r'\\frac{\1}{\2}', expr)

    # Normalize LaTeX formatting
    expr = re.sub(r'\\mathrm\{~?d\}', 'd', expr)
    expr = re.sub(r'\\mathrm\{([a-zA-Z0-9]+)\}', r'\1', expr)
    expr = re.sub(r'\\left|\\right|\\,|\\quad|\\!', '', expr)
    expr = re.sub(r'\\text\s*\{([^}]+)\}', r'\1', expr)
    expr = re.sub(r'\\dot\s*\{([^}]+)\}', r'\1', expr)

    # Remove excess spacing
    expr = re.sub(r'([a-zA-Z0-9])\s+([a-zA-Z0-9])', r'\1\2', expr)

    # Fix unbalanced \frac terms: \frac{a}{b}c → \frac{a}{b} c
    expr = re.sub(r'(\\frac\{[^}]+\}\{[^}]+\})([a-zA-Z])', r'\1 \2', expr)

    # Remove trailing punctuation
    expr = re.sub(r'\}\s*[\.,;:]+(?=\s*\})', '}', expr)
    expr = expr.rstrip('.;, ')

    return expr.strip()


def verify_latex(latex_code: str) -> str:
    latex_code = latex_code.strip()
    latex_code = re.sub(r"^\${1,2}", "", latex_code)
    latex_code = re.sub(r"\${1,2}$", "", latex_code).strip()

    # Handle environments like aligned, array, gather etc.
    env_match = re.search(r"\\begin\{(\w+)\}(.+?)\\end\{\1\}", latex_code, flags=re.DOTALL)
    if env_match:
        environment = env_match.group(1)
        inner = env_match.group(2).strip()
        rows = re.split(r'\\\\', inner)
        output = [f"<!-- LaTeX block: {environment} -->"]

        for row in rows:
            row = row.strip()
            if not row:
                continue

            # Remove leading '&=', '=' etc.
            row = re.sub(r'^&?=+', '', row).strip()

            # Split by & or = signs to validate RHS/LHS separately
            expressions = [e.strip() for e in re.split(r"&|=", row) if e.strip()]
            verified = []

            for expr in expressions:
                cleaned = clean_latex_expr(expr)
                try:
                    parse_latex(cleaned)
                    verified.append(cleaned)
                except Exception as e:
                    logging.warning(f"Invalid LaTeX fragment: {cleaned} | Error: {e}")
                    verified.append(cleaned)

            # Join with = to resemble original format
            output.append("$$\n" + " = ".join(verified) + "\n$$")

        return "\n".join(output)

    # Single expression
    cleaned = clean_latex_expr(latex_code)
    try:
        parse_latex(cleaned)
        return f"$$\n{cleaned}\n$$"
    except Exception as e:
        logging.warning(f"Invalid LaTeX: {cleaned} | Error: {e}")
        return f"<!-- Invalid LaTeX -->\n$$\n{cleaned}\n$$"


def clean_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    output = []

    def handle_formula(tag):
        latex_div = tag.find("div")
        if latex_div:
            return verify_latex(latex_div.text.strip())
        return ""

    for tag in soup.body.descendants:
        if tag.name in {"h1", "h2", "h3"}:
            prefix = "#" * int(tag.name[1])
            output.append(f"{prefix} {tag.text.strip()}")
        elif tag.name == "p":
            text = tag.text.strip()
            if text:
                output.append(text)
        elif tag.name == "div" and tag.get("class") == ["formula"]:
            formula = handle_formula(tag)
            if formula:
                output.append(formula)
        elif tag.name == "div" and tag.get("class") == ["image"]:
            output.append("![Image Placeholder]")

    return "\n\n".join(output)
