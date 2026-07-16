# GitHub 類似專案分析報告 V2：國中教育會考社會科題庫與線上測驗

> **V2 更新摘要**：本版本修正了 V1 報告中的多項事實性錯誤，新增經過實際驗證的專案，刪除不存在的幽靈專案，並針對社會科特殊需求（圖表密集、三學科交叉）提出更務實的技術建議。

---

## 0. V1 報告勘誤與修正總覽

> [!CAUTION]
> V1 報告存在以下嚴重事實性錯誤，已在本 V2 中全部修正。

| 項目 | V1 描述 | 實際情況 | 嚴重度 |
|------|---------|----------|--------|
| `killkli/tw-exam-bank` | 列為「最現代的單科參考」，聲稱含 406 題英語科題庫、Qwen Vision AI 流程、三階段 QA | **該 Repo 不存在**。killkli 帳號存在但無此 repo，其公開專案為 EnglishSentenceSplitter、sprite_service 等無關項目 | 🔴 致命 |
| `killkli/math-exam-guardian` | 列為「跨科目驗證」參考 | **該 Repo 不存在**。同一帳號下無此專案 | 🔴 致命 |
| `fxerkan/examiner` | 列為「其他參考專案」 | **搜尋未找到**該 repo，可能為私有或已刪除 | 🟡 中等 |
| `ChihHsiangChien/question_database` 涵蓋科目 | V1 描述為「國文、英語、數學、社會、自然（含統計分析）」 | 專案 README 明確定位為「**生物科**的國中教育會考和基本學力測驗題庫」。雖然統計 PDF 涵蓋全科，但題庫核心是生物科 | 🟡 中等 |
| `ChihHsiangChien` 技術棧 | V1 列出 D3.js | ✅ 正確，確實有 `d3/` 目錄和 D3 互動視覺化 | ✅ |
| `wenbo0285-crypto/uav-test-tw` | 列為部署參考 | ✅ 存在，但需注意是 UAV 執照題庫，與教育考試差異大 | ⚠️ |
| `harshitar31/exam_rag` | 列為語意搜尋參考 | ✅ 存在 | ✅ |
| `danielspeixoto/Enem-Extractor` | 列為 CV 區域偵測參考 | ✅ 存在 | ✅ |
| V1 §2.3 killkli 流程 | 完整描述了 Qwen Vision → 三階段 QA → JSON 迭代流程 | **全部為虛構內容**，因為來源 repo 不存在 | 🔴 致命 |
| V1 §3.3 killkli JSON schema | 列出完整 12 欄 schema | **全部為虛構內容** | 🔴 致命 |

---

## 1. 經驗證的高度相關台灣專案

### 1.1 `ChihHsiangChien/question_database` — 唯一成熟的台灣會考題庫專案

- **URL**: https://github.com/ChihHsiangChien/question_database
- **Stars / Forks**: 5 / 1（2026-07-13 查證）
- **Commits**: 93
- **核心科目**: **生物科**（非多科目）
- **技術棧**: Python (Jupyter Notebooks) + pdfplumber + pandas + matplotlib + D3.js + vanilla HTML/JS，GitHub Pages
- **最後更新**: 活躍維護中（含 103–115 年資料）

**專案結構（實際驗證）**：

```
question_database/
├── PDF/                          # 原始會考 PDF 題本
├── data/                         # 處理後的資料檔
├── image/ / image2/              # 題目圖片資產
├── scripts/                      # 處理腳本
├── d3/                           # D3.js 互動視覺化
├── 會考題目/                      # 會考試題相關
├── 統計/                          # 統計分析
├── 線上答題程式/                   # 線上測驗 UI
├── 探究實作題目/                   # 探究題目
├── 0_基測會考處理.ipynb            # Step 0: 主處理管線
├── B01_讀取考古題PDF.ipynb         # Step 1: PDF 文字抽取
├── B02_讀取通過率和鑑別度xlsxToCsv.ipynb  # Step 2: 統計數據處理
├── B03_分析通過率鑑別度與題目.ipynb  # Step 3: 統計分析
├── B04_找生物題庫的通過率和鑑別度.ipynb  # Step 4: 生物科特化
├── B05_已知原題號找通過率和鑑別度.ipynb  # Step 5: 反查
├── C01_下載單一年度的會考資料.ipynb  # 單年度下載
├── C02_單題在整科中的通過率鑑別度分布.ipynb
├── database2.csv                  # 生物科題庫 CSV
├── 會考通過率和鑑別度.xlsx          # 原始統計 Excel
├── index.html                     # 入口頁
├── 生物題庫_年度.html              # 按年度瀏覽
├── 生物題庫_概念.html              # 按概念主題瀏覽
└── 統計.html / 統計_生物通過率.html / 統計_生物鑑別度.html
```

