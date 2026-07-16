#!/usr/bin/env python3
"""
Parse exam text into structured JSON question bank. V4: group-passage extraction,
option-tail cleaning, figure attribution separation.
"""
import re
import json
import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT_DIR, 'data')

# ──  utilities ──────────────────────────────────────────────────────

def clean_control_chars(text: str) -> str:
    """Remove control characters (\\x00-\\x1f except \\n) mixed in by PDF extraction."""
    return re.sub(r'[\x00-\x09\x0b-\x1f]', '', text)


def load_figure_page_map(year: str) -> dict[str, int]:
    """Load figure-id → primary_page mapping from data/<year>_figures.json."""
    fig_path = os.path.join(ROOT_DIR, 'data', f'{year}_figures.json')
    if not os.path.exists(fig_path):
        return {}
    with open(fig_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    mapping = {}
    for entry in raw:
        if 'id' in entry and 'primary_page' in entry:
            mapping[entry['id']] = entry['primary_page']
    return mapping


def find_q_start_index(content: str, qnum: int) -> int:
    """Find the start index of question number *qnum* inside *content*."""
    m = re.search(rf'(?:^|\n){qnum}\.\s', content)
    return m.start() if m else 0


def clean_option_tail(opt_text: str) -> str:
    """
    Remove trailing figure/table label fragments that leaked from the PDF text
    stream into option text.  Only strips leading characters that could not be
    a natural sentence ending.
    e.g. '日本藉由牡丹社事件擴張勢力表' → '日本藉由牡丹社事件擴張勢力'
         '嚴格限制人口移入表'           → '嚴格限制人口移入'
    """
    # Strip trailing figure/table labels: just 圖 or 表 after non-punctuation
    opt_text = re.sub(r'[圖表](?:\(\S*\))?$', '', opt_text)
    # Strip trailing page number digits
    opt_text = re.sub(r'\d{1,2}$', '', opt_text)
    # Strip trailing garbage chars (非中文/英文/句號)
    opt_text = re.sub(r'[\x00-\x1f\uFFFD]+$', '', opt_text)
    return opt_text.strip()


def has_image_options(opts: dict) -> bool:
    """True if options are image-based (not extractable as text).

    Two signals:
      1. ≥ 2 options are literally empty
      2. All non-empty options look like fallback-grabbed junk — short strings
         that are just the next option label, e.g. '(B)', '(C)', '(D)'.
         When the real option content is an image, the fallback regex only
         captures the next label as text.
    """
    vals = [str(v).strip() for v in opts.values()]
    empty = [k for k, v in opts.items() if not v or not str(v).strip()]
    if len(empty) >= 2:
        return True
    # Fallback-grab detector: pattern where A=(B), B=(C), C=(D)
    # This happens when the real option content is an image — the fallback
    # regex captures only the next option's label, not the image content.
    # C may also contain leaked junk after '(D)' like '表(六)...'
    looks_image = True
    for i, letter in enumerate(['A', 'B', 'C']):
        v = opts.get(letter, '')
        if v:
            v = str(v).strip()
            next_label = chr(ord('B') + i)  # A→(B), B→(C), C→(D)
            if not v.startswith(f'({next_label})'):
                looks_image = False
                break
        # if v is empty, that's also fine (image option with no text at all)
    if looks_image:
        return True
    return False


def mark_image_options(questions: list[dict], year: str) -> None:
    """Tag questions whose options are images with an image-options filename.

    Sets two fields on each in-place:
      - image_options: "{year}{q:02d}i.jpg" or None
      - image_options_full: True  → all of A/B/C/D are images
                            False → only A/B/C are images, D has text
                            None  → not an image-option question
    """
    for q in questions:
        if not has_image_options(q.get('options', {})):
            q['image_options'] = None
            q['image_options_full'] = None
            continue
        qnum = q['number']
        fname = f'{year}{qnum:02d}i.jpg'
        # D is also image iff its text is empty
        d_text = q.get('options', {}).get('D', '')
        d_empty = not d_text or not str(d_text).strip()
        q['image_options'] = fname
        q['image_options_full'] = bool(d_empty)

# ──  passage / questions splitting  ─────────────────────────────────

def find_passage_boundary(text_after_d: str) -> int | None:
    """
    Inside the text *after* the last (D) marker, locate the byte offset
    where the real reading-passage starts.

    Must skip:
      - (D) option text itself (first line)
      - Table/figure label lines   e.g. '表(八)', '圖(十六)'
      - Pure numeric / tabular data lines
      - Very short non-Chinese lines
      - Page markers / boilerplate
    """
    lines = text_after_d.split('\n')
    cumulative = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Always skip the first non-empty line — it is the tail of (D)
        if i == 0:
            cumulative += len(line) + 1
            continue

        # Empty line
        if not stripped:
            cumulative += len(line) + 1
            continue

        # Standalone table/figure label
        if re.match(r'^[圖表]\([一二三四五六七八九十\u3127\d]+\)$', stripped):
            cumulative += len(line) + 1
            continue

        # Pure numeric / tabular data line
        if re.match(r'^[\d\s,.\-/%☆\u2605\u2606★☆\u3000]+$', stripped):
            cumulative += len(line) + 1
            continue

        # Page-number / marker boilerplate
        if re.match(
            r'^(=== PAGE \d+ ===|\d{1,2}|請翻頁繼續作答|試題結束)$',
            stripped
        ):
            cumulative += len(line) + 1
            continue

        # Very short line without substantial CJK content
        cjk_count = len(re.findall(r'[\u4e00-\u9fff]', stripped))
        if len(stripped) < 6 and cjk_count < 6:
            cumulative += len(line) + 1
            continue

        # Reached a line with ≥ 10 CJK chars → passage starts here
        if cjk_count >= 10:
            return cumulative

        cumulative += len(line) + 1

    return None


def split_passage_and_questions(
    content: str, q_start: int, q_end: int
) -> tuple[str, str]:
    """
    Split a group block's *content* into (passage, clean_questions_part).

    Strategy:
      1. Find the last (D) marker.  Look for passage text after it
         (the common case: passage follows the questions).
      2. If no passage found there, check for passage text *before*
         the first question number (the rarer case, e.g. 113 Q44-45).
      3. Return (passage, content up to passage boundary).
    """
    passage = ''
    clean_content = content

    # ── strategy A: passage after last (D) ──
    d_matches = list(re.finditer(r'\(D\)', content))
    if d_matches:
        last_d_end = d_matches[-1].end()
        after_d = content[last_d_end:]
        boundary = find_passage_boundary(after_d)
        if boundary is not None:
            abs_passage_start = last_d_end + boundary
            passage = content[abs_passage_start:].strip()
            clean_content = content[:abs_passage_start].strip()

    # ── strategy B: passage before first question ──
    if not passage:
        first_q_idx = find_q_start_index(content, q_start)
        if first_q_idx > 0:
            before_q = content[:first_q_idx].strip()
            # Remove the block-leading「閱讀下列選文…」line if it leaked through
            before_q = re.sub(r'^閱讀下列選文.*?\n', '', before_q)
            # Remove page-number / empty lines at the very end of the head
            before_q = re.sub(r'\s*\d{1,2}\s*$', '', before_q).strip()
            if len(before_q) > 20:
                passage = before_q
                clean_content = content[first_q_idx:].strip()

    return passage, clean_content

# ──  question extraction  ───────────────────────────────────────────

def extract_question(qnum: int, body: str, qtype: str) -> dict | None:
    """Extract stem and options from a single question's body text."""
    body = re.sub(r'[\x00-\x09\x0b-\x1f]', '', body)

    opt_a = body.find('(A)')
    if opt_a == -1:
        return None

    stem = body[:opt_a].strip()
    stem = re.sub(r'\s+', '', stem)

    options_raw = body[opt_a:]

    # Primary: use [^\(]+ which naturally stops at next ( for A-C,
    # and for D we also stop at next question-number boundary
    opts = {}
    matches = re.findall(r'\(([A-D])\)\s*([^\(]+)', options_raw)
    for letter, text in matches:
        opts[letter] = re.sub(r'\s+', '', text.strip())

    # Trim D: stop at next question-number boundary if present in body
    if 'D' in opts:
        d_trim = re.split(r'\n\d{1,2}\.\s', opts['D'], maxsplit=1)
        if len(d_trim) > 1:
            opts['D'] = d_trim[0]

    # Fallback for any missing OR empty options (coordinate-style options like
    # "(A) (11.88°N，2.49°E)" are stripped to "" by the primary regex's
    # character class [^\(]+ which stops at the next "(")
    needs_fallback = len(opts) < 4 or any(
        not v or not str(v).strip() for v in opts.values()
    )
    if needs_fallback:
        for letter in ['A', 'B', 'C', 'D']:
            v = opts.get(letter, '')
            if not v or not str(v).strip():
                if letter == 'D':
                    pat = rf'\({letter}\)\s*(.*?)(?=\n\d{{1,2}}\.\s|\Z)'
                else:
                    pat = rf'\({letter}\)\s*(.*?)(?=\([A-D]\)|\n\d{{1,2}}\.\s|\Z)'
                m = re.search(pat, options_raw, re.DOTALL)
                if m:
                    opts[letter] = re.sub(r'\s+', '', m.group(1).strip())

    all_text = stem + ''.join(opts.values())
    all_refs = re.findall(
        r'[圖表]\([一二三四五六七八九十\u3127\d]+\)', all_text
    )
    figs = list(set(f for f in all_refs if f.startswith('圖')))
    tbls = list(set(f for f in all_refs if f.startswith('表')))

    return {
        'number': qnum,
        'type': qtype,
        'group_range': None,
        'group_id': None,
        'stem': stem,
        'options': opts,
        'passage': None,
        'passage_figures': [],
        'passage_figure_pages': {},
        'passage_tables': [],
        'passage_table_pages': {},
        'figures': figs,
        'figure_pages': {},
        'tables': tbls,
        'table_pages': {},
        'image_options': None,
        'image_options_full': None,
    }


def set_single_defaults(q: dict) -> None:
    """Fill new-group fields with neutral defaults for single questions."""
    q['group_id'] = None
    q['passage'] = None
    q['passage_figures'] = []
    q['passage_figure_pages'] = {}
    q['passage_tables'] = []
    q['passage_table_pages'] = {}
    q['image_options'] = None
    q['image_options_full'] = None

# ──  section parsers  ───────────────────────────────────────────────

def parse_section(text: str, default_type: str) -> list[dict]:
    """Parse a section by finding numbered question blocks."""
    pattern = re.compile(
        r'(?:^|\n)(\d{1,2})\.(?:\s*\n|\s+)(.*?)(?=\n\d{1,2}\.\s|\Z)',
        re.DOTALL
    )
    matches = pattern.findall(text)
    questions = []
    for num_str, body in matches:
        qnum = int(num_str)
        q = extract_question(qnum, body, default_type)
        if q and len(q['options']) >= 3:
            questions.append(q)
    return questions


def parse_group_section(text: str, fig_page_map: dict) -> list[dict]:
    """
    Parse the 二、題組 section.

    For each 「閱讀下列選文，回答第 X 至 Y 題」 block:
      1. Split off the reading-passage from the question text.
      2. Parse sub-questions from the clean question area only.
      3. Clean stray figure/table labels from option tails.
      4. Separate passage-level figures from sub-question figures.
      5. Attach passage + metadata to every sub-question in the group.
    """
    if not text:
        return []

    block_pattern = re.compile(
        r'閱讀下列選文，回答第\s*(\d+)\s*至\s*(\d+)\s*題[：:]?\s*\n'
        r'(.*?)(?=閱讀下列選文|試題結束|\Z)',
        re.DOTALL
    )
    blocks = block_pattern.findall(text)
    questions = []

    for q_start_s, q_end_s, content in blocks:
        q_start = int(q_start_s)
        q_end = int(q_end_s)
        group_id = f'{q_start}-{q_end}'

        # 1. split passage
        passage, clean_content = split_passage_and_questions(
            content, q_start, q_end
        )

        # 2. parse sub-questions from clean area
        sub_qs = parse_section(clean_content, '題組子題')
        sub_qs.sort(key=lambda x: x['number'])

        # 3. clean option tails
        for q in sub_qs:
            for letter in list(q['options'].keys()):
                q['options'][letter] = clean_option_tail(
                    q['options'][letter]
                )

        # 4. figure/table attribution
        passage_all = re.findall(
            r'[圖表]\([一二三四五六七八九十\u3127\d]+\)', passage
        )
        passage_figs = list(set(f for f in passage_all if f.startswith('圖')))
        passage_tbls = list(set(f for f in passage_all if f.startswith('表')))
        passage_fig_pages = {
            f: fig_page_map.get(f)
            for f in passage_figs
            if fig_page_map.get(f) is not None
        }
        passage_tbl_pages = {
            t: fig_page_map.get(t)
            for t in passage_tbls
            if fig_page_map.get(t) is not None
        }

        passage_all_set = set(passage_all)
        for q in sub_qs:
            q['figures'] = [
                f for f in q.get('figures', [])
                if f not in passage_all_set
            ]
            q['tables'] = [
                t for t in q.get('tables', [])
                if t not in passage_all_set
            ]
            q['group_range'] = [q_start, q_end]
            q['group_id'] = group_id
            q['type'] = '題組子題'

        # 5. attach passage to every sub-question
        for q in sub_qs:
            q['passage'] = passage if passage else None
            q['passage_figures'] = passage_figs
            q['passage_figure_pages'] = passage_fig_pages
            q['passage_tables'] = passage_tbls
            q['passage_table_pages'] = passage_tbl_pages

        questions += sub_qs

    return questions

# ──  main pipeline  ─────────────────────────────────────────────────

def parse_questions(filepath: str) -> list[dict]:
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = f.read()

    # Control-char cleanup
    raw = clean_control_chars(raw)

    # Remove page markers and boilerplate
    raw = re.sub(r'=== PAGE \d+ ===', '', raw)
    raw = re.sub(r'請翻頁繼續作答', '', raw)
    raw = re.sub(r'試題結束', '', raw)
    raw = re.sub(r'\n{3,}', '\n\n', raw)

    # Remove instruction page (page 1)
    idx_start = raw.find('一、單題')
    if idx_start == -1:
        idx_start = raw.find('一、')
    if idx_start > 0:
        raw = raw[idx_start:]

    questions: list[dict] = []

    # Split into single / group sections
    group_idx = raw.find('二、題組')
    if group_idx > 0:
        single_text = raw[:group_idx]
        group_text = raw[group_idx:]
    else:
        single_text = raw
        group_text = ''

    # Parse year from filename for figure-page mapping
    basename = os.path.basename(filepath)
    year = basename[:3]
    fig_page_map = load_figure_page_map(year)

    # Single questions
    single_qs = parse_section(single_text, '單題')
    for q in single_qs:
        set_single_defaults(q)
        for letter in list(q['options'].keys()):
            q['options'][letter] = clean_option_tail(q['options'][letter])
    questions += single_qs

    # Group questions
    questions += parse_group_section(group_text, fig_page_map)  # already cleans options

    # Mark image-option questions (V5)
    mark_image_options(questions, year)

    return questions


def main() -> None:
    if len(sys.argv) < 2:
        text_files = [
            os.path.join(ROOT_DIR, 'pipeline', 'output', f'{y}_text.txt')
            for y in ['112', '113', '114', '115']
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

        nums = sorted([q['number'] for q in questions])
        missing = [n for n in range(1, 55) if n not in nums]

        print(f'{year}: {len(questions)}/54 questions | Missing: {missing[:5]}...')

        if questions:
            q1 = questions[0]
            print(f'  Q{q1["number"]}: {q1["stem"][:60]}...')
            print(f'  Options: {dict(zip(q1["options"].keys(), [v[:20] for v in q1["options"].values()]))}')


if __name__ == '__main__':
    main()
