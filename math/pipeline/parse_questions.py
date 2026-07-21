#!/usr/bin/env python3
"""
Parse math exam text into structured JSON question bank.
25 multiple choice + 2 non-calculator questions.
Handles LaTeX conversion, group passages (Q23-25), and figure attribution.
"""
import re
import json
import sys
import os

# Force stdout to be utf-8 on Windows
sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT_DIR, 'data')

# ──  LaTeX conversion helpers ───────────────────────────────────────

def convert_superscripts(text: str) -> str:
    """Convert inline superscript digits to LaTeX ^ notation.
    e.g. '4x2 − 3x − 5' -> '4x^2 - 3x - 5'
    Handles common patterns in math exam text.
    """
    # Common patterns: digit followed by space or end -> superscript
    # x2 -> x^2, x3 -> x^3, an -> a_n, etc.
    # Pattern: letter followed by 1-3 digits that look like exponents
    # We target specific patterns found in the exam

    # Handle (1.025)7 and (1.025)8 — exponent after closing paren
    text = re.sub(r'\)\s*(\d)\b', r')^{\1}', text)

    # Handle x2, y2, z2 (single letter + single digit exponent)
    text = re.sub(r'([a-zA-Z])([23])(?=\s|$|,|;|，|。|\)|\(|\+|\-|\*|/|÷|×|±|=)', r'\1^{\2}', text)

    # Handle a1, an, an (subscripts in sequences like a1, an, ar)
    text = re.sub(r'\b([a-zA-Z])([nr])\b', r'\1_{\2}', text)

    # Handle powers: r2, r3, c2 (Pythagorean, circle area, etc.)
    text = re.sub(r'\b([rc])([23])\b', r'\1^{\2}', text)

    # Handle specific exam patterns like 2x2, 10x, ax2, bx2
    text = re.sub(r'\b(\d+)([a-zA-Z])([23])\b', r'\1\2^{\3}', text)

    # Handle (x + 5)2 style
    text = re.sub(r'\)\s*([23])\s', r')^{\1} ', text)

    # Handle square root patterns: b2 -> b^2 (for sqrt content)
    # Handle: x = −b ± √(b^2 − 4ac) / 2a pattern
    # The reference formula has: x = −b ± b 2 − 4 a c / 2a
    # We handle the sqrt pattern separately

    return text


def convert_fractions(text: str) -> str:
    """Convert inline fraction patterns to LaTeX.
    e.g. 'n(a1 + an)/2' -> '\\frac{n(a_1 + a_n)}{2}'
    """
    # Pattern: Sn = n ( a1 + an ) / 2 — common formula pattern
    # This is complex; we handle it in post-processing

    # Simple fraction: number/number or letter/letter at end of expression
    # We only convert clear cases to avoid false positives
    return text


def latexify_math(text: str) -> str:
    """Convert plain math text to LaTeX format.
    Conservative approach: wrap math expressions in $ delimiters.
    """
    # Clean up whitespace
    text = text.strip()

    # Convert superscripts
    text = convert_superscripts(text)

    # Common LaTeX conversions
    text = text.replace('×', r' \times ')
    text = text.replace('÷', r' \div ')
    text = text.replace('±', r' \pm ')
    text = text.replace('∠', r'\angle ')
    text = text.replace('°', r'^\circ ')
    text = text.replace('−', '-')
    text = text.replace('π', r'\pi ')
    text = text.replace('△', r'\triangle ')
    text = text.replace('√', r'\sqrt{}')

    # Clean up multiple spaces
    text = re.sub(r'  +', ' ', text).strip()

    return text


def stem_to_latex(stem: str) -> str:
    """Convert a question stem to LaTeX-enriched text.
    Wraps math expressions in $ delimiters for KaTeX rendering.
    """
    # Don't modify if already has LaTeX markers
    if '$' in stem:
        return stem

    # Simple approach: identify math expressions and wrap in $...$
    # Math expressions: contain variables, operators, numbers mixed together
    # Chinese text stays as-is

    # For now, apply conservative conversion to the full stem
    # Frontend will use KaTeX auto-render for inline math
    result = stem

    # Convert known math patterns
    result = convert_superscripts(result)

    # Convert operator symbols to LaTeX equivalents for KaTeX
    # Keep as unicode where KaTeX can handle them
    result = result.replace('−', '-')  # minus sign

    return result


