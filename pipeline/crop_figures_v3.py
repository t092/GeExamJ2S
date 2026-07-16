#!/usr/bin/env python3
"""
V3: Frame-based figure cropping.
Uses PDF vector rectangles ('re' items) as figure frame boundaries.
Principle: each 圖(N) has its own frame box. Gaps between frames = separate figures.
"""
import fitz
import os
import re
import json
from PIL import Image

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(ROOT_DIR, '114年國中教育會考社會科題本.pdf')
PAGES_DIR = os.path.join(ROOT_DIR, 'assets', '114', 'pages')
OUT_DIR = os.path.join(ROOT_DIR, 'web', 'pic')
DPI = 200

CN_DIGITS = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}

def chinese_to_int(cn):
    if cn == '十': return 10
    if cn.startswith('十'): return 10 + CN_DIGITS.get(cn[1:], 0)
    if cn.endswith('十'): return CN_DIGITS.get(cn[0], 1) * 10
    if '十' in cn:
        parts = cn.split('十')
        return CN_DIGITS.get(parts[0], 0) * 10 + CN_DIGITS.get(parts[1], 0)
    if cn in CN_DIGITS: return CN_DIGITS[cn]
    try: return int(cn)
    except: return None

def get_frame_rects(page):
    """Get all rectangular frames from vector drawings.
    Deduplicates overlapping rects (fill+stroke layers at same position)."""
    drawings = page.get_drawings()
    rects = []
    for d in drawings:
        for item in d.get("items", []):
            if item[0] == "re":
                r = item[1]
                w, h = r.width, r.height
                if w > 80 and h > 50:
                    rects.append({
                        "bbox": [r.x0, r.y0, r.x1, r.y1],
                        "w": w, "h": h,
                    })
    
    # Deduplicate overlapping rects (same position within 5pt tolerance)
    deduped = []
    for r in rects:
        is_dup = False
        for d in deduped:
            if (abs(r["bbox"][0] - d["bbox"][0]) < 5 and
                abs(r["bbox"][1] - d["bbox"][1]) < 5 and
                abs(r["bbox"][2] - d["bbox"][2]) < 5 and
                abs(r["bbox"][3] - d["bbox"][3]) < 5):
                is_dup = True
                break
        if not is_dup:
            deduped.append(r)
    
    return deduped

def get_h_v_lines(page):
    """Get all horizontal and vertical lines with significant length."""
    drawings = page.get_drawings()
    h_lines = []
    v_lines = []
    for d in drawings:
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                dy, dx = abs(p1.y - p2.y), abs(p1.x - p2.x)
                if dy < 2 and dx > 50:
                    h_lines.append(((p1.y + p2.y) / 2, min(p1.x, p2.x), max(p1.x, p2.x)))
                elif dx < 2 and dy > 30:
                    v_lines.append(((p1.x + p2.x) / 2, min(p1.y, p2.y), max(p1.y, p2.y)))
    return h_lines, v_lines

def find_figure_labels(page):
    """Find all 圖(N) standalone labels."""
    labels = []
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] == 0:
            for line in b.get("lines", []):
                text = "".join(s["text"] for s in line.get("spans", [])).strip()
                m = re.match(r'^圖\(([一二三四五六七八九十\d]+)\)$', text)
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

def detect_frames_from_lines(page, labels):
    """Use horizontal & vertical lines to find figure frame boundaries.
    This is more robust than relying on 're' items alone."""
    h_lines, v_lines = get_h_v_lines(page)
    
    if not h_lines or not v_lines:
        return None
    
    # Group h-lines by y position
    h_sorted = sorted(h_lines, key=lambda l: l[0])
    h_clusters = []
    current = [h_sorted[0]]
    for l in h_sorted[1:]:
        if abs(l[0] - current[-1][0]) < 5:
            current.append(l)
        else:
            h_clusters.append(sum(c[0] for c in current) / len(current))
            current = [l]
    h_clusters.append(sum(c[0] for c in current) / len(current))
    
    # Group v-lines by x position
    v_sorted = sorted(v_lines, key=lambda l: l[0])
    v_clusters = []
    current = [v_sorted[0]]
    for l in v_sorted[1:]:
        if abs(l[0] - current[-1][0]) < 5:
            current.append(l)
        else:
            v_clusters.append(sum(c[0] for c in current) / len(current))
            current = [l]
    v_clusters.append(sum(c[0] for c in current) / len(current))
    
    # For each label, find the nearest frame (h-lines above and below, v-lines left and right)
    frames = []
    for label in labels:
        ly = label["y"]
        lx = label["x"]
        
        # Find h-lines above label (frame top + bottom)
        h_above = [y for y in h_clusters if y < ly]
        # Find v-lines near label (frame left + right)
        v_near = [x for x in v_clusters if abs(x - lx) < 200]
        
        if len(h_above) >= 2 and len(v_near) >= 2:
            h_above.sort(reverse=True)
            frame_bottom = h_above[0]  # closest h-line above = frame bottom
            frame_top = h_above[1]     # next h-line above = frame top
            v_near.sort()
            frame_left = v_near[0]      # leftmost near v-line
            frame_right = v_near[-1]    # rightmost near v-line
            
            frames.append({
                "label_id": label["id"],
                "label_num": label["num"],
                "bbox": [frame_left, frame_top, frame_right, frame_bottom],
                # Extended crop: frame + label below
                "crop_bbox": [frame_left, frame_top, frame_right, ly + 15],
            })
    
    return frames

