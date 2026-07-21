#!/usr/bin/env python3
"""
Render math exam PDF pages to PNG for visual reference and figure cropping.
Usage: python math/pipeline/extract_images.py
"""
import fitz
import os
import glob

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(ROOT_DIR, 'assets')

def extract_images(pdf_path, year, dpi=200):
    doc = fitz.open(pdf_path)
    pages = len(doc)
    year_dir = os.path.join(ASSETS_DIR, year)
    pages_dir = os.path.join(year_dir, 'pages')
    os.makedirs(pages_dir, exist_ok=True)

    zoom = dpi / 72
    for page_num in range(pages):
        page = doc[page_num]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        page_path = os.path.join(pages_dir, f'page_{page_num + 1:02d}.png')
        pix.save(page_path)

    doc.close()
    return pages

def main():
    pdfs = sorted(glob.glob(os.path.join(ROOT_DIR, '*年國中教育會考數學科題本.pdf')))
    for pdf_path in pdfs:
        basename = os.path.basename(pdf_path)
        year = basename[:3]
        print(f'Rendering {year}年 pages...')
        pages = extract_images(pdf_path, year)
        pages_dir = os.path.join(ASSETS_DIR, year, 'pages')
        page_count = len(os.listdir(pages_dir)) if os.path.exists(pages_dir) else 0
        print(f'  {pages} pages rendered -> {ASSETS_DIR}/{year}/pages/')

if __name__ == '__main__':
    main()
