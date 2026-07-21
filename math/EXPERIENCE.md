# 國中教育會考數學科題庫 Pipeline 經驗彙整

> 適用範圍：國中教育會考數學科題本（115 年起）。  
> 目的：記錄從 PDF 到結構化 JSON + LaTeX 的完整流程、已知問題與修復方式，作為未來製作自動化 skill 的基底。

---

## 1. 總體架構

```
math/
├── <year>年國中教育會考數學科題本.pdf  # 原始題本 PDF
├── pipeline/
│   ├── extract_all.py      # PyMuPDF 文字擷取
│   ├── extract_images.py   # 頁面渲染（200dpi PNG）
│   ├── parse_questions.py  # 正規表示法解析 → data/<year>.json
│   ├── latex_convert.py    # 加入 LaTeX 欄位（stem_latex / options_latex）
│   ├── crop_figures.py     # 向量圖裁切 → pic/
│   └── check_quality.py    # 驗證腳本
├── data/                   # 結構化題庫 JSON
├── assets/<year>/pages/    # 頁面渲染圖
├── pic/                    # 裁切圖表（item/ 子目錄放圖片選項）
└── web/                    # 前端閱讀器
```

### 執行順序

```bash
cd math
python pipeline/extract_all.py         # 1. 文字擷取
python pipeline/extract_images.py       # 2. 頁面渲染
python pipeline/parse_questions.py      # 3. 解析題目 → data/115.json
python pipeline/latex_convert.py        # 4. LaTeX 轉換
python pipeline/crop_figures.py         # 5. 圖表裁切
python pipeline/check_quality.py        # 6. 驗證
```

---

## 2. PDF 文字擷取（extract_all.py）

### 工具選擇
- **使用 PyMuPDF（fitz）**，不可用 pdfplumber。
- pdfplumber 在 CID-encoded CJK 字型上會輸出亂碼。
- PyMuPDF `page.get_text()` 可正確回傳中文。

### 實務要點
- 數學科 PDF 有 14 頁，27 題（25 選擇題 + 2 非選擇題）。
- 第 1 頁為作答說明，需跳過（從「第一部分：選擇題」開始）。
- 第 14 頁為參考公式，需從非選擇題的題幹中切除（`re.sub(r'\n參考公式.*$', '', stem)`）。

---

## 3. 題目解析（parse_questions.py）

### 3.1 題型分類

| 題型 | 數量 | 識別方式 |
|------|------|----------|
| 選擇題 | 22 題（Q1-Q22） | 數字後接 `(A)` 選項 |
| 題組子題 | 3 題（Q23-Q25） | 出現在「請閱讀下列選文後，回答23～25題」區塊內 |
| 非選擇題 | 2 題 | 出現在「第二部分：非選擇題」區塊 |

### 3.2 正規表示法切割

#### 題號分割
```python
pattern = re.compile(
    r'(?:^|\n)(\d{1,2})\.(?:\s*\n|\s+)(.*?)(?=\n\d{1,2}\.\s|\Z)',
    re.DOTALL
)
```
- 使用 `\n\d{1,2}\.\s` 作為下一個題目的邊界。
- 題號範圍：Q1-Q22 為單題，Q23-Q25 為題組。

#### 選項解析（parse_choices）

```python
for letter in ['A', 'B', 'C', 'D']:
    if letter == 'D':
        pat = rf'\(D\)\s*(.*?)(?=\n\d{{1,2}}\.\s|\Z)'
    else:
        next_letter = chr(ord(letter) + 1)
        pat = rf'\(letter\)\s*(.*?)(?=\(next_letter\))'
    m = re.search(pat, options_raw, re.DOTALL)
```

### 3.3 已知問題與修復

#### 問題 A：D 選項擷取到圖表標籤與頁碼

**現象**：D 選項內容包含 `圖(一) 2`、`表(一) 3`、`圖(四) 圖(三) 圖(五) 5` 等不該出現的結尾。

**原因**：D 選項的正規表示法以 `\n\d{1,2}\.\s` 為邊界，但 `(D)` 與下一個題號之間會有圖表標籤（`圖(一)`、`表(一)`）、頁碼（`=== PAGE N ===`）、換頁提示（`請翻頁繼續作答`）、以及頁碼數字。

