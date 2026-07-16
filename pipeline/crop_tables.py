#!/usr/bin/env python3
"""
crop_tables.py — Unified table cropping for all years (112/113/114).

Addresses the systematic cluster-detection failure where PDF tables drawn with
segmented vertical lines get truncated.  Uses a two-pronged approach:

1. **Line-structure detection** (new, primary):
   From the 表(N) label position, trace horizontally-aligned lines downward
   to reconstruct the full table boundary.  This is far more reliable than
   clustering drawing elements.

2. **Post-crop verification** (safety net):
   After any detection method produces a crop_bbox, verify that no additional
   table H-lines exist just beyond the crop boundary.  Extend if needed.

Retains the existing 4-method fallback chain as secondary options:
   frame rects → embedded images → cluster → heuristic crop

Output:  web/pic/{year}t{NN:02d}.jpg  +  updates figures_{year}.json
"""
import fitz
import os
import re
import sys
import json
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT_DIR, 'web', 'pic')
DPI = 200

CN_DIGITS = {
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '\u3127': 1,
}


# ── utilities ────────────────────────────────────────────────────────

def chinese_to_int(cn):
    """Convert Chinese numeral to int. 一=1, 十=10, 二十一=21, etc."""
    if cn == '十':
        return 10
    if cn.startswith('十'):
        return 10 + CN_DIGITS.get(cn[1:], 0)
    if cn.endswith('十'):
        return CN_DIGITS.get(cn[0], 1) * 10
    if '十' in cn:
        parts = cn.split('十')
        return CN_DIGITS.get(parts[0], 0) * 10 + CN_DIGITS.get(parts[1], 0)
    if cn in CN_DIGITS:
        return CN_DIGITS[cn]
    try:
        return int(cn)
    except (ValueError, TypeError):
        return None


def find_table_labels(page):
    """Find all standalone 表(N) labels and their positions."""
    labels = []
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] == 0:
            for line in b.get("lines", []):
                text = "".join(s["text"] for s in line.get("spans", [])).strip()
                m = re.match(r'^表\(([一二三四五六七八九十\u3127\d]+)\)$', text)
                if m:
                    num = chinese_to_int(m.group(1))
                    if num:
                        labels.append({
                            "id": text,
                            "num": num,
                            "y": line["bbox"][1],
                            "x": (line["bbox"][0] + line["bbox"][2]) / 2,
                            "bbox": list(line["bbox"]),
                        })
    return labels


def get_page_lines(page):
    """Extract all horizontal and vertical lines from page drawings."""
    drawings = page.get_drawings()
    h_lines = []
    v_lines = []
    for d in drawings:
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                dy = abs(p1.y - p2.y)
                dx = abs(p1.x - p2.x)
                if dy < 2 and dx > 15:
                    y = (p1.y + p2.y) / 2
                    x0 = min(p1.x, p2.x)
                    x1 = max(p1.x, p2.x)
                    h_lines.append({"y": y, "x0": x0, "x1": x1, "len": dx})
                elif dx < 2 and dy > 15:
                    x = (p1.x + p2.x) / 2
                    y0 = min(p1.y, p2.y)
                    y1 = max(p1.y, p2.y)
                    v_lines.append({"x": x, "y0": y0, "y1": y1, "len": dy})
    return h_lines, v_lines


def crop_and_save(page_png, bbox, out_path, padding=4):
    """Crop a region from a page render PNG and save as JPEG."""
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
    cropped = img.crop(crop).convert("RGB")
    cropped.save(out_path, "JPEG", quality=90)
    return cropped.size


# ── Method 0 (NEW): Line-structure table detection ──────────────────

