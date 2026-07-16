#!/usr/bin/env python3
"""
Crop the entire option area (with (A)(B)(C)(D) labels + image content)
for questions whose options are images.  Saves to web/pic/item/ as JPG.

Strategy: find the option region on the page and extend it generously
to include visual content below the text labels.
"""
import fitz
import os
import re
import json
import sys
from PIL import Image

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_PIC = os.path.join(ROOT_DIR, 'web', 'pic')
ITEM_DIR = os.path.join(WEB_PIC, 'item')
DPI = 200

PDF_PATHS = {
    '112': '112年國中教育會考社會科題本.pdf',
    '113': '113年國中教育會考社會科題本.pdf',
    '114': '114年國中教育會考社會科題本.pdf',
    '115': '115年國中教育會考社會科題本.pdf',
}


def load_image_option_questions() -> list[dict]:
    """Scan data/*.json for questions with image_options set.
    Returns list of (year, question_dict) augmented with page_number.
    """
    items = []
    for year in ['112', '113', '114', '115']:
        json_path = os.path.join(ROOT_DIR, 'data', f'{year}.json')
        if not os.path.exists(json_path):
            continue
        with open(json_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        for q in questions:
            io = q.get('image_options')
            if not io:
                continue
            page_num = find_page_for_question(year, int(q['number']), q.get('group_range'))
            items.append({
                'year': year,
                'number': q['number'],
                'type': q['type'],
                'filename': io,
                'full': q.get('image_options_full', True),
                'group_range': q.get('group_range'),
                'page': page_num,
            })
    return items


_PAGE_MAP_CACHE: dict[str, dict[int, int]] = {}

def _build_page_map(year: str, pdf_path: str) -> dict[int, int]:
    """Scan PDF pages 2-15 for question numbers, return qnum→page mapping."""
    if year in _PAGE_MAP_CACHE:
        return _PAGE_MAP_CACHE[year]
    doc = fitz.open(pdf_path)
    qn_to_page = {}
    for pg_idx in range(1, min(15, doc.page_count)):
        page = doc[pg_idx]
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                text = "".join([span["text"] for span in line["spans"]])
                m = re.match(r'^\s*(\d{1,2})\.\s+', text)
                if not m:
                    m = re.match(r'^\s*(\d{1,2})\uff0e\s+', text)
                if m:
                    qn = int(m.group(1))
                    if qn <= 54:
                        qn_to_page[qn] = pg_idx + 1
    doc.close()
    _PAGE_MAP_CACHE[year] = qn_to_page
    return qn_to_page

def find_page_for_question(year: str, qnum: int, group_range: list | None) -> int | None:
    """Determine which page a question is on by searching PDF text."""
    pdf_path = os.path.join(ROOT_DIR, PDF_PATHS[year])
    if not os.path.exists(pdf_path):
        return None
    qn_to_page = _build_page_map(year, pdf_path)
    return qn_to_page.get(qnum)


def locate_option_bbox(page: fitz.Page, qnum: int) -> list[float] | None:
    """
    Find the bbox covering the entire option area (A)-(D) including image content.

    Strategy:
      1. Find question-number 'N.' → top anchor for this question
      2. Find next question-number → bottom boundary constraint
      3. Within [q_top, next_q_top], find (A)-(D) label positions
      4. Extend bottom to include: embedded images, drawing clusters, frame rects
         that lie within the question's vertical zone
    """
    text_page = page.get_text("dict")
    blocks = text_page.get("blocks", [])

    page_w = page.rect.width
    page_h = page.rect.height

    # ── Step 1: find all question numbers on this page ──
    # Returns list of (qnum, line_y_top)
    q_positions: list[tuple[int, float]] = []

    for b in blocks:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            line_text = ''.join(s['text'] for s in line.get('spans', [])).strip()
            if not line_text:
                continue
            m = re.match(r'(\d{1,2})\.', line_text)
            if m:
                qn = int(m.group(1))
                if 1 <= qn <= 54:
                    # A question number might appear in the middle of a long block
                    # (stem text flowing from previous page).  Prefer the first
                    # occurrence that is a real question header, not a mid-text ref.
                    # Distinguish by: short preceding text or standalone.
                    for span in line.get("spans", []):
                        st = span['text'].strip()
                        if st == f'{qn}.' or st.startswith(f'{qn}.'):
                            q_positions.append((qn, line['bbox'][1]))
                            break

    # Deduplicate: if same qnum appears twice (continuation from prior page vs real start),
    # keep the lower one (further down the page = real start, continuation is above)
    q_map: dict[int, float] = {}
    for qn, y in q_positions:
        if qn in q_map:
            q_map[qn] = max(q_map[qn], y)  # prefer lower (real start)
        else:
            q_map[qn] = y

    # Find current question and next question y-bounds
    q_top = q_map.get(qnum)
    if q_top is None:
        print(f'  [WARN] Cannot find question number {qnum}. on page')
        return None

    # Next question number → upper boundary for options
    next_q_y = None
    if qnum < 54:
        for nq in range(qnum + 1, min(qnum + 5, 55)):
            ny = q_map.get(nq)
            if ny and ny > q_top:
                next_q_y = ny
                break

    # ── Step 2: find option labels (A)-(D) within our vertical zone ──
    opt_labels: dict[str, float] = {}
    zone_bottom = next_q_y if next_q_y else page_h - 10
    zone_top = q_top

    for b in blocks:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            line_text = ''.join(s['text'] for s in line.get('spans', [])).strip()
            line_y = line['bbox'][1]
            if line_y <= zone_top:
                continue
            if next_q_y and line_y >= next_q_y:
                continue
            for letter in ['A', 'B', 'C', 'D']:
                label = f'({letter})'
                if line_text == label or line_text.startswith(label):
                    opt_labels.setdefault(letter, line_y)

    if not opt_labels:
        print('  [WARN] Cannot find any (A)-(D) labels between Q{qnum} and next')
        # Fallback: search after q_top without zone constraint
        for b in blocks:
            if b.get("type") != 0:
                continue
            for line in b.get("lines", []):
                line_text = ''.join(s['text'] for s in line.get('spans', [])).strip()
                line_y = line['bbox'][1]
                if line_y <= zone_top:
                    continue
                for letter in ['A', 'B', 'C', 'D']:
                    label = f'({letter})'
                    if line_text == label or line_text.startswith(label):
                        opt_labels.setdefault(letter, line_y)
                if opt_labels:
                    # Take the first cluster = our question's options
                    break
            if opt_labels:
                break

    if not opt_labels:
        print('  [WARN] Cannot find any (A)-(D) labels anywhere after Q{qnum}')
        return None

    opt_top_y = min(opt_labels.values()) - 10
    opt_bottom_y = max(opt_labels.values()) + 20

    # ── Step 3: expand to include embedded images ──
    images = page.get_image_info()
    for img in images:
        ib = img['bbox']
        img_bottom = ib[3]
        img_top = ib[1]
        if img_bottom <= opt_top_y:
            continue
        if next_q_y and img_top >= next_q_y:
            continue
        # Image overlaps the option zone vertically
        if img_bottom > opt_bottom_y:
            opt_bottom_y = img_bottom + 10
        if img_top < opt_top_y:
            opt_top_y = img_top - 10

    # ── Step 4: expand to include drawing frame rects ──
    drawings = page.get_drawings()
    for d in drawings:
        for item in d.get("items", []):
            if item[0] != "re":
                continue
            r = item[1]
            if r.width < 40 or r.height < 20:
                continue
            if r.y1 <= opt_top_y:
                continue
            if next_q_y and r.y0 >= next_q_y:
                continue
            if r.y1 > opt_bottom_y:
                opt_bottom_y = r.y1 + 10
            if r.y0 < opt_top_y:
                opt_top_y = r.y0 - 10

    # ── Step 5: expand to include drawing clusters (vector art) ──
    # Cluster nearby non-rect drawing bboxes (lines, curves, quads)
    drawing_clusters = []
    for d in drawings:
        r = d.get("rect")
        if r is None or r.is_empty:
            continue
        dw, dh = r.width, r.height
        if dw < 5 and dh < 5:
            continue
        y0, y1 = r.y0, r.y1
        if y1 <= opt_top_y:
            continue
        if next_q_y and y0 >= next_q_y:
            continue
        drawing_clusters.append((y0, y1, dw, dh))

    if drawing_clusters:
        # Sort by Y, then merge nearby clusters (within 8pt gap)
        clusters = sorted(drawing_clusters, key=lambda c: c[0])
        merged = [list(clusters[0])]
        for cy0, cy1, cw, ch in clusters[1:]:
            last = merged[-1]
            if cy0 <= last[1] + 8:
                last[1] = max(last[1], cy1)
                last[2] = max(last[2], cw)
                last[3] = max(last[3], ch)
            else:
                merged.append([cy0, cy1, cw, ch])

        # Only extend if a cluster is substantial (w > 60 or h > 40)
        for cy0, cy1, cw, ch in merged:
            if cy1 > opt_bottom_y and (cw > 60 or ch > 40):
                opt_bottom_y = cy1 + 15
            if cy0 < opt_top_y and (cw > 60 or ch > 40):
                opt_top_y = cy0 - 10

    # ── Step 6: constrain bottom by next question ──
    if next_q_y and opt_bottom_y > next_q_y:
        opt_bottom_y = next_q_y - 5

    # ── Step 7: x bounds ──
    margin_left = 40
    margin_right = 45
    opt_left = margin_left
    opt_right = page_w - margin_right

    opt_top_y = max(5, opt_top_y)
    opt_bottom_y = min(page_h - 10, opt_bottom_y)

    return [opt_left, opt_top_y, opt_right, opt_bottom_y]


def crop_and_save(page_png: str, bbox: list[float], out_path: str, padding: int = 8) -> tuple | None:
    scale = DPI / 72
    img = Image.open(page_png)
    crop = (
        max(0, int((bbox[0] - padding) * scale)),
        max(0, int((bbox[1] - padding) * scale)),
        min(img.width, int((bbox[2] + padding) * scale)),
        min(img.height, int((bbox[3] + padding) * scale)),
    )
    if crop[2] <= crop[0] or crop[3] <= crop[1]:
        return None
    cropped = img.crop(crop).convert('RGB')
    cropped.save(out_path, 'JPEG', quality=90)
    return cropped.size


def main() -> None:
    items = load_image_option_questions()
    if not items:
        print('No image-option questions found.')
        return

    print(f'{len(items)} image-option questions to crop:\n')
    for it in items:
        print(f'  {it["year"]} Q{it["number"]:>2} → {it["filename"]}  '
              f'(page #{it["page"]}, type={it["type"]}, full={it["full"]})')
    print()

    os.makedirs(ITEM_DIR, exist_ok=True)

    opened_pdfs = {}
    total_ok = 0
    total_fail = 0

    for it in items:
        year = it['year']
        qnum = it['number']
        page_num = it['page']
        fname = it['filename']
        full = it['full']
        label = f'{year} Q{qnum}'

        print(f'--- {label} (page {page_num}) ---')

        # Open PDF
        if year not in opened_pdfs:
            pdf_path = os.path.join(ROOT_DIR, PDF_PATHS[year])
            if not os.path.exists(pdf_path):
                print(f'  [FAIL] PDF not found: {pdf_path}')
                total_fail += 1
                continue
            opened_pdfs[year] = fitz.open(pdf_path)

        doc = opened_pdfs[year]
        page_idx = page_num - 1
        if page_idx < 0 or page_idx >= len(doc):
            print(f'  [FAIL] Page {page_num} out of range (doc has {len(doc)} pages)')
            total_fail += 1
            continue

        page = doc[page_idx]

        # Find option bbox
        bbox = locate_option_bbox(page, qnum)
        if bbox is None:
            print(f'  [FAIL] Cannot locate option area')
            total_fail += 1
            continue

        pts_w = bbox[2] - bbox[0]
        pts_h = bbox[3] - bbox[1]
        print(f'  bbox=[{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}]  '
              f'{pts_w:.0f}×{pts_h:.0f}pt  [{pts_h/pts_w:.2f} aspect]')

        # Load page PNG
        page_png = os.path.join(ROOT_DIR, 'assets', year, 'pages',
                                f'page_{page_num:02d}.png')
        if not os.path.exists(page_png):
            print(f'  [FAIL] Page PNG not found: {page_png}')
            total_fail += 1
            continue

        # Crop
        out_path = os.path.join(ITEM_DIR, fname)
        result = crop_and_save(page_png, bbox, out_path, padding=10)
        if result is None:
            print(f'  [FAIL] Invalid crop dimensions')
            total_fail += 1
            continue

        px_w, px_h = result
        size_kb = os.path.getsize(out_path) / 1024
        print(f'  [OK] {px_w}×{px_h}px  ({size_kb:.0f} KB)  → {fname}')
        total_ok += 1

    for doc in opened_pdfs.values():
        doc.close()

    print(f'\nDone: {total_ok} cropped, {total_fail} failed (of {len(items)} total)')


if __name__ == '__main__':
    main()