**修復**：`clean_option_tail()` 函數依序清除：
1. 從第一個 `圖(某)`/`表(某)` 到字串結尾（`\s*[圖表]\(\s*...\)\s*.*$` with DOTALL）
2. 從 `\uf026`/`\uFFFD` 替代字元到結尾
3. 頁碼標記（`=== PAGE \d+ ===`）
4. 換頁提示（`請翻頁繼續作答`）
5. 控制字元

```python
def clean_option_tail(opt_text: str) -> str:
    opt_text = re.sub(r'\s*[圖表]\(\s*[一二三四五六七八九十\u3127\d]+\s*\)\s*.*$', '', opt_text, flags=re.DOTALL)
    opt_text = re.sub(r'[\uf026\uFFFD].*$', '', opt_text, flags=re.DOTALL)
    opt_text = re.sub(r'\s*=== PAGE \d+ ===\s*.*$', '', opt_text, flags=re.DOTALL)
    opt_text = re.sub(r'\s*請翻頁繼續作答\s*.*$', '', opt_text, flags=re.DOTALL)
    opt_text = re.sub(r'[\x00-\x1f]+', '', opt_text)
    return opt_text.strip()
```

**影響題號**：Q3, Q6, Q9, Q12, Q15, Q18, Q20, Q22, Q25（D 選項）+ 非選 Q2（題幹）。

#### 問題 B：非選題題幹尾部殘留圖表標籤

**現象**：非選 Q2 題幹結尾出現 `圖(十三) 圖(十四) 13`。

**原因**：現有 `\n\d{1,2}\s*\n` 正規表示法無法匹配結尾無換行的頁碼數字，且圖表標籤與頁碼交錯出現。

**修復**：使用 while 迴圈重複清除直到無變化：

```python
while True:
    old = stem
    stem = re.sub(r'\s*[圖表]\(\s*...\)\s*$', '', stem)
    stem = re.sub(r'\s*=== PAGE \d+ ===\s*$', '', stem)
    stem = re.sub(r'\s*試題結束\s*$', '', stem)
    stem = re.sub(r'\s+\d{1,2}\s*$', '', stem)
    if stem == old:
        break
```

#### 問題 C：題組段落切割

數學科 Q23-Q25 為題組，段落文字可能出現在：
- 第一個子題的 `(D)` 之後（最常見）
- 最後一個子題的 `(D)` 之後（備用方案）
- 第一個子題之前（備用方案）

`split_passage_and_questions()` 依序嘗試三種模式。

#### 問題 D：非選擇題題幹分割

**現象**：非選擇題的題幹包含場景描述 + 子題 (1) + 子題 (2)，全部擠在 `stem` 欄位中，無法分開渲染。

**原因**：parse_questions.py 將非選擇題的整段文字視為單一 `stem`，未分割子題。

**修復**：`split_nonchoice_stem()` 只匹配第一個 `(1)` 和其後第一個 `(2)` 為分割點，
避免子題文字中的 `(1)` 引用（如 `承(1)`）被誤判。**`(1)`/`(2)` 標記保留在子題文字開頭**，確保渲染時題號可見。在 LaTeX 轉換前執行分割。

```python
def split_nonchoice_stem(stem):
    m1 = re.search(r'\s*\(1\)\s*', stem)
    if not m1: return stem, []
    stem_text = stem[:m1.start()]
    rest_after_1 = stem[m1.end():]
    m2 = re.search(r'\s*\(2\)\s*', rest_after_1)
    if not m2: return stem_text, ['(1) ' + rest_after_1.strip()]
    sub_q1 = '(1) ' + rest_after_1[:m2.start()].strip()
    sub_q2 = '(2) ' + rest_after_1[m2.end():].strip()
    return stem_text, [sub_q1, sub_q2]
```

**對話修正歷程**：
1. 初版移除 `(1)`/`(2)` 標記 → 用戶回饋應保留題號
2. 修正為 prepend `(1) ` / `(2) ` 到子題文字前方

**注意事項**：
- 分割後的 `stem`（場景描述）可能不包含 `(1)`/`(2)` 等數學運算子，
  導致 `has_math()` 判定為 False。需以全部前後文（stem + sub_qs）判斷。
