#!/usr/bin/env python3
"""
Diagnostic: dump all text blocks, embedded images, drawings for the
three problematic image-options questions.

Output written to UTF-8 files, not stdout.
"""
import fitz
import os
import re
import sys
import io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASES = [
    ("113", 7,  3),
    ("114", 29, 8),
    ("115", 41, 11),
]

PDF_MAP = {y: os.path.join(ROOT, f'{y}年國中教育會考社會科題本.pdf') for y in ('113','114','115')}

OUT = io.StringIO()

def w(s=""):
    OUT.write(s + "\n")

for year, qnum, page_num in CASES:
    pdf_path = PDF_MAP[year]
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]
    pw, ph = page.rect.width, page.rect.height

    w("=" * 80)
    w(f"  {year} Q{qnum}  —  page {page_num}  ({pw:.0f}x{ph:.0f}pt)")
    w("=" * 80)

    # ── 1. ALL TEXT BLOCKS / LINES, sorted by Y ──
    w("\n── ALL TEXT LINES (sorted by Y) ──")
    blocks = page.get_text("dict")["blocks"]
    text_lines = []
    for b in blocks:
        if b.get("type") != 0:
            continue
        bnum = b.get("number", 0)
        for line in b.get("lines", []):
            txt = ''.join(s['text'] for s in line.get('spans', [])).strip()
            if not txt:
                continue
            xi0, yi0, xi1, yi1 = line['bbox']
            h = yi1 - yi0
            text_lines.append((yi0, yi1, xi0, xi1, h, txt, bnum, "line"))
            # Also individual spans for precise label detection
            for s in line.get('spans', []):
                st = s['text'].strip()
                if not st:
                    continue
                sb = s['bbox']
                text_lines.append((sb[1], sb[3], sb[0], sb[2], sb[3]-sb[1],
                                   f'SP:"{st}"', bnum, "span"))
    text_lines.sort(key=lambda x: x[0])
    for yi0, yi1, xi0, xi1, h, txt, bnum, kind in text_lines:
        marker = ""
        if kind == "line":
            t = txt.strip()
            if t in ('(A)', '(B)', '(C)', '(D)') or t.startswith('(A)') or t.startswith('(B)') or t.startswith('(C)') or t.startswith('(D)'):
                marker = " <=== OPTION"
        w(f"  y={yi0:7.1f}→{yi1:7.1f} h={h:5.1f}  "
          f"[{xi0:6.1f},{yi0:6.1f},{xi1:6.1f},{yi1:6.1f}]  "
          f"b{bnum} {kind:<5} {txt[:80]}{marker}")

    # ── 2. EMBEDDED IMAGES ──
    w("\n── EMBEDDED IMAGES (page.get_image_info()) ──")
    imgs = page.get_image_info()
    if not imgs:
        w("  (none)")
    else:
        for i, img in enumerate(imgs):
            b = img['bbox']
            sz = img.get('size', '?')
            w(f"  img[{i}] [{b[0]:7.1f},{b[1]:7.1f},{b[2]:7.1f},{b[3]:7.1f}]  "
              f"{b[2]-b[0]:5.0f}x{b[3]-b[1]:5.0f}pt  size={sz}  "
              f"digest={img.get('digest','')}")

    # ── 3. ALL DRAWINGS ──
    w("\n── DRAWINGS (page.get_drawings(), rects only) ──")
    drawings = page.get_drawings()
    rect_count = 0
    for i, d in enumerate(drawings):
        for item in d.get("items", []):
            op = item[0]
            if op == "re":
                r = item[1]
                # It's a Rect with optional fill/stroke
                even_odd = getattr(r, 'even_odd', None)
                fill_opacity = getattr(r, 'fill_opacity', None)
                stroke_opacity = getattr(r, 'stroke_opacity', None)
                w(f"  d[{i}] rect [{r.x0:7.1f},{r.y0:7.1f},{r.x1:7.1f},{r.y1:7.1f}]  "
                  f"{r.width:5.0f}x{r.height:5.0f}pt  fill_opacity={fill_opacity}  "
                  f"stroke_opacity={stroke_opacity}  even_odd={even_odd}")
                rect_count += 1
            elif op == "l":
                p1, p2 = item[1], item[2]
                w(f"  d[{i}] line ({p1.x:7.1f},{p1.y:7.1f})→({p2.x:7.1f},{p2.y:7.1f})")
    w(f"  total rects: {rect_count}")

    # ── 4. FIND CONTENT BELOW OPTION LABELS ──
    w("\n── OPTION LABEL DETAILS ──")
    d_y_top, d_y_bot, d_x0 = None, None, None
    a_y_top, a_x0 = None, None
    for yi0, yi1, xi0, xi1, h, txt, bnum, kind in text_lines:
        if kind == "span":
            t = txt.strip()
            if t == '(A)':
                a_y_top, a_x0 = yi0, xi0
                w(f"  (A) span: y={yi0:.1f}→{yi1:.1f}  x={xi0:.1f}→{xi1:.1f}")
            elif t == '(B)':
                w(f"  (B) span: y={yi0:.1f}→{yi1:.1f}  x={xi0:.1f}→{xi1:.1f}")
            elif t == '(C)':
                w(f"  (C) span: y={yi0:.1f}→{yi1:.1f}  x={xi0:.1f}→{xi1:.1f}")
            elif t == '(D)':
                d_y_top, d_y_bot, d_x0 = yi0, yi1, xi0
                w(f"  (D) span: y={yi0:.1f}→{yi1:.1f}  x={xi0:.1f}→{xi1:.1f}")

    if d_y_top is None:
        # Try finding from line text
        for yi0, yi1, xi0, xi1, h, txt, bnum, kind in text_lines:
            if kind == "line" and txt.strip().startswith("(D)"):
                d_y_top, d_y_bot, d_x0 = yi0, yi1, xi0
                w(f"  (D) line:  y={yi0:.1f}→{yi1:.1f}")
                break

    if d_y_top is None:
        w("  (D) label NOT FOUND!")
        doc.close()
        continue

    w(f"\n  (D) bbox: [{d_x0:.1f},{d_y_top:.1f},?,{d_y_bot:.1f}]")

    # ── 5. CONTEXT BELOW (D) ──
    w(f"\n── EVERYTHING BELOW (D) at y>{d_y_top:.1f} ──")

    w("  --- TEXT lines ---")
    count = 0
    for yi0, yi1, xi0, xi1, h, txt, bnum, kind in text_lines:
        if kind == "line" and yi0 > d_y_top + 5:
            w(f"    y={yi0:7.1f}→{yi1:7.1f} h={h:5.1f}  [x0={xi0:.1f}]  {txt[:100]}")
            count += 1
        if count > 15:
            w("    ... (truncated)")
            break

    w("  --- IMAGES overlapping y>(D)top ──")
    img_count = 0
    for i, img in enumerate(imgs):
        b = img['bbox']
        if b[1] >= d_y_top - 15 or b[3] >= d_y_top - 15:
            w(f"    img[{i}] [{b[0]:.1f},{b[1]:.1f},{b[2]:.1f},{b[3]:.1f}]  "
              f"{b[2]-b[0]:.0f}x{b[3]-b[1]:.0f}pt")
            img_count += 1
    if img_count == 0:
        w("    (none)")

    w("  --- DRAWING rects overlapping y>(D)top ──")
    rect_count = 0
    for i, d in enumerate(drawings):
        for item in d.get("items", []):
            if item[0] != "re":
                continue
            r = item[1]
            if r.y0 >= d_y_top - 15 or r.y1 >= d_y_top - 15:
                w(f"    d[{i}] rect [{r.x0:.1f},{r.y0:.1f},{r.x1:.1f},{r.y1:.1f}]  "
                  f"{r.width:.0f}x{r.height:.0f}pt")
                rect_count += 1
    if rect_count == 0:
        w("    (none)")

    # ── 6. RAW TEXT from question to next ──
    w("\n── RAW PAGE TEXT (excerpt around this Q) ──")
    raw = page.get_text("text")
    raw_lines = raw.split('\n')
    qnum_str = str(qnum)
    started = False
    next_q_str = str(qnum + 1)
    for ln in raw_lines:
        m_start = re.match(rf'^\s*{qnum_str}[.\uff0e]', ln)
        if m_start:
            started = True
        if started:
            w(f"  | {ln[:120]}")
            if re.match(rf'^\s*{next_q_str}[.\uff0e]', ln) or re.match(rf'^\s*40\uff0e', ln):
                break

    # ── 7. RECOMMENDATION ──
    w("\n── RECOMMENDED BBOX ──")

    # Default bottom: (D) bottom + 20pt
    default_bottom = d_y_bot + 20

    # Check images below options
    img_bottom = default_bottom
    for img in imgs:
        b = img['bbox']
        if b[1] >= d_y_top - 30 and b[3] > d_y_bot + 10:
            img_bottom = max(img_bottom, b[3] + 15)
    w(f"  option-label based bottom:  {default_bottom:.1f}  (D_bot={d_y_bot:.1f} + 20)")
    w(f"  image-extended bottom:      {img_bottom:.1f}")

    # Check drawing rects below options
    frame_bottom = default_bottom
    for d in drawings:
        for item in d.get("items", []):
            if item[0] != "re":
                continue
            r = item[1]
            # Large rect that overlaps option area
            if r.width > 50 and r.height > 30:
                if r.y0 >= d_y_top - 30 and r.y1 <= ph * 0.85:
                    frame_bottom = max(frame_bottom, r.y1 + 10)
    w(f"  frame-extended bottom:      {frame_bottom:.1f}")

    proposed_bottom = max(default_bottom, img_bottom, frame_bottom)

    # Next question safety
    next_q_found = None
    for yi0, yi1, xi0, xi1, h, txt, bnum, kind in text_lines:
        if kind == "line":
            t = txt.strip()
            if t == f'{qnum + 1}.':
                next_q_found = yi0
                break
    if next_q_found:
        proposed_bottom = min(proposed_bottom, next_q_found - 5)
        w(f"  next-Q-safety bottom:       {proposed_bottom:.1f}  (nextQ at y={next_q_found:.1f})")
    else:
        w(f"  next-Q-safety: not found")

    # Top: (A) label top - 10
    proposed_top = a_y_top - 10 if a_y_top else d_y_top - 50
    proposed_top = max(10, proposed_top)

    # X bounds
    margin_left = 40
    margin_right = 45
    proposed_bbox = [margin_left, proposed_top, pw - margin_right, min(ph - 10, proposed_bottom)]
    pts_w = proposed_bbox[2] - proposed_bbox[0]
    pts_h = proposed_bbox[3] - proposed_bbox[1]

    w(f"\n  Final bbox: [{proposed_bbox[0]:.0f},{proposed_bbox[1]:.0f},"
      f"{proposed_bbox[2]:.0f},{proposed_bbox[3]:.0f}]  "
      f"{pts_w:.0f}x{pts_h:.0f}pt  [{pts_h/pts_w:.2f} aspect]")

    # What would the OLD algorithm produce?
    # It uses: opt_top = min(option_y) - 10, opt_bottom = opt_bottom_(D) + 20
    # Then images below with ib[1] >= opt_bottom - 15 AND ib[3] > opt_bottom
    # Then drawing rects >50x30 that overlap vertically

    # Simulate old algorithm
    old_opt_labels = {}
    for yi0, yi1, xi0, xi1, h, txt, bnum, kind in text_lines:
        if kind == "span" and txt.strip() in ('(A)', '(B)', '(C)', '(D)'):
            old_opt_labels[txt.strip()] = yi0
    if old_opt_labels:
        old_opt_top = min(old_opt_labels.values()) - 10
        old_d_y = old_opt_labels.get('(D)', d_y_top)
        old_opt_bottom = old_d_y + 20  # approx (old code: max(opt_labels.values()) + 20)
        # images
        for img in imgs:
            ib = img['bbox']
            if ib[1] >= old_opt_bottom - 15 and ib[3] > old_opt_bottom:
                old_opt_bottom = max(old_opt_bottom, ib[3] + 15)
        # frames
        for d in drawings:
            for item in d.get("items", []):
                if item[0] != "re":
                    continue
                r = item[1]
                if r.width > 50 and r.height > 30:
                    if r.y0 >= old_opt_top and r.y1 <= ph * 0.85:
                        old_opt_bottom = max(old_opt_bottom, r.y1 + 10)
        # next Q safety
        if next_q_found and next_q_found < old_opt_bottom:
            old_opt_bottom = next_q_found - 5
        old_h = old_opt_bottom - old_opt_top
        w(f"\n  OLD algorithm would produce: "
          f"{old_opt_bottom-old_opt_top:.0f}pt tall "
          f"(opt_top={old_opt_top:.1f}, opt_bottom={old_opt_bottom:.1f})")

    w("")

    doc.close()

# Write output
out_path = os.path.join(ROOT, "pipeline", "diagnose_output2.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(OUT.getvalue())
print(f"Output written to {out_path}")
print(f"Total chars: {OUT.tell()}")