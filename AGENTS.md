# AGENTS.md — JHexam

國中教育會考社會科題庫與線上測驗系統。

## Project structure

```
JHexam/
├── pipeline/              # PDF → JSON extraction (Python)
│   ├── extract_all.py     # PyMuPDF text extraction, all 3 years
│   ├── parse_questions.py # Regex-based question parser → data/*.json (V4)
│   ├── extract_images.py  # PyMuPDF page renders + embedded images → assets/
│   ├── check_groups.py    # V4 verification: group-passage & option quality
│   └── output/            # Extracted raw text (*_text.txt)
├── data/                  # Structured question bank (JSON, 1 file/year)
├── assets/                # Images: page renders + figures per year
│   └── <year>/pages/figures/
├── web/                   # Static quiz frontend
├── *.pdf                  # 112/113/114年國中教育會考社會科題本
└── AGENTS.md
```

## Key technical facts

### PDF text extraction
- **Use PyMuPDF (fitz)**, not pdfplumber. pdfplumber fails on CID-encoded CJK fonts — output is garbled.
- PyMuPDF `page.get_text()` returns clean Chinese text from 會考 PDFs.

### Question parsing regex
- Exam format: `一、單題：(1～42題)` + `二、題組：(43～54題)`
- Question numbers use BOTH formats:
  - Q1-Q9: `\nN.\n` (number on its own line)
  - Q10+: `\nN. ` (inline with content)
- Regex for splitting: `r'(?:^|\n)(\d{1,2})\.(?:\s*\n|\s+)(.*?)(?=\n\d{1,2}\.\s|\Z)'` with DOTALL
- Each year has exactly 54 questions (42 single + 12 in groups)

### Figure references
- Figure labels appear as separate text blocks in PDF: `圖(一)`, `表(一)` etc.
- Regex: `r'[圖表]\([一二三四五六七八九十\d]+\)'`
- ~25-29 questions per year reference figures
- Embedded images extracted via `page.get_images()` + `doc.extract_image()`
- Full-page renders saved as `assets/<year>/pages/page_NN.png`
- Cropped individual figures: `web/pic/114pNN.jpg` (圖(N) → 114pNN, 20+ per year)

### Question groups (題組)
- Section `二、題組` has Q43–Q54 (4 groups × 3 questions each)
- Passage blocks identified by: `閱讀下列選文，回答第 X 至 Y 題`
- Passage text appears either AFTER the last sub-question (most common) or BEFORE the
  first sub-question (e.g. 113 Q44-45) in the PDF text stream.  The parser handles both.
- `split_passage_and_questions()` extracts the passage; `find_passage_boundary()`
  skips intervening table data, page numbers, and control characters.
- Each sub-question now carries the full passage, passage-level figure references,
  and a `group_id`.

### Data schema (JSON)
```json
{
  "number": 1,
  "type": "單題" | "題組子題",
  "group_range": [43, 45] | null,
  "group_id": "43-45" | null,
  "stem": "...",
  "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "image_options": "11529i.jpg" | null,
  "image_options_full": true | false | null,
  "passage": "..." | null,
  "passage_figures": ["圖(一)"],
  "passage_figure_pages": {"圖(一)": 4},
  "figures": ["圖(一)", "表(二)"],
  "figure_pages": {"圖(一)": 4}
}
```
- `group_id`: set on all group sub-questions (e.g. `"52-54"`); `null` for single questions.
- `passage`: the reading passage text.  Identical for all sub-questions in the same group.
- `passage_figures` / `passage_figure_pages`: figures referenced by the passage itself
  (not by any sub-question).  Sub-question `figures` no longer include these.
- Options no longer leak passage text or figure/table label fragments.
- Control characters (`\x00–\x1f` except `\n`) are stripped during parsing.
- `image_options`: filename in `web/pic/item/` (e.g. `"11529i.jpg"`) for questions whose
  options are image-based (maps, symbols, stamps).  `null` for normal text-option questions.
- `image_options_full`:
  - `true` → all of A/B/C/D are images (render 4 letter buttons + option image)
  - `false` → A/B/C are images, D has text (render 3 buttons + image + D text block)
  - `null` → not an image-option question

### Image-option questions
7 questions across 4 years have image-based options that cannot be extracted as text:

| Year | Q | Type | File |
|------|---|------|------|
| 112 | 39 | 單題 | 11239i.jpg |
| 113 | 7 | 單題 | 11307i.jpg |
| 114 | 29 | 單題 | 11429i.jpg |
| 114 | 43 | 題組子題 | 11443i.jpg |
| 115 | 27 | 單題 | 11527i.jpg |
| 115 | 29 | 單題 | 11529i.jpg |
| 115 | 41 | 單題 | 11541i.jpg |

Crops are stored in `web/pic/item/{year}{q:02d}i.jpg`.  The cropping script
`pipeline/crop_image_options.py` reads `image_options` from JSON, locates the
(A)-(D) label area on the page, and extends the bbox downward to include
embedded images, frame rectangles, and drawing clusters.  Frontend checks
`q.image_options` and routes to a dedicated renderer with letter buttons.

## Plugin-driven image analysis
- `opencode-parser` (npm): Parses PDF/DOCX/XLSX/PPTX/images in opencode
- `opencode-see-image` (npm): Routes images to MiniMax M3 vision model for text-only models
- Use `opencode plugin opencode-see-image --global` to install globally

## Figure cropping skill
- **jhexam-figure-crop** skill: `~/.config/opencode/ext-skills/jhexam-figure-crop/`
- Generalized script: `scripts/crop_figures.py <project_root> <year>`
- Handles both **figures (圖)** and **tables (表)** with separate method chains
- **Figure methods** (3+1): frame rects → embedded images → drawing clusters → heuristic crop
- **Table methods** (5+post): lines (Method 0) → frame rects → embedded images → drawing clusters → heuristic crop → verify_and_extend post-processing
- Naming: `{year}p{NN:02d}.jpg` for figures, `{year}t{NN:02d}.jpg` for tables, in `web/pic/`
- Side-by-side figures (圖八/圖九): use x-weighted matching to separate them
- Vector-text figures (newspaper 圖十): cluster glyphs within label vicinity, right column only
- Segmented table V-lines: `merge_h_lines` + `verify_and_extend` to prevent truncation
- `ㄧ` (U+3127) zhuyin encoding: handled automatically in table label detection

## Commands
```bash
# Extract text from all PDFs
python pipeline/extract_all.py

# Parse questions → data/*.json
python pipeline/parse_questions.py

# Extract images → assets/
python pipeline/extract_images.py

# Validate parse quality
python pipeline/check_quality.py

# Validate group passages & option tails (V4)
python pipeline/check_groups.py

# Crop image-option question areas → web/pic/item/
python pipeline/crop_image_options.py
```

## Conventions
- Chinese filenames are fine; use PowerShell Get-ChildItem to resolve paths for Python
- Always store files as UTF-8
- Year identifiers: `112` (2023), `113` (2024), `114` (2025), `115` (2026)
- Each year has 54 questions (Q1-42 single, Q43-54 in groups)