- 子題在渲染時以 ❓ emoji + 粗體加大字級呈現，與場景描述明顯區隔。
- `(1)` / `(2)` 在 KaTeX 渲染後為正常括號數字（`$(1)$`）。

#### 問題 E：子題專屬圖表引用

**現象**：非選擇題 Q2 的 `figures` 欄位合併了全部圖表（十三、十四、十五），
但各子題只引用特定圖表：子題 (1) 引用 圖(十四)，子題 (2) 引用 圖(十五)。

**原因**：`figures` 欄位從全文提取，未區分子題層級。

**修復**：
1. 從每個子題文字中提取圖表引用 → `extract_sub_q_figures()`
2. 將各子題的圖表儲存為 `sub_question_figures` 二維陣列
3. 題幹級 `figures` 排序後（中文數字 → int）顯示在題幹下方
4. 各子題的專屬圖表顯示在該子題下方

```python
_FIG_PAT = re.compile(r'[圖表]\(\s*[一二三四五六七八九十\d]+\s*\)')

def extract_sub_q_figures(sub_qs: list) -> list:
    result = []
    for sq in sub_qs:
        figs = _FIG_PAT.findall(sq)
        figs = [re.sub(r'\s+', '', f) for f in figs]  # normalize 圖( 十四)→圖(十四)
        result.append(figs if figs else None)
    return result
```

**渲染順序**（經對話修正）：
```
題幹文字
├── 全部圖形（左→右，中文數字排序）          # 圖(十三) 圖(十四) 圖(十五)
├── 子題 (1) + 專屬圖表                     # 圖(十四)
└── 子題 (2) + 專屬圖表                     # 圖(十五)
```

**對話修正歷程**：
1. 初版將 stem 級圖表放在子題之後 → 用戶回饋應放在題幹結尾下方、第一子題上方
2. 修正為：題幹 → 全部圖表 → 子題（各附專屬圖表）

---

## 4. LaTeX 轉換（latex_convert.py）

### 4.1 轉換流程

```python
def wrap_math(text):
    text = convert_geometry(text)        # 幾何符號
    text = convert_superscripts(text)     # 上標
    text = convert_factor_exponents(text) # 因數分解上標修復
    text = convert_subscripts(text)       # 下標
    text = convert_sqrt(text)            # 根號
    text = MATH_SYMBOLS 取代              # 數學符號
    text = wrap_math_segments(text)       # 包裹 $...$
    return text
```

### 4.2 數學符號對照表

| 原始 | LaTeX | 備註 |
|------|-------|------|
| `×` | `\times` | 乘號 |
| `÷` | `\div` | 除號 |
| `±` | `\pm` | 正負號 |
| `−` | `-` | 減號（Unicode 減號轉 ASCII） |
| `∠` | `\angle` | 角 |
| `°` | `^\circ` | 度 |
| `△` | `\triangle` | 三角形（U+25B3） |
| `∆` | `\triangle` | 三角形（U+2206，increment 符號，PDF 常用） |
| `π` | `\pi` | 圓周率 |
| `√` | `\sqrt{}` | 根號（需後續處理內容） |
| `⊥` | `\perp` | 垂直 |
| `∥` | `\parallel` | 平行 |

### 4.3 上標處理

#### 標準模式
```python
# (expr)2 → (expr)^{2}
text = re.sub(r'\)([23])(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|×|±|=|<|>|≤|≥)', r')^{\1}', text)

# x2 → x^{2}
text = re.sub(r'([a-zA-Z])([23])(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|×|±|=|<|>|≤|≥)', r'\1^{\2}', text)

# 4.4 × 105 → 4.4 × 10^{5}（科學記號）
text = re.sub(r'(\d+)\s*×\s*10(\d)(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|±|=|<|>|≤|≥)', r'\1 \\times 10^{\2}', text)
```

#### 因數分解上標修復（PDF 擷取遺失）

**現象**：`22 × 11` 實際應為 `2² × 11`，PDF 文字擷取時上標字元 ² 遺失。

**觸發條件**：文字包含 `因數`、`倍數`、`質因數` 關鍵字。