# ──  Figure/table reference extraction ──────────────────────────────

def extract_figures(text: str) -> list[str]:
    """Extract all 圖(N) references from text. Handles whitespace inside parens."""
    refs = re.findall(r'圖\(\s*[一二三四五六七八九十\u3127\d]+\s*\)', text)
    # Normalize: remove internal whitespace
    return list(set(re.sub(r'\s+', '', r) for r in refs))


def extract_tables(text: str) -> list[str]:
    """Extract all 表(N) references from text. Handles whitespace inside parens."""
    refs = re.findall(r'表\(\s*[一二三四五六七八九十\u3127\d]+\s*\)', text)
    return list(set(re.sub(r'\s+', '', r) for r in refs))


# ──  Question parsing ───────────────────────────────────────────────

def clean_control_chars(text: str) -> str:
    return re.sub(r'[\x00-\x09\x0b-\x1f]', '', text)


def clean_option_tail(opt_text: str) -> str:
    """Remove trailing figure/table labels, page markers, boilerplate, and metadata."""
    # Strip everything from first figure/table label onwards
    opt_text = re.sub(
        r'\s*[圖表]\(\s*[一二三四五六七八九十\u3127\d]+\s*\)\s*.*$',
        '', opt_text, flags=re.DOTALL
    )
    # Strip from replacement characters (marks footnotes like \uf026)
    opt_text = re.sub(r'[\uf026\uFFFD].*$', '', opt_text, flags=re.DOTALL)
    # Strip page markers
    opt_text = re.sub(r'\s*=== PAGE \d+ ===\s*.*$', '', opt_text, flags=re.DOTALL)
    # Strip boilerplate
    opt_text = re.sub(r'\s*請翻頁繼續作答\s*.*$', '', opt_text, flags=re.DOTALL)
    # Strip remaining control characters
    opt_text = re.sub(r'[\x00-\x1f]+', '', opt_text)
    return opt_text.strip()


def parse_choices(body: str) -> dict:
    """Parse (A)-(D) options from question body text.
    Returns dict with 'stem' and 'options'.
    """
    body = clean_control_chars(body)

    opt_a = body.find('(A)')
    if opt_a == -1:
        return None

    stem = body[:opt_a].strip()
    stem = re.sub(r'\s+', ' ', stem)

    options_raw = body[opt_a:]

    # Primary: capture option text, handling nested parens in math expressions.
    # For A-C: stop at next (X) label. For D: stop at next question number.
    opts = {}
    for letter in ['A', 'B', 'C', 'D']:
        if letter == 'D':
            pat = rf'\({letter}\)\s*(.*?)(?=\n\d{{1,2}}\.\s|\Z)'
        else:
            next_letter = chr(ord(letter) + 1)
            pat = rf'\({letter}\)\s*(.*?)(?=\({next_letter}\))'
        m = re.search(pat, options_raw, re.DOTALL)
        if m:
            opts[letter] = re.sub(r'\s+', ' ', m.group(1).strip())

    return {'stem': stem, 'options': opts}


def find_passage_boundary(text_after_d: str) -> int | None:
    """Find where the reading passage starts after the last (D) option."""
    lines = text_after_d.split('\n')
    cumulative = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        if i == 0:
            cumulative += len(line) + 1
            continue

        if not stripped:
            cumulative += len(line) + 1
            continue

        # Standalone figure/table label (with optional whitespace)
        if re.match(r'^[圖表]\(\s*[一二三四五六七八九十\u3127\d]+\s*\)$', stripped):
            cumulative += len(line) + 1
            continue

        # Pure numeric / tabular data
        if re.match(r'^[\d\s,.\-/%\u3000]+$', stripped):
            cumulative += len(line) + 1
            continue

        # Page markers / boilerplate
        if re.match(
            r'^(=== PAGE \d+ ===|\d{1,2}|請翻頁繼續作答|試題結束|圈/[分小]時為.*)$',
            stripped
        ):
            cumulative += len(line) + 1
            continue

        # Very short line without substantial CJK
        cjk_count = len(re.findall(r'[\u4e00-\u9fff]', stripped))
        if len(stripped) < 6 and cjk_count < 6:
            cumulative += len(line) + 1
            continue

        # Reached passage text
        if cjk_count >= 10:
            return cumulative

        cumulative += len(line) + 1

    return None


