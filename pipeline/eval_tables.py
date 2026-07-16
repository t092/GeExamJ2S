#!/usr/bin/env python3
"""Save table parse results to JSON for inspection (avoid console encoding issues)."""
import fitz
import re
import os
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_text_spans(page):
    spans = []
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] == 0:
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    text = span["text"].strip()
                    if text:
                        spans.append({
                            "text": text,
                            "bbox": list(span["bbox"]),
                            "size": span.get("size", 10),
                            "x0": span["bbox"][0],
                            "y0": span["bbox"][1],
                            "x1": span["bbox"][2],
                            "y1": span["bbox"][3],
                        })
    return spans

def cluster_rows(spans, y_tolerance=3):
    if not spans:
        return []
    spans_sorted = sorted(spans, key=lambda s: (s["y0"], s["x0"]))
    rows = []
    current_row = [spans_sorted[0]]
    current_y = spans_sorted[0]["y0"]
    for s in spans_sorted[1:]:
        if abs(s["y0"] - current_y) <= y_tolerance:
            current_row.append(s)
        else:
            rows.append(current_row)
            current_row = [s]
            current_y = s["y0"]
    rows.append(current_row)
    return rows

def parse_table(page, page_num):
    spans = get_text_spans(page)
    rows = cluster_rows(spans)
    multi_col_rows = [r for r in rows if len(r) >= 2]
    if len(multi_col_rows) < 3:
        return None
    
    all_x0 = sorted([s["x0"] for r in multi_col_rows for s in r])
    col_boundaries = []
    if all_x0:
        current_col = [all_x0[0]]
        for x in all_x0[1:]:
            if x - current_col[-1] < 30:
                current_col.append(x)
            else:
                col_boundaries.append(sum(current_col) / len(current_col))
                current_col = [x]
        col_boundaries.append(sum(current_col) / len(current_col))
    
    table_rows = []
    for r in multi_col_rows:
        row_data = {}
        for s in r:
            min_dist = float('inf')
            nearest_col = -1
            for i, cb in enumerate(col_boundaries):
                d = abs(s["x0"] - cb)
                if d < min_dist:
                    min_dist = d
                    nearest_col = i
            if nearest_col >= 0:
                key = str(nearest_col)
                if key not in row_data:
                    row_data[key] = s["text"]
                else:
                    row_data[key] += " " + s["text"]
        if row_data:
            table_rows.append({"y": r[0]["y0"], "cells": row_data})
    
    return {
        "page": page_num,
        "col_count": len(col_boundaries),
        "col_boundaries": [round(x, 1) for x in col_boundaries],
        "rows": table_rows,
    }

def main():
    out_dir = os.path.join(ROOT_DIR, 'pipeline', 'output')
    os.makedirs(out_dir, exist_ok=True)
    
    results = {}
    for year in ['114']:
        pdf_path = os.path.join(ROOT_DIR, f'{year}年國中教育會考社會科題本.pdf')
        if not os.path.exists(pdf_path):
            continue
        doc = fitz.open(pdf_path)
        results[year] = {}
        for page_num in [4, 11, 12]:
            page = doc[page_num - 1]
            t = parse_table(page, page_num)
            if t:
                results[year][f'page_{page_num}'] = t
        doc.close()
    
    out = os.path.join(out_dir, 'table_eval.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'Saved -> {out}')

if __name__ == '__main__':
    main()
