#!/usr/bin/env python3
"""
Diagnostic: dump all text blocks, embedded images, drawings for the
three problematic image-options questions.
"""
import fitz
import os
import re
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASES = [
    ("113", 7,  3),
    ("114", 29, 8),
    ("115", 41, 11),
]

PDF_MAP = {y: os.path.join(ROOT, f'{y}年國中教育會考社會科題本.pdf') for y in ('113','114','115')}

for year, qnum, page_num in CASES:
    pdf_path = PDF_MAP[year]
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]  # 0-indexed
    pw, ph = page.rect.width, page.rect.height

    print("=" * 80)
    print(f"  {year} Q{qnum}  —  page {page_num}  ({pw:.0f}×{ph:.0f}pt)")
    print("=" * 80)

    # ── 1. ALL TEXT BLOCKS / LINES, sorted by Y ──
    print("\n── TEXT BLOCKS (sorted by Y) ──")
    blocks = page.get_text("dict")["blocks"]
    text_lines = []
    for b in blocks:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            txt = ''.join(s['text'] for s in line.get('spans', [])).strip()
            if not txt:
                continue
            bbox = line['bbox']
            text_lines.append((bbox[1], bbox, txt))
            # Also print individual spans for precise (A)/(B) location
            for s in line.get('spans', []):
                st = s['text'].strip()
                if not st:
                    continue
                sb = s['bbox']
                text_lines.append((sb[1], sb, f'  SPAN: "{st}"'))
    text_lines.sort(key=lambda x: x[0])
    for y, bbox, txt in text_lines:
        y0, y1 = bbox[1], bbox[3]
        # Mark option labels
        marker = ""
        if txt.strip().startswith("(") and txt.strip().endswith(")"):
            letter = txt.strip()[1]
            if letter in 'ABCD':
                marker = " <=== OPTION LABEL"
        print(f"  y={y0:6.1f}→{y1:6.1f}  [{bbox[0]:6.1f}, {y0:6.1f}, {bbox[2]:6.1f}, {y1:6.1f}]  {txt[:80]}{marker}")

    # ── 2. EMBEDDED IMAGES ──
    print("\n── EMBEDDED IMAGES (page.get_image_info()) ──")
    imgs = page.get_image_info()
    if not imgs:
        print("  (none)")
    else:
        for i, img in enumerate(imgs):
            b = img['bbox']
            sz = img.get('size', '?')
            print(f"  img[{i}]  [{b[0]:.1f}, {b[1]:.1f}, {b[2]:.1f}, {b[3]:.1f}]  "
                  f"{b[2]-b[0]:.0f}×{b[3]-b[1]:.0f}pt  size={sz}")

    # ── 3. ALL DRAWINGS (vec objects) ──
    print("\n── DRAWINGS (page.get_drawings(), all items) ──")
    drawings = page.get_drawings()
    if not drawings:
        print("  (none)")
    else:
        for i, d in enumerate(drawings):
            for item in d.get("items", []):
                op = item[0]
                geom = item[1]
                r = geom  # rect for "re", Point for "l"/"c" etc
                if op == "re":
                    # rect: fitz.Rect
                    print(f"  d[{i}] rect  [{r.x0:.1f}, {r.y0:.1f}, {r.x1:.1f}, {r.y1:.1f}]  "
                          f"{r.width:.0f}×{r.height:.0f}pt")
                elif op == "l":
                    print(f"  d[{i}] line  from=({r.x:.1f},{r.y:.1f}) to=({geom[2].x:.1f},{geom[2].y:.1f})")
                elif op == "c":
                    print(f"  d[{i}] curve  from=({r.x:.1f},{r.y:.1f}) to=({geom[3].x:.1f},{geom[3].y:.1f})")
                elif op == "qu":
                    print(f"  d[{i}] quad  from=({r.x:.1f},{r.y:.1f}) to=({geom[3].x:.1f},{geom[3].y:.1f})")
                else:
                    print(f"  d[{i}] {op}  {r}")

    # ── 4. PAGE-DETAILED CONTEXT around the (D) label ──
    print("\n── CONTEXT: above / below (D) label ──")
    # Find (D) label Y
    d_y = None
    for y, bbox, txt in text_lines:
        if txt.strip() == "(D)" or txt.strip().startswith("(D)"):
            d_y = bbox[3]
            print(f"  (D) label found at y={bbox[1]:.1f}→{bbox[3]:.1f}, x0={bbox[0]:.1f}")
            break
    if d_y is None:
        print("  (D) label NOT FOUND!")
    else:
        # Show all text below it
        print(f"  --- below (D) at y>{d_y:.1f}:")
        for y, bbox, txt in text_lines:
            if bbox[1] > d_y - 5:
                print(f"    y={bbox[1]:6.1f}→{bbox[3]:6.1f}  [{bbox[0]:6.1f}, {bbox[1]:6.1f}, {bbox[2]:6.1f}, {bbox[3]:6.1f}]  {txt[:80]}")
        # Show images below it
        print(f"  --- images overlapping y>{d_y:.1f}:")
        for i, img in enumerate(imgs):
            b = img['bbox']
            if b[1] >= d_y - 15 or b[3] >= d_y - 15:
                print(f"    img[{i}]  [{b[0]:.1f}, {b[1]:.1f}, {b[2]:.1f}, {b[3]:.1f}]  "
                      f"{b[2]-b[0]:.0f}×{b[3]-b[1]:.0f}pt")
        # Show drawings below it
        print(f"  --- drawings overlapping y>{d_y:.1f}:")
        for i, d in enumerate(drawings):
            for item in d.get("items", []):
                if item[0] != "re":
                    continue
                r = item[1]
                if r.y0 >= d_y - 15 or r.y1 >= d_y - 15:
                    print(f"    d[{i}] rect  [{r.x0:.1f}, {r.y0:.1f}, {r.x1:.1f}, {r.y1:.1f}]  "
                          f"{r.width:.0f}×{r.height:.0f}pt")

    # ── 5. RAW text (not sorted) for full context ──
    print("\n── RAW TEXT (page.get_text()) ──")
    raw = page.get_text()
    # Print starting from around the question
    qnum_str = str(qnum)
    # Find Q line
    lines = raw.split('\n')
    started = False
    for ln in lines:
        if re.match(rf'^\s*{qnum_str}[.\uff0e]', ln):
            started = True
        if started:
            print(f"  |{ln[:100]}")
            if re.match(rf'^\s*{qnum_str+1}[.\uff0e]', ln):
                break

    print("\n── RECOMMENDATION ──")

    # Determine the true bottom: max of:
    #   - (D) label bottom + generous margin
    #   - last embedded image below options + margin
    #   - last drawing rect below options + margin
    #   - next question Y (safety)

    d_label_bottom = d_y if d_y else 0

    # images below options
    img_bottom = d_label_bottom
    for img in imgs:
        b = img['bbox']
        if b[1] >= d_label_bottom - 30:
            img_bottom = max(img_bottom, b[3])

    # drawings below options
    # Actually look for drawings that are option-containing frames
    frame_bottom = d_label_bottom
    for d in drawings:
        for item in d.get("items", []):
            if item[0] != "re":
                continue
            r = item[1]
            if r.width > 50 and r.height > 30 and r.y0 >= d_label_bottom - 30 and r.y1 <= ph * 0.85:
                frame_bottom = max(frame_bottom, r.y1)

    proposed_bottom = max(d_label_bottom + 20, img_bottom + 15, frame_bottom + 10)

    # Next question safety
    next_q_str = f'{qnum + 1}.'
    for b in blocks:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            lt = ''.join(s['text'] for s in line.get('spans', [])).strip()
            if lt == next_q_str:
                next_y = line['bbox'][1]
                proposed_bottom = min(proposed_bottom, next_y - 5)

    # Option top: (A) y
    a_y = None
    for y, bbox, txt in text_lines:
        if txt.strip().startswith("(A)"):
            a_y = bbox[1]
            break
    if a_y is None:
        a_y = d_label_bottom - 50  # fallback

    proposed_top = a_y - 10 if a_y else d_label_bottom - 100

    margin_left = 40
    margin_right = 45
    proposed_bbox = [margin_left, max(10, proposed_top), pw - margin_right, min(ph - 10, proposed_bottom)]
    pts_h = proposed_bbox[3] - proposed_bbox[1]
    print(f"  (D) label bottom:  {d_label_bottom:.1f}")
    print(f"  Last image bottom: {img_bottom:.1f}")
    print(f"  Last frame bottom: {frame_bottom:.1f}")
    print(f"\n  Proposed bbox: [{proposed_bbox[0]:.0f}, {proposed_bbox[1]:.0f}, "
          f"{proposed_bbox[2]:.0f}, {proposed_bbox[3]:.0f}]  "
          f"{proposed_bbox[2]-proposed_bbox[0]:.0f}×{pts_h:.0f}pt")
    print()

    doc.close()

print("=" * 80)
print("  DONE")
print("=" * 80)