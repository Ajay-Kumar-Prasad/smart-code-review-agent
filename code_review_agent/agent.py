import os
import logging
import re
import google.cloud.logging
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents import SequentialAgent
from google.adk.tools.tool_context import ToolContext

# --- Setup Logging and Environment ---
cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent / ".env")
model_name = os.getenv("MODEL", "gemini-2.5-flash")


# ---------------------------------------------------------------------------
# TOOLS
# ---------------------------------------------------------------------------

def save_code_to_state(tool_context: ToolContext, code: str, language: str = "auto") -> dict:
    """
    Saves the submitted code snippet and language to shared state
    so downstream agents can access it.

    Args:
        tool_context: ADK tool context carrying shared session state.
        code: The raw source code string submitted by the user.
        language: Programming language (e.g. 'python', 'javascript').
                  Defaults to 'auto' for automatic detection.

    Returns:
        dict with status and detected/provided language.
    """
    tool_context.state["CODE"] = code
    tool_context.state["LANGUAGE"] = language
    logging.info(f"[State updated] Code saved. Language hint: {language}")
    return {"status": "success", "language": language}


def run_static_checks(tool_context: ToolContext) -> dict:
    """
    Runs lightweight, deterministic static checks on the saved code:
    - Line count
    - Presence of TODO / FIXME / HACK comments
    - Very long lines (>120 chars)
    - Bare except clauses (Python)
    - console.log left in code (JS/TS)
    - Missing docstrings on top-level Python functions

    Args:
        tool_context: ADK tool context carrying shared session state.

    Returns:
        dict with static analysis findings.
    """
    code: str = tool_context.state.get("CODE", "")
    language: str = tool_context.state.get("LANGUAGE", "auto").lower()
    lines = code.splitlines()

    findings = []
    warnings = []

    # --- Universal checks ---
    line_count = len(lines)
    long_lines = [i + 1 for i, l in enumerate(lines) if len(l) > 120]
    todo_lines = [i + 1 for i, l in enumerate(lines)
                  if re.search(r'\b(TODO|FIXME|HACK|XXX)\b', l, re.IGNORECASE)]

    if long_lines:
        warnings.append(f"Lines exceeding 120 characters: {long_lines[:5]}"
                        + (" (and more...)" if len(long_lines) > 5 else ""))

    if todo_lines:
        findings.append(f"Unresolved TODO/FIXME/HACK comments at lines: {todo_lines}")

    # --- Python-specific checks ---
    if language in ("python", "auto"):
        bare_except = [i + 1 for i, l in enumerate(lines)
                       if re.match(r'\s*except\s*:', l)]
        if bare_except:
            findings.append(f"Bare 'except:' clause (catches all exceptions) at lines: {bare_except}. "
                            "Use 'except SpecificException:' instead.")

        # Check top-level def for missing docstrings
        missing_docs = []
        for i, line in enumerate(lines):
            if re.match(r'^def\s+\w+', line):
                next_lines = lines[i + 1: i + 4]
                has_doc = any('"""' in nl or "'''" in nl for nl in next_lines)
                if not has_doc:
                    missing_docs.append(i + 1)
        if missing_docs:
            findings.append(f"Top-level functions without docstrings at lines: {missing_docs[:5]}")

    # --- JavaScript / TypeScript checks ---
    if language in ("javascript", "typescript", "js", "ts", "auto"):
        console_logs = [i + 1 for i, l in enumerate(lines)
                        if re.search(r'console\.log\(', l)]
        if console_logs:
            findings.append(f"console.log() statements found at lines: {console_logs[:5]} "
                            "(remove before production).")

    result = {
        "line_count": line_count,
        "long_lines": long_lines,
        "static_findings": findings,
        "static_warnings": warnings,
    }
    tool_context.state["STATIC_RESULTS"] = result
    logging.info(f"[Static checks] findings={findings}, warnings={warnings}")
    return result


# ---------------------------------------------------------------------------
# SPECIALIST AGENTS  (mirror: comprehensive_researcher + response_formatter)
# ---------------------------------------------------------------------------

