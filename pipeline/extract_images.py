#!/usr/bin/env python3
"""
Extract images from exam PDFs using PyMuPDF.
- Renders each page as high-res PNG for visual reference
- Extracts embedded images with bbox info
Saves to assets/<year>/

Usage: python extract_images.py
"""
import fitz
import os
import sys
import glob

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(ROOT_DIR, 'assets')

def extract_images(pdf_path, year, dpi=200):
    """Render pages as images and extract embedded images."""
    doc = fitz.open(pdf_path)
    pages = len(doc)
    year_dir = os.path.join(ASSETS_DIR, year)
    pages_dir = os.path.join(year_dir, 'pages')
    figs_dir = os.path.join(year_dir, 'figures')
    
    os.makedirs(pages_dir, exist_ok=True)
    os.makedirs(figs_dir, exist_ok=True)

    zoom = dpi / 72  # default PDF DPI is 72

    for page_num in range(pages):
        page = doc[page_num]
        
        # Render full page
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        page_path = os.path.join(pages_dir, f'page_{page_num + 1:02d}.png')
        pix.save(page_path)

        # Extract embedded images
        images = page.get_images(full=True)
        for img_idx, img_info in enumerate(images):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            img_bytes = base_image['image']
            img_ext = base_image['ext']
            
            # Get image position on page
            img_rects = page.get_image_rects(img_info)
            if img_rects:
                rect = img_rects[0]
                bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
                # Only extract if image is substantial (> 50x50 points)
                w, h = rect.width, rect.height
                if w > 50 and h > 50:
                    fig_path = os.path.join(figs_dir, f'p{page_num+1:02d}_img{img_idx+1:02d}.{img_ext}')
                    with open(fig_path, 'wb') as f:
                        f.write(img_bytes)

    doc.close()
    return pages

def main():
    pdfs = sorted(glob.glob(os.path.join(ROOT_DIR, '*年國中教育會考社會科題本.pdf')))
    
    for pdf_path in pdfs:
        basename = os.path.basename(pdf_path)
        year = basename[:3]
        
        print(f'Extracting images from {year}年...')
        pages = extract_images(pdf_path, year)
        
        pages_dir = os.path.join(ASSETS_DIR, year, 'pages')
        figs_dir = os.path.join(ASSETS_DIR, year, 'figures')
        page_count = len(os.listdir(pages_dir)) if os.path.exists(pages_dir) else 0
        fig_count = len(os.listdir(figs_dir)) if os.path.exists(figs_dir) else 0
        
        print(f'  {pages} page renders + {fig_count} embedded figures extracted')
        print(f'  -> {ASSETS_DIR}/{year}/')

if __name__ == '__main__':
    main()