**修復**：
```python
def convert_factor_exponents(text: str) -> str:
    if not any(kw in text for kw in ['因數', '倍數', '質因數']):
        return text
    text = re.sub(r'([23])\1\s*×\s*(\d+)', r'\1^{\1} \\times \2', text)
    return text
```

### 4.4 幾何符號轉換

#### 線段符號（`\overline{AB}`）

**觸發條件**：文字包含 `△`、`∠`、`⊥`、`∥`、`菱形`、`平行四邊形`、`正三角形`、`正六邊形`、`正n邊形`、`角柱`、`角平分線`、`半徑`、`直徑`、`線段`、`圓心` 等關鍵字。

**規則**：兩個連續大寫字母，前接空白/逗號/頓號/句號，後接 `=`、`的`、`上`、`為`、`、`、`中`、`與`、`和`、`相交`、`兩線段`、`⊥`、`∥` 等。

```python
text = re.sub(
    r'(?<=[\s,，、。】])([A-Z])([A-Z])(?=\s*(?:[=]|的|上|為|、|中|與|和|相交|兩線段|。|，|⊥|∥|\)))',
    r'\\overline{\1\2}',
    text
)
```

**注意事項**：
- 三角形名稱（`△ABC`）中的 `AB` 不會被轉換，因為後面接 `C` 而非關鍵字。
- 角名稱（`∠ABC`）中的 `AB` 不會被轉換，同理。
- 四邊形名稱（`ABCD`）中的 `AB` 不會被轉換，因為後面接 `C`。

#### 弧符號（`\overset{\frown}{AB}`）

**觸發條件**：文字（或結合題幹文字）包含 `圓` 關鍵字。

**規則**：兩個連續大寫字母後接 `= N°`。

```python
text = re.sub(
    r'([A-Z])([A-Z])(?=\s*=\s*\d+\s*°)',
    r'\\overset{\\frown}{\1\2}',
    text
)
```

**注意事項**：
- 使用 `\overset{\frown}{AB}` 而非 `\overarc{AB}`，因為 KaTeX 0.16.9 不支援 `\overarc`。
- 傳入 `stem_context` 參數以在選項轉換中繼承題幹的圓形上下文。

### 4.5 中文字下標與多行分數

#### 中文字下標

**現象**：PDF 擷取的文字中，`V指`、`V實` 等帶中文字下標的變數被當成一般文字，無法正確渲染為 LaTeX 下標。

**修復**：`convert_chinese_subscripts()` 將 `V指` 轉為 `V_{\text{指}}`，並將行內分數 `V_{\text{實}}/10` 轉為 `\frac{V_{\text{實}}}{10}`。

```python
def convert_chinese_subscripts(text: str) -> str:
    # V + 中文字 → V_{\text{中文字}}
    text = re.sub(r'([A-Z])([一-鿿])', r'\1_{\\text{\2}}', text)
    # 行內分數：V_{\text{實}}/10 → \frac{V_{\text{實}}}{10}
    text = re.sub(r'(V_\{\\text\{[一-鿿]+\}\})/(\d+)', r'\\frac{\1}{\2}', text)
    return text
```

#### 多行分數修復

**現象**：PDF 中的分數以多行呈現（分子、分母、公式行分開），導致公式被截斷。

```
V實
10
V指 − V實 ≤       + 4
```

**修復**：`fix_multiline_fraction()` 將分子/分母重新組合到公式行中。

```python
def fix_multiline_fraction(text: str) -> str:
    def _join_frac(m):
        num, den, formula = m.group(1), m.group(2), m.group(3)
        formula = re.sub(r'(≤)\s+(\+)', rf'\1 {num}/{den} \2', formula)
        return formula
    text = re.sub(r'(\S+)\n(\d+)\n(.+?)(?=\n|$)', _join_frac, text, flags=re.DOTALL)
    return text
```

**注意事項**：
- 此函數必須在所有其他轉換之前執行，因為它依賴原始的換行結構。
- `\text{...}` 區塊中的中文字會被 `_MATH_RUN` 視為中斷點，需在 `wrap_math_segments()` 中使用佔位符保護。

### 4.6 下標處理

