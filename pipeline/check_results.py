import json
from collections import Counter
with open(r'C:\Users\grifo\OneDrive\AI\VibeVoding\JHexam\web\pic\figures_114.json', encoding='utf-8') as f:
    d = json.load(f)
c = Counter(v['method'] for v in d['matched'].values())
print('Methods:', dict(c))
for fid, v in sorted(d['matched'].items(), key=lambda x: x[1]['num']):
    h = v['frame_bbox'][3] - v['frame_bbox'][1]
    flag = ' TALL' if h > 300 else ''
    print(f'{fid} -> {v["output"]} {v["size"][0]}x{v["size"][1]} {v["method"]} frame_h={h:.0f}{flag}')
