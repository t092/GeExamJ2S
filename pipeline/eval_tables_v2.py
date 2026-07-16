#!/usr/bin/env python3
"""
Vector-based table parser. Uses PDF's table border lines (horizontal + vertical)
to identify table regions, then extracts text within each cell.

Strategy:
1. Find horizontal lines (table row borders) — y-coords that have lines spanning similar x-ranges
2. Find vertical lines (table column borders) — x-coords that have lines spanning similar y-ranges
3. Intersect to find table grid
4. Extract text spans within each cell
"""
import fitz
import os
import json
import re
from collections import defaultdict

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_lines(page):
    """Extract horizontal and vertical lines from vector graphics."""
    drawings = page.get_drawings()
    h_lines = []  # (y, x0, x1)
    v_lines = []  # (x, y0, y1)
    
    for d in drawings:
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 2 and abs(p2.x - p1.x) > 30:
                    h_lines.append((round(p1.y, 1), round(min(p1.x, p2.x), 1), round(max(p1.x, p2.x), 1)))
                elif abs(p1.x - p2.x) < 2 and abs(p2.y - p1.y) > 20:
                    v_lines.append((round(p1.x, 1), round(min(p1.y, p2.y), 1), round(max(p1.y, p2.y), 1)))
    
    return h_lines, v_lines

def find_table_grids(h_lines, v_lines, min_rows=3, min_cols=2):
    """Find table grids by clustering line positions.
    
    A table grid = a set of horizontal lines at similar y positions AND
    vertical lines at similar x positions, forming a rectangular region.
    """
    # Cluster horizontal lines by y position
    h_sorted = sorted(h_lines, key=lambda l: l[0])
    h_clusters = []  # list of (y, [lines])
    for line in h_sorted:
        y, x0, x1 = line
        placed = False
        for cluster in h_clusters:
            if abs(y - cluster[0]) < 5:
                cluster[2].append((x0, x1))
                # Update average y
                cluster[0] = (cluster[0] * (len(cluster[2]) - 1) + y) / len(cluster[2])
                placed = True
                break
        if not placed:
            h_clusters.append([y, line, [(x0, x1)]])
    
    # Cluster vertical lines by x position
    v_sorted = sorted(v_lines, key=lambda l: l[0])
    v_clusters = []
    for line in v_sorted:
        x, y0, y1 = line
        placed = False
        for cluster in v_clusters:
            if abs(x - cluster[0]) < 5:
                cluster[2].append((y0, y1))
                cluster[0] = (cluster[0] * (len(cluster[2]) - 1) + x) / len(cluster[2])
                placed = True
                break
        if not placed:
            v_clusters.append([x, line, [(y0, y1)]])
    
    # Find table grids: groups of h-clusters and v-clusters that form a rectangle
    # A table needs: >=3 horizontal lines (>=2 rows) and >=2 vertical lines (>=1 col separator)
    # AND the h-lines and v-lines should span a common region
    
    tables = []
    
    # Group h-clusters that share similar x-ranges (same table)
    h_groups = []
    for hc in h_clusters:
        y = hc[0]
        x_ranges = hc[2]
        x_start = min(xr[0] for xr in x_ranges)
        x_end = max(xr[1] for xr in x_ranges)
        
        placed = False
        for group in h_groups:
            # Check if this h-cluster's x-range overlaps with the group's x-range
            all_x_ranges = [xr for g in group for xr in g[2]]
            g_x_start = min(xr[0] for xr in all_x_ranges)
            g_x_end = max(xr[1] for xr in all_x_ranges)
            if (x_start >= g_x_start - 20 and x_start <= g_x_end + 20) or \
               (x_end >= g_x_start - 20 and x_end <= g_x_end + 20):
                group.append(hc)
                placed = True
                break
        if not placed:
            h_groups.append([hc])
    
    # For each h-group, find matching v-clusters
    for h_group in h_groups:
        if len(h_group) < min_rows:
            continue
        
        ys = sorted([hc[0] for hc in h_group])
        x_ranges = [xr for hc in h_group for xr in hc[2]]
        x_start = min(xr[0] for xr in x_ranges)
        x_end = max(xr[1] for xr in x_ranges)
        y_start = min(ys)
        y_end = max(ys)
        
        # Find v-clusters within this region
        matching_v = []
        for vc in v_clusters:
            x = vc[0]
            y_ranges = vc[2]
            v_y_start = min(yr[0] for yr in y_ranges)
            v_y_end = max(yr[1] for yr in y_ranges)
            
            # v-line should be within or overlapping the h-line region
            if x >= x_start - 10 and x <= x_end + 10 and \
               v_y_end >= y_start - 10 and v_y_start <= y_end + 10:
                matching_v.append(x)
        
        matching_v = sorted(set(matching_v))
        if len(matching_v) >= min_cols - 1:  # Need at least 1 internal separator for 2 cols
            # Build grid
            col_bounds = [x_start] + matching_v + [x_end]
            row_bounds = ys
            
            tables.append({
                "bbox": [x_start, y_start, x_end, y_end],
                "row_bounds": row_bounds,
                "col_bounds": col_bounds,
                "rows": len(row_bounds) - 1,
                "cols": len(col_bounds) - 1,
            })
    
    return tables

