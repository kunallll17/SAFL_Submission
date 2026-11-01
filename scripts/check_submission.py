"""Check the contest's section, prose and result-bullet requirements."""
import re
from pathlib import Path

text = (Path(__file__).resolve().parents[1] / "docs/SUBMISSION_DRAFT.md").read_text(encoding="utf-8")
expected = {"summary", "website", "assumption", "problem", "approach", "threat", "evaluation", "limitations", "reflection"}
present = set(re.findall(r"<!-- words:(\w+):", text))
sections = re.findall(r"^## (\d+)\. ", text, flags=re.M)
failed = present != expected or sections != [str(i) for i in range(1, 11)]
print(f"Required sections and prose blocks: {'MISSING' if failed else 'OK'}")
for name, lower, upper, content in re.findall(r"<!-- words:(\w+):(\d+):(\d+) -->(.*?)<!-- end:\1 -->", text, flags=re.S):
    count = len(content.split())
    valid = int(lower) <= count <= int(upper)
    print(f"{name}: {count} words (required {lower}-{upper}): {'OK' if valid else 'OUT OF RANGE'}")
    failed |= not valid
results = re.search(r"### Key results\n(.*?)(?=\n### |\Z)", text, flags=re.S)
bullet_count = len(re.findall(r"^- ", results.group(1), flags=re.M)) if results else 0
valid_results = 2 <= bullet_count <= 4
print(f"Key results: {bullet_count} bullets (required 2-4): {'OK' if valid_results else 'OUT OF RANGE'}")
raise SystemExit(1 if failed or not valid_results else 0)