def split_passage_and_questions(content: str, q_start: int, q_end: int) -> tuple[str, str]:
    """Split group block into (passage, clean_questions_part).

    For math exams, the passage is often interleaved between sub-questions
    (e.g., passage after Q23's (D), before Q24). We check for passage
    after the FIRST (D) marker, not the last.
    """
    passage = ''
    clean_content = content

    # Math strategy: passage between first (D) and next question number.
    # Extract the passage but keep all sub-questions in clean_content.
    d_matches = list(re.finditer(r'\(D\)', content))
    if d_matches:
        first_d_end = d_matches[0].end()
        # Find next question number after first (D)
        next_q = re.search(rf'\n{q_start + 1}\.\s', content[first_d_end:])
        if next_q:
            between = content[first_d_end:first_d_end + next_q.start()]
            # Check if this between-text is a real passage
            boundary = find_passage_boundary(between)
            if boundary is not None:
                passage = between[boundary:].strip()
                # Rebuild clean_content: Q23 questions + (D) + Q24 onwards
                # Remove the passage from between, keep the rest
                clean_content = (
                    content[:first_d_end + boundary] +
                    content[first_d_end + next_q.start():]
                ).strip()

    # Fallback: passage after last (D) — same as social studies
    if not passage:
        if d_matches:
            last_d_end = d_matches[-1].end()
            after_d = content[last_d_end:]
            boundary = find_passage_boundary(after_d)
            if boundary is not None:
                abs_passage_start = last_d_end + boundary
                passage = content[abs_passage_start:].strip()
                clean_content = content[:abs_passage_start].strip()

    # Fallback: passage before first question
    if not passage:
        first_q_idx = content.find(f'{q_start}.')
        if first_q_idx > 0:
            before_q = content[:first_q_idx].strip()
            before_q = re.sub(r'^請閱讀下列選文.*?\n', '', before_q)
            before_q = re.sub(r'\s*\d{1,2}\s*$', '', before_q).strip()
            if len(before_q) > 20:
                passage = before_q
                clean_content = content[first_q_idx:].strip()

    return passage, clean_content


def parse_noncalc_section(text: str) -> list[dict]:
    """Parse the 非選擇題 section (2 long-form questions)."""
    questions = []

    # Split by question number — handle page boundaries carefully.
    # Q1 body ends before next page number + figure label pattern.
    # Q2 body ends before 參考公式.
    pattern = re.compile(
        r'(?:^|\n)(\d{1})\.(?:\s*\n|\s+)(.*?)(?=\n\d{1}\.\s|\Z)',
        re.DOTALL
    )
    matches = pattern.findall(text)

    for num_str, body in matches:
        qnum = int(num_str)
        body = clean_control_chars(body)

        # Clean the stem
        stem = body.strip()

        # Remove trailing page artifacts: page numbers, figure labels,
        # and reference formula content that leaked in
        # Remove 參考公式 section (everything from 參考公式 onwards)
        stem = re.sub(r'\n參考公式.*$', '', stem, flags=re.DOTALL)
        # Remove trailing page numbers and standalone figure labels at the end
        stem = re.sub(r'\n\d{1,2}\s*\n([圖表]\(\s*[一二三四五六七八九十\u3127\d]+\s*\)\s*\n?)*\s*$', '', stem)
        # Remove formula block lines (start with \uf026 or contain formula patterns)
        stem = re.sub(r'\n\uf026.*$', '', stem, flags=re.DOTALL)

        stem = re.sub(r'\s+', ' ', stem).strip()

        # Extract figures from stem
        all_figs = extract_figures(stem)
        all_tbls = extract_tables(stem)

        # Strip metadata tail: repeat until no more metadata found
        while True:
            old = stem
            stem = re.sub(r'\s*[圖表]\(\s*[一二三四五六七八九十\u3127\d]+\s*\)\s*$', '', stem)
            stem = re.sub(r'\s*=== PAGE \d+ ===\s*$', '', stem)
            stem = re.sub(r'\s*試題結束\s*$', '', stem)
            stem = re.sub(r'\s+\d{1,2}\s*$', '', stem)
            if stem == old:
                break
        stem = stem.strip()

        questions.append({
            'number': qnum,
            'type': '非選擇題',
            'group_range': None,
            'group_id': None,
            'stem': stem,
            'options': None,
            'passage': None,
            'passage_figures': [],
            'passage_figure_pages': {},
            'passage_tables': [],
            'passage_table_pages': {},
            'figures': all_figs,
            'figure_pages': {},
            'tables': all_tbls,
            'table_pages': {},
            'image_options': None,
            'image_options_full': None,
        })

    return questions