def extract_cells(page, table):
    """Extract text content within each cell of the table grid."""
    spans = []
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] == 0:
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    text = span["text"].strip()
                    if text:
                        sx = (span["bbox"][0] + span["bbox"][2]) / 2
                        sy = (span["bbox"][1] + span["bbox"][3]) / 2
                        spans.append({"text": text, "x": sx, "y": sy})
    
    cells = []
    for r in range(len(table["row_bounds"]) - 1):
        row_cells = []
        for c in range(len(table["col_bounds"]) - 1):
            x0 = table["col_bounds"][c]
            x1 = table["col_bounds"][c + 1]
            y0 = table["row_bounds"][r]
            y1 = table["row_bounds"][r + 1]
            
            # Find spans within this cell (with some tolerance)
            cell_spans = [s for s in spans 
                         if s["x"] >= x0 - 5 and s["x"] <= x1 + 5
                         and s["y"] >= y0 - 2 and s["y"] <= y1 + 2]
            
            # Sort by reading order (top-to-bottom, left-to-right)
            cell_spans.sort(key=lambda s: (s["y"], s["x"]))
            cell_text = " ".join(s["text"] for s in cell_spans)
            row_cells.append(cell_text)
        cells.append(row_cells)
    
    return cells

def main():
    out_dir = os.path.join(ROOT_DIR, 'pipeline', 'output')
    
    results = {}
    for year in ['114']:
        pdf_path = os.path.join(ROOT_DIR, f'{year}年國中教育會考社會科題本.pdf')
        if not os.path.exists(pdf_path):
            continue
        doc = fitz.open(pdf_path)
        results[year] = {}
        
        # Check all pages for tables
        for page_num in range(1, len(doc) + 1):
            page = doc[page_num - 1]
            h_lines, v_lines = get_lines(page)
            tables = find_table_grids(h_lines, v_lines)
            
            if tables:
                results[year][f'page_{page_num}'] = {
                    "tables_found": len(tables),
                    "tables": []
                }
                for t in tables:
                    cells = extract_cells(page, t)
                    results[year][f'page_{page_num}']["tables"].append({
                        "bbox": [round(v, 1) for v in t["bbox"]],
                        "rows": t["rows"],
                        "cols": t["cols"],
                        "row_bounds": [round(y, 1) for y in t["row_bounds"]],
                        "col_bounds": [round(x, 1) for x in t["col_bounds"]],
                        "cells": cells,
                    })
        doc.close()
    
    out = os.path.join(out_dir, 'vector_table_eval.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'Saved -> {out}')

if __name__ == '__main__':
    main()
