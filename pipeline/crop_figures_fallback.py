#!/usr/bin/env python3
"""
Fallback cropper for unmatched figures (those on the right side of the page).
Strategy: for right-side labels, crop the right-half region from the text above
to the label position.
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

def get_text_items(page):
    """Get all text line items with bbox."""
    items = []
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] == 0:
            for line in b.get("lines", []):
                text = "".join(s["text"] for s in line.get("spans", [])).strip()
                if text:
                    items.append({
                        "text": text,
                        "bbox": list(line["bbox"]),
                        "size": line["spans"][0].get("size", 10) if line["spans"] else 10,
                    })
    return items

def get_drawing_clusters(page):
    drawings = page.get_drawings()
    bboxes = []
    for d in drawings:
        rect = d.get("rect")
        if rect and rect.width > 20 and rect.height > 20:
            bboxes.append([rect.x0, rect.y0, rect.x1, rect.y1])
    if not bboxes:
        return []
    sorted_b = sorted(bboxes, key=lambda b: b[1])
    clusters = [[sorted_b[0]]]
    for b in sorted_b[1:]:
        cur = clusters[-1]
        cur_bbox = [min(c[0] for c in cur), min(c[1] for c in cur),
                    max(c[2] for c in cur), max(c[3] for c in cur)]
        if b[1] <= cur_bbox[3] + 15 and b[0] <= cur_bbox[2] + 15 and b[2] >= cur_bbox[0] - 15:
            cur.append(b)
        else:
            clusters.append([b])
    result = []
    for cluster in clusters:
        bbox = [min(c[0] for c in cluster), min(c[1] for c in cluster),
                max(c[2] for c in cluster), max(c[3] for c in cluster)]
        result.append({"bbox": bbox, "used": False})
    return result

def crop_right_side_fallback(page, label, text_items, drawings, all_labels_on_page):
    """For right-side labels, find figure boundary using text + drawings + other labels."""
    page_w = page.rect.width
    label_y = label["y"]
    label_x = label["x"]
    
    # Fixed figure column: based on drawing-crop analysis, figures span x≈325-540
    right_start = 325
    right_end = page_w - 55
    
    # Find other figure labels ABOVE this one on the same page
    labels_above = [
        l for l in all_labels_on_page
        if l["y"] < label_y - 5 and abs(l["x"] - label_x) < 150
    ]
    labels_above.sort(key=lambda l: l["y"], reverse=True)
    
    # fig_top: below previous label, or fixed height above current label
    fig_top = 50
    if labels_above:
        fig_top = labels_above[0]["y"] + 15
    else:
        # Default: figure occupies ~250pt above its label
        fig_top = max(50, label_y - 250)
    
    fig_bottom = label_y - 2
    
    return [right_start, fig_top, right_end, fig_bottom]

def crop_and_save(page_png_path, bbox, out_path, padding=8):
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
    # Load existing results
    map_path = os.path.join(OUT_DIR, 'figures_114.json')
    with open(map_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data["matched"]
    unmatched = data["unmatched"]
    
    if not unmatched:
        print('No unmatched figures to process')
        return
    
    doc = fitz.open(PDF_PATH)
    
    # Group unmatched by page
    by_page = {}
    for u in unmatched:
        by_page.setdefault(u["page"], []).append(u)
    
    for page_num, labels in by_page.items():
        page = doc[page_num - 1]
        text_items = get_text_items(page)
        drawings = get_drawing_clusters(page)
        page_png = os.path.join(PAGES_DIR, f'page_{page_num:02d}.png')
        
        # Collect ALL figure labels on this page for boundary detection
        all_labels_on_page = []
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b["type"] == 0:
                for line in b.get("lines", []):
                    text = "".join(s["text"] for s in line.get("spans", [])).strip()
                    if re.match(r'^[圖表]\(', text):
                        all_labels_on_page.append({
                            "text": text,
                            "y": line["bbox"][1],
                            "x": (line["bbox"][0] + line["bbox"][2]) / 2,
                        })
        
        for label_info in labels:
            label = {
                "id": label_info["id"],
                "num": label_info["num"],
                "y": label_info["label_pos"][1],
                "x": label_info["label_pos"][0],
            }
            bbox = crop_right_side_fallback(page, label, text_items, drawings, all_labels_on_page)
            num = label["num"]
            out_name = f'114p{num:02d}.jpg'
            out_path = os.path.join(OUT_DIR, out_name)
            size = crop_and_save(page_png, bbox, out_path)
            
            if size:
                results[label["id"]] = {
                    "num": num,
                    "page": page_num,
                    "method": "right-fallback",
                    "bbox": [round(v) for v in bbox],
                    "output": out_name,
                    "size": size,
                }
                print(f'  {label["id"]} -> {out_name} ({size[0]}x{size[1]}, right-fallback)')
    
    doc.close()
    
    # Save updated mapping
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump({
            "matched": results,
            "unmatched": [],
        }, f, ensure_ascii=False, indent=2)
    
    print(f'\nTotal matched: {len(results)}/21')

if __name__ == '__main__':
    main()
