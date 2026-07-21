#!/usr/bin/env python3
"""
Convert math expressions in question bank JSON to LaTeX format.
Adds stem_latex and options_latex fields to each question.
Uses KaTeX-compatible syntax for frontend rendering.

Usage: python math/pipeline/latex_convert.py
"""
import re
import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, 'data')

# ──  Math symbol mapping ────────────────────────────────────────────

MATH_SYMBOLS = {
    '×': r' \times ',
    '÷': r' \div ',
    '±': r' \pm ',
    '∓': r' \mp ',
    '∠': r'\angle ',
    '°': r'^\circ ',
    '△': r'\triangle ',
    '∆': r'\triangle ',
    'π': r'\pi ',
    '√': r'\sqrt{}',
    '∞': r'\infty ',
    '≈': r'\approx ',
    '≠': r'\neq ',
    '≤': r'\leq ',
    '≥': r'\geq ',
    '≡': r'\equiv ',
    '⊥': r'\perp ',
    '∥': r'\parallel ',
    '−': '-',  # Unicode minus to ASCII
}

# Patterns that indicate math content (not CJK text)
MATH_INDICATORS = re.compile(
    r'[a-zA-Z][a-zA-Z0-9]*\s*[=+\-*/^()\[\]{}<>≤≥±×÷]|'
    r'\d+\s*[=+\-*/^()×÷]|'
    r'[×÷±√∠°△π≤≥∓≈≠∞≡⊥∥]'
)


def has_math(text: str) -> bool:
    """Check if text contains math expressions."""
    # Skip pure CJK text
    if not re.search(r'[a-zA-Z0-9=+\-*/^()×÷±√∠°△π]', text):
        return False
    # Must have at least one math-like pattern
    return bool(MATH_INDICATORS.search(text))


def convert_superscripts(text: str) -> str:
    """Convert inline superscript digits to LaTeX ^ notation."""
    # Handle (expr)2, (expr)3 — exponent after closing paren
    text = re.sub(r'\)([23])(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|×|±|=|<|>|≤|≥)', r')^{\1}', text)

    # Handle single letter + single digit exponent: x2, y3, a2, b2
    # But avoid matching things like a1, a2 (these are subscripts in sequences)
    # In math exam context, x2 is almost always x^2, not x_2
    text = re.sub(
        r'([a-zA-Z])([23])(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|×|±|=|<|>|≤|≥)',
        r'\1^{\2}',
        text
    )

    # Handle digit+letter+digit exponent: 4x2, 10x3, 2a2
    text = re.sub(
        r'(\d)([a-zA-Z])([23])(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|×|±|=)',
        r'\1\2^{\3}',
        text
    )

    # Handle specific power patterns from exam:
    # 4.4 × 105 -> 4.4 × 10^{5}
    # 7.3 × 106 -> 7.3 × 10^{6}
    # 5.4 × 107 -> 5.4 × 10^{7}
    # 1.7 × 105-108 -> 1.7 × 10^{5-8}
    text = re.sub(
        r'(\d+)\s*×\s*10(\d)(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|±|=|<|>|≤|≥)',
        r'\1 \\times 10^{\2}',
        text
    )

    # Handle (1.025)7 and (1.025)8
    text = re.sub(r'\)([78])(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|×|±|=)', r')^{\1}', text)

    # Handle r2 (circle area), c2 (Pythagorean)
    text = re.sub(
        r'\b([rc])([23])(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|×|±|=)',
        r'\1^{\2}',
        text
    )

    return text


def convert_factor_exponents(text: str) -> str:
    """Fix superscript digits merged with base in factorization context.
    PDF extraction loses ²³ superscripts: "22 × 11" → "2^{2} \\times 11".
    Only fires when text contains factor-related keywords.
    """
    if not any(kw in text for kw in ['因數', '倍數', '質因數']):
        return text

    # Repeated digit like 22 or 33 followed by × and a factor
    text = re.sub(
        r'([23])\1\s*×\s*(\d+)',
        r'\1^{\1} \\times \2',
        text
    )
    return text


def convert_subscripts(text: str) -> str:
    """Convert subscript notation in sequences.
    a1, an, ar, Sn, a1r^n-1 etc.
    """
    # a1, a2 (sequence terms)
    text = re.sub(r'\b([a-zA-Z])(\d)\b', r'\1_{\2}', text)

    # an, ar (general terms with letter subscripts)
    text = re.sub(r'\b([a-zA-Z])([nr])(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|×|±|=)', r'\1_{\2}', text)

    # Sn (sum of n terms)
    text = re.sub(r'\b([A-Z])([n])(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|×|±|=)', r'\1_{\2}', text)

    return text


