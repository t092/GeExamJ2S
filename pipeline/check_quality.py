import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for year in ['112', '113', '114']:
    path = os.path.join(ROOT, 'data', f'{year}.json')
    with open(path, encoding='utf-8') as f:
        qs = json.load(f)
    
    figs = [q for q in qs if q['figures']]
    groups = [q for q in qs if q['type'] == '題組子題']
    
    print(f'{year}: {len(qs)} total, {len(figs)} with figures, {len(groups)} group questions')
    if figs:
        for q in figs[:5]:
            print(f'  Q{q["number"]}: {q["figures"]}')
