import fitz
doc = fitz.open(r'C:\Users\grifo\OneDrive\AI\VibeVoding\JHexam\114年國中教育會考社會科題本.pdf')
page = doc[5]
drawings = page.get_drawings()
in_range = []
for d in drawings:
    r = d.get('rect')
    if r and r.y0 > 200 and r.y1 < 520:
        if r.width > 30 and r.height > 30:
            in_range.append({'bbox': [round(r.x0), round(r.y0), round(r.x1), round(r.y1)]})
print('Drawings in y=[200,520]:', len(in_range))
for d in in_range[:10]:
    print(d['bbox'])

rects = []
for d in drawings:
    for item in d.get('items', []):
        if item[0] == 're':
            r = item[1]
            if r.y0 > 200 and r.y1 < 520 and r.width > 80 and r.height > 50:
                rects.append({'bbox': [round(r.x0), round(r.y0), round(r.x1), round(r.y1)]})
print('\nRects in y=[200,520]:', len(rects))
for r in rects:
    print(r['bbox'])
doc.close()
