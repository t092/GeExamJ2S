#!/usr/bin/env python3
"""Evaluate Method 3: Figure cropping from page renders.
Crop figures from page PNGs using label bbox + heuristic boundary detection."""
import fitz
import os
import json
import re
from PIL import Image

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_figure_labels(page):
    """Find standalone figure/table labels and their positions."""
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
                    })
    return labels

def estimate_figure_bbox(page, label, all_text_items):
    """Estimate the figure's bbox by looking at text above the label."""
    page_w = page.rect.width
    page_h = page.rect.height
    
    label_y = label["y"]
    label_x = label["x"]
    
    # Find text items above this label (within 300px and similar x range)
    items_above = [
        t for t in all_text_items
        if t["bbox"][3] < label_y - 5
        and t["bbox"][3] > label_y - 400
    ]
    items_above.sort(key=lambda t: t["bbox"][3], reverse=True)  # closest first
    
    # Figure top = just below the closest text item above
    fig_top = 50  # default page margin
    for t in items_above:
        # Skip items that are clearly part of the figure (very small font orCID)
        if t["size"] >= 8 and not re.match(r'^[圖表]\(', t["text"]):
            fig_top = t["bbox"][3] + 3
            break
    
    # Figure bottom = label top - small gap
    fig_bottom = label_y - 2
    
    # Figure sides: use label x as center, expand to page margins
    # Labels are usually centered below the figure
    fig_left = max(45, label_x - 200)
    fig_right = min(page_w - 45, label_x + 200)
    
    # But if label is at far right, figure may be at right half
    if label_x > page_w * 0.6:
        fig_left = page_w * 0.4
        fig_right = page_w - 45
    elif label_x < page_w * 0.4:
        fig_left = 45
        fig_right = page_w * 0.6
    
    return [fig_left, fig_top, fig_right, fig_bottom]

def crop_figure(page_png_path, bbox, output_path, dpi=200):
    """Crop a region from the page render PNG."""
    # PDF coords are in points (72 dpi). Page render is at `dpi`.
    scale = dpi / 72
    
    img = Image.open(page_png_path)
    crop_box = (
        int(bbox[0] * scale),
        int(bbox[1] * scale),
        int(bbox[2] * scale),
        int(bbox[3] * scale),
    )
    
    # Validate crop box
    if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
        return None
    
    cropped = img.crop(crop_box)
    cropped.save(output_path, "WEBP", quality=85)
    return cropped.size

def main():
    out_dir = os.path.join(ROOT_DIR, 'pipeline', 'output')
    crops_dir = os.path.join(ROOT_DIR, 'assets', '114', 'crops')
    os.makedirs(crops_dir, exist_ok=True)
    
    results = {}
    pdf_path = os.path.join(ROOT_DIR, '114年國中教育會考社會科題本.pdf')
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        labels = find_figure_labels(page)
        
        if not labels:
            continue
        
        # Get all text items with positions
        all_items = []
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b["type"] == 0:
                for line in b.get("lines", []):
                    text = "".join(s["text"] for s in line.get("spans", [])).strip()
                    if text:
                        all_items.append({
                            "text": text,
                            "bbox": list(line["bbox"]),
                            "size": line["spans"][0].get("size", 10) if line["spans"] else 10,
                        })
        
        page_png = os.path.join(ROOT_DIR, 'assets', '114', 'pages', f'page_{page_num+1:02d}.png')
        
        for label in labels:
            bbox = estimate_figure_bbox(page, label, all_items)
            fig_id = label["id"].replace("(", "_").replace(")", "")
            out_path = os.path.join(crops_dir, f'{fig_id}.webp')
            
            size = crop_figure(page_png, bbox, out_path)
            
            results[label["id"]] = {
                "page": page_num + 1,
                "label_pos": [round(label["x"]), round(label["y"])],
                "crop_bbox": [round(v) for v in bbox],
                "output": f'assets/114/crops/{fig_id}.webp',
                "size": size,
            }
    
    doc.close()
    
    out = os.path.join(out_dir, 'figure_crop_eval.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'Saved -> {out}')
    print(f'Crops -> {crops_dir}')

if __name__ == '__main__':
    main()