def find_column_xs(v_lines, y_top, y_bot, x_min, x_max):
    """
    Find column boundary x-positions from vertical lines within a y-range.
    Returns a sorted list of distinct x positions (the table's column separators).
    """
    col_xs = set()
    for l in v_lines:
        if (l["x"] >= x_min - 10 and l["x"] <= x_max + 10
                and l["y0"] >= y_top - 5 and l["y1"] <= y_bot + 5):
            col_xs.add(round(l["x"]))
    # Merge x positions within 5pt
    merged = []
    for x in sorted(col_xs):
        if merged and abs(x - merged[-1]) < 5:
            continue
        merged.append(x)
    return merged


def is_table_row_y(y, v_lines, col_xs, tolerance=5):
    """
    Check whether y-position has vertical lines at the known column x-positions.
    A real table row should have V-lines at ≥2 column boundaries crossing y.
    """
    if len(col_xs) < 2:
        return True  # can't verify without columns, assume ok
    matches = 0
    for cx in col_xs:
        for vl in v_lines:
            if (abs(vl["x"] - cx) < tolerance
                    and vl["y0"] <= y + 2
                    and vl["y1"] >= y - 2):
                matches += 1
                break
    return matches >= 2


def merge_h_lines(h_lines):
    """
    Group H-lines by y (within 1.5pt) and merge overlapping or adjacent segments
    on the same row level.
    """
    if not h_lines:
        return []
    groups = []
    for l in sorted(h_lines, key=lambda x: x["y"]):
        added = False
        for g in groups:
            if abs(g[0]["y"] - l["y"]) < 1.5:
                g.append(l)
                added = True
                break
        if not added:
            groups.append([l])
            
    merged = []
    for g in groups:
        g.sort(key=lambda x: x["x0"])
        row_merged = []
        for l in g:
            if not row_merged:
                row_merged.append(dict(l))
            else:
                last = row_merged[-1]
                # Merge if they overlap or have a gap of at most 5pt
                if l["x0"] - last["x1"] <= 5:
                    last["x1"] = max(last["x1"], l["x1"])
                    last["len"] = last["x1"] - last["x0"]
                else:
                    row_merged.append(dict(l))
        merged.extend(row_merged)
    return merged


