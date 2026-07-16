#!/usr/bin/env python3
"""Check if PDF has table border lines (vector graphics) we can use as boundaries."""
import fitz
import os
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def analyze_page_graphics(page, page_num):
    """Get vector graphics (lines, rects) that could be table borders."""
    drawings = page.get_drawings()
    
    # Filter for horizontal/vertical lines (potential table borders)
    h_lines = []
    v_lines = []
    rects = []
    
    for d in drawings:
        for item in d.get("items", []):
            if item[0] == "l":  # line
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 2:  # horizontal
                    h_lines.append({
                        "y": round(p1.y, 1),
                        "x0": round(min(p1.x, p2.x), 1),
                        "x1": round(max(p1.x, p2.x), 1),
                        "width": d.get("width", 1),
                    })
                elif abs(p1.x - p2.x) < 2:  # vertical
                    v_lines.append({
                        "x": round(p1.x, 1),
                        "y0": round(min(p1.y, p2.y), 1),
                        "y1": round(max(p1.y, p2.y), 1),
                        "width": d.get("width", 1),
                    })
            elif item[0] == "re":  # rectangle
                r = item[1]
                rects.append({
                    "x0": round(r.x0, 1),
                    "y0": round(r.y0, 1),
                    "x1": round(r.x1, 1),
                    "y1": round(r.y1, 1),
                    "width": r.width,
                    "height": r.height,
                })
    
    return {
        "page": page_num,
        "h_lines_count": len(h_lines),
        "v_lines_count": len(v_lines),
        "rects_count": len(rects),
        "h_lines": sorted(h_lines, key=lambda l: l["y"])[:20],
        "v_lines": sorted(v_lines, key=lambda l: l["x"])[:20],
        "rects": [r for r in rects if r["width"] > 50 and r["height"] > 30][:10],
    }

def main():
    out_dir = os.path.join(ROOT_DIR, 'pipeline', 'output')
    
    results = {}
    for year in ['114']:
        pdf_path = os.path.join(ROOT_DIR, f'{year}年國中教育會考社會科題本.pdf')
        if not os.path.exists(pdf_path):
            continue
        doc = fitz.open(pdf_path)
        results[year] = {}
        # Check pages with tables
        for page_num in [4, 11, 12]:
            page = doc[page_num - 1]
            results[year][f'page_{page_num}'] = analyze_page_graphics(page, page_num)
        doc.close()
    
    out = os.path.join(out_dir, 'graphics_eval.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'Saved -> {out}')

if __name__ == '__main__':
    main()
