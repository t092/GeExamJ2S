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

## Image analysis
- If the current model has built-in vision, use native model vision directly for image understanding.
- Do not use image-analysis plugins when built-in vision is available.
- Use external/plugin vision tools only as a fallback when the model cannot read images natively, or when explicitly requested.

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

## Math (數學科)

數學科所有工作檔案與資料獨立放在 `math/` 目錄下，與社會科完全分離。

```
JHexam/math/
├── 114年國中教育會考數學科題本.pdf   # 數學科 PDF 題本 (114年)
├── 115年國中教育會考數學科題本.pdf   # 數學科 PDF 題本 (115年)
├── pipeline/     # PDF 提取、解析、裁圖等 Python 腳本
│   ├── extract_all.py       # PyMuPDF text extraction
│   ├── parse_questions.py   # Question parser → data/115.json
│   ├── extract_images.py    # Page renders → assets/115/pages/
│   ├── crop_figures.py      # Crop figures → pic/
│   ├── latex_convert.py     # Add LaTeX fields to JSON
│   └── check_quality.py     # Validation
├── data/         # 題庫 JSON 資料 (114.json, 115.json)
├── assets/       # 頁面渲染
│   ├── 114/pages/
│   └── 115/pages/
├── pic/          # 裁切後圖表
│   └── item/
└── web/          # Static math viewer（直接進入題目頁，左上角年份下拉切換）
```

### 數學科 vs 社會科差異

| 項目 | 社會科 | 數學科 |
|------|--------|--------|
| 題數 | 54題 (42單+12組) | 27題 (25選+2非選) |
| 題型 | 單題/題組子題 | 選擇題/題組子題/非選擇題 |
| 圖片類型 | 嵌入點陣圖 | 向量繪圖 (get_pixmap裁切) |
| 圖片選項 | 有 (7題) | 無 |
| 數學式 | 無 | LaTeX 轉換 |
| 題組 | 4組 (43-54) | 1組 (23-25) |
| 參考公式 | 無 | 頁14 |

### 數學科 JSON Schema

```json
{
  "number": 1,
  "type": "選擇題" | "題組子題" | "非選擇題",
  "group_range": [23, 25] | null,
  "group_id": "23-25" | null,
  "stem": "解二元一次聯立方程式 x + 2y = 5 ...",
  "stem_latex": "解二元一次聯立方程式 x + 2y = 5 ...",
  "options": {"A": "−4", "B": "−2", "C": "2", "D": "4"},
  "options_latex": {"A": "-4", "B": "-2", "C": "2", "D": "4"},
  "passage": "汽車上會安裝圖(十二)的時速錶..." | null,
  "passage_figures": ["圖(十二)"],
  "figures": ["圖(一)"],
  "tables": ["表(一)"]
}
```

### LaTeX 轉換規則

- `×` → `\times`, `÷` → `\div`, `±` → `\pm`
- `∠` → `\angle`, `°` → `^\circ`, `△` → `\triangle`, `π` → `\pi`
- `√N` → `\sqrt{N}`, `√(expr)` → `\sqrt{expr}`
- `4x2` → `4x^{2}`, `(1.025)7` → `(1.025)^{7}`
- `4.4 × 105` → `4.4 \times 10^{5}` (科學記號)
- `a1`, `an`, `Sn` → `a_{1}`, `a_{n}`, `S_{n}` (數列下標)
- `stem_latex` / `options_latex`: `null` 表示無需 LaTeX 轉換

### 數學科裁圖

- 命名：`{year}p{NN:02d}.jpg` (圖), `{year}t{NN:02d}.jpg` (表), in `math/pic/`
- 方法：text block 搜尋 → 獨立標籤偵測 → 鄰近向量繪圖聚合 → bbox 裁切
- 圖(十三)+(十四) 合併裁切 (並排圖)
- 16 張圖表 (15 圖 + 1 表)

### 數學科命令

```bash
# 全部在 math/ 目錄下執行
cd math

# 1. Extract text
python pipeline/extract_all.py

# 2. Render pages
python pipeline/extract_images.py

# 3. Parse questions → data/{year}.json
python pipeline/parse_questions.py

# 4. Convert math expressions → LaTeX
python pipeline/latex_convert.py

# 5. Crop figures → pic/
python pipeline/crop_figures.py

# 6. Validate
python pipeline/check_quality.py
```

## Conventions
- Chinese filenames are fine; use PowerShell Get-ChildItem to resolve paths for Python
- Always store files as UTF-8
- Year identifiers: `112` (2023), `113` (2024), `114` (2025), `115` (2026)
- Math: 27 questions (25 choices + 2 non-choice), 1 group (Q23-25)
- Social studies: 54 questions (42 single + 12 in groups)