```python
# a1 → a_{1}（數列項）
text = re.sub(r'\b([a-zA-Z])(\d)\b', r'\1_{\2}', text)

# an → a_{n}（一般項）
text = re.sub(r'\b([a-zA-Z])([nr])(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|×|±|=)', r'\1_{\2}', text)

# Sn → S_{n}（總和）
text = re.sub(r'\b([A-Z])([n])(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|×|±|=)', r'\1_{\2}', text)
```

### 4.7 數學段包裹與數學偵測

#### `has_math()` — 判斷文字是否包含數學

```python
MATH_INDICATORS = re.compile(
    r'[a-zA-Z][a-zA-Z0-9]*\s*[=+\-*/^()\[\]{}<>≤≥±×÷]|'   # 字母+運算子
    r'\d+\s*[=+\-*/^()×÷]|'                                   # 數字+運算子
    r'[×÷±√∠°△π≤≥∓≈≠∞≡⊥∥]'                                   # 獨立數學符號
)

def has_math(text: str) -> bool:
    if not re.search(r'[a-zA-Z0-9=+\-*/^()×÷±√∠°△π]', text):
        return False   # 完全沒有數學相關字元
    return bool(MATH_INDICATORS.search(text))
```

**對話修正歷程**：
- 初版 `MATH_INDICATORS` 只偵測「字母+運算子」或「數字+運算子」
- Passage 文字含 `×`、`≤` 等獨立數學符號（前後皆為中文），`has_math()` 回傳 False
- 導致 passage 的 `stem_latex` 未生成，bold/emoji 標記也遺失
- **修復**：增加第三條分支 `[×÷±√∠°△π≤≥∓≈≠∞≡⊥∥]`，捕捉獨立數學符號

#### `wrap_math_segments()` — 數學段 $ 包裹

使用 `_MATH_RUN` 正規表示法（非 CJK 字元連續區段）偵測數學內容，並包裹 `$...$`：

```python
_BREAK_CHARS = '\u4e00-\u9fff\u3000-\u303f\uff00-\uff65「」『』（）《》〈〉﹒～\n'
_MATH_RUN = re.compile(r'[^' + _BREAK_CHARS + ']+')
```

僅包裹包含字母、數字或反斜線的區段（純空白/標點不包裹）。

**注意事項**：
- `\n` 已加入 `_BREAK_CHARS`，確保換行符會中斷數學段，避免跨行公式被錯誤包裹。
- `\text{...}` 區塊中的中文字會被視為中斷點，需使用佔位符（`\x00TEXT{}`）保護後再恢復。

---

## 5. 圖表裁切（crop_figures.py）

### 5.1 類型與方法

| 類型 | 方法 | 說明 |
|------|------|------|
| 圖（Figure） | 向量繪圖聚合 | 文字標籤偵測 → 鄰近向量繪圖 bbox 合併 |
| 表（Table） | 同上 + 線條偵測 | 額外偵測水平/垂直線條防止截斷 |
| 並排圖 | x 權重匹配 | 圖(十三)+(十四) 分離 |

### 5.2 命名規則

- `{year}p{NN:02d}.jpg` — 圖（如 `115p01.jpg`）
- `{year}t{NN:02d}.jpg` — 表（如 `115t01.jpg`）
- `{year}p{NN:02d}i.jpg` — 圖片選項（如 `11527i.jpg`）

### 5.3 向量圖 vs 點陣圖

- 數學科：**向量繪圖**（`doc.get_page_pixmap(clip=bbox)` 直接裁切）
- 社會科：**嵌入點陣圖**（`page.get_images()` + `doc.extract_image()`）

### 5.4 圖表排序

數學試卷的圖表以中文數字編號（一～十五），程式內按數值排序：

```python
_CN_DIGITS = {'一':1, '二':2, '三':3, '四':4, '五':5, '六':6, '七':7, '八':8, '九':9, '十':10}

def _chinese_to_int(s: str) -> int:
    s = s.strip()
    if s.isdigit(): return int(s)
    if s in _CN_DIGITS and s != '十': return _CN_DIGITS[s]
    if '十' in s:
        parts = s.split('十')
        tens = _CN_DIGITS.get(parts[0], 1) if parts[0] else 1
        ones = _CN_DIGITS.get(parts[1], 0) if parts[1] else 0
        return tens * 10 + ones
    return 0

def _fig_sort_key(fig: str) -> int:
    m = re.search(r'[圖表]\(\s*([^)]+)\s*\)', fig)
    return _chinese_to_int(m.group(1)) if m else 0

# 使用：sorted(figures, key=_fig_sort_key)
```

