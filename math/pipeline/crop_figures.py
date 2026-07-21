#!/usr/bin/env python3
"""
Crop individual figures and tables from math exam PDF page renders.
Math figures are vector drawings, so we render page regions at high DPI
and crop to figure bounding boxes.
Usage: python math/pipeline/crop_figures.py
"""
import fitz
import os
import re
import glob

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(ROOT_DIR, 'assets')
PIC_DIR = os.path.join(ROOT_DIR, 'pic')

DPI = 200  # matches extract_images.py

_CN_DIGITS = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
              '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, 'ㄧ': 1}

def _chinese_to_int(s: str) -> int:
    s = s.strip()
    if s.isdigit():
        return int(s)
    if s in _CN_DIGITS and s != '十':
        return _CN_DIGITS[s]
    if '十' in s:
        parts = s.split('十')
        tens = _CN_DIGITS.get(parts[0], 1) if parts[0] else 1
        ones = _CN_DIGITS.get(parts[1], 0) if parts[1] else 0
        return tens * 10 + ones
    return 0

def find_figure_regions(page, label: str) -> list[fitz.Rect]:
    """Find bounding boxes for a figure label on a page.

    Uses text blocks to distinguish standalone figure labels (captions)
    from inline references in question text.  A standalone label is in
    a small text block that contains ONLY the label text.

    Then finds nearby vector drawings to determine the figure bbox.
    """
    num_match = re.search(r'\(([一二三四五六七八九十\u3127\d\s]+)\)', label)
    if not num_match:
        return []
    num_text = num_match.group(1).strip()

    # Build search variants for the PDF text
    spaced_label = f'{label[0]}( {num_text})'
    normal_label = f'{label[0]}({num_text})'

    # Get text blocks to find standalone labels
    blocks = page.get_text('blocks')

    # Find the standalone label block (small block containing only the label)
    label_rect = None
    for b in blocks:
        bx0, by0, bx1, by1, btext, bno, btype = b
        btext_stripped = btext.strip()
        # Check if this block is essentially just the label
        if btext_stripped in (spaced_label, normal_label, label):
            label_rect = fitz.Rect(bx0, by0, bx1, by1)
            break
        # Also check if the block is very short and contains the label
        if len(btext_stripped) < 20 and label in btext_stripped.replace(' ', ''):
            label_rect = fitz.Rect(bx0, by0, bx1, by1)
            break

    # Fallback: use search_for with word-level filtering
    if label_rect is None:
        for variant in [spaced_label, normal_label]:
            found = page.search_for(variant)
            if found:
                # Filter: prefer instances in the right half of the page
                # (where figure captions typically appear)
                page_w = page.rect.width
                right_instances = [r for r in found if r.x0 > page_w * 0.4]
                if right_instances:
                    label_rect = right_instances[0]
                else:
                    label_rect = found[0]
                break

    if label_rect is None:
        return []

    # Get all drawings on the page
    drawings = page.get_drawings()

    x0, y0, x1, y1 = label_rect.x0, label_rect.y0, label_rect.x1, label_rect.y1

    # Expand search area around the label
    search_rect = fitz.Rect(
        max(0, x0 - 120),
        max(0, y0 - 200),
        min(page.rect.width, x1 + 120),
        min(page.rect.height, y1 + 30)
    )

    # Collect all drawing rects in the search area
    nearby_drawings = []
    for d in drawings:
        dr = d['rect']
        if search_rect.intersects(dr):
            nearby_drawings.append(dr)

    if nearby_drawings:
        # Union all nearby drawings
        union = nearby_drawings[0]
        for dr in nearby_drawings[1:]:
            union |= dr
        # Add the label area too
        union |= label_rect
        # Add some padding
        union = fitz.Rect(
            max(0, union.x0 - 10),
            max(0, union.y0 - 10),
            min(page.rect.width, union.x1 + 10),
            min(page.rect.height, union.y1 + 10)
        )
        return [union]
    else:
        # Fallback: expand the label bbox upward
        expanded = fitz.Rect(
            max(0, x0 - 120),
            max(0, y0 - 200),
            min(page.rect.width, x1 + 120),
            min(page.rect.height, y1 + 30)
        )
        return [expanded]


def crop_figures(pdf_path: str, year: str):
    """Crop all figures from a math exam PDF."""
    doc = fitz.open(pdf_path)
    year_dir = os.path.join(PIC_DIR)
    os.makedirs(year_dir, exist_ok=True)

    zoom = DPI / 72

    # Collect all figure/table labels from all pages.
    # The raw text has spaces like "圖( 一)" — normalize to "圖(一)".
    all_labels = set()
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        labels = re.findall(r'[圖表]\(\s*[一二三四五六七八九十\u3127\d]+\s*\)', text)
        # Normalize whitespace
        labels = {re.sub(r'\s+', '', l) for l in labels}
        all_labels.update(labels)

    print(f'Found {len(all_labels)} figure/table labels: {sorted(all_labels)}')

    # For each label, find it on its page and crop
    cropped = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        # Find labels on this page (with whitespace, then normalize)
        page_labels_raw = re.findall(r'[圖表]\(\s*[一二三四五六七八九十\u3127\d]+\s*\)', text)
        page_labels = {re.sub(r'\s+', '', l) for l in page_labels_raw}

        for label in set(page_labels):
            if label in cropped:
                continue  # already cropped

            rects = find_figure_regions(page, label)

            for i, rect in enumerate(rects):
                # Skip tiny regions
                if rect.width < 20 or rect.height < 20:
                    continue

                # Render the cropped region
                mat = fitz.Matrix(zoom, zoom)
                clip = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1)
                pix = page.get_pixmap(matrix=mat, clip=clip)

                # Generate filename
                # Convert 圖(一) to 115p01, 表(一) to 115t01
                label_type = label[0]  # 圖 or 表
                num_str = re.search(r'\(([一二三四五六七八九十\u3127\d]+)\)', label)
                if num_str:
                    num_text = num_str.group(1)
                    num = _chinese_to_int(num_text)
                    suffix = 'p' if label_type == '圖' else 't'
                    fname = f'{year}{suffix}{num:02d}.jpg'
                else:
                    fname = f'{year}_{label}_{i}.jpg'

                fpath = os.path.join(year_dir, fname)
                pix.save(fpath)
                cropped[label] = fname
                print(f'  {label} -> {fname} ({int(rect.width)}x{int(rect.height)} on p{page_num+1})')

    doc.close()
    return cropped


def main():
    pdfs = sorted(glob.glob(os.path.join(ROOT_DIR, '*年國中教育會考數學科題本.pdf')))
    for pdf_path in pdfs:
        basename = os.path.basename(pdf_path)
        year = basename[:3]
        print(f'Cropping figures from {year}年...')
        cropped = crop_figures(pdf_path, year)
        print(f'  {len(cropped)} figures cropped -> {PIC_DIR}/')

if __name__ == '__main__':
    main()
