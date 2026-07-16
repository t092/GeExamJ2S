#!/usr/bin/env python3
"""Merge figure page mappings into question JSON."""
import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, 'data')

for year in ['112', '113', '114']:
    qpath = os.path.join(DATA_DIR, f'{year}.json')
    fpath = os.path.join(DATA_DIR, f'{year}_figures.json')
    
    if not os.path.exists(qpath) or not os.path.exists(fpath):
        continue
    
    with open(qpath, encoding='utf-8') as f:
        questions = json.load(f)
    with open(fpath, encoding='utf-8') as f:
        fig_map = {fi["id"]: fi for fi in json.load(f)}
    
    for q in questions:
        q["figure_pages"] = {}
        for fig_id in q.get("figures", []):
            if fig_id in fig_map:
                q["figure_pages"][fig_id] = fig_map[fig_id]["primary_page"]
    
    # Also add page numbers for each question (which page the stem text is on)
    # This requires going back to the PDF... skip for now
    
    with open(qpath, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    
    with_figs = [q for q in questions if q.get("figure_pages")]
    print(f'{year}: {len(with_figs)}/{len(questions)} questions with figure page mappings')
