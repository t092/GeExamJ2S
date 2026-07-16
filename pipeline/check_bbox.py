import json
with open(r'C:\Users\grifo\OneDrive\AI\VibeVoding\JHexam\web\pic\figures_114.json', encoding='utf-8') as f:
    d = json.load(f)
for fid in ['圖(九)', '圖(十)', '圖(十一)']:
    if fid in d['matched']:
        m = d['matched'][fid]
        print(fid, 'page', m['page'], 'bbox', m['bbox'], 'method', m['method'])
