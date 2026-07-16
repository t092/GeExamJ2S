#!/usr/bin/env python3
"""
Map figure/table references to the page they appear on.
Creates a mapping: figure_id -> page_number for each year.

Also detects which figure labels actually have standalone labels
vs. just inline mentions.

Output: data/<year>_figures.json
"""
import fitz
import re
import os
import glob
import json
from collections import defaultdict

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, 'data')

def find_figure_pages(pdf_path):
    """Find which page each figure/table appears on."""
    doc = fitz.open(pdf_path)
    
    # figure_id -> set of pages where it appears
    fig_pages = defaultdict(set)
    # page -> list of figure ids
    page_figs = defaultdict(list)
    
    for page_num in range(len(doc)):
        full_text = doc[page_num].get_text()
        
        # Find all standalone figure labels: 圖(一), 表(一), etc.
        # These appear as separate text blocks in the PDF
        blocks = doc[page_num].get_text("dict")["blocks"]
        for b in blocks:
            if b["type"] == 0:
                for line in b.get("lines", []):
                    text = "".join(s["text"] for s in line.get("spans", []))
                    text = text.strip()
                    
                    # Match standalone labels like "圖(一)", "圖(十六)", "表(二)"
                    m = re.match(r'^[圖表]\([一二三四五六七八九十\d]+\)$', text)
                    if m:
                        fig_id = m.group(0)
                        fig_pages[fig_id].add(page_num + 1)
        
        # Also find inline references like "...如圖(一)所示..."
        inline = re.findall(r'[圖表]\([一二三四五六七八九十\d]+\)', full_text)
        for fig_id in inline:
            fig_pages[fig_id].add(page_num + 1)
    
    doc.close()
    
    # Convert to simple mapping: figure_id -> primary page
    result = []
    for fig_id in sorted(fig_pages.keys()):
        pages = sorted(fig_pages[fig_id])
        # Primary page = most frequent or earliest
        result.append({
            "id": fig_id,
            "pages": pages,
            "primary_page": pages[0],
            "type": "圖" if fig_id.startswith("圖") else "表"
        })
    
    return result

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    for year in ['112', '113', '114']:
        pdf_path = os.path.join(ROOT_DIR, f'{year}年國中教育會考社會科題本.pdf')
        if not os.path.exists(pdf_path):
            continue
        
        figures = find_figure_pages(pdf_path)
        
        out_path = os.path.join(DATA_DIR, f'{year}_figures.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(figures, f, ensure_ascii=False, indent=2)
        
        maps = [f for f in figures if f["type"] == "圖"]
        tables = [f for f in figures if f["type"] == "表"]
        
        print(f'{year}年: {len(figures)} figures ({len(maps)} 圖, {len(tables)} 表)')
        for f in figures[:8]:
            print(f'  {f["id"]} on pages {f["pages"]}')

if __name__ == '__main__':
    main()