# ──  Main parse function ────────────────────────────────────────────

def parse_questions(filepath: str) -> list[dict]:
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = f.read()

    raw = clean_control_chars(raw)

    # Remove page markers and boilerplate
    raw = re.sub(r'=== PAGE \d+ ===', '', raw)
    raw = re.sub(r'請翻頁繼續作答', '', raw)
    raw = re.sub(r'試題結束', '', raw)
    raw = re.sub(r'\n{3,}', '\n\n', raw)

    # Remove instruction page (page 1)
    idx_start = raw.find('第一部分：選擇題')
    if idx_start == -1:
        idx_start = raw.find('第一部分')
    if idx_start > 0:
        raw = raw[idx_start:]

    questions: list[dict] = []

    # Split into 選擇題 and 非選擇題 sections
    noncalc_idx = raw.find('第二部分：非選擇題')
    if noncalc_idx > 0:
        choice_text = raw[:noncalc_idx]
        noncalc_text = raw[noncalc_idx:]
    else:
        choice_text = raw
        noncalc_text = ''

    # Parse 選擇題 (Q1-Q25)
    # Find where the group section starts (e.g. Q23-25 or Q24-25)
    group_match = re.search(r'請閱讀下列選文後\s*，\s*回答\s*(\d+)', choice_text)
    if group_match:
        group_idx = group_match.start()
        q_start = int(group_match.group(1))
        single_text = choice_text[:group_idx]
        group_text = choice_text[group_idx:]
    else:
        q_start = 23  # default fallback
        single_text = choice_text
        group_text = ''

    # Parse single questions
    pattern = re.compile(
        r'(?:^|\n)(\d{1,2})\.(?:\s*\n|\s+)(.*?)(?=\n\d{1,2}\.\s|\Z)',
        re.DOTALL
    )
    matches = pattern.findall(single_text)

    for num_str, body in matches:
        qnum = int(num_str)
        if qnum >= q_start:
            break  # group questions handled separately
        result = parse_choices(body)
        if result and len(result['options']) >= 3:
            stem = result['stem']
            opts = result['options']

            # Clean option tails
            for letter in list(opts.keys()):
                opts[letter] = clean_option_tail(opts[letter])

            # Extract figures from stem
            all_figs = extract_figures(stem)
            all_tbls = extract_tables(stem)

            # Remove standalone figure labels from stem
            stem_clean = re.sub(r'\n[圖表]\(\s*[一二三四五六七八九十\u3127\d]+\s*\)\s*', '', stem).strip()

            questions.append({
                'number': qnum,
                'type': '選擇題',
                'group_range': None,
                'group_id': None,
                'stem': stem_clean,
                'options': opts,
                'passage': None,
                'passage_figures': [],
                'passage_figure_pages': {},
                'passage_tables': [],
                'passage_table_pages': {},
                'figures': all_figs,
                'figure_pages': {},
                'tables': all_tbls,
                'table_pages': {},
                'image_options': None,
                'image_options_full': None,
            })

    # Parse group questions (Q23-Q25) with shared passage
    if group_text:
        # Find group block: 「請閱讀下列選文後，回答23 ～25 題」
        block_pattern = re.compile(
            r'請閱讀下列選文後，回答(\d+)\s*[～~]\s*(\d+)\s*題[：:]?\s*\n'
            r'(.*?)(?=第二部分|\Z)',
            re.DOTALL
        )
        block_match = block_pattern.search(group_text)

        if block_match:
            q_start = int(block_match.group(1))
            q_end = int(block_match.group(2))
            group_id = f'{q_start}-{q_end}'
            content = block_match.group(3)

            # Split passage from questions
            passage, clean_content = split_passage_and_questions(
                content, q_start, q_end
            )

            # Parse sub-questions
            sub_pattern = re.compile(
                r'(?:^|\n)(\d{1,2})\.(?:\s*\n|\s+)(.*?)(?=\n\d{1,2}\.\s|\Z)',
                re.DOTALL
            )
            sub_matches = sub_pattern.findall(clean_content)

            for num_str, body in sub_matches:
                qnum = int(num_str)
                if not (q_start <= qnum <= q_end):
                    continue
                result = parse_choices(body)
                if result and len(result['options']) >= 3:
                    stem = result['stem']
                    opts = result['options']

                    for letter in list(opts.keys()):
                        opts[letter] = clean_option_tail(opts[letter])

                    all_figs = extract_figures(stem)
                    all_tbls = extract_tables(stem)

                    # Remove standalone figure labels from stem
                    stem_clean = re.sub(r'\n[圖表]\([一二三四五六七八九十\u3127\d]+\)\s*', '', stem).strip()

                    # Passage figures
                    passage_figs = extract_figures(passage) if passage else []
                    passage_tbls = extract_tables(passage) if passage else []

                    questions.append({
                        'number': qnum,
                        'type': '題組子題',
                        'group_range': [q_start, q_end],
                        'group_id': group_id,
                        'stem': stem_clean,
                        'options': opts,
                        'passage': passage if passage else None,
                        'passage_figures': passage_figs,
                        'passage_figure_pages': {},
                        'passage_tables': passage_tbls,
                        'passage_table_pages': {},
                        'figures': all_figs,
                        'figure_pages': {},
                        'tables': all_tbls,
                        'table_pages': {},
                        'image_options': None,
                        'image_options_full': None,
                    })

    # Parse 非選擇題 (2 questions)
    if noncalc_text:
        questions += parse_noncalc_section(noncalc_text)

    return questions


