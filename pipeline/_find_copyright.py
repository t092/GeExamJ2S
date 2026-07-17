import json, re, sys

with open("data/112.json", encoding="utf-8") as f:
    text = f.read()

out = []
idx = text.find("甄戰")
count = 0
while idx != -1:
    count += 1
    snippet = text[idx:idx+150]
    out.append(f"#{count} at {idx}: {repr(snippet)}")
    idx = text.find("甄戰", idx + 1)

out.append(f"Total: {count}")
with open("pipeline/output/_copyright_debug.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
