#!/usr/bin/env python3
"""Analyze figure references and image positions in PDF for auto-linking."""
import fitz
import re
import os
import glob
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def analyze_page(doc, page_num):
    """Extract text blocks and image positions from a page."""
    page = doc[page_num]
    
    # Get text blocks with positions
    blocks = page.get_text("dict")["blocks"]
    text_blocks = []
    for b in blocks:
        if b["type"] == 0:  # text block
            for line in b.get("lines", []):
                text = ""
                for span in line.get("spans", []):
                    text += span["text"]
                if text.strip():
                    text_blocks.append({
                        "text": text.strip(),
                        "bbox": list(line["bbox"]),
                        "font": line["spans"][0].get("font", "") if line["spans"] else ""
                    })
    
    # Get image positions
    images = page.get_image_info()
    
    # Find figure/table labels
    fig_refs = []
    for tb in text_blocks:
        if re.search(r'[圖表]\([一二三四五六七八九十\d]+\)', tb["text"]):
            fig_refs.append(tb)
    
    return text_blocks, images, fig_refs

def find_figure_images(page_num, fig_refs, images):
    """Match figure references to nearby images by vertical proximity."""
    matches = []
    for ref in fig_refs:
        ref_y = ref["bbox"][1]  # top of figure label
        ref_x = ref["bbox"][0]
        
        # Figure labels are usually BELOW the actual figure
        # Look for images that are above this label
        candidates = []
        for img in images:
            img_y1 = img["bbox"][3]  # bottom of image
            img_x0 = img["bbox"][0]
            img_x1 = img["bbox"][2]
            
            # Image should be above or overlapping the label, within reasonable distance
            vertical_dist = ref_y - img_y1
            if 0 < vertical_dist < 200 and abs(ref_x - img_x0) < 100:
                candidates.append({
                    "bbox": img["bbox"],
                    "size": (img["bbox"][2] - img["bbox"][0]) * (img["bbox"][3] - img["bbox"][1]),
                    "dist": vertical_dist
                })
        
        if candidates:
            # Pick the largest/closest
            best = min(candidates, key=lambda c: c["dist"])
            matches.append({
                "label": ref["text"],
                "label_pos": ref["bbox"],
                "image_bbox": best["bbox"]
            })
    
    return matches

def main():
    for year in ['112', '113', '114']:
        pdf_path = os.path.join(ROOT_DIR, f'{year}年國中教育會考社會科題本.pdf')
        if not os.path.exists(pdf_path):
            continue
            
        doc = fitz.open(pdf_path)
        print(f'\n{"="*60}')
        print(f'{year}年: {len(doc)} pages')
        
        for page_num in range(len(doc)):
            text_blocks, images, fig_refs = analyze_page(doc, page_num)
            matches = find_figure_images(page_num, fig_refs, images)
            
            if fig_refs or images:
                page = doc[page_num]
                page_size = page.rect
                
                print(f'\n  Page {page_num+1}: {len(images)} images, {len(fig_refs)} fig labels')
                for f in fig_refs[:5]:
                    print(f'    Label: "{f["text"]}" at ({f["bbox"][0]:.0f}, {f["bbox"][1]:.0f})')
                for m in matches[:5]:
                    print(f'    Match: {m["label"]} -> image at {[f"{v:.0f}" for v in m["image_bbox"]]}')
                
                # Show orphan images (not matched)
                matched_bboxes = {tuple(m["image_bbox"]) for m in matches}
                orphans = [img for img in images if tuple(img["bbox"]) not in matched_bboxes]
                if orphans and len(orphans) <= 3:
                    for o in orphans:
                        print(f'    Orphan image: {[f"{v:.0f}" for v in o["bbox"]]}')

        doc.close()

if __name__ == '__main__':
    main()
