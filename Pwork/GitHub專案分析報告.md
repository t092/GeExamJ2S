# GitHub 類似專案分析報告：國中教育會考社會科題庫與線上測驗

## 1. 高度相關的台灣會考專案

### 1.1 `ChihHsiangChien/question_database` — 最成熟的工程參考

- **URL**: https://github.com/ChihHsiangChien/question_database
- **技術棧**: Python + pdfplumber + pandas + Jupyter + matplotlib + D3.js + vanilla HTML/JS，GitHub Pages
- **涵蓋科目**: 國文、英語、數學、社會、自然（含通過率/鑑別度統計分析）
- **最後更新**: 2026-07-11（活躍維護中）
- **特色**: 多科目題庫 + D3 散佈圖視覺化 + 線上答題 UI

### 1.2 `killkli/tw-exam-bank` — 最現代的單科參考

- **URL**: https://github.com/killkli/tw-exam-bank
- **技術棧**: 純 HTML/CSS/JS（無 build），GitHub Actions 部署至 Pages
- **科目**: 英語科（406 題，102–114 年）
- **最後更新**: 2026-04-27
- **特色**: 使用 Qwen Vision AI 進行 PDF 轉 JSON + 三階段人工 QA

### 1.3 `killkli/math-exam-guardian` — 跨科目驗證

- **URL**: https://github.com/killkli/math-exam-guardian
- **科目**: 數學科（102–114 年）
- **特色**: 與 tw-exam-bank 同作者，驗證 Qwen-vision 管線可跨科目擴展

### 1.4 `wenbo0285-crypto/uav-test-tw` — 部署驗證參考

- **URL**: https://github.com/wenbo0285-crypto/uav-test-tw
- **技術棧**: 靜態 HTML/CSS/JS，Netlify 部署
- **特色**: 1,420 題 UAV 執照題庫，有 `npm run validate` 驗證題庫完整性
- **參考價值**: 部署與資料驗證模式

---

## 2. PDF → 題庫的抽取方法

### 2.1 方法比較

| 方法 | 優點 | 缺點 | 社會科適用性 |
|------|------|------|--------------|
| **純文字抽取 (pdfplumber/PyMuPDF)** | 快速、確定性、可腳本化、低成本 | 圖表/地圖全丟失，CID 編碼亂碼 | ❌ 社會科 30-45% 題目依賴圖表 |
| **OCR (Tesseract/PaddleOCR)** | 可處理掃描 PDF | 無法保留版面語意（哪張圖屬於哪題） | ⚠️ 會考 PDF 是原生文字層，OCR 非必要 |
| **電腦視覺區域偵測 (OpenCV)** | 可裁切圖表並關聯題目 | 需逐年調整版面參數，脆弱 | ✅ 適合圖表密集的社會科 |
| **LLM Vision (Qwen-VL/GPT-4V/Claude)** | 一次輸出結構化 JSON，處理複雜版面，可標記圖表關聯 | 成本高、非確定性、需人工 QA | ✅✅ 最佳端到端方案 |
| **混合式 (pdfplumber + LLM)** | 文字層便宜準確，LLM 處理圖表關聯與結構化 | 需整合兩條管線 | ✅✅ 成本效益最佳 |

### 2.2 `ChihHsiangChien` 的實際流程（已驗證可運作）

1. `requests` 下載題本 PDF + 統計 PDF（cap.rcpet.edu.tw 或 Google Drive）
2. `pdfplumber.extract_words()` + x 座標欄位映射解析統計表（90–147.5px = 國文，147.5–228.5 = 英語聽力...）
3. `page.extract_text()` + regex `(?=\n(\d{1,2}\.\s+.*?\(D\).*?\n))` 擷取每題（從題號到 (D) 選項）
4. 合併 CSV、`drop_duplicates(subset=['year','number'], keep='last')` 去重
5. 產生 HTML 報告 + matplotlib 散佈圖
6. **痛點**：圖表全部變成 `(cid:XXXXX)` 佔位符，無法顯示

### 2.3 `killkli` 的實際流程

1. 將 PDF 整本餵給 Qwen Vision Model
2. 模型輸出結構化 JSON（題幹、選項、答案、概念標籤）
3. 三階段人工 QA：研究者 → 專家 → 評估者
4. 多版本 JSON 迭代（`exam-questions-original.json` → `v2.json` → `v3-pre-ocr-fix.json` → `v3.json` → `questions.json`）
5. `consolidate.py` 彙整各年度批次檔案

### 2.4 其他參考專案的抽取方法