def convert_sqrt(text: str) -> str:
    r"""Convert square root notation.
    √504 -> \sqrt{504}
    """
    # √ followed by expression in braces or by numbers/letters
    # Handle √(expression) -> \sqrt{expression}
    text = re.sub(r'√\(([^)]+)\)', r'\\sqrt{\1}', text)
    # Handle √number -> \sqrt{number}
    text = re.sub(r'√(\d+)', r'\\sqrt{\1}', text)
    # Handle √a -> \sqrt{a}
    text = re.sub(r'√([a-zA-Z])', r'\\sqrt{\1}', text)

    return text


def convert_fractions(text: str) -> str:
    """Convert simple inline fractions to LaTeX \frac{}{}.
    Only handles clear cases to avoid false positives.
    """
    # Pattern: (expr1)/(expr2) where both are simple
    # We skip this for now — fractions in the exam are rare and complex
    return text


def fix_multiline_fraction(text: str) -> str:
    """Fix fractions split across lines by PDF extraction.

    PDF renders fractions as:
        V實
        10
        V指 − V實 ≤       + 4

    This joins the numerator/denominator back into the formula line:
        V指 − V實 ≤ V實/10 + 4

    The formula is wrapped in $$...$$ for display math.
    """
    # Pattern: numerator\ndenominator\nformula_line
    # Insert the fraction into the formula at the ≤...<gap>+ position
    def _join_frac(m):
        num = m.group(1)
        den = m.group(2)
        formula = m.group(3)
        # Insert fraction: "≤       + 4" → "≤ V實/10 + 4"
        formula = re.sub(r'(≤)\s+(\+)', rf'\1 {num}/{den} \2', formula)
        return formula

    text = re.sub(
        r'(\S+)\n(\d+)\n(.+?)(?=\n|$)',
        _join_frac,
        text,
        flags=re.DOTALL
    )
    return text


def convert_chinese_subscripts(text: str) -> str:
    """Convert Chinese subscripts to LaTeX notation.

    V指 → V_{\\text{指}}
    V實 → V_{\\text{實}}
    Also converts inline fraction: V_{\\text{實}}/10 → \\frac{V_{\\text{實}}}{10}
    """
    # V + single CJK character as subscript
    text = re.sub(
        r'([A-Z])([一-鿿])',
        r'\1_{\\text{\2}}',
        text
    )
    # Inline fraction: V_{\text{實}}/10 → \frac{V_{\text{實}}}{10}
    text = re.sub(
        r'(V_\{\\text\{[一-鿿]+\}\})/(\d+)',
        r'\\frac{\1}{\2}',
        text
    )
    return text


def convert_geometry(text: str, stem_context: str = '') -> str:
    """Convert geometry notation to LaTeX in geometry context.
    - Line segments: AB → \\overline{AB} in geometry context
    - Arcs: AB = 87° → \\overarc{AB} = 87^\\circ in circle context
    Uses stem_context for circle detection when text lacks circle keywords.
    """
    # Combine text and stem context for circle detection
    combined = text + ' ' + stem_context

    # Arc notation: in circle context, two-letter pairs followed by = N°
    if '圓' in combined:
        text = re.sub(
            r'([A-Z])([A-Z])(?=\s*=\s*\d+\s*°)',
            r'\\overset{\\frown}{\1\2}',
            text
        )

    # Line segment notation: two uppercase letters in geometry context
    if any(kw in combined for kw in [
        '△', '∠', '⊥', '∥', '菱形', '平行四邊形', '正三角形', '正六邊形',
        '正n邊形', '角柱', '角平分線', '半徑', '直徑', '線段', '圓心'
    ]):
        # Two uppercase letters preceded by space/start/comma/punctuation
        # and followed by =, 的, 上, 為, 、, 中, 與, 和, 相交, 兩線段, etc.
        text = re.sub(
            r'(?<=[\s,，、。】])([A-Z])([A-Z])(?=\s*(?:[=]|的|上|為|、|中|與|和|相交|兩線段|。|，|⊥|∥|\)))',
            r'\\overline{\1\2}',
            text
        )
        # Also handle line segments at start of text
        text = re.sub(
            r'^([A-Z])([A-Z])(?=\s*(?:[=]|的|上|為|、|中|與|和|相交|兩線段))',
            r'\\overline{\1\2}',
            text
        )

    return text