def detect_frames_from_rects(page, labels):
    """Use 're' rectangle items as figure frames."""
    rects = get_frame_rects(page)
    if not rects:
        return None
    
    frames = []
    used = set()
    for label in sorted(labels, key=lambda l: l["y"]):
        ly = label["y"]
        lx = label["x"]
        
        # Find closest rectangle above or around the label
        candidates = []
        for i, r in enumerate(rects):
            if i in used:
                continue
            rb = r["bbox"]
            # Rectangle should be above or overlapping the label
            if rb[3] <= ly + 20 and rb[1] >= ly - 500:
                # X overlap with label
                if rb[0] <= lx + 80 and rb[2] >= lx - 80:
                    dist = ly - rb[3]
                    candidates.append({"idx": i, "bbox": rb, "dist": dist})
        
        if candidates:
            # Filter out oversized rectangles (>400pt tall = likely page/layout border)
            good = [c for c in candidates if c["bbox"][3] - c["bbox"][1] < 400]
            if good:
                # Prefer x-aligned rect 
                good.sort(key=lambda c: abs((c["bbox"][0] + c["bbox"][2]) / 2 - lx) * 5 + c["dist"])
                best = good[0]
            else:
                # All candidates are oversized — skip rect method for this label
                continue
            used.add(best["idx"])
            
            frames.append({
                "label_id": label["id"],
                "label_num": label["num"],
                "bbox": best["bbox"],
                "crop_bbox": [best["bbox"][0], best["bbox"][1], best["bbox"][2], ly + 15],
                "method": "frame",
            })
    
    return frames

def crop_and_save(page_png, bbox, out_path, padding=4):
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

def detect_frames_from_embedded(page, labels):
    """Try embedded raster images as figure boundaries."""
    imgs = page.get_image_info()
    candidates = [{
        "bbox": list(i["bbox"]),
        "w": i["bbox"][2] - i["bbox"][0],
        "h": i["bbox"][3] - i["bbox"][1],
    } for i in imgs if i["bbox"][2] - i["bbox"][0] > 80 and i["bbox"][3] - i["bbox"][1] > 50]
    
    if not candidates:
        return None
    
    frames = []
    used = set()
    for label in sorted(labels, key=lambda l: l["y"]):
        ly = label["y"]
        lx = label["x"]
        
        best_idx = -1
        best_dist = float('inf')
        for i, img in enumerate(candidates):
            if i in used:
                continue
            ib = img["bbox"]
            if ib[3] <= ly + 20 and ib[1] >= ly - 500:
                x_off = abs((ib[0] + ib[2]) / 2 - lx)
                dist = ly - ib[3]
                score = x_off * 5 + dist
                if score < best_dist:
                    best_dist = score
                    best_idx = i
        
        if best_idx >= 0:
            used.add(best_idx)
            ib = candidates[best_idx]["bbox"]
            frames.append({
                "label_id": label["id"],
                "label_num": label["num"],
                "bbox": ib,
                "crop_bbox": [ib[0], ib[1], ib[2], ly + 15],
                "method": "embedded",
            })
    
    return frames if frames else None

def detect_frames_from_crop(page, labels):
    """Heuristic fallback: crop right-side area between labels.
    Uses drawings to estimate figure top position."""
    page_w = page.rect.width
    drawings = page.get_drawings()
    
    # Find all figure labels for boundary detection
    all_labels = []
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] == 0:
            for line in b.get("lines", []):
                text = "".join(s["text"] for s in line.get("spans", [])).strip()
                if re.match(r'^[圖表]\(', text):
                    all_labels.append((line["bbox"][1], (line["bbox"][0] + line["bbox"][2]) / 2))
    all_labels.sort(key=lambda l: l[0])
    
    frames = []
    for label in labels:
        ly = label["y"]
        
        # Find label above this one for lower bound
        fig_top = 50
        for ay, ax in all_labels:
            if ay < ly - 10 and abs(ax - label["x"]) < 200:
                fig_top = ay + 15
        
        # Refine fig_top using drawings: find topmost drawing in right half above label
        right_drawings = []
        for d in drawings:
            r = d.get("rect")
            if r and r.width > 10 and r.height > 10:
                if r.x0 > 310 and r.y0 >= fig_top and r.y1 <= ly:
                    right_drawings.append(r.y0)
        
        if right_drawings:
            drawing_top = min(right_drawings)
            # Only use if it's not too far from fig_top
            if drawing_top > fig_top:
                fig_top = max(fig_top, drawing_top - 10)
        
        # If no label above, use reasonable height
        if fig_top == 50:
            fig_top = max(50, ly - 250)
        
        frames.append({
            "label_id": label["id"], "label_num": label["num"],
            "bbox": [325, fig_top, page_w - 55, ly - 2],
            "crop_bbox": [325, fig_top, page_w - 55, ly + 15],
            "method": "crop",
        })
    
    return frames

def detect_frames_from_clusters(page, labels):
    """Label-driven clustering: for each label, cluster nearby drawings."""
    drawings = page.get_drawings()
    
    frames = []
    for label in sorted(labels, key=lambda l: l["y"]):
        ly = label["y"]
        
        bboxes = []
        for d in drawings:
            r = d.get("rect")
            if r and r.width > 5 and r.height > 5:
                if r.x0 > 310 and r.y1 <= ly + 10 and r.y0 >= ly - 300:
                    bboxes.append([r.x0, r.y0, r.x1, r.y1])
        
        if len(bboxes) < 10:
            continue
        
        sorted_b = sorted(bboxes, key=lambda b: b[1])
        clusters = [[sorted_b[0]]]
        for b in sorted_b[1:]:
            cur = clusters[-1]
            cb = [min(c[0] for c in cur), min(c[1] for c in cur),
                  max(c[2] for c in cur), max(c[3] for c in cur)]
            if (b[1] <= cb[3] + 10 and b[0] <= cb[2] + 10 and b[2] >= cb[0] - 10):
                cur.append(b)
            else:
                clusters.append([b])
        
        best_cb = None
        best_n = 0
        for c in clusters:
            cb = [min(x[0] for x in c), min(x[1] for x in c),
                  max(x[2] for x in c), max(x[3] for x in c)]
            w, h = cb[2] - cb[0], cb[3] - cb[1]
            if len(c) > best_n and w > 50 and h > 50 and len(c) > 10:
                best_n = len(c)
                best_cb = cb
        
        if best_cb:
            frames.append({
                "label_id": label["id"], "label_num": label["num"],
                "bbox": best_cb,
                "crop_bbox": [best_cb[0], best_cb[1], best_cb[2], ly + 15],
                "method": "cluster",
            })
    
    return frames if frames else None

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    doc = fitz.open(PDF_PATH)
    
    all_results = {}
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        labels = find_figure_labels(page)
        if not labels:
            continue
        
        page_png = os.path.join(PAGES_DIR, f'page_{page_num+1:02d}.png')
        
        # Collect all possible frames: rect-based + embedded-based
        all_frames = []
        
        rect_frames = detect_frames_from_rects(page, labels) or []
        all_frames.extend(rect_frames)
        
        emb_frames = detect_frames_from_embedded(page, labels) or []
        all_frames.extend(emb_frames)
        
        clu_frames = detect_frames_from_clusters(page, labels) or []
        all_frames.extend(clu_frames)
        
        # For each label, pick the best frame by method priority + proximity
        # Priority: frame > embedded > cluster > crop
        method_rank = {"frame": 0, "embedded": 1, "cluster": 2, "crop": 3}
        label_best = {}
        for f in all_frames:
            lid = f["label_id"]
            method = f.get("method", "crop")
            rank = method_rank.get(method, 3)
            crop_h = f["crop_bbox"][3] - f["crop_bbox"][1]
            if lid not in label_best:
                label_best[lid] = (f, crop_h, rank)
            elif rank < label_best[lid][2]:
                label_best[lid] = (f, crop_h, rank)
            elif rank == label_best[lid][2] and crop_h < label_best[lid][1]:
                label_best[lid] = (f, crop_h, rank)
        
        # For labels without any match, use heuristic fallback
        missing = [l for l in labels if l["id"] not in label_best]
        if missing:
            crop_frames = detect_frames_from_crop(page, missing) or []
            for f in crop_frames:
                lid = f["label_id"]
                rank = 3
                crop_h = f["crop_bbox"][3] - f["crop_bbox"][1]
                if lid not in label_best or rank < label_best[lid][2]:
                    label_best[lid] = (f, crop_h, rank)
        
        # Save all best frames
        for lid, (f, _, _) in label_best.items():
            num = f["label_num"]
            method = f.get("method", "frame")
            out_name = f'114p{num:02d}.jpg'
            out_path = os.path.join(OUT_DIR, out_name)
            size = crop_and_save(page_png, f["crop_bbox"], out_path)
            if size:
                all_results[lid] = {
                    "num": num, "page": page_num + 1, "method": method,
                    "frame_bbox": [round(v) for v in f["bbox"]],
                    "crop_bbox": [round(v) for v in f["crop_bbox"]],
                    "output": out_name, "size": size,
                }
        
        for l in labels:
            if l["id"] not in all_results:
                print(f'  * unmatched: {l["id"]} (page {page_num+1}, y={l["y"]:.0f})')
    
    doc.close()
    
    # Save mapping
    map_path = os.path.join(OUT_DIR, 'figures_114.json')
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump({"matched": all_results, "unmatched": []}, f, ensure_ascii=False, indent=2)
    
    print(f'\nTotal: {len(all_results)}/21 figures')
    print(f'Methods: {sum(1 for r in all_results.values() if r["method"]=="frame")} frame-rect, {sum(1 for r in all_results.values() if r["method"]=="line")} line-based')

if __name__ == '__main__':
    main()