**注意**：排序在 `latex_convert.py` 的 `process_year()` 中對非選擇題自動執行。

---

## 6. 資料結構（JSON Schema）

```json
{
  "number": 1,
  "type": "選擇題" | "題組子題" | "非選擇題",
  "group_range": [23, 25] | null,
  "group_id": "23-25" | null,
  "stem": "解二元一次聯立方程式 x + 2y = 5 ...",
  "stem_latex": "解二元一次聯立方程式 $x + 2y = 5 ...$",
  "options": {"A": "−4", "B": "−2", "C": "2", "D": "4"},
  "options_latex": {"A": "$-4$", "B": "$-2$", "C": "$2$", "D": "$4$"},
  "passage": "閱讀選文..." | null,
  "passage_latex": "閱讀選文..." | null,
  "passage_figures": ["圖(十二)"],
  "figures": ["圖(一)"],
  "tables": ["表(一)"],
  "image_options": "11527i.jpg" | null,
  "image_options_full": true | false | null,
  "sub_questions": ["(1) 子題一...", "(2) 子題二..."] | null,
  "sub_questions_latex": ["$(1)$ 子題一...", "$(2)$ 子題二..."] | null,
  "sub_question_figures": [["圖(十四)"], ["圖(十五)"]] | null
}
```

### 欄位說明

| 欄位 | 說明 |
|------|------|
| `stem` | 原始題幹文字（保留 PDF 擷取原始內容） |
| `stem_latex` | LaTeX 轉換後題幹（KaTeX 可渲染）；`null` 表示無需轉換 |
| `options` | 原始選項文字 |
| `options_latex` | LaTeX 轉換後選項（逐字母）；`null` 表示該選項無需轉換 |
| `passage` | 題組段落文字 |
| `passage_latex` | 題組段落 LaTeX 版 |
| `figures` / `tables` | 題幹引用的圖表編號（排序後，左→右） |
| `passage_figures` | 段落引用的圖表（僅用於題組） |
| `image_options` | 圖片選項的檔案名稱（如 `"11527i.jpg"`） |
| `image_options_full` | `true`=全部選項為圖片；`false`=A-C 圖片 D 文字；`null`=非圖片選項 |
| `sub_questions` | **非選擇題專用**：子題文字陣列，含 `(1)`/`(2)` 前綴 |
| `sub_questions_latex` | 子題 LaTeX 版；`null` 表示無需轉換 |
| `sub_question_figures` | **非選擇題專用**：各子題的專屬圖表引用（二維陣列） |

---

## 7. 驗證（check_quality.py）

### 檢查項目
- 題數總計（27 題：25 選擇 + 2 非選）
- 題號連續性（無遺漏題號）
- 每題是否都有選項（非選題除外）
- 圖表引用是否都在 assets 中有對應檔案
- 題組結構是否正確（Q23-Q25 的 `group_id` 一致）

---

## 8. 已知脆弱點與應對策略

### 8.1 D 選項邊界

**風險**：D 選項使用 `\n\d{1,2}\.\s` 為邊界，但圖表標籤和頁碼夾在 D 選項與下一個題號之間。

**對策**：`clean_option_tail()` 積極清除所有非內容的結尾資料。

### 8.2 PDF 上標遺失

**風險**：上標字元（², ³）在 PDF 文字擷取中可能遺失或變成普通數字。

**對策**：`convert_factor_exponents()` 在因數分解上下文中將 `22 × 11` 轉為 `2^{2} \times 11`。

### 8.3 幾何符號偵測

**風險**：線段符號（`AB` 應為 `\overline{AB}`）和弧符號（`AB` 應為 `\overset{\frown}{AB}`）在純文字中無法區分。

**對策**：
- 依賴上下文關鍵字（`△`、`∠`、`圓` 等）決定啟用哪種轉換。
- 使用 `stem_context` 參數將題幹的幾何上下文傳遞給選項轉換。

### 8.4 非選題結尾