def wrap_math(text: str, stem_context: str = '') -> str:
    """Convert math symbols to LaTeX and wrap math segments in $...$.
    Preserves CJK text as-is outside the $ delimiters.
    """
    # Fix multi-line fractions BEFORE any other conversion
    text = fix_multiline_fraction(text)

    # Convert Chinese subscripts BEFORE other conversions
    text = convert_chinese_subscripts(text)

    # Convert geometry notation FIRST (before other conversions)
    text = convert_geometry(text, stem_context)

    # Convert superscripts (before symbol replacement destroys patterns)
    text = convert_superscripts(text)

    # Fix merged superscripts in factorization context
    text = convert_factor_exponents(text)

    # Convert subscripts
    text = convert_subscripts(text)

    # Convert square roots
    text = convert_sqrt(text)

    # Then handle math symbols
    for old, new in MATH_SYMBOLS.items():
        text = text.replace(old, new)

    # Wrap math segments in $...$
    text = wrap_math_segments(text)

    # Clean up multiple spaces
    text = re.sub(r'  +', ' ', text).strip()

    return text


# Characters that break a math segment (CJK ideographs + CJK punctuation + newline)
_BREAK_CHARS = '\u4e00-\u9fff\u3000-\u303f\uff00-\uff65「」『』（）《》〈〉﹒～\n'
_MATH_RUN = re.compile(r'[^' + _BREAK_CHARS + ']+')

# Placeholder for \text{...} blocks during segment wrapping
_TEXT_PLACEHOLDER = '\x00TEXT{}'


def wrap_math_segments(text: str) -> str:
    """Wrap non-CJK runs containing math content in $...$.

    A run is wrapped if it contains at least one letter, digit, or backslash
    (i.e. it is not just spaces/punctuation between CJK text).
    Handles \\text{...} blocks by temporarily replacing them.
    """
    # Protect \text{...} blocks from segment splitting
    text_blocks = []
    def _save_text_block(m):
        text_blocks.append(m.group(0))
        return _TEXT_PLACEHOLDER
    text = re.sub(r'\\text\{[^}]*\}', _save_text_block, text)

    def repl(m):
        seg = m.group(0)
        if '$' in seg:  # already wrapped
            return seg
        if not re.search(r'[a-zA-Z0-9\\]', seg):
            return seg  # spaces/punctuation only — leave outside
        stripped = seg.strip()
        if not stripped:
            return seg
        lead = seg[:len(seg) - len(seg.lstrip())]
        trail = seg[len(seg.rstrip()):]
        return f'{lead}${stripped}${trail}'

    text = _MATH_RUN.sub(repl, text)

    # Restore \text{...} blocks
    for block in text_blocks:
        text = text.replace(_TEXT_PLACEHOLDER, block, 1)

    return text


def latexify_stem(stem: str) -> str:
    """Convert a question stem to LaTeX-enriched text."""
    if not has_math(stem):
        return stem

    return wrap_math(stem)


def latexify_option(opt: str, stem: str = '') -> str:
    """Convert an option text to LaTeX-enriched text.
    Uses stem context for geometry detection (e.g., circle context for arcs).
    """
    if not has_math(opt) and not has_math(stem):
        return opt

    # If stem has math/geometry context, pass it to wrap_math for option conversion
    return wrap_math(opt, stem)


def split_nonchoice_stem(stem: str):
    """Split non-choice question stem into description and sub-questions.

    Non-choice questions have form:
        description... (1) sub-question 1... (2) sub-question 2...

    Only the FIRST (1) and the FIRST (2) after (1) are treated as markers.
    Any later (1)/(2) inside sub-question text (e.g. "承 (1)") are preserved.
    The markers (1)/(2) are included in the sub-question text for rendering.
    Returns (stem_text, [sub_q1, sub_q2, ...])
    """
    m1 = re.search(r'\s*\(1\)\s*', stem)
    if not m1:
        return stem, []

    stem_text = stem[:m1.start()]
    rest_after_1 = stem[m1.end():]

    m2 = re.search(r'\s*\(2\)\s*', rest_after_1)
    if not m2:
        return stem_text, ['(1) ' + rest_after_1.strip()]

    sub_q1 = '(1) ' + rest_after_1[:m2.start()].strip()
    sub_q2 = '(2) ' + rest_after_1[m2.end():].strip()
    return stem_text.strip(), [sub_q1, sub_q2]


# ──  Figure helpers ───────────────────────────────────────────────────

_CN_DIGITS = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
              '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