# ──  Main ───────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        text_files = [
            os.path.join(ROOT_DIR, 'pipeline', 'output', '115_text.txt')
        ]
    else:
        text_files = sys.argv[1:]

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for filepath in text_files:
        if not os.path.exists(filepath):
            print(f'File not found: {filepath}')
            continue

        basename = os.path.basename(filepath)
        year = basename[:3]

        questions = parse_questions(filepath)

        json_path = os.path.join(OUTPUT_DIR, f'{year}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)

        nums = sorted([q['number'] for q in questions if q['type'] != '非選擇題'])
        noncalc_nums = sorted([q['number'] for q in questions if q['type'] == '非選擇題'])
        total = len(questions)
        mc_count = len(nums)
        nc_count = len(noncalc_nums)

        missing = [n for n in range(1, 26) if n not in nums]

        print(f'{year}: {total} total ({mc_count} 選擇題 + {nc_count} 非選擇題)')
        if missing:
            print(f'  Missing 選擇題: {missing}')
        if mc_count > 0:
            q1 = [q for q in questions if q['type'] == '選擇題'][0]
            print(f'  Q{q1["number"]}: {q1["stem"][:60]}...')
            print(f'  Options: {dict(zip(q1["options"].keys(), [v[:20] for v in q1["options"].values()]))}')
        if nc_count > 0:
            q_nc = [q for q in questions if q['type'] == '非選擇題'][0]
            print(f'  非選Q{q_nc["number"]}: {q_nc["stem"][:60]}...')


if __name__ == '__main__':
    main()