def detect_table_from_lines(page, label):
    """
    Reconstruct table boundaries from horizontal + vertical line structure.

    Strategy:
    1. Merge adjacent/overlapping H-line segments at each y-coordinate (row level).
    2. Filter these merged H-lines below the label.
    3. Use V-lines to confirm table grid structure.
    4. Chase consecutive rows downward.
    """
    ly = label["y"]
    lx = label["x"]

    h_lines, v_lines = get_page_lines(page)
    merged_h = merge_h_lines(h_lines)

    # Step 1: Candidate merged H-lines below the label within 500pt
    candidates_h = [
        l for l in merged_h
        if ly - 5 <= l["y"] <= ly + 500
        and l["len"] > 50
        and abs((l["x0"] + l["x1"]) / 2 - lx) < 250
    ]
    if not candidates_h:
        return None

    # Group H-lines by y (merge within 3pt → same row)
    candidates_h.sort(key=lambda l: l["y"])
    row_ys = []
    row_x0s = []
    row_x1s = []
    for l in candidates_h:
        if row_ys and abs(l["y"] - row_ys[-1]) < 3:
            row_x0s[-1] = min(row_x0s[-1], l["x0"])
            row_x1s[-1] = max(row_x1s[-1], l["x1"])
        else:
            row_ys.append(l["y"])
            row_x0s.append(l["x0"])
            row_x1s.append(l["x1"])

    if len(row_ys) < 2:
        return None

    # Find dominant x-range (median x0, median x1)
    med_x0 = sorted(row_x0s)[len(row_x0s) // 2]
    med_x1 = sorted(row_x1s)[len(row_x1s) // 2]

    # Step 2: Filter rows that match the dominant x-range
    table_row_ys = []
    table_x0 = med_x0
    table_x1 = med_x1
    for i, y in enumerate(row_ys):
        if abs(row_x0s[i] - med_x0) < 30 and abs(row_x1s[i] - med_x1) < 30:
            table_row_ys.append(y)
            table_x0 = min(table_x0, row_x0s[i])
            table_x1 = max(table_x1, row_x1s[i])

    if len(table_row_ys) < 2:
        return None

    # Step 3: Find column x-positions from V-lines within the candidate area
    preliminary_top = table_row_ys[0]
    preliminary_bot = table_row_ys[-1]
    col_xs = find_column_xs(v_lines, preliminary_top, preliminary_bot,
                            table_x0, table_x1)

    # Step 4: Build consecutive chain, verifying each row has V-line support
    valid_chain = [table_row_ys[0]]  # first row always accepted
    for i in range(1, len(table_row_ys)):
        gap = table_row_ys[i] - valid_chain[-1]
        if gap > 80:
            # Large gap — only continue if V-lines confirm continuity
            if len(col_xs) >= 2 and is_table_row_y(
                    table_row_ys[i], v_lines, col_xs):
                valid_chain.append(table_row_ys[i])
            else:
                break
        else:
            valid_chain.append(table_row_ys[i])

    if len(valid_chain) < 2:
        return None

    # Step 5: Refine x boundaries using V-lines
    table_y_top = valid_chain[0]
    table_y_bot = valid_chain[-1]
    final_col_xs = find_column_xs(v_lines, table_y_top, table_y_bot,
                                  table_x0, table_x1)
    if final_col_xs:
        table_x0 = min(table_x0, min(final_col_xs))
        table_x1 = max(table_x1, max(final_col_xs))

    # Search for unit labels (e.g., "單位：件") directly below the table to include them
    blocks = page.get_text("dict")["blocks"]
    unit_y_max = table_y_bot
    for b in blocks:
        if b["type"] == 0:
            for line in b.get("lines", []):
                text = "".join(s["text"] for s in line.get("spans", [])).strip()
                if "單位" in text:
                    bx0, by0, bx1, by1 = line["bbox"]
                    # If it is directly below the table (within 25pt) and horizontally aligned
                    if table_y_bot <= by0 <= table_y_bot + 25:
                        if bx0 >= table_x0 - 20 and bx1 <= table_x1 + 20:
                            unit_y_max = max(unit_y_max, by1)
    if unit_y_max > table_y_bot:
        table_y_bot = unit_y_max

    crop_bbox = [
        table_x0 - 3,
        min(ly - 3, table_y_top - 10),
        table_x1 + 3,
        table_y_bot + 5,
    ]

    return {
        "label_id": label["id"],
        "label_num": label["num"],
        "bbox": [table_x0, table_y_top, table_x1, table_y_bot],
        "crop_bbox": crop_bbox,
        "method": "lines",
        "rows": len(valid_chain),
        "col_xs": final_col_xs,
    }


# ── Method 1: Frame rect detection (for tables) ────────────────────

def detect_frame_tbl(page, label):
    """Find a vector rectangle frame immediately below the table label."""
    ly = label["y"]
    lx = label["x"]

    drawings = page.get_drawings()
    rects = []
    for d in drawings:
        for item in d.get("items", []):
            if item[0] == "re":
                r = item[1]
                if r.width > 80 and r.height > 30:
                    rects.append([r.x0, r.y0, r.x1, r.y1])

    # Deduplicate
    deduped = []
    for r in rects:
        is_dup = any(
            abs(r[0] - d[0]) < 5 and abs(r[1] - d[1]) < 5
            and abs(r[2] - d[2]) < 5 and abs(r[3] - d[3]) < 5
            for d in deduped
        )
        if not is_dup:
            deduped.append(r)

    candidates = []
    for rb in deduped:
        # Frame top must be at or below the label
        if rb[1] < ly:
            continue
        if rb[1] > ly + 40:
            continue
        # Frame bottom within 500pt
        if rb[3] > ly + 500:
            continue
        # X center alignment
        if abs((rb[0] + rb[2]) / 2 - lx) > 100:
            continue
        # Not too tall (page/layout borders)
        if rb[3] - rb[1] > 400:
            continue
        candidates.append(rb)

    if not candidates:
        return None

    # Pick the closest by y and x
    candidates.sort(key=lambda c: abs((c[0] + c[2]) / 2 - lx) * 5 + (c[1] - ly))
    best = candidates[0]

    return {
        "label_id": label["id"],
        "label_num": label["num"],
        "bbox": best,
        "crop_bbox": [best[0], max(0, best[1] - 10), best[2], best[3]],
        "method": "frame",
    }


# ── Method 2: Embedded image detection (for tables) ────────────────

def detect_emb_tbl(page, label):
    """Find embedded raster images below the table label."""
    ly = label["y"]
    lx = label["x"]

    imgs = page.get_image_info()
    candidates = [
        list(i["bbox"]) for i in imgs
        if i["bbox"][2] - i["bbox"][0] > 80
        and i["bbox"][3] - i["bbox"][1] > 30
        and i["bbox"][1] >= ly
        and i["bbox"][1] <= ly + 40
        and i["bbox"][3] <= ly + 500
        and abs((i["bbox"][0] + i["bbox"][2]) / 2 - lx) < 100
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda c: abs((c[0] + c[2]) / 2 - lx) * 5 + (c[1] - ly))
    best = candidates[0]

    return {
        "label_id": label["id"],
        "label_num": label["num"],
        "bbox": best,
        "crop_bbox": [best[0], max(0, best[1] - 10), best[2], best[3]],
        "method": "embedded",
    }


# ── Method 3: Cluster detection (improved for tables) ──────────────

def detect_cluster_tbl(page, label):
    """
    Cluster drawing elements below the table label.
    Improved version with higher y-tolerance and x-center filtering.
    """
    ly = label["y"]
    lx = label["x"]
    drawings = page.get_drawings()

    bboxes = []
    for d in drawings:
        r = d.get("rect")
        if r and max(r.width, r.height) > 3:
            x_center = (r.x0 + r.x1) / 2
            if (r.x0 > 50
                and abs(x_center - lx) < 300
                and r.y0 >= ly - 10
                and r.y1 <= ly + 400):
                bboxes.append([r.x0, r.y0, r.x1, r.y1])

    if len(bboxes) < 5:
        return None

    # Sort by y, cluster with generous y-tolerance (50pt) and x-overlap (30pt)
    sorted_b = sorted(bboxes, key=lambda b: b[1])
    clusters = [[sorted_b[0]]]
    for b in sorted_b[1:]:
        cur = clusters[-1]
        cb = [
            min(c[0] for c in cur), min(c[1] for c in cur),
            max(c[2] for c in cur), max(c[3] for c in cur),
        ]
        if (b[1] <= cb[3] + 50
                and b[0] <= cb[2] + 30
                and b[2] >= cb[0] - 30):
            cur.append(b)
        else:
            clusters.append([b])

    # Score clusters: prefer close to label, penalize x offset
    best_frame = None
    best_score = -999999
    for c in clusters:
        cb = [
            min(x[0] for x in c), min(x[1] for x in c),
            max(x[2] for x in c), max(x[3] for x in c),
        ]
        w, h = cb[2] - cb[0], cb[3] - cb[1]
        if w < 50 or h < 30 or len(c) < 5:
            continue
        dist = cb[1] - ly + abs((cb[0] + cb[2]) / 2 - lx) * 0.5
        if dist > 300 or cb[1] < ly - 10:
            continue
        score = 5000 - dist * 10 + len(c)
        if score > best_score:
            best_score = score
            # Cap bottom to avoid merging unrelated content
            bot = min(cb[3], ly + 400)
            best_frame = [cb[0], cb[1], cb[2], bot]

    if best_frame is None:
        return None

    return {
        "label_id": label["id"],
        "label_num": label["num"],
        "bbox": best_frame,
        "crop_bbox": [
            best_frame[0],
            max(0, best_frame[1] - 15),
            best_frame[2],
            best_frame[3] + 5,
        ],
        "method": "cluster",
    }


# ── Method 4: Heuristic fallback crop ──────────────────────────────

def detect_crop_tbl(page, label, all_labels):
    """Heuristic fallback: estimate table area below the label."""
    ly = label["y"]
    lx = label["x"]
    page_w = page.rect.width

    # Bottom boundary: default ly + 200, constrained by next label
    fig_bottom = ly + 200
    for other in all_labels:
        if other["y"] > ly + 20 and other["y"] < fig_bottom:
            fig_bottom = other["y"] - 15

    # Left boundary: depends on label x position
    if lx > page_w * 0.4:
        left_x = 305
    else:
        left_x = 66

    crop_bbox = [left_x, ly + 5, page_w - 55, fig_bottom]

    return {
        "label_id": label["id"],
        "label_num": label["num"],
        "bbox": crop_bbox,
        "crop_bbox": crop_bbox,
        "method": "crop",
    }


# ── Post-processing: verify & extend ────────────────────────────────

def verify_and_extend(page, label, crop_result):
    """
    Post-crop verification: check if any table H-lines extend beyond
    the crop boundary.  If so, extend the crop_bbox to include them.

    Key safeguard: only extend if the candidate H-lines have matching
    vertical column separators at the table's known column x-positions.
    This prevents grabbing unrelated underlines/chart lines.
    """
    crop_bbox = list(crop_result["crop_bbox"])
    crop_x0, crop_y0, crop_x1, crop_y1 = crop_bbox

    h_lines, v_lines = get_page_lines(page)

    # Get column positions from the detection result, or from V-lines
    # within the existing crop area
    col_xs = crop_result.get("col_xs", [])
    if not col_xs:
        col_xs = find_column_xs(v_lines, crop_y0, crop_y1,
                                crop_x0, crop_x1)

    # Find H-lines just below the crop boundary that match the table
    extensions = []
    for l in h_lines:
        # x-range must closely match the table's span
        if abs(l["x0"] - crop_x0) > 30:
            continue
        if abs(l["x1"] - crop_x1) > 30:
            continue
        # Must be near or just below the crop boundary (within 100pt)
        if l["y"] < crop_y1 - 10:
            continue
        if l["y"] > crop_y1 + 100:
            continue
        # Must have vertical line support at ≥2 column positions
        if col_xs and len(col_xs) >= 2:
            if not is_table_row_y(l["y"], v_lines, col_xs, tolerance=8):
                continue
        extensions.append(l["y"])

    if extensions:
        max_y = max(extensions)
        if max_y > crop_y1 + 3:
            # Chase further: there might be more rows below
            while True:
                more = []
                for l in h_lines:
                    if abs(l["x0"] - crop_x0) > 30:
                        continue
                    if abs(l["x1"] - crop_x1) > 30:
                        continue
                    if l["y"] <= max_y:
                        continue
                    if l["y"] > max_y + 80:
                        continue
                    if col_xs and len(col_xs) >= 2:
                        if not is_table_row_y(l["y"], v_lines, col_xs, tolerance=8):
                            continue
                    more.append(l["y"])
                if more:
                    max_y = max(more)
                else:
                    break

            new_y1 = max_y + 5
            crop_result["crop_bbox"] = [crop_x0, crop_y0, crop_x1, new_y1]
            crop_result["extended"] = True
            crop_result["extended_by"] = round(new_y1 - crop_y1)

    return crop_result


# ── Main pipeline ────────────────────────────────────────────────────

def process_page(page, page_num, page_png, year, all_labels_on_page):
    """Process all table labels on a page. Returns dict of results."""
    results = {}

    for label in sorted(all_labels_on_page, key=lambda l: l["y"]):
        lid = label["id"]
        lnum = label["num"]

        # Try detection methods in priority order:
        # 0. Line-structure (new, most reliable for tables)
        # 1. Frame rect
        # 2. Embedded image
        # 3. Cluster
        # 4. Heuristic crop
        result = None

        # Method 0: Line-structure detection
        result = detect_table_from_lines(page, label)
        if result:
            method_used = "lines"
        else:
            # Method 1: Frame rect
            result = detect_frame_tbl(page, label)
            if result:
                method_used = "frame"
            else:
                # Method 2: Embedded image
                result = detect_emb_tbl(page, label)
                if result:
                    method_used = "embedded"
                else:
                    # Method 3: Cluster
                    result = detect_cluster_tbl(page, label)
                    if result:
                        method_used = "cluster"
                    else:
                        # Method 4: Heuristic fallback
                        result = detect_crop_tbl(page, label, all_labels_on_page)
                        method_used = "crop"

        if result is None:
            print(f"  ⚠ {lid} (p.{page_num + 1}): no detection method succeeded")
            continue

        # Post-processing: verify and extend
        result = verify_and_extend(page, label, result)

        # Crop and save
        out_name = f'{year}t{lnum:02d}.jpg'
        out_path = os.path.join(OUT_DIR, out_name)
        size = crop_and_save(page_png, result["crop_bbox"], out_path)

        if size:
            ext_info = ""
            if result.get("extended"):
                ext_info = f", extended +{result['extended_by']}pt"
            rows_info = ""
            if "rows" in result:
                rows_info = f", {result['rows']} rows"
            print(f"  ✓ {lid} → {out_name} ({size[0]}x{size[1]}, "
                  f"method={result['method']}{rows_info}{ext_info})")

            results[lid] = {
                "num": lnum,
                "page": page_num + 1,
                "type": "表",
                "method": result["method"],
                "frame_bbox": [round(v) for v in result["bbox"]],
                "crop_bbox": [round(v) for v in result["crop_bbox"]],
                "output": out_name,
                "size": list(size),
            }
        else:
            print(f"  ✗ {lid} (p.{page_num + 1}): crop failed (empty region)")

    return results


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    years = sys.argv[1:] if len(sys.argv) > 1 else ['112', '113', '114']

    for year in years:
        pdf_path = os.path.join(ROOT_DIR, f'{year}年國中教育會考社會科題本.pdf')
        pages_dir = os.path.join(ROOT_DIR, 'assets', year, 'pages')

        if not os.path.exists(pdf_path):
            print(f"PDF not found: {pdf_path}")
            continue
        if not os.path.exists(pages_dir):
            print(f"Page renders not found: {pages_dir}")
            continue

        doc = fitz.open(pdf_path)
        print(f"\n{'=' * 60}")
        print(f"  {year}年 表格裁切")
        print(f"{'=' * 60}")

        all_table_results = {}

        for page_num in range(len(doc)):
            page = doc[page_num]
            labels = find_table_labels(page)
            if not labels:
                continue

            page_png = os.path.join(pages_dir, f'page_{page_num + 1:02d}.png')
            if not os.path.exists(page_png):
                print(f"  ⚠ Page render not found: {page_png}")
                continue

            results = process_page(page, page_num, page_png, year, labels)
            all_table_results.update(results)

        doc.close()

        # Update figures_{year}.json — merge table results into existing data
        fig_json = os.path.join(OUT_DIR, f'figures_{year}.json')
        if os.path.exists(fig_json):
            with open(fig_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"matched": {}, "unmatched": []}

        # Replace all table entries
        for key in list(data["matched"].keys()):
            if key.startswith('表'):
                del data["matched"][key]

        data["matched"].update(all_table_results)

        with open(fig_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        n_tables = len(all_table_results)
        print(f"\n  Total: {n_tables} tables processed for {year}年")


if __name__ == '__main__':
    main()