# Agent 1 — Code Analyser (mirrors comprehensive_researcher)
code_analyser = Agent(
    name="code_analyser",
    model=model_name,
    description="Deep-dives into the submitted code to find bugs, "
                "code-smell, security issues, and improvement opportunities.",
    instruction="""
You are a senior software engineer conducting a thorough code review.

You have access to:
1. run_static_checks — call this FIRST to get objective, line-level findings.
2. The raw code is in state key CODE and the language hint in LANGUAGE.

After calling run_static_checks, perform your own LLM-powered analysis covering:

BUGS & LOGIC ERRORS
- Off-by-one errors, null/undefined dereferences, infinite loops,
  incorrect conditionals, wrong operator precedence.

SECURITY VULNERABILITIES
- Hardcoded secrets/credentials, SQL injection risks, insecure use of eval(),
  unvalidated user input, path traversal, etc.

CODE QUALITY & MAINTAINABILITY
- Magic numbers/strings, deeply nested logic, functions that do too much
  (Single Responsibility Principle), poor variable/function naming.

PERFORMANCE
- Unnecessary loops inside loops, repeated expensive calls, missing memoisation,
  large allocations inside hot paths.

BEST PRACTICES
- Missing error handling, missing type hints / JSDoc, dead code, unnecessary
  imports, style inconsistencies.

Produce a structured JSON-like summary with these keys:
  bugs            : list of issues (each: line, severity HIGH/MEDIUM/LOW, description)
  security        : list of issues
  quality         : list of issues
  performance     : list of issues
  best_practices  : list of issues
  quality_score   : integer 0-100 (100 = perfect production-ready code)
  score_rationale : one sentence explaining the score

CODE:
{ CODE }

LANGUAGE:
{ LANGUAGE }
""",
    tools=[run_static_checks],
    output_key="analysis_data",
)

# Agent 2 — Report Writer (mirrors response_formatter)
report_writer = Agent(
    name="report_writer",
    model=model_name,
    description="Turns raw analysis data into a clean, developer-friendly "
                "code review report with actionable recommendations.",
    instruction="""
You are a friendly but precise tech lead writing the final code review report.

Use ANALYSIS_DATA to produce a well-formatted review with these sections:

## 📊 Quality Score
Show the score out of 100 with a one-line rationale.
Add a visual bar:  ████████░░ 80/100

## 🐛 Bugs & Logic Errors
List each finding with: Line reference | Severity badge (🔴 HIGH / 🟡 MEDIUM / 🟢 LOW) | Description | Fix suggestion

## 🔒 Security Issues
Same format. If none, say "✅ No security issues found."

## 🧹 Code Quality & Maintainability
Same format.

## ⚡ Performance
Same format.

## ✅ Best Practices
Same format.

## 💡 Top 3 Recommendations
Number the three highest-impact changes the developer should make first.

## 👍 What's Done Well
End on a positive note — highlight at least one thing the code does correctly.

Be specific, concise, and actionable. Avoid vague advice like "improve readability".

ANALYSIS_DATA:
{ analysis_data }
""",
)

# ---------------------------------------------------------------------------
# WORKFLOW  (mirrors tour_guide_workflow)
# ---------------------------------------------------------------------------

review_workflow = SequentialAgent(
    name="review_workflow",
    description="Runs code analysis then formats the final review report.",
    sub_agents=[
        code_analyser,   # Step 1: deep analysis
        report_writer,   # Step 2: formatted report
    ],
)

# ---------------------------------------------------------------------------
# ROOT AGENT  (mirrors greeter / root_agent)
# ---------------------------------------------------------------------------

root_agent = Agent(
    name="code_review_greeter",
    model=model_name,
    description="Entry point for the Smart Code Review Agent. "
                "Greets the developer and collects their code snippet.",
    instruction="""
You are the Smart Code Review Agent — a senior engineer assistant that reviews
code and gives clear, structured, actionable feedback.

On the first turn:
- Greet the user warmly.
- Ask them to paste the code snippet they want reviewed.
- Ask for the programming language (Python, JavaScript, etc.) — or say they can
  skip it and you will auto-detect.

When the user provides code:
- Call the 'save_code_to_state' tool, passing:
    code     = the full code snippet the user shared
    language = the language they mentioned (or 'auto' if not specified)
- After the tool confirms success, immediately hand off to the
  'review_workflow' sub-agent to run the full analysis.

Do NOT attempt to analyse the code yourself. Your only job is greeting,
collecting, and saving — then delegating.
""",
    tools=[save_code_to_state],
    sub_agents=[review_workflow],
)