_CN_NUM_PAT = re.compile(r'[圖表]\(\s*([^)]+)\s*\)')


def _chinese_to_int(s: str) -> int:
    """Convert Chinese numeral string to int. 一→1, 十二→12, 二十三→23."""
    s = s.strip()
    if s.isdigit():
        return int(s)
    # Single digit
    if s in _CN_DIGITS and s != '十':
        return _CN_DIGITS[s]
    # Tens (十, 二十, 三十...)
    if '十' in s:
        parts = s.split('十')
        tens = _CN_DIGITS.get(parts[0], 1) if parts[0] else 1
        ones = _CN_DIGITS.get(parts[1], 0) if parts[1] else 0
        return tens * 10 + ones
    return 0


def _fig_sort_key(fig: str) -> int:
    """Extract numeric sort key from 圖(N) or 表(N)."""
    m = _CN_NUM_PAT.search(fig)
    if m:
        return _chinese_to_int(m.group(1))
    return 0


_FIG_PAT = re.compile(r'[圖表]\(\s*[一二三四五六七八九十\d]+\s*\)')


def extract_sub_q_figures(sub_qs: list) -> list:
    """Extract figure references from each sub-question text."""
    result = []
    for sq in sub_qs:
        figs = _FIG_PAT.findall(sq)
        figs = [re.sub(r'\s+', '', f) for f in figs]
        result.append(figs if figs else None)
    return result


# ──  Main processing ────────────────────────────────────────────────

def process_year(year: str) -> None:
    json_path = os.path.join(DATA_DIR, f'{year}.json')
    if not os.path.exists(json_path):
        print(f'{year}: data file not found')
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    modified = 0
    for q in questions:
        # ──  Non-choice: split stem before LaTeX conversion ──────────
        if q['type'] == '非選擇題':
            stem_text, sub_qs = split_nonchoice_stem(q['stem'])
            q['stem'] = stem_text
            q['sub_questions'] = sub_qs

            # Sort all figures by number (left to right)
            if q.get('figures'):
                q['figures'] = sorted(q['figures'], key=_fig_sort_key)
            if q.get('tables'):
                q['tables'] = sorted(q['tables'], key=_fig_sort_key)

            # Extract per-sub-question figure references
            q['sub_question_figures'] = extract_sub_q_figures(sub_qs)

            # Check math presence on the FULL original text so that
            # numbers in the description (400, 5, 2...) get converted
            full_original = q['stem'] + ' ' + ' '.join(sub_qs) if sub_qs else q['stem']
            has_math_ctx = has_math(stem_text) or has_math(full_original)

            if has_math_ctx:
                latex_stem = wrap_math(stem_text)
                q['stem_latex'] = latex_stem if latex_stem != stem_text else None

                sub_qs_latex = []
                for sq in sub_qs:
                    sq_latex = wrap_math(sq)
                    sub_qs_latex.append(sq_latex if sq_latex != sq else sq)
                q['sub_questions_latex'] = (
                    sub_qs_latex
                    if any(a != b for a, b in zip(sub_qs_latex, sub_qs))
                    else None
                )
            else:
                q['stem_latex'] = None
                q['sub_questions_latex'] = None
            modified += 1

        else:
            q['sub_questions'] = None
            q['sub_questions_latex'] = None
            q['sub_question_figures'] = None

            # Convert stem
            original_stem = q['stem']
            latex_stem = latexify_stem(original_stem)
            if latex_stem != original_stem:
                q['stem_latex'] = latex_stem
                modified += 1
            else:
                q['stem_latex'] = None

        # Convert options
        if q.get('options'):
            latex_opts = {}
            opts_modified = False
            for letter, text in q['options'].items():
                latex_opt = latexify_option(text, q['stem'])
                if latex_opt != text:
                    latex_opts[letter] = latex_opt
                    opts_modified = True
                else:
                    latex_opts[letter] = None
            if opts_modified:
                q['options_latex'] = latex_opts
                modified += 1
            else:
                q['options_latex'] = None
        else:
            q['options_latex'] = None

        # Convert passage (group questions)
        if q.get('passage'):
            latex_passage = latexify_stem(q['passage'])
            if latex_passage != q['passage']:
                q['passage_latex'] = latex_passage
            else:
                q['passage_latex'] = None
        else:
            q['passage_latex'] = None

    # Save back
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f'{year}: {modified} questions with LaTeX expressions')


def main():
    years = sys.argv[1:] if len(sys.argv) > 1 else ['115']
    for year in years:
        process_year(year)


if __name__ == '__main__':
    main()
