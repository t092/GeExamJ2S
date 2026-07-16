#!/usr/bin/env python3
"""Evaluate Method 3 v2: Figure cropping using vector drawings.
Use page.get_drawings() to find the actual figure area (non-text graphics)."""
import fitz
import os
import json
import re
from PIL import Image

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_figure_labels(page):
    labels = []
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] == 0:
            for line in b.get("lines", []):
                text = "".join(s["text"] for s in line.get("spans", [])).strip()
                m = re.match(r'^[圖表]\(([一二三四五六七八九十\d]+)\)$', text)
                if m:
                    labels.append({
                        "id": text,
                        "bbox": list(line["bbox"]),
                        "y": line["bbox"][1],
                        "x": line["bbox"][0],
                        "x_center": (line["bbox"][0] + line["bbox"][2]) / 2,
                    })
    return labels

def get_drawings_bbox(page):
    """Get bounding boxes of all vector drawings (non-text graphics)."""
    drawings = page.get_drawings()
    bboxes = []
    for d in drawings:
        rect = d.get("rect")
        if rect:
            # Filter out tiny drawings (likely text underscores or dots)
            if rect.width > 20 and rect.height > 20:
                bboxes.append({
                    "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                    "w": rect.width,
                    "h": rect.height,
                })
    return bboxes

def cluster_drawings(drawings_bboxes, tolerance=10):
    """Cluster nearby drawing bboxes into groups (each group = one figure)."""
    if not drawings_bboxes:
        return []
    
    # Sort by y position
    sorted_d = sorted(drawings_bboxes, key=lambda d: d["bbox"][1])
    
    clusters = []
    current = [sorted_d[0]]
    
    for d in sorted_d[1:]:
        # Check if this drawing is close to the current cluster
        cluster_bbox = [
            min(c["bbox"][0] for c in current),
            min(c["bbox"][1] for c in current),
            max(c["bbox"][2] for c in current),
            max(c["bbox"][3] for c in current),
        ]
        
        # If drawing overlaps or is near the cluster, add it
        if (d["bbox"][1] <= cluster_bbox[3] + tolerance and
            d["bbox"][0] <= cluster_bbox[2] + tolerance and
            d["bbox"][2] >= cluster_bbox[0] - tolerance):
            current.append(d)
        else:
            clusters.append(current)
            current = [d]
    
    clusters.append(current)
    
    # Convert each cluster to a merged bbox
    result = []
    for cluster in clusters:
        bbox = [
            min(c["bbox"][0] for c in cluster),
            min(c["bbox"][1] for c in cluster),
            max(c["bbox"][2] for c in cluster),
            max(c["bbox"][3] for c in cluster),
        ]
        result.append({
            "bbox": bbox,
            "w": bbox[2] - bbox[0],
            "h": bbox[3] - bbox[1],
            "count": len(cluster),
        })
    
    return result

def match_label_to_drawing(label, drawing_clusters):
    """Match a figure label to the nearest drawing cluster above it."""
    label_y = label["y"]
    label_x = label["x_center"]
    
    candidates = []
    for dc in drawing_clusters:
        dbbox = dc["bbox"]
        # Drawing should be ABOVE the label (with some tolerance)
        if dbbox[3] <= label_y + 5 and dbbox[1] >= label_y - 400:
            # Check x overlap or proximity
            if dbbox[0] <= label_x + 50 and dbbox[2] >= label_x - 50:
                # Distance from label to drawing bottom
                dist = label_y - dbbox[3]
                candidates.append({"dist": dist, "bbox": dbbox, "cluster": dc})
    
    if candidates:
        # Pick the closest one
        candidates.sort(key=lambda c: c["dist"])
        return candidates[0]["bbox"], candidates[0]["cluster"]
    return None, None

def crop_figure(page_png_path, bbox, output_path, dpi=200, padding=5):
    scale = dpi / 72
    img = Image.open(page_png_path)
    crop_box = (
        max(0, int((bbox[0] - padding) * scale)),
        max(0, int((bbox[1] - padding) * scale)),
        min(img.width, int((bbox[2] + padding) * scale)),
        min(img.height, int((bbox[3] + padding) * scale)),
    )
    if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
        return None
    cropped = img.crop(crop_box)
    cropped.save(output_path, "WEBP", quality=85)
    return cropped.size

def main():
    out_dir = os.path.join(ROOT_DIR, 'pipeline', 'output')
    crops_dir = os.path.join(ROOT_DIR, 'assets', '114', 'crops_v2')
    os.makedirs(crops_dir, exist_ok=True)
    
    results = {}
    pdf_path = os.path.join(ROOT_DIR, '114年國中教育會考社會科題本.pdf')
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        labels = find_figure_labels(page)
        if not labels:
            continue
        
        drawings = get_drawings_bbox(page)
        clusters = cluster_drawings(drawings)
        
        page_png = os.path.join(ROOT_DIR, 'assets', '114', 'pages', f'page_{page_num+1:02d}.png')
        
        for label in labels:
            bbox, cluster = match_label_to_drawing(label, clusters)
            fig_id = label["id"].replace("(", "_").replace(")", "")
            
            if bbox:
                out_path = os.path.join(crops_dir, f'{fig_id}.webp')
                size = crop_figure(page_png, bbox, out_path)
                
                results[label["id"]] = {
                    "page": page_num + 1,
                    "label_pos": [round(label["x"]), round(label["y"])],
                    "drawing_bbox": [round(v) for v in bbox],
                    "drawing_count": cluster["count"],
                    "output": f'assets/114/crops_v2/{fig_id}.webp',
                    "size": size,
                }
            else:
                results[label["id"]] = {
                    "page": page_num + 1,
                    "label_pos": [round(label["x"]), round(label["y"])],
                    "error": "no matching drawing found",
                }
    
    doc.close()
    
    out = os.path.join(out_dir, 'figure_crop_v2_eval.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    matched = sum(1 for r in results.values() if "error" not in r)
    print(f'Saved -> {out}')
    print(f'Matched: {matched}/{len(results)} figures')
    print(f'Crops -> {crops_dir}')

if __name__ == '__main__':
    main()