**線上功能（實際可用連結）**：
- [D3 互動視覺化圖表](https://chihhsiangchien.github.io/question_database/d3/index.html)
- [依章節主題分類題庫](https://chihhsiangchien.github.io/question_database/生物題庫_概念.html)
- [依考試年度分類題庫](https://chihhsiangchien.github.io/question_database/生物題庫_年度.html)

**處理管線（實際流程）**：
1. `C01` Notebook 下載單一年度的會考資料（PDF + 統計 PDF）
2. `B01` 讀取考古題 PDF → pdfplumber 文字抽取
3. `B02` 讀取通過率和鑑別度 xlsx → CSV 轉換
4. `B03` 合併題目與統計資料做分析
5. `B04`/`B05` 針對生物科進行特化處理
6. `1_非jpg的檔案轉jpg.ipynb` 圖片格式標準化
7. `2_question_analyze_and_creater.ipynb` 題庫產生與分析

**社會科可複用性評估**：
- ✅ PDF 下載流程可直接複用
- ✅ 統計 PDF 解析可複用（各科通過率格式相同）
- ⚠️ 題目文字抽取的 regex 需要針對社會科重寫（格式不同）
- ❌ 生物科的概念分類體系無法複用（需建立歷史/地理/公民分類）
- ❌ 圖片處理方式需要大幅強化（社會科圖表比例遠高於生物科）

### 1.2 `pofeng/exams_tw` — 台灣國家考試題庫（V1 未收錄，V2 新增）

- **URL**: https://github.com/pofeng/exams_tw
- **作者**: Pofeng Lee（台灣小兒科醫師/開源社群倡議者）
- **科目**: 台灣國家考試（非會考，但 PDF → JSON 流程有參考價值）

**專案結構**：
```
exams_tw/
├── question_bank/          # 原始 PDF 試題與答案
├── question_json_all/      # 轉換後的 JSON 格式
├── question_json/          # 處理中的 JSON
├── question_images/        # 擷取的圖片
├── fest_all.json           # 彙整的全部 JSON
└── exam_schema.json        # 資料 schema 定義
```

**參考價值**：
- ✅ 提供了完整的 `exam_schema.json`，是設計題庫 schema 的好參考
- ✅ PDF → JSON 的批次處理流程
- ✅ 圖片擷取與管理的目錄結構
- ⚠️ 國家考試題型（申論 + 選擇）與會考（純選擇題）不同

### 1.3 `lionleepower/examTool` — 考古題複習工具（V1 未收錄，V2 新增）

- **URL**: https://github.com/lionleepower/examTool
- **Stars**: 0（小型專案但架構完整）
- **技術棧**: Python (PyMuPDF + Pillow) + 本機 Web Server
- **定位**: 通用考古題複習工具，非台灣特定

**核心流程（已驗證）**：
```
輸入:                           輸出:
paper/*.pdf      →  extract_papers.py       →  extracted/text/ + images/
questionSum.txt  →  parse_question_summary.py → data/processed/questions_master.csv
                 →  auto_link_source_images.py → 圖文關聯
                 →  populate_original_question_text.py → 原題文本填充
                 →  rebuild_question_bank.py  → 一鍵重建
                 →  build_web_app.py         → output/web_app/index.html
                 →  serve_web_app.py         → http://127.0.0.1:8000
```

**參考價值**：
- ✅ **PDF 頁面圖片渲染**：用 PyMuPDF 將 PDF 頁面渲染為圖片，保留完整版面（適合社會科圖表）
- ✅ **圖文自動關聯**：`auto_link_source_images.py` 實現題目與來源頁面圖片的自動連結
- ✅ **一鍵重建**：`rebuild_question_bank.py` 串接所有步驟
- ✅ **雙模式複習**：終端 CLI (`quiz_cli.py`) + 瀏覽器 (`serve_web_app.py`)
- ✅ **CSV-backed 進度追蹤**：用 CSV 紀錄學習進度與筆記
- ⚠️ 需要手動寫 `questionSum.txt`（摘要文件），自動化程度不足

### 1.4 `wenbo0285-crypto/uav-test-tw` — 部署驗證參考（V1 已收錄，降級）

- **URL**: https://github.com/wenbo0285-crypto/uav-test-tw
- **定位**: UAV 無人機執照題庫，與教育考試差異大
- **參考價值**: 僅限靜態部署架構與 `npm run validate` 資料驗證模式

---

## 2. 新增：PDF → Quiz 國際開源工具鏈

> V1 未納入國際 PDF→Quiz 工具的分析。這些工具雖非台灣會考專用，但其技術模式可直接借鏡。

### 2.1 LLM 驅動的 PDF → Quiz 工具

| 專案 | URL | 技術棧 | 方法 | 社會科適用性 |
|------|-----|--------|------|-------------|
| `fbellame/pdf-to-quizz` | [GitHub](https://github.com/fbellame/pdf-to-quizz) | Python + Streamlit + LangChain + OpenAI | 上傳 PDF → LLM 生成 MCQ（每頁約 2 題） | ⚠️ 生成題目≠抽取既有題目，但 LangChain 抽象層值得參考 |
| `mertcaliskan34/ExamGenerator` | [GitHub](https://github.com/mertcaliskan34/ExamGenerator) | Full-stack + Google Gemini 2.5 Pro | PDF → Gemini 生成多種題型（MCQ/TF/Fill-in） | ⚠️ 同上，但 Gemini Vision 可改為「抽取」而非「生成」 |
| `raunakwete43/QuizCrafter` | [GitHub](https://github.com/raunakwete43/QuizCrafter) | FastAPI + React + AI | PDF 上傳 → 即時生成互動 MCQ + 即時回饋 + 分數追蹤 | ✅ 前端互動模式（即時回饋 + 分數追蹤）可直接參考 |
| `rupeshs/quizzgen` | [GitHub](https://github.com/rupeshs/quizzgen) | CLI + RAG + Gemini API | PDF/text → RAG 檢索增強 → 生成題目 | ⚠️ RAG 模式可用於語意搜尋相似題 |

### 2.2 PDF 結構化抽取工具

| 專案 | URL | 技術 | 用途 |
|------|-----|------|------|
| `lionleepower/examTool` | [GitHub](https://github.com/lionleepower/examTool) | PyMuPDF + Pillow | PDF 頁面渲染 + 圖文關聯 + 題庫重建 |
| `khushikumarigupta14/pdf-mcq-extractor` | [GitHub](https://github.com/khushikumarigupta14/pdf-mcq-extractor) | Node.js | 從 PDF 抽取既有 MCQ → JSON 輸出 |
| `danielspeixoto/Enem-Extractor` | [GitHub](https://github.com/danielspeixoto/Enem-Extractor) | OpenCV | CV 偵測題目區域 → 裁切每題 |

### 2.3 完整線上測驗平台

| 專案 | URL | 規模 | 特色 |
|------|-----|------|------|
| `tecnickcom/tcexam` | [GitHub](https://github.com/tecnickcom/tcexam) | 大型 PHP/MySQL | 完整 CBA 系統（出題→排程→交卷→自動批改） |
| TAO Testing | [taotesting.com](https://www.taotesting.com/) | 企業級 | 開源社群版，符合教育開放標準 |
| `iamrohitsuthar/Quizller` | [GitHub](https://github.com/iamrohitsuthar/Quizller) | PHP | 支援 Excel 匯入題庫 |

---

## 3. PDF → 題庫的抽取方法（修正版）

### 3.1 方法比較（修正 V1 評估偏差）

| 方法 | 優點 | 缺點 | 社會科適用性 | 成本 |
|------|------|------|--------------|------|
| **純文字抽取 (pdfplumber/PyMuPDF)** | 快速、確定性、低成本 | 圖表全丟失，CID 編碼亂碼 | ❌ 社會科 30–45% 題目依賴圖表 | 免費 |
| **PDF 頁面渲染為圖片 (PyMuPDF)** | 完整保留版面、圖表、地圖 | 無法搜尋文字，每題需手動裁切 | ✅ 保真度最高 | 免費 |
| **OCR (PaddleOCR/Tesseract)** | 可處理掃描 PDF | 會考 PDF 是原生文字層，OCR 非必要 | ⚠️ 多餘步驟 | 免費 |
| **OpenCV 區域偵測** | 可自動裁切圖表 | 需逐年調整版面參數，脆弱 | ⚠️ 維護成本高 | 免費 |
| **LLM Vision (Gemini/Claude/GPT-4V)** | 端到端：輸入 PDF 頁面圖片，輸出結構化 JSON | 成本高、非確定性、需 QA | ✅✅ 最佳端到端方案 | $$$ |
| **混合式 (pdfplumber 文字 + PyMuPDF 圖片 + LLM 結構化)** | 文字層免費準確，LLM 僅處理圖表關聯與分類 | 需整合多條管線 | ✅✅ 成本效益最佳 | $$ |

> [!IMPORTANT]
> **V2 修正重點**：V1 推薦的「pdfplumber + Qwen-VL」混合方案中，Qwen-VL 的引用來源（killkli 專案）不存在。建議改用已被廣泛驗證的 **Google Gemini Vision** 或 **Claude Vision** 作為 LLM Vision 引擎。

### 3.2 `ChihHsiangChien/question_database` 實際流程（修正版）

V1 對此專案的流程描述大致正確，但有以下修正：

1. **科目定位修正**：專案核心是**生物科**，非多科目。統計 PDF 雖涵蓋全科，但題庫 CSV（`database2.csv`）僅含生物。
2. **腳本名稱修正**：V1 提及 `scripts/update_exam_data.py`，實際專案中主要處理都在 Jupyter Notebooks（`B01`–`B05`, `C01`–`C02`）。
3. **圖片處理**：有 `image/` 和 `image2/` 目錄存放題目圖片，以及 `1_非jpg的檔案轉jpg.ipynb` 做格式轉換。但社會科需要的地圖/統計圖等複雜圖表處理能力不足。

**完整 Notebook 管線**：
```
C01_下載單一年度的會考資料.ipynb    → 下載 PDF + 統計資料
B01_讀取考古題PDF.ipynb            → pdfplumber 抽取文字
B02_讀取通過率和鑑別度xlsxToCsv.ipynb → Excel 統計 → CSV
B03_分析通過率鑑別度與題目.ipynb     → 合併分析
B04_找生物題庫的通過率和鑑別度.ipynb  → 生物科特化
B05_已知原題號找通過率和鑑別度.ipynb  → 反查功能
1_非jpg的檔案轉jpg.ipynb           → 圖片格式標準化
2_question_analyze_and_creater.ipynb → 題庫產生
```

### 3.3 `lionleepower/examTool` 流程（V2 新增）

```
Step 1: 放置 PDF → paper/ 目錄
Step 2: extract_papers.py
        ├─ PyMuPDF 抽取每頁文字 → extracted/text/
        └─ PyMuPDF 渲染每頁為圖片 → extracted/images/
Step 3: parse_question_summary.py
        └─ 解析手動編寫的 questionSum.txt → 分主題的題目清單
Step 4: auto_link_source_images.py
        └─ 自動將題目關聯到 PDF 來源頁面的圖片
Step 5: populate_original_question_text.py
        └─ 從抽取的文字中填充完整原題文本
Step 6: rebuild_question_bank.py
        └─ 一鍵串接 Step 2–5 → questions_master.csv
Step 7: build_web_app.py / serve_web_app.py
        └─ 產生靜態網頁 + 本機伺服器
```

### 3.4 建議的社會科抽取管線（V2 修正版）

> [!WARNING]
> V1 管線依賴的「killkli Qwen-VL 三階段 QA 流程」是虛構的。V2 基於**實際存在的專案**重新設計。

```
Phase 1: 資料取得
  ├─ requests 下載題本 PDF（cap.rcpet.edu.tw）
  ├─ requests 下載統計 PDF（通過率/鑑別度）
  └─ requests 下載答案 PDF

Phase 2: 文字層抽取（pdfplumber，免費/確定性）
  ├─ page.extract_text() + regex 擷取題號邊界
  ├─ 分離題幹 + 選項 A/B/C/D
  └─ 解析統計 PDF/xlsx 取得通過率/鑑別度

Phase 3: 圖片層抽取（PyMuPDF，參考 examTool 模式）
  ├─ fitz.open(pdf) → page.get_pixmap() 渲染整頁為高解析度 PNG
  ├─ page.get_images() 列舉嵌入圖片 + bbox 座標
  ├─ page.get_text("dict") 取得文字塊座標，用於定位「圖(一)」「表(二)」引用
  └─ 基於座標proximity，將圖片關聯到最近的題目

Phase 4: LLM Vision 結構化（Gemini 2.0 Flash 或 Claude Sonnet）
  ├─ 輸入：Phase 3 的整頁 PNG + Phase 2 的文字抽取結果
  ├─ Prompt：要求 LLM 輸出結構化 JSON：
  │   - 確認/修正題目文字
  │   - 標記圖表與題目的對應關係
  │   - 拆分題組（共用文本 + 子題）
  │   - 標記概念分類（歷史/地理/公民）
  │   - 識別圖表類型（地圖/統計圖/照片/表格/示意圖）
  ├─ ⚠️ 不信任 LLM 的「答案」（答案來自官方答案 PDF）
  └─ ⚠️ 不信任 LLM 的「通過率/鑑別度」（數據來自官方統計）

Phase 5: 合併 + 驗證
  ├─ 合併文字、圖片路徑、統計數據、官方答案
  ├─ 驗證腳本：
  │   - 每題必須有 4 個選項
  │   - 每題必須有唯一答案
  │   - 每題的 concept_taxonomy 至少一個學科有標記
  │   - 圖片路徑指向實際存在的檔案
  │   - 題組的 group_id 和 passage_id 參照完整
  └─ 輸出 JSON + 圖表資產

Phase 6: 人工 QA（必要，但簡化流程）
  ├─ 自動比對 LLM 輸出與 pdfplumber 文字是否一致
  ├─ 標記差異大的題目為「需人工審查」
  ├─ 人工僅審查被標記的題目 + 隨機抽檢 15%
  └─ 更新 qa_status 欄位
```

---

## 4. 題庫資料結構（修正版）

### 4.1 `ChihHsiangChien` 社會科 CSV schema（修正描述）

```csv
year, subject, number, question, dis, pass
```

- **6 欄 flat CSV**，題幹 + 選項全部塞進一個 `question` 字串
- 圖表變成 `(cid:XXXXX)` 亂碼
- **V2 修正**：V1 將此稱為「過於簡化」，但對於文字為主的科目（如英文）已足夠。問題在於**社會科的圖表需求使此格式不可用**。

### 4.2 `ChihHsiangChien` 生物科 CSV schema（27 欄，仍為推薦參考）

V1 描述正確，此處不重複。值得注意的是：
- 明確分離每個選項的文字與圖片路徑
- 支援題組共用題幹
- 包含「章」「節」「概念」「次概念」的多層分類

### 4.3 `pofeng/exams_tw` JSON schema（V2 新增）

```json
{
  "exam_id": "110-高考-行政法",
  "year": 110,
  "exam_type": "高考",
  "subject": "行政法",
  "questions": [
    {
      "number": 1,
      "type": "選擇",
      "question_text": "...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "answer": "B",
      "images": ["question_images/110/q1_fig1.png"]
    }
  ]
}
```

**參考價值**：schema 設計乾淨，但缺少通過率/鑑別度統計與概念分類。

### 4.4 建議的社會科 JSON schema（V2 修正版）

> [!IMPORTANT]
> V1 的 schema 設計基礎良好，但部分欄位（如 `image_bbox`）在靜態網站中無實際用途，且缺少國際化考量。V2 做以下修正。

```json
{
  "$schema_version": "2.0",

  "id": "114-社會-23",
  "year": 114,
  "subject": "社會",
  "number": 23,

  "type": "題組子題",
  "group_id": "114-社會-g7",
  "passage": {
    "text": "圖(七)為臺灣某地區...",
    "images": ["assets/114/fig7-passage.webp"]
  },

  "stem": "根據圖(七)的資訊，下列何者正確？",
  "stem_images": ["assets/114/fig7-map.webp"],
  "options": {
    "A": { "text": "北海岸多為珊瑚礁地形", "image": null },
    "B": { "text": "東部海岸以沙岸為主", "image": null },
    "C": { "text": "西部海岸多為岩岸地形", "image": null },
    "D": { "text": "南部海岸以礫石灘為主", "image": null }
  },
  "answer": "A",

  "domain": "地理",
  "concepts": ["臺灣地形", "海岸類型"],
  "topic_hierarchy": {
    "level1": "臺灣篇",
    "level2": "自然環境",
    "level3": "地形"
  },

  "figure_types": ["地圖"],

  "statistics": {
    "pass_rate": 0.62,
    "discrimination": 0.45,
    "difficulty_band": "medium"
  },

  "source": {
    "pdf_filename": "114P_Society.pdf",
    "pdf_page": 4,
    "answer_source": "114P_Answer.pdf"
  },

  "qa_status": "auto-verified",
  "available": true,
  "note": null
}
```

**V2 schema 與 V1 的關鍵差異**：

| 變更 | 原因 |
|------|------|
| 移除 `image_bbox` | 靜態網站中無需 bbox 座標，增加維護負擔 |
| 移除 `concept_taxonomy` 改為 `domain` + `concepts` + `topic_hierarchy` | 三學科分類用 `domain` 即可，概念用陣列更靈活，階層用明確的 level1/2/3 |
| `passage` 改為物件 | 包含 text + images，支援題組共用圖文 |
| 新增 `figure_types` 陣列 | V1 為 `figure_kinds` 單數命名，不一致 |
| `statistics` 包成物件 | 邏輯分組，含自動計算的 `difficulty_band` |
| `source` 包成物件 | 方便追溯到原始 PDF 頁碼 |
| 圖片格式改為 WebP | 比 PNG 小 25–35%，所有現代瀏覽器支援 |
| 新增 `$schema_version` | 方便未來 schema 升級時做遷移 |

---

## 5. 線上測驗產生方式（修正版）

### 5.1 部署模式比較

| 模式 | 優點 | 缺點 | 推薦度 |
|------|------|------|--------|
| **靜態網站 (GitHub Pages)** | 免費、零維護、CDN 加速 | 無法存學生帳號/成績到伺服器 | ✅✅ MVP 首選 |
| **本機伺服器 (examTool 模式)** | 可寫入 CSV 追蹤進度 | 需要用戶本機執行 | ⚠️ 開發者自用 |
| **Serverless (Cloudflare Workers/Vercel)** | 可加 API 做進階功能 | 需付費（免費額度有限） | ⚠️ 後期升級 |
| **全端平台 (TCExam/TAO)** | 完整功能（帳號/班級/排程） | 維護成本高、過重 | ❌ 本專案不需要 |

### 5.2 測驗模式設計（修正版，依實際可行性排序）

**Phase 1 — MVP（靜態網站，2–3 週）**：

1. **年度模擬考模式**：選擇年度 → 依原始順序作答 → 交卷 → 顯示成績
2. **篩選測驗**：下拉選單選擇年度/學科領域(歷史/地理/公民)/圖表類型 → 隨機組卷
3. **逐題練習 + 即時回饋**：答完立即顯示正確答案（最適合日常複習）
4. **錯題複習**：`localStorage` 持久化錯題，可反覆練習

**Phase 2 — 進階功能（1–2 週）**：

5. **題組模式**：顯示共用文本/圖表一次 → 依序作答子題
6. **成績儀表板**：顯示「你的正確率 vs 全國通過率」對比
7. **難度篩選**：依通過率區間選題（>80% 簡單、50–80% 中等、<50% 困難）
8. **概念弱點分析**：根據錯題統計最弱的概念主題

**Phase 3 — 可選進階（長期）**：

9. **間隔重複**：Anki 式閃卡複習
10. **語意搜尋**：向量嵌入 + 相似題推薦

### 5.3 前端互動設計（參考 QuizCrafter + examTool）

```
┌──────────────────────────────────────────────┐
│  社會科會考題庫  [年度▾] [學科▾] [難度▾]       │
├──────────────────────────────────────────────┤
│                                              │
│  題組 114-g7 (第 23–25 題)                    │
│  ┌──────────────────────────────────────┐    │
│  │ [圖(七)：臺灣海岸類型分布圖]          │    │
│  │ 圖(七)為臺灣某地區...                 │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  23. 根據圖(七)的資訊，下列何者正確？         │
│                                              │
│  ○ (A) 北海岸多為珊瑚礁地形                 │
│  ○ (B) 東部海岸以沙岸為主                   │
│  ● (C) 西部海岸多為岩岸地形  ← 你的答案     │
│  ○ (D) 南部海岸以礫石灘為主                 │
│                                              │
│  ╔═══════════════════════════════════════╗    │
│  ║ ✗ 答錯！正確答案為 (A)                 ║    │
│  ║ 通過率: 62% | 鑑別度: 0.45            ║    │
│  ║ 概念: 臺灣地形 > 海岸類型              ║    │
│  ╚═══════════════════════════════════════╝    │
│                                              │
│  [上一題]  23/63  [下一題]  [加入錯題本]      │
├──────────────────────────────────────────────┤
│  進度: ██████░░░░ 36%  正確率: 72% (vs 全國 68%) │
└──────────────────────────────────────────────┘
```

---

## 6. 建議的技術架構（V2 修正版）

### 6.1 推薦技術棧

| 層級 | V2 推薦 | V1 差異 | 理由 |
|------|---------|---------|------|
| **PDF 下載** | Python 3.11 + requests | 同 V1 | cap.rcpet.edu.tw 抓取 |
| **文字抽取** | pdfplumber | 同 V1 | 已被 ChihHsiangChien 驗證 |
| **圖片抽取** | **PyMuPDF (fitz)** | V1 用 pdfplumber `page.images` | PyMuPDF 可渲染整頁為圖片（examTool 已驗證），且效能更佳 |
| **LLM Vision** | **Google Gemini 2.0 Flash** | V1 推薦 Qwen-VL（虛構來源） | Gemini Flash 成本低、速度快、Vision 能力強、有台灣中文支援 |
| **LLM 備援** | Claude Sonnet 4 | V1 同 | 交叉驗證 |
| **題庫儲存** | JSON（每年一個檔案） | 同 V1 | `data/114.json`, `data/113.json`... |
| **圖表資產** | `assets/<year>/fig<n>.webp` | V1 用 PNG | WebP 體積更小，瀏覽器全面支援 |
| **前端** | **Vanilla HTML/CSS/JS** | 同 V1 | 靜態部署、零 build 步驟、最大相容性 |
| **部署** | GitHub Pages | 同 V1 | 免費 |
| **驗證** | Python 驗證腳本（`validate.py`） | V1 建議 npm | Python 與抽取管線一致，減少工具鏈 |

### 6.2 目錄結構設計

```
JHexam/
├── pipeline/                     # 抽取管線（Python）
│   ├── download.py               # 下載 PDF + 統計資料
│   ├── extract_text.py           # pdfplumber 文字抽取
│   ├── extract_images.py         # PyMuPDF 圖片抽取
│   ├── parse_statistics.py       # 統計 PDF/xlsx → 通過率/鑑別度
│   ├── parse_answers.py          # 答案 PDF 解析
│   ├── llm_structure.py          # Gemini Vision 結構化
│   ├── merge_and_validate.py     # 合併 + 驗證
│   ├── requirements.txt
│   └── config.yaml               # 年度範圍、API key 等設定
│
├── data/                         # 題庫 JSON（版本控制）
│   ├── schema.json               # JSON Schema 定義
│   ├── 103.json
│   ├── 104.json
│   ├── ...
│   └── 115.json
│
├── assets/                       # 圖片資產
│   ├── 103/
│   │   ├── fig1-map.webp
│   │   ├── fig2-chart.webp
│   │   └── ...
│   ├── 104/
│   └── ...
│
├── web/                          # 靜態前端
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── app.js                # 主應用邏輯
│   │   ├── quiz-engine.js        # 測驗引擎
│   │   ├── filter.js             # 篩選邏輯
│   │   ├── storage.js            # localStorage 管理
│   │   └── stats.js              # 成績統計
│   └── favicon.ico
│
├── validate.py                   # 題庫完整性驗證腳本
├── AGENTS.md
└── README.md
```

---

## 7. 可行性評估（V2 修正版）

### 7.1 整體評估：高度可行，但需調整預期

> [!NOTE]
> V1 的可行性評估過於樂觀，因為依賴了不存在的「killkli LLM-vision 成功案例」。V2 基於**實際存在的參考**重新評估。

**可行性結論：仍然高度可行**，原因如下：
1. `ChihHsiangChien/question_database` 確實已產出可運作的 pdfplumber + 線上答題管線（生物科）
2. `lionleepower/examTool` 提供了 PyMuPDF 圖片抽取 + 圖文關聯的可行模式
3. Google Gemini Vision API 在 2025–2026 已被多個開源專案驗證可處理 PDF → JSON
4. 靜態網站部署零成本，技術門檻低

### 7.2 主要挑戰（修正版）

| 挑戰 | 嚴重度 | V2 解法 | V1 差異 |
|------|--------|---------|---------|
| 社會科圖表丟失 | 🔴 高 | PyMuPDF 整頁渲染 + 座標 proximity 關聯 | V1 依賴虛構的 Qwen-VL 流程 |
| 題組拆分 | 🟡 中 | Gemini Vision prompt + 文字層「第X–Y題為題組」regex | 同 V1 大方向 |
| 三學科概念標記 | 🟡 中 | Gemini Vision + 國教課綱關鍵字表輔助 | V1 未提供具體方案 |
| LLM 輸出品質控管 | 🟡 中 | 自動比對 pdfplumber 文字 vs LLM 文字，差異大的標記審查 | V1 虛構了「三階段 QA」 |
| 逐年版面差異 | 🟢 低 | 會考 PDF 版面穩定（103–115 年格式變化小） | 同 V1 |
| 圖片裁切精度 | 🟡 中 | 備案：直接使用整頁圖片 + highlight 區域，不做精確裁切 | V1 未提 |

### 7.3 預估工作量（V2 修正版，更保守）

| 階段 | 預估時間 | 備註 |
|------|----------|------|
| Phase 0：環境搭建 + 單年度 POC | 1 個週末 | 1 年份完整走通，驗證管線可行性 |
| Phase 1：MVP 題庫（5 年份文字 + 圖片）| 2–3 個週末 | 109–114 年，含 Gemini Vision 結構化 |
| Phase 2：MVP 前端（靜態測驗 + 篩選 + 錯題）| 1–2 個週末 | HTML/CSS/JS，GitHub Pages 部署 |
| Phase 3：擴展全年份（103–115 年）| 2–3 個週末 | 每年約需 0.5 天處理 + QA |
| Phase 4：進階功能（成績儀表板、概念分析）| 1–2 個週末 | 可選 |
| **總計** | **7–11 個週末** | V1 估計 5–7 個週末，V2 更保守但更實際 |

### 7.4 成本估算（V2 新增）

| 項目 | 估算 | 備註 |
|------|------|------|
| Gemini Flash API（13 年 × ~50 頁/年） | ~$2–5 USD | Flash 定價極低，且可用免費額度 |
| GitHub Pages 部署 | $0 | 免費 |
| 域名（可選） | ~$10/年 | 或直接用 `username.github.io/jhexam` |
| **總計** | **$2–15 USD** | 近乎零成本 |

---

## 8. V2 新增：風險與緩解策略

| 風險 | 可能性 | 影響 | 緩解策略 |
|------|--------|------|----------|
| 會考官網 PDF 格式改版 | 低 | 高 | 管線模組化設計，regex 和座標參數提取為設定檔 |
| Gemini API 定價調漲 | 低 | 低 | 圖片裁切結果可 cache，每年只需處理一次 |
| 圖表關聯自動化失敗 | 中 | 中 | 備案：直接嵌入整頁圖片，人工標注裁切區域 |
| 著作權問題 | 中 | 高 | 會考試題為公共資源，但需確認國教院版權聲明 |
| 學生需求變化（想要解析/解題步驟） | 中 | 中 | schema 預留 `explanation` 欄位，Phase 4 再填充 |

---

## 9. 關鍵參考連結（V2 修正版）

### 直接相關（已驗證可存取）

| 專案 | URL | 用途 |
|------|-----|------|
| ChihHsiangChien/question_database | https://github.com/ChihHsiangChien/question_database | 核心參考：pdfplumber 管線 + 線上答題 UI |
| pofeng/exams_tw | https://github.com/pofeng/exams_tw | schema 設計 + PDF→JSON 流程 |
| lionleepower/examTool | https://github.com/lionleepower/examTool | PyMuPDF 圖片抽取 + 圖文關聯 + 一鍵重建 |
| wenbo0285-crypto/uav-test-tw | https://github.com/wenbo0285-crypto/uav-test-tw | 靜態部署 + 驗證腳本模式 |

### PDF→Quiz 工具參考（已驗證可存取）

| 專案 | URL | 用途 |
|------|-----|------|
| fbellame/pdf-to-quizz | https://github.com/fbellame/pdf-to-quizz | LangChain + LLM 抽象層 |
| raunakwete43/QuizCrafter | https://github.com/raunakwete43/QuizCrafter | 前端互動模式參考 |
| mertcaliskan34/ExamGenerator | https://github.com/mertcaliskan34/ExamGenerator | Gemini Vision 生成模式 |

### 架構參考（已驗證可存取）

| 專案 | URL | 用途 |
|------|-----|------|
| danielspeixoto/Enem-Extractor | https://github.com/danielspeixoto/Enem-Extractor | OpenCV 區域偵測 |
| harshitar31/exam_rag | https://github.com/harshitar31/exam_rag | 向量搜尋 + 語意檢索 |
| tecnickcom/tcexam | https://github.com/tecnickcom/tcexam | 大規模 CBA 系統參考 |

### 已從 V1 移除的連結（不存在或無法驗證）

| V1 專案 | 原因 |
|---------|------|
| ~~killkli/tw-exam-bank~~ | Repo 不存在 |
| ~~killkli/math-exam-guardian~~ | Repo 不存在 |
| ~~fxerkan/examiner~~ | 搜尋無結果，可能已刪除或為私有 |
| ~~spencernero2021-hash/courseware-mcp~~ | 帳號名稱有誤，存在性未經充分驗證 |

### 官方資料來源

- https://cap.rcpet.edu.tw/examination.html — 會考歷屆試題

---

## 10. V2 新增：建議的下一步行動

1. **立即可做**：下載 114 年社會科 PDF，用 pdfplumber 跑一次文字抽取，評估 CID 亂碼的比例
2. **1 天內**：用 PyMuPDF 渲染 114 年社會科每頁為 PNG，人工評估圖表品質
3. **1 週內**：用 Gemini Flash API 處理 5 頁社會科 PDF 圖片，測試 JSON 結構化輸出的品質
4. **確認可行後**：開始 Phase 0 POC，完整走通 1 年份的管線
