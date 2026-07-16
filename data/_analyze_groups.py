#!/usr/bin/env python3
"""Analyze group questions across all years."""
import re, json, os, sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for year in ['112','113','114']:
    txt_path = os.path.join(ROOT, 'pipeline', 'output', f'{year}_text.txt')
    json_path = os.path.join(ROOT, 'data', f'{year}.json')
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    markers = list(re.finditer(r'閱讀下列選文，回答第\s*(\d+)\s*至\s*(\d+)\s*題', text))
    print(f'=== {year} ===')
    for m in markers:
        start, end = int(m.group(1)), int(m.group(2))
        print(f'  Group {start}-{end}: raw text pos={m.start()}')
    
    data = json.load(open(json_path, 'r', encoding='utf-8'))
    groups = [q for q in data if q['type'] == '題組子題']
    nums = [q['number'] for q in groups]
    print(f'  Group questions in JSON: {nums}')
    
    for q in groups:
        d_text = q['options'].get('D', '')
        if len(d_text) > 80:
            print(f'  *** Q{q["number"]} option D len={len(d_text)} (BAD)')
            print(f'      First 40: {d_text[:40]}')
            print(f'      Last 40:  {d_text[-40:]}')
    
    q43 = [q for q in data if q['number'] == 43]
    if q43:
        q43 = q43[0]
        print(f'  Q43 type: {q43["type"]}, group_range: {q43.get("group_range")}')
    
    # Check option counts
    for q in groups:
        opt_count = len(q['options'])
        if opt_count < 4:
            print(f'  *** Q{q["number"]} has only {opt_count} options: {list(q["options"].keys())}')
    
    print()

# Detailed check per year
for year in ['112','113','114']:
    print(f'=== {year} Q42-45 details ===')
    data = json.load(open(os.path.join(ROOT, 'data', f'{year}.json'), 'r', encoding='utf-8'))
    for q in data:
        if q['number'] >= 42 and q['number'] <= 45:
            stem_preview = q['stem'][:50] if q['stem'] else '(empty)'
            print(f"  Q{q['number']}: type={q['type']}, gr={q.get('group_range')}, stem={stem_preview}...")
    print()
