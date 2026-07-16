import fitz
import re
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Extract text from answer PDF
doc = fitz.open("112年會考社會科答案.pdf")
full_text = ""
for page in doc:
    full_text += page.get_text() + "\n"

# Parse answer & explanation
# Pattern: N.(letter) explanation...
# N ranges 1-54, letter A-D
answers = {}
pattern = r'(\d{1,2})\.\(([A-D])\)\s*(.*?)(?=\n\d{1,2}\.|$)'
matches = re.findall(pattern, full_text, re.DOTALL)

for num_str, answer, explanation in matches:
    n = int(num_str)
    explanation = explanation.strip()
    answers[n] = {"answer": answer, "explanation": explanation}

print(f"Parsed {len(answers)} questions")
for n in range(1, 55):
    if n not in answers:
        print(f"  MISSING: Q{n}")

# Merge into 112.json
with open("data/112.json", encoding="utf-8") as f:
    questions = json.load(f)

updated = 0
for q in questions:
    n = q["number"]
    if n in answers:
        q["answer"] = answers[n]["answer"]
        q["explanation"] = answers[n]["explanation"]
        updated += 1

with open("data/112.json", "w", encoding="utf-8") as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)

print(f"\nUpdated {updated} questions in data/112.json")
