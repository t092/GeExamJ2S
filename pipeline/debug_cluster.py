import fitz
doc = fitz.open(r'C:\Users\grifo\OneDrive\AI\VibeVoding\JHexam\114年國中教育會考社會科題本.pdf')
page = doc[5]
drawings = page.get_drawings()

bboxes = []
for d in drawings:
    r = d.get("rect")
    if r and r.width > 1 and r.height > 1:
        bboxes.append([r.x0, r.y0, r.x1, r.y1])

print(f'Total bboxes: {len(bboxes)}')

sorted_b = sorted(bboxes, key=lambda b: b[1])
clusters = [[sorted_b[0]]]
for b in sorted_b[1:]:
    cur = clusters[-1]
    cb = [min(c[0] for c in cur), min(c[1] for c in cur),
          max(c[2] for c in cur), max(c[3] for c in cur)]
    if (b[1] <= cb[3] + 10 and b[0] <= cb[2] + 20 and b[2] >= cb[0] - 20):
        cur.append(b)
    else:
        clusters.append([b])

print(f'Clusters: {len(clusters)}')
for i, c in enumerate(clusters[:10]):
    cb = [min(x[0] for x in c), min(x[1] for x in c), max(x[2] for x in c), max(x[3] for x in c)]
    w = cb[2] - cb[0]
    h = cb[3] - cb[1]
    passes = len(c)>20 and w>80 and h>50
    print(f'C{i}: [{cb[0]:.0f},{cb[1]:.0f},{cb[2]:.0f},{cb[3]:.0f}] w={w:.0f} h={h:.0f} n={len(c)} pass={passes}')

doc.close()