**風險**：非選題題幹的結尾可能包含圖表標籤、頁碼、試題結束標記等。

**對策**：使用 `while True` 迴圈重複清除，直到無變化。

### 8.5 LaTeX 相容性

**風險**：部分 LaTeX 指令（如 `\overarc`）在 KaTeX 中不支援。

**對策**：使用 KaTeX 相容的替代方案（`\overset{\frown}{AB}` 代替 `\overarc{AB}`）。

### 8.6 中文字下標與多行分數

**風險**：PDF 中的中文字下標（如 `V指`、`V實`）和多行分數（分子/分母/公式分行）無法正確轉換為 LaTeX。

**對策**：
- `fix_multiline_fraction()` 在所有轉換之前執行，將分行分數重新組合。
- `convert_chinese_subscripts()` 將 `V指` 轉為 `V_{\text{指}}`，並處理行內分數。
- `wrap_math_segments()` 使用佔位符保護 `\text{...}` 區塊，避免中文字中斷數學段。
- `_BREAK_CHARS` 包含 `\n`，確保換行符會中斷數學段。

### 8.7 Unicode 變體

**風險**：PDF 中可能使用不同的 Unicode 字元表示同一符號（如 `△` U+25B3 vs `∆` U+2206）。

**對策**：在 `MATH_SYMBOLS` 中同時收錄所有已知變體。

### 8.8 數學偵測遺漏（has_math 過窄）

**風險**：`has_math()` 只偵測「字母/數字 + 運算子」的模式，會漏掉獨立數學符號
（如 passage 中的 `×`、`≤`）。這會導致 `stem_latex`/`passage_latex` 未被生成，
後續處理（bold/emoji 標記）也一併遺失。

**對策**：在 `MATH_INDICATORS` 增加第三條分支 `[×÷±√∠°△π≤≥∓≈≠∞≡⊥∥]`。

### 8.9 圖表引用空白正規化

**風險**：PDF 文字中圖表引用格式不一致（`圖(十四)` vs `圖( 十四)`），
比對失敗導致圖片渲染時顯示不出對應檔案。

**對策**：`extract_sub_q_figures()` 使用 `re.sub(r'\s+', '', f)` 移除括號內空白。

---
## 9. 開發流程模式：反覆還原（Git Checkout）模式

`latex_convert.py` 是多步驟的後處理腳本，當需要調整其邏輯時，
JSON 資料可能已被前次執行修改（如 stems 已分割、passage_latex 已生成）。
新邏輯無法作用於已修改的資料。

### 標準做法

每次修改 `latex_convert.py` 的資料處理邏輯後，執行以下步驟：

```bash
# 1. 從 git 還原原始 JSON 資料
python -c "
import subprocess, json
result = subprocess.run(['git', 'show', '<original_commit>:math/data/<year>.json'],
                        capture_output=True)
data = json.loads(result.stdout)
# ... 重新施加任何手動標記（如 passage 的 **/⭐ 標記）...
json.dump(data, open('math/data/<year>.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
"

# 2. 重新執行轉換
python math/pipeline/latex_convert.py

# 3. 驗證結果
python math/pipeline/check_quality.py
```

### 適用情境

- 調整 `split_nonchoice_stem()` 邏輯
- 修改 `MATH_INDICATORS` 偵測條件
- 新增或修改 JSON 欄位
- 任何需要在「原始 PDF 解析結果」上重跑的修改

### 避免的模式

- ❌ 直接編輯 `math/data/<year>.json` 後再跑 `latex_convert.py`（重複處理）
- ❌ 在已分割的 stems 上測試新分割邏輯（stems 已無標記，邏輯永遠失敗）
- ✅ 一律從原始 commit 還原 → 施加靜態標記 → 跑轉換

---

## 10. 前端注意事項

`latex_convert.py` 是多步驟的後處理腳本，當需要調整其邏輯時，
JSON 資料可能已被前次執行修改（如 stems 已分割、passage_latex 已生成）。
新邏輯無法作用於已修改的資料。

### 標準做法

每次修改 `latex_convert.py` 的資料處理邏輯後，執行以下步驟：

