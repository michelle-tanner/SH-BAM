from pathlib import Path
from query_system.parser import parse_document

docs = Path("query_system/docs")
for f in sorted(docs.iterdir()):
    try:
        text = parse_document(f)
        print(f"{f.name}: {len(text)} chars, {len(text.split())} words")
        if text.strip():
            print(f"  preview: {text[:150].strip()!r}")
    except Exception as e:
        print(f"{f.name}: ERROR - {e}")
