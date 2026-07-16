import json, sys
sys.stdout.reconfigure(encoding='utf-8')

for year in ['112','113','114']:
    data = json.load(open(f'data/{year}.json','r',encoding='utf-8'))
    groups = [q for q in data if q['type'] == '題組子題']
    print(f'=== {year} ===')
    for q in groups:
        d = q['options'].get('D','')
        status = 'BAD' if len(d) > 80 else 'OK'
        print(f"  Q{q['number']:2d} D={len(d):3d}ch [{status}]  {d[:50]}...")
    print()