| 專案 | PDF 方法 | 管線 | 輸出 |
|------|----------|------|------|
| `fxerkan/examiner` | pdfplumber + Claude API | PDF 文字 → regex 邊界偵測 → Claude 驗證/增強答案 | JSON+CSV，含選項、評論、信心分數 |
| `harshitar31/exam_rag` | PDF → 向量 + SQLite | 爬蟲 → 抽取 → 嵌入 → 向量搜尋 | SQLite + embeddings |
| `Dannavv/Extract-Gate-CSE-Questions` | 文字抽取 + 主題分類 | PDF/線上題庫 → 主題標記 | 按學科分類 |
| `danielspeixoto/Enem-Extractor` | OpenCV 電腦視覺 | CV 偵測題目區域 → 裁切 | 每題 JSON |
| `spencernero2021-hash/courseware-mcp` | PDF/PPTX → MCP → DeepSeek | 本地 MCP 伺服器餵 DeepSeek 產生摘要/心智圖/模擬考 | LLM 生成 |

---

## 3. 題庫資料結構

### 3.1 `ChihHsiangChien` 社會科 schema（6 欄，過於簡化）

```csv
year, subject, number, question, dis, pass
104, 社會, 1, 1.圖(一)為臺灣1980年...（題幹+選項全部塞進一個字串，圖表變成(cid:XXXXX)）, 0.37, 0.89
```

**問題**：題幹 + 選項 + 圖表全部塞進一個字串欄位，圖表變成 `(cid:7447)` 亂碼，無法分離顯示。

### 3.2 `ChihHsiangChien` 生物科 schema（27 欄，推薦參考）

```csv
序號, 章, 節, 概念, 次概念, 考法, 題組, 題組題幹, 題組圖1, 題組圖2, 圖高,
題幹, 題幹圖1, 題幹圖2, 選項A, 選項B, 選項C, 選項D,
圖A, 圖B, 圖C, 圖D, 出處, 答案, 原題號, 鑑別度, 通過率
```

**優點**：明確分離每選項文字與圖片路徑、題組共用題幹與圖片。

### 3.3 `killkli` JSON schema（12 欄，現代化）

```json
{
  "id": "102-3",
  "year": 102,
  "number": 3,
  "type": "vocabulary | grammar | reading | cloze | conversation",
  "difficulty": "basic | medium | difficult | null",
  "concepts": ["詞義理解"],
  "question": "...(題幹，可為多行/含 Markdown 表格)",
  "passage": "",
  "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "answer": "A",
  "group_id": null,
  "note": null,
  "available": true
}
```

**優點**：分離 `passage`（共用閱讀文本）、`group_id`（題組）、`concepts`（多標籤概念）、`available` 標記無法重現的題目。

### 3.4 建議的社會科 schema（混合兩者優點）

```json
{
  "id": "114-社會-23",
  "year": 114,
  "subject": "社會",
  "number": 23,
  "type": "題組 | 單題",
  "group_id": "114-社會-g7",
  "passage_id": "114-社會-p7",
  "stem": "題幹文字",
  "stem_images": ["assets/114/society/fig7-1.png"],
  "options": {
    "A": {"text": "...", "image": null},
    "B": {"text": "...", "image": null},
    "C": {"text": "...", "image": "assets/114/society/fig7-2.png"},
    "D": {"text": "...", "image": null}
  },
  "answer": "C",
  "concepts": ["臺灣地形", "海岸類型"],
  "concept_taxonomy": {"歷史": [], "地理": ["臺灣地形", "海岸類型"], "公民": []},
  "figure_kinds": ["地圖"],
  "difficulty": "medium",
  "pass_rate": 0.62,
  "discrimination": 0.45,
  "source": "114P_Society.pdf p.4",
  "pdf_page": 4,
  "image_bbox": [120, 340, 480, 260],
  "available": true,
  "qa_status": "expert-verified",
  "note": null
}
```

**社會科特有設計**：
- `concept_taxonomy`：歷史/地理/公民三學科多標籤分類
- `figure_kinds`：地圖、統計圖、照片、表、示意圖等圖表類型標記
- `stem_images` + `options[*].image`：支援題幹與選項各自的圖表
- `group_id` / `passage_id`：支援題組共用文本與圖表

---

## 4. 線上測驗產生方式

### 4.1 部署模式

所有台灣會考專案都使用**靜態網站**（GitHub Pages），無後端伺服器，零成本。

### 4.2 測驗模式（依優先順序）

1. **篩選後測驗**：下拉選單選擇年度/題型/概念/難度 → 從符合條件的題目中組卷
2. **逐題作答 + 即時回饋**：答完立即顯示正確答案 + 解析（最適合讀書）
3. **模擬考模式**：限時作答 → 交卷 → 顯示成績與解析
4. **錯題複習**：持久化錯題至 localStorage，可反覆練習弱點
5. **題組模式**：顯示共用文本/圖表一次，再依序作答子題
6. **成績儀表板**：顯示通過率比較（「你這次正確率 65%；當年全國平均 60%」）

### 4.3 進階功能（可選）

- **自適應選題**：依通過率區間選題（目前無專案實作，但資料已具備）
- **間隔重複**：Anki 式閃卡複習（參考 `fauvault` 專案）
- **語意搜尋**：向量嵌入 + 相似題推薦（參考 `exam_rag`）

---

## 5. 建議的技術架構

### 5.1 推薦技術棧

