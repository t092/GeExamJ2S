import json, sys
sys.stdout.reconfigure(encoding='utf-8')

# Summary: which groups have issues and which don't
print("=== COMPLETE ISSUE MAP ===")
print()
for year in ['112','113','114']:
    data = json.load(open(f'data/{year}.json','r',encoding='utf-8'))
    groups = [q for q in data if q['type'] == '題組子題']
    
    # Find unique group ranges
    seen = set()
    ranges = []
    for q in groups:
        gr = tuple(q.get('group_range') or [])
        if gr and gr not in seen:
            seen.add(gr)
            ranges.append(gr)
    
    print(f'{year}年:')
    for gr in sorted(ranges):
        last_q = [q for q in groups if q['number'] == gr[1]][0]
        first_q = [q for q in groups if q['number'] == gr[0]][0]
        d = last_q['options'].get('D', '(MISSING)')
        d_len = len(d)
        # Any sub-question with missing options?
        sub_qs = [q for q in groups if q.get('group_range') and tuple(q['group_range']) == gr]
        opt_issues = []
        for sq in sub_qs:
            if len(sq['options']) < 4:
                opt_issues.append(f"Q{sq['number']}缺選項(只有{list(sq['options'].keys())})")
            for k,v in sq['options'].items():
                if not v:
                    opt_issues.append(f"Q{sq['number']}({k})空白")
        
        status = '✗' if d_len > 30 else '✓'
        print(f'  Group {gr[0]}-{gr[1]}: 末題Q{gr[1]} D長度={d_len:3d}字 [{status}]')
        if opt_issues:
            for oi in opt_issues:
                print(f'    ⚠ {oi}')
    print()
