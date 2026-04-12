# query_system/docx_writer.py
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

GENERATED_DOCS_DIR = Path("query_system/docs/generated_docs")
GENERATOR_SCRIPT   = Path(__file__).parent.parent / "generate_report.js"
LOGO_PATH          = "/Users/sandrabach/Documents/TIR 2026/SH-BAM/frontend/public/logo2.png"

CREWAI_JUNK = [
    "i now can give a great answer",
    "i need to", "i will ", "let me ",
    "final answer:", "thought:", "action:", "observation:",
]

def _clean_text(text: str) -> str:
    """Remove citations and markdown formatting."""
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\[source:[^\]]+\]', '', text)
    text = re.sub(r'\[[^\]]+\]\(#[^\)]*\)', '', text)
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return text.strip()

def _is_junk(text: str) -> bool:
    """Returns True if line should be discarded."""
    s = text.strip().lower()
    if not s or len(s) <= 2:
        return True
    if any(s.startswith(j) for j in CREWAI_JUNK):
        return True
    # Reference list entries like "[1] report1.pdf"
    if re.match(r'^\[\d+\]\s+\S+', s):
        return True
    # Pure punctuation/numbers
    if re.match(r'^[\W\d]+$', s):
        return True
    return False

def _is_table_row(line: str) -> bool:
    """Detect markdown table rows."""
    return bool(re.match(r'^\s*\|', line))

def _parse_table_row(line: str) -> list[str]:
    """Extract non-empty cells from a markdown table row."""
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    return [_clean_text(c) for c in cells if c.strip() and c.strip() != '---' and not re.match(r'^[-\s]+$', c.strip())]

# Section headings that should NOT cause content to be skipped
WHAT_KW = {"what happened", "what's new", "announcement", "topline"}
WHY_KW  = {"why it matters", "why this matters", "significance"}
# These heading words signal the section ends — skip the heading but keep routing content
END_KW  = {"sources", "references"}

def _parse_markdown_sections(content: str) -> dict:
    result = {
        "title":          "",
        "impact":         "MEDIUM",
        "what_happened":  [],
        "why_it_matters": [],
        "tell_me_more":   [],
        "metadata":       {},
    }

    lines       = content.splitlines()
    title_found = False
    current     = "what_happened"   # default: all content goes to what_happened
    skip_next   = False             # used to skip table separator rows

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            skip_next = False
            continue

        # ── Markdown table rows ────────────────────────────────────────────────
        if _is_table_row(stripped):
            # Skip separator rows (|---|---|)
            if re.match(r'^[\|\s\-:]+$', stripped):
                continue
            cells = _parse_table_row(stripped)
            # Skip header rows that are just column names
            header_words = {"program", "indication", "phase", "milestone", "preclinical"}
            if cells and not all(c.lower() in header_words for c in cells):
                text = " | ".join(c for c in cells if c)
                if text and not _is_junk(text):
                    result[current].append(text)
            continue

        # ── Headings ───────────────────────────────────────────────────────────
        if stripped.startswith("#"):
            heading = _clean_text(stripped.lstrip("#").strip())
            lower   = heading.lower()

            # First H1 → title
            if not title_found and stripped.startswith("# "):
                result["title"] = heading
                title_found = True
                continue

            # Skip "Sources" / "References" headings — stop adding content from them
            if any(k in lower for k in END_KW):
                current = None
                continue

            # Impact in heading
            m = re.search(r'\b(HIGH|MEDIUM|LOW)\b', heading, re.IGNORECASE)
            if m:
                result["impact"] = m.group(1).upper()
                continue

            # Route section based on keywords
            if any(k in lower for k in WHAT_KW):
                current = "what_happened"
            elif any(k in lower for k in WHY_KW):
                current = "why_it_matters"
            else:
                # All other headings (Overview, Safety, Pipeline, etc.)
                # keep current section — just continue accumulating content
                pass
            continue

        # ── Stop processing if we hit sources section ──────────────────────────
        if current is None:
            continue

        # ── Impact line ────────────────────────────────────────────────────────
        m = re.search(r'impact.*?:\s*(HIGH|MEDIUM|LOW)', stripped, re.IGNORECASE)
        if m:
            result["impact"] = m.group(1).upper()
            continue

        # ── Bullet lines ───────────────────────────────────────────────────────
        bullet_match = re.match(r'^\s*[\*\-\+\u2022]\s+(.+)', line)
        if bullet_match:
            text = _clean_text(bullet_match.group(1))
            # Skip if it's just a source filename bullet
            if re.match(r'^report\d*\.(pdf|docx|txt)$', text.lower()):
                continue
            if text and not _is_junk(text):
                result[current].append(text)
            continue

        # ── Plain paragraph lines ──────────────────────────────────────────────
        cleaned = _clean_text(stripped)
        if cleaned and not _is_junk(cleaned):
            result[current].append(cleaned)

    # Fallback — if what_happened empty, promote tell_me_more
    if not result["what_happened"] and result["tell_me_more"]:
        result["what_happened"] = result["tell_me_more"]
        result["tell_me_more"]  = []

    return result


def save_as_docx(
    synthesis_result: dict,
    query: str = "",
    metadata: dict | None = None,
) -> Path:
    GENERATED_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    sections    = _parse_markdown_sections(synthesis_result.get("content", ""))
    timestamp   = datetime.now().strftime("%Y-%m-%d_%H%M")
    safe_query  = re.sub(r"[^\w\s-]", "", query)[:40].strip().replace(" ", "_")
    filename    = f"CI_Report_{safe_query}_{timestamp}.docx"
    output_path = GENERATED_DOCS_DIR / filename

    payload = {
        "title":          sections["title"] or query or "Synthesized Intelligence Report",
        "impact":         sections["impact"],
        "what_happened":  sections["what_happened"],
        "why_it_matters": sections["why_it_matters"],
        "tell_me_more":   sections["tell_me_more"],
        "sources":        synthesis_result.get("sources", []),
        "metadata":       metadata or {},
        "logo_path":      LOGO_PATH,
        "output_path":    str(output_path),
    }

    try:
        proc = subprocess.run(
            ["node", str(GENERATOR_SCRIPT)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        raise RuntimeError("Node.js not found. Install with: brew install node")
    except subprocess.TimeoutExpired:
        raise RuntimeError("docx generation timed out.")

    if proc.returncode != 0:
        raise RuntimeError(f"docx generation failed:\n{proc.stderr}")

    stdout = proc.stdout.strip()
    if not stdout.startswith("OK:"):
        raise RuntimeError(f"Unexpected output:\n{stdout}\n{proc.stderr}")

    return output_path