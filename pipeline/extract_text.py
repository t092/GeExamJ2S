import fitz
import sys
import os

pdf_path = sys.argv[1]
out_dir = os.path.dirname(os.path.abspath(__file__))

doc = fitz.open(pdf_path)
txt_path = os.path.join(out_dir, 'output', '114_text.txt')

with open(txt_path, 'w', encoding='utf-8') as f:
    for i in range(len(doc)):
        f.write(f'=== PAGE {i+1} ===\n')
        f.write(doc[i].get_text())
        f.write('\n')

print(f'Done. {len(doc)} pages -> {txt_path}')
doc.close()
