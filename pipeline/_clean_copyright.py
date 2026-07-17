import json, re

with open("data/112.json", encoding="utf-8") as f:
    questions = json.load(f)

# Pattern: copyright header + page number at end of explanation
pat = re.compile(
    r'\n\n甄戰一點通高中影音教材\s+版權所有©\s+'
    r'[\uf358\uf356\uf358\uf359 ]+EDTung Inc\. All Rights Reserved'
    r'\n112年會考\(社會科詳解\)\n\d+$'
)

cleaned = 0
for q in questions:
    if "explanation" in q and q["explanation"]:
        new = pat.sub("", q["explanation"])
        if new != q["explanation"]:
            q["explanation"] = new
            cleaned += 1

with open("data/112.json", "w", encoding="utf-8") as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)

print(f"Cleaned {cleaned} explanations")
