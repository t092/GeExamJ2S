#!/usr/bin/env python3
"""
Extract text from math exam PDFs using PyMuPDF.
Usage: python math/pipeline/extract_all.py
"""
import fitz
import os
import glob

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')

def extract_pdf(pdf_path, txt_path):
    doc = fitz.open(pdf_path)
    pages = len(doc)
    with open(txt_path, 'w', encoding='utf-8') as f:
        for i in range(pages):
            f.write(f'=== PAGE {i + 1} ===\n')
            f.write(doc[i].get_text())
            f.write('\n')
    doc.close()
    return pages

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pdfs = sorted(glob.glob(os.path.join(ROOT_DIR, '*年國中教育會考數學科題本.pdf')))
    for pdf_path in pdfs:
        basename = os.path.basename(pdf_path)
        year = basename[:3]
        txt_path = os.path.join(OUTPUT_DIR, f'{year}_text.txt')
        if os.path.exists(txt_path):
            print(f'Skipping {year} (already exists)')
            continue
        pages = extract_pdf(pdf_path, txt_path)
        print(f'{year}年: {pages} pages -> {txt_path}')

if __name__ == '__main__':
    main()