| 層級 | 推薦 | 理由 |
|------|------|------|
| **抽取管線** | Python 3.11 + pdfplumber + pandas + Pillow | 與 `ChihHsiangChien` 完全一致，已驗證可處理會考 PDF |
| **圖表抽取** | pdfplumber `page.images` + bbox 裁切 | 平行管線，與文字抽取同時進行 |
| **LLM 輔助**（可選） | Qwen-VL-Max 或 Claude Vision | 處理題組拆分、圖表關聯、概念標記 |
| **題庫儲存** | JSON 檔案存於 git（每年一個檔案） | GitHub 原生、可 diff、適合靜態網站 |
| **圖表資產** | `assets/<year>/society/fig<n>.png` | 結構化目錄，隨題庫一起版本控制 |
| **測驗前端** | Vanilla HTML/CSS/JS 或 Astro + vanilla JS | 靜態部署，零後端成本 |
| **部署** | GitHub Pages + GitHub Actions | 免費，`data/` 變更時自動部署 |
| **資料驗證** | `npm run validate` 腳本 | 確保每題有完整選項、答案、可用狀態 |

### 5.2 建議的抽取管線（混合式）

```
Step 1: 下載
  └─ requests 下載題本 PDF + 統計 PDF + 答案 PDF（cap.rcpet.edu.tw）

Step 2: 文字層抽取（pdfplumber）
  ├─ page.extract_text() + regex 擷取每題
  ├─ 分離題幹 + 選項 A/B/C/D
  └─ 解析統計 PDF 取得通過率/鑑別度

Step 3: 圖表層抽取（pdfplumber，平行進行）
  ├─ page.images 列舉所有嵌入圖片 + bbox
  ├─ page.cropbbox().to_image() 匯出為 PNG
  └─ 依閱讀順序 proximity 關聯圖表與題目

Step 4: LLM Vision 清理（可選但推薦）
  ├─ 拆分題組（共用文本 + 子題）
  ├─ 標記概念（歷史/地理/公民）
  ├─ 偵測「圖(一)」「表(二)」引用並關聯裁切圖
  └─ 不信任 LLM 的答案（答案來自官方答案 PDF）

Step 5: 合併 + 驗證
  ├─ 合併文字、圖表、統計、答案
  ├─ 驗證腳本檢查完整性
  └─ 輸出 JSON + 圖表資產

Step 6: 人工 QA（必要）
  ├─ 研究者隨機抽檢 20%
  ├─ 專家審查邊界/cid-rich 題目
  └─ 評估者簽核
```

---

## 6. 可行性評估

### 6.1 整體評估：高度可行

- `ChihHsiangChien/question_database` 已提供可運作的 pdfplumber 管線，且已產出社會科 CSV
- `killkli/tw-exam-bank` 展示了 LLM-vision 方法可乾淨處理圖表密集科目
- 整個技術棧免費、靜態、可 GitHub 託管

### 6.2 主要挑戰

| 挑戰 | 嚴重度 | 解法 |
|------|--------|------|
| 社會科圖表丟失（cid 亂碼） | 高 | pdfplumber image bbox 裁切 + LLM vision 關聯 |
| 題組拆分（共用文本 + 子題） | 中 | LLM vision 或手動規則 |
| 概念標記（歷史/地理/公民） | 中 | LLM 輔助 + 人工校對 |
| 逐年版面差異 | 低 | 會考 PDF 版面相對穩定 |

### 6.3 預估工作量

| 階段 | 預估時間 |
|------|----------|
| MVP（靜態網站 + JSON 題庫 + 篩選測驗 + 即時回饋 + 錯題複習） | 2–3 個週末 |
| LLM vision 圖表抽取 + 三階段 QA（每年） | 每年額外 2 個週末 |
| 進階功能（自適應選題、成績儀表板） | 1–2 個週末 |

---

## 7. 關鍵參考連結

### 直接相關（可複製程式碼/schema）

- https://github.com/ChihHsiangChien/question_database
- https://github.com/ChihHsiangChien/question_database/blob/master/scripts/update_exam_data.py
- https://github.com/ChihHsiangChien/question_database/blob/master/data/society.csv
- https://github.com/killkli/tw-exam-bank
- https://github.com/killkli/tw-exam-bank/blob/main/data/exam-questions.json
- https://github.com/killkli/tw-exam-bank/blob/main/data/consolidate.py
- https://github.com/killkli/math-exam-guardian
- https://github.com/wenbo0285-crypto/uav-test-tw

### 架構參考（非台灣特定，提供設計靈感）

- https://github.com/fxerkan/examiner — LLM 輔助 PDF 解析模式
- https://github.com/danielspeixoto/Enem-Extractor — CV 區域偵測裁切圖表
- https://github.com/tecnickcom/tcexam — 大規模 CBA 伺服器參考
- https://github.com/harshitar31/exam_rag — 語意搜尋功能參考

### 官方資料來源

- https://cap.rcpet.edu.tw/examination.html — 會考歷屆試題（兩個台灣專案共同引用）
