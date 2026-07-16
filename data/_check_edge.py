import json, sys
sys.stdout.reconfigure(encoding='utf-8')

# Check borderline cases
for year in ['112','113','114']:
    data = json.load(open(f'data/{year}.json','r',encoding='utf-8'))
    groups = [q for q in data if q['type'] == '題組子題']
    print(f'=== {year}: ALL group last-question option D (full text) ===')
    
    # Find which questions are the LAST in each group
    group_ranges = set()
    for q in groups:
        if q.get('group_range'):
            group_ranges.add(tuple(q['group_range']))
    
    for gr in sorted(group_ranges):
        last_q_num = gr[1]
        last_q = [q for q in groups if q['number'] == last_q_num]
        if last_q:
            q = last_q[0]
            d = q['options'].get('D', '(MISSING)')
            print(f'  Group {gr[0]}-{gr[1]}, Q{last_q_num}: D="{d}"')
            print(f'    len={len(d)}')
            print()

# Also check 112 Q45 trailing 表
print("=== 112 Q45 special ===")
data = json.load(open('data/112.json','r',encoding='utf-8'))
q45 = [q for q in data if q['number'] == 45][0]
print(f"  D = '{q45['options']['D']}'")

# 114 Q43 missing options
print("\n=== 114 Q43 special ===")
data = json.load(open('data/114.json','r',encoding='utf-8'))
q43 = [q for q in data if q['number'] == 43][0]
print(f"  options = {q43['options']}")
print(f"  stem = {q43['stem']}")
