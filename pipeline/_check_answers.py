import json
with open("data/112.json", encoding="utf-8") as f:
    questions = json.load(f)

checked = [1, 24, 43, 54]
for n in checked:
    q = questions[n-1]
    print("Q{}: answer={}".format(n, q.get("answer")))
    print("  explanation: {}...".format(q.get("explanation", "")[:80]))
    print()

missing = [q["number"] for q in questions if "answer" not in q or q["answer"] is None]
print("Missing answer:", missing)
print("Total:", len(questions), "questions with answer:", sum(1 for q in questions if "answer" in q and q["answer"] is not None))
