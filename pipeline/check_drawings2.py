import fitz
doc = fitz.open(r'C:\Users\grifo\OneDrive\AI\VibeVoding\JHexam\114年國中教育會考社會科題本.pdf')
page = doc[5]
drawings = page.get_drawings()
all_d = []
for d in drawings:
    r = d.get('rect')
    if r and r.y0 > 300 and r.y1 < 520:
        all_d.append({
            'x0': round(r.x0), 'y0': round(r.y0), 'x1': round(r.x1), 'y1': round(r.y1),
            'w': round(r.width), 'h': round(r.height)
        })
all_d.sort(key=lambda x: (x['y0'], x['x0']))
print(f'ALL drawings [300,520]: {len(all_d)}')
for d in all_d[:30]:
    print(f'  [{d["x0"]},{d["y0"]},{d["x1"]},{d["y1"]}] {d["w"]}x{d["h"]}')
if len(all_d) > 30:
    print(f'  ... +{len(all_d)-30} more')
    
# Cluster nearby drawings
bboxes = [[d['x0'], d['y0'], d['x1'], d['y1']] for d in all_d]
if bboxes:
    sorted_b = sorted(bboxes, key=lambda b: b[1])
    clusters = [[sorted_b[0]]]
    for b in sorted_b[1:]:
        cur = clusters[-1]
        cb = [min(c[0] for c in cur), min(c[1] for c in cur), max(c[2] for c in cur), max(c[3] for c in cur)]
        if b[1] <= cb[3] + 10 and b[0] <= cb[2] + 10 and b[2] >= cb[0] - 10:
            cur.append(b)
        else:
            clusters.append([b])
    print(f'\nClusters: {len(clusters)}')
    for i, c in enumerate(clusters):
        bbox = [min(x[0] for x in c), min(x[1] for x in c), max(x[2] for x in c), max(x[3] for x in c)]
        print(f'  C{i}: [{round(bbox[0])},{round(bbox[1])},{round(bbox[2])},{round(bbox[3])}] w={round(bbox[2]-bbox[0])} h={round(bbox[3]-bbox[1])} n={len(c)}')
doc.close()
