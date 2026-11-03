import json
from collections import Counter
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "research" / "remaining_text" / "candidates.json"
d = json.loads(p.read_text(encoding="utf-8"))
print("total", len(d))
print("category", Counter(x["category"] for x in d))
for cat in sorted(set(x["category"] for x in d)):
    sub = [x for x in d if x["category"] == cat]
    print(cat, "classes", Counter(x.get("class", "?") for x in sub).most_common(8))
