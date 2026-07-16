import json
with open(r'C:\Users\grifo\OneDrive\AI\VibeVoding\JHexam\pipeline\output\vector_table_eval.json', encoding='utf-8') as f:
    d = json.load(f)
y = d['114']
for pn in ['page_11', 'page_12']:
    if pn in y:
        print(f'=== {pn} ===')
        for i, t in enumerate(y[pn]['tables']):
            print(f'Table {i}: {t["rows"]}x{t["cols"]} at {t["bbox"]}')
            for r, row in enumerate(t['cells'][:8]):
                print(f'  R{r}: {row}')