```bash
# 1. 從 git 還原原始 JSON 資料
python -c "
import subprocess, json
result = subprocess.run(['git', 'show', '<original_commit>:math/data/<year>.json'],
                        capture_output=True)
data = json.loads(result.stdout)
# ... 重新施加任何手動標記（如 passage 的 **/⭐ 標記）...
json.dump(data, open('math/data/<year>.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
"

# 2. 重新執行轉換
python math/pipeline/latex_convert.py

# 3. 驗證結果
python math/pipeline/check_quality.py
```

### 適用情境

- 調整 `split_nonchoice_stem()` 邏輯
- 修改 `MATH_INDICATORS` 偵測條件
- 新增或修改 JSON 欄位
- 任何需要在「原始 PDF 解析結果」上重跑的修改

### 避免的模式

- ❌ 直接編輯 `math/data/<year>.json` 後再跑 `latex_convert.py`（重複處理）
- ❌ 在已分割的 stems 上測試新分割邏輯（stems 已無標記，邏輯永遠失敗）
- ✅ 一律從原始 commit 還原 → 施加靜態標記 → 跑轉換

---


### 9.1 KaTeX 版本
- 使用 KaTeX 0.16.9（CDN 載入）
- 需同時載入 `katex.min.css`、`katex.min.js`、`auto-render.min.js`

### 9.2 渲染順序
- 優先使用 `stem_latex` / `options_latex`（含 `$...$` 的完整 LaTeX 字串）
- 無 `..._latex` 欄位時使用 `stem` / `options`（純文字）

### 9.3 圖片選項
- `image_options` 非 `null` 時，使用專用圖片選項渲染器
- 顯示 4 個字母按鈕（A/B/C/D）+ 對應圖片
- `image_options_full` 控制 D 選項是否也為圖片

### 9.4 粗體與 Emoji 重點標記

支援在 JSON 文字欄位中使用 `**...**` 標記粗體，渲染時自動轉換為 `<strong>`：

```javascript
markBold(s) {
    return String(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
},
```

**使用方式**（passage 欄位）：
```
⭐ **實際速率＝輪胎轉速 × 輪胎周長** ⭐
```

**渲染流程**：
1. `esc()` 先轉義 `&<>`（保留 `$` 供 KaTeX 使用）
2. `markBold()` 將 `**...**` 轉為 `<strong>`
3. 最終插入 DOM 後由 `renderMathInElement` 處理 KaTeX

**注意**：`esc()` 和 `markBold()` 的執行順序不可互換 — 先 escape 再 markBold，
避免 `<strong>` 被 escape 破壞。

### 9.5 非選擇題渲染結構

非選擇題的 DOM 結構（與選擇題/題組完全分離的渲染分支）：

```
<div class="q-card">
  <div class="q-header">非選1 / 非選2</div>
  <div class="q-stem">場景描述文字...</div>
  
  <!-- 題幹級圖表：全部圖形，左→右 -->
  <div class="q-figures">圖(十三) 圖(十四) 圖(十五)</div>
  
  <!-- 子題容器：每題為獨立卡片 -->
  <div class="q-sub-questions">
    <div class="q-sub-question">
      <span class="q-sub-q-marker">❓</span>
      <span class="q-sub-q-text">(1) 子題文字...</span>
    </div>
    <div class="q-figures">圖(十四)</div>      <!-- 子題專屬圖表 -->
    
    <div class="q-sub-question">
      <span class="q-sub-q-marker">❓</span>
      <span class="q-sub-q-text">(2) 子題文字...</span>
    </div>
    <div class="q-figures">圖(十五)</div>      <!-- 子題專屬圖表 -->
  </div>
  
  <div class="answer-placeholder">...</div>
</div>
```

**CSS 關鍵樣式**：
```css
.q-sub-question {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 14px 18px; background: #f8f9fb;
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);  /* 紅色左邊框 */
    border-radius: 8px;
}
.q-sub-q-text { font-size: 1.1rem; font-weight: 700; }
.q-sub-question + .q-figures { margin-top: -6px; padding-left: 48px; }
```

**對話修正歷程**：
1. 初版全部圖表放在子題之後 → 用戶回饋應在題幹下方、第一子題上方
2. 修正後題幹級圖表移到 `q-stem` 與 `q-sub-questions` 之間