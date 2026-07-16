#!/usr/bin/env python3
"""
Crop figures from 114年社會科題本 and save as 114pNN.jpg in web/pic/.

Naming: 圖(一) → 114p01.jpg, 圖(十) → 114p10.jpg, 圖(二十一) → 114p21.jpg
Tables (表) use same number space: 表(一) → 114t01.jpg (but here we only process 圖)

Strategy:
1. Find all 圖(N) labels in PDF with positions
2. Find vector drawing clusters on each page
3. Match each label to a unique drawing cluster above it
4. Crop from page render PNG, save as JPG
5. For unmatched labels, fall back to embedded image search or text-based estimation
"""
import fitz
import os
import json
import re
from PIL import Image

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(ROOT_DIR, '114年國中教育會考社會科題本.pdf')
PAGES_DIR = os.path.join(ROOT_DIR, 'assets', '114', 'pages')
OUT_DIR = os.path.join(ROOT_DIR, 'web', 'pic')
DPI = 200

CN_DIGITS = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}

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
    except ValueError:
        return None

def find_figure_labels(page):
    """Find standalone 圖(N) labels and their positions."""
    labels = []
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] == 0:
            for line in b.get("lines", []):
                text = "".join(s["text"] for s in line.get("spans", [])).strip()
                # Match 圖(一), 圖(十), 圖(二十一), 圖(1), etc.
                m = re.match(r'^圖\(([一二三四五六七八九十\d]+)\)$', text)
                if m:
                    num = chinese_to_int(m.group(1))
                    if num:
                        labels.append({
                            "id": text,
                            "num": num,
                            "raw_num": m.group(1),
                            "bbox": list(line["bbox"]),
                            "y": line["bbox"][1],
                            "x": (line["bbox"][0] + line["bbox"][2]) / 2,
                        })
    return labels

def get_drawing_clusters(page):
    """Get clustered vector drawing bboxes (potential figures)."""
    drawings = page.get_drawings()
    bboxes = []
    for d in drawings:
        rect = d.get("rect")
        if rect and rect.width > 20 and rect.height > 20:
            bboxes.append([rect.x0, rect.y0, rect.x1, rect.y1])
    
    if not bboxes:
        return []
    
    # Cluster nearby bboxes
    sorted_b = sorted(bboxes, key=lambda b: b[1])
    clusters = [[sorted_b[0]]]
    for b in sorted_b[1:]:
        cur = clusters[-1]
        cur_bbox = [
            min(c[0] for c in cur),
            min(c[1] for c in cur),
            max(c[2] for c in cur),
            max(c[3] for c in cur),
        ]
        if (b[1] <= cur_bbox[3] + 15 and
            b[0] <= cur_bbox[2] + 15 and
            b[2] >= cur_bbox[0] - 15):
            cur.append(b)
        else:
            clusters.append([b])
    
    result = []
    for cluster in clusters:
        bbox = [
            min(c[0] for c in cluster),
            min(c[1] for c in cluster),
            max(c[2] for c in cluster),
            max(c[3] for c in cluster),
        ]
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        # Filter: figures should be at least 50x50 points
        if w >= 50 and h >= 50:
            result.append({"bbox": bbox, "w": w, "h": h, "used": False})
    return result

def match_labels_to_clusters(labels, clusters):
    """Match each label to a unique cluster above it. Returns {label_id: bbox}."""
    matches = {}
    for label in sorted(labels, key=lambda l: l["y"]):
        label_y = label["y"]
        label_x = label["x"]
        
        candidates = []
        for i, c in enumerate(clusters):
            if c["used"]:
                continue
            cb = c["bbox"]
            # Cluster should be above the label
            if cb[3] <= label_y + 5 and cb[1] >= label_y - 500:
                # X overlap with label
                if cb[0] <= label_x + 80 and cb[2] >= label_x - 80:
                    dist = label_y - cb[3]
                    # Prefer clusters with good x-center alignment
                    x_center = (cb[0] + cb[2]) / 2
                    x_offset = abs(x_center - label_x)
                    candidates.append({"idx": i, "dist": dist, "x_offset": x_offset, "bbox": cb})
        
        if candidates:
            # Pick closest with reasonable x alignment
            candidates.sort(key=lambda c: (c["dist"] + c["x_offset"] * 0.5))
            best = candidates[0]
            clusters[best["idx"]]["used"] = True
            matches[label["id"]] = best["bbox"]
    
    return matches

def find_embedded_images(page):
    """Find embedded raster images with bbox."""
    images = []
    for img in page.get_image_info():
        bbox = img["bbox"]
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w > 50 and h > 50:
            images.append({"bbox": list(bbox), "w": w, "h": h})
    return images

def match_labels_to_images(unmatched_labels, images):
    """For labels without drawing cluster, try embedded images."""
    matches = {}
    used_imgs = set()
    for label in sorted(unmatched_labels, key=lambda l: l["y"]):
        label_y = label["y"]
        label_x = label["x"]
        
        candidates = []
        for i, img in enumerate(images):
            if i in used_imgs:
                continue
            ib = img["bbox"]
            if ib[3] <= label_y + 5 and ib[1] >= label_y - 500:
                if ib[0] <= label_x + 80 and ib[2] >= label_x - 80:
                    dist = label_y - ib[3]
                    candidates.append({"idx": i, "dist": dist, "bbox": ib})
        
        if candidates:
            candidates.sort(key=lambda c: c["dist"])
            best = candidates[0]
            used_imgs.add(best["idx"])
            matches[label["id"]] = best["bbox"]
    
    return matches

def crop_and_save(page_png_path, bbox, out_path, padding=8):
    """Crop bbox from page PNG, save as JPG."""
    scale = DPI / 72
    img = Image.open(page_png_path)
    crop_box = (
        max(0, int((bbox[0] - padding) * scale)),
        max(0, int((bbox[1] - padding) * scale)),
        min(img.width, int((bbox[2] + padding) * scale)),
        min(img.height, int((bbox[3] + padding) * scale)),
    )
    if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
        return None
    cropped = img.crop(crop_box).convert("RGB")
    cropped.save(out_path, "JPEG", quality=90)
    return cropped.size

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    doc = fitz.open(PDF_PATH)
    
    all_labels = []
    page_data = {}
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        labels = find_figure_labels(page)
        if labels:
            clusters = get_drawing_clusters(page)
            images = find_embedded_images(page)
            page_data[page_num] = {
                "labels": labels,
                "clusters": clusters,
                "images": images,
                "png": os.path.join(PAGES_DIR, f'page_{page_num+1:02d}.png'),
            }
            all_labels.extend([(page_num, l) for l in labels])
    
    print(f'Found {len(all_labels)} 圖 labels across {len(page_data)} pages')
    
    results = {}
    
    # Phase 1: match via drawing clusters
    for page_num, data in page_data.items():
        labels = data["labels"]
        clusters = data["clusters"]
        matches = match_labels_to_clusters(labels, clusters)
        
        for label in labels:
            if label["id"] in matches:
                bbox = matches[label["id"]]
                num = label["num"]
                out_name = f'114p{num:02d}.jpg'
                out_path = os.path.join(OUT_DIR, out_name)
                size = crop_and_save(data["png"], bbox, out_path)
                if size:
                    results[label["id"]] = {
                        "num": num,
                        "page": page_num + 1,
                        "method": "drawing",
                        "bbox": [round(v) for v in bbox],
                        "output": out_name,
                        "size": size,
                    }
    
    # Phase 2: unmatched labels try embedded images
    for page_num, data in page_data.items():
        unmatched = [l for l in data["labels"] if l["id"] not in results]
        if not unmatched:
            continue
        matches = match_labels_to_images(unmatched, data["images"])
        for label in unmatched:
            if label["id"] in matches:
                bbox = matches[label["id"]]
                num = label["num"]
                out_name = f'114p{num:02d}.jpg'
                out_path = os.path.join(OUT_DIR, out_name)
                size = crop_and_save(data["png"], bbox, out_path)
                if size:
                    results[label["id"]] = {
                        "num": num,
                        "page": page_num + 1,
                        "method": "embedded",
                        "bbox": [round(v) for v in bbox],
                        "output": out_name,
                        "size": size,
                    }
    
    # Phase 3: still unmatched — record for manual handling
    still_unmatched = []
    for page_num, data in page_data.items():
        for label in data["labels"]:
            if label["id"] not in results:
                still_unmatched.append({
                    "id": label["id"],
                    "num": label["num"],
                    "page": page_num + 1,
                    "label_pos": [round(label["x"]), round(label["y"])],
                })
    
    doc.close()
    
    # Save mapping JSON
    map_path = os.path.join(OUT_DIR, 'figures_114.json')
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump({
            "matched": results,
            "unmatched": still_unmatched,
        }, f, ensure_ascii=False, indent=2)
    
    print(f'\nMatched: {len(results)}/{len(all_labels)}')
    print(f'Unmatched: {len(still_unmatched)}')
    if still_unmatched:
        print('\nUnmatched figures (need manual review):')
        for u in still_unmatched:
            print(f'  {u["id"]} (page {u["page"]})')
    
    print(f'\nOutput -> {OUT_DIR}')
    for fid, info in sorted(results.items(), key=lambda x: x[1]["num"]):
        print(f'  {fid} -> {info["output"]} ({info["size"][0]}x{info["size"][1]}, {info["method"]})')

if __name__ == '__main__':
    main()
