#!/usr/bin/env python3
"""
V4 verification script for group-question parsing quality.
Run after parse_questions.py to validate all group-related invariants.
"""
import json
import os
import sys
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, 'data')

def load_json(year: str):
    path = os.path.join(DATA_DIR, f'{year}.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_bak(year: str):
    """Load backup JSON (pre-V4) for comparison."""
    path = os.path.join(DATA_DIR, f'{year}.json.bak')
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def has_control_chars(s: str) -> bool:
    return bool(re.search(r'[\x00-\x09\x0b-\x1f]', s or ''))

def run_checks(year: str) -> dict:
    """Run all checks for a year. Returns {check_name: 'PASS'|'FAIL: reason'}."""
    results = {}
    data = load_json(year)
    bak = load_bak(year)

    # ── C1: question count ──
    if len(data) == 54:
        results['C1_count'] = 'PASS'
    else:
        results['C1_count'] = f'FAIL: {len(data)} questions'

    # ── C2: last question in every group has clean (D) ≤ 40 chars ──
    groups: dict[str, list[dict]] = {}
    for q in data:
        gid = q.get('group_id')
        if gid:
            groups.setdefault(gid, []).append(q)

    c2_failures = []
    for gid, qs in groups.items():
        qs_sorted = sorted(qs, key=lambda x: x['number'])
        last_q = qs_sorted[-1]
        d_text = last_q.get('options', {}).get('D', '')
        if len(d_text) > 40:
            c2_failures.append(f'{year} {gid} Q{last_q["number"]} D.len={len(d_text)}')
    results['C2_D_clean'] = 'PASS' if not c2_failures else f'FAIL: {"; ".join(c2_failures)}'

    # ── C3: group_id consistency ──
    c3_failures = []
    for gid, qs in groups.items():
        for q in qs:
            if q['group_id'] != gid:
                c3_failures.append(f'Q{q["number"]} gid={q["group_id"]} expected={gid}')
    results['C3_gid_consistent'] = 'PASS' if not c3_failures else f'FAIL: {"; ".join(c3_failures)}'

    # ── C4: every group sub-question has passage (>30 chars) ──
    c4_failures = []
    for q in data:
        if q['type'] == '題組子題':
            p = q.get('passage')
            if not p or len(p) <= 30:
                c4_failures.append(f'Q{q["number"]} passage_len={len(p) if p else 0}')
    results['C4_passage_present'] = 'PASS' if not c4_failures else f'FAIL: {"; ".join(c4_failures)}'

    # ── C5: passage identical within same group ──
    c5_failures = []
    for gid, qs in groups.items():
        passages = {q.get('passage', '') for q in qs}
        if len(passages) > 1:
            c5_failures.append(gid)
    results['C5_passage_same'] = 'PASS' if not c5_failures else f'FAIL: {", ".join(c5_failures)}'

    # ── C6: passage_figures found in passage text ──
    c6_failures = []
    for q in data:
        pfigs = q.get('passage_figures', [])
        passage = q.get('passage', '') or ''
        for f in pfigs:
            if f not in passage:
                c6_failures.append(f'Q{q["number"]} {f}')
    results['C6_passage_figs_in_text'] = 'PASS' if not c6_failures else f'FAIL: {"; ".join(c6_failures)}'

    # ── C7: sub-q figures do not intersect with passage_figures ──
    c7_failures = []
    for q in data:
        if q['type'] == '題組子題':
            overlap = set(q.get('figures', [])) & set(q.get('passage_figures', []))
            if overlap:
                c7_failures.append(f'Q{q["number"]} overlap={overlap}')
    results['C7_figs_no_overlap'] = 'PASS' if not c7_failures else f'FAIL: {"; ".join(c7_failures)}'

    # ── C8: single questions (Q1-42) core content stable vs .bak ──
    #     Allows: control-char cleanup, label-tail removal, figure list reorder
    if bak:
        bak_map = {q['number']: q for q in bak if q['number'] <= 42}
        cur_map = {q['number']: q for q in data if q['number'] <= 42}
        c8_failures = []
        for num in sorted(set(list(bak_map.keys()) + list(cur_map.keys()))):
            if num not in bak_map or num not in cur_map:
                c8_failures.append(f'Q{num} missing')
                continue
            b = bak_map[num]
            c = cur_map[num]
            if b['stem'] != c['stem']:
                c8_failures.append(f'Q{num} stem diff')
            # Options: strip control chars from BAK, allow tail-clean diffs
            for letter in ['A', 'B', 'C', 'D']:
                b_opt = re.sub(r'[\x00-\x1f]', '', b.get('options', {}).get(letter, ''))
                c_opt = c.get('options', {}).get(letter, '')
                if b_opt != c_opt:
                    # Accept if BAK is CUR + trailing 圖/表 label fragment
                    tail_diff = len(b_opt) - len(c_opt)
                    if not (b_opt[:len(c_opt)] == c_opt and tail_diff <= 3
                            and re.match(r'^[圖表\d]+$', b_opt[len(c_opt):])):
                        c8_failures.append(f'Q{num} {letter}: diff')
            # Figures: compare as union sets (V4 separated 圖/表 into two fields,
            # so the bak (single figures field) must be compared with cur.figures+cur.tables)
            if set(b.get('figures', [])) != (set(c.get('figures', [])) | set(c.get('tables', []))):
                c8_failures.append(f'Q{num} figures diff')
        results['C8_single_stable'] = 'PASS' if not c8_failures else f'FAIL: {"; ".join(c8_failures)}'
    else:
        results['C8_single_stable'] = 'SKIP (no .bak)'

    # ── C9: no control chars in any text field ──
    c9_failures = []
    for q in data:
        for field in ['stem', 'passage']:
            val = q.get(field) or ''
            if has_control_chars(val):
                c9_failures.append(f'Q{q["number"]}.{field}')
        for letter, val in (q.get('options') or {}).items():
            if has_control_chars(val):
                c9_failures.append(f'Q{q["number"]}.options.{letter}')
    results['C9_no_control_chars'] = 'PASS' if not c9_failures else f'FAIL: {"; ".join(c9_failures[:5])}...'

    # ── C10: no option ends with孤立 '圖'/'表' ──
    c10_failures = []
    for q in data:
        for letter, val in (q.get('options') or {}).items():
            if re.search(r'[圖表]$', val):
                c10_failures.append(f'Q{q["number"]}.{letter}')
    results['C10_option_tail_clean'] = 'PASS' if not c10_failures else f'FAIL: {"; ".join(c10_failures)}'

    # ── C11: 114 Q43 empty options are preserved (not fabricated) ──
    if year == '114':
        q43 = next((q for q in data if q['number'] == 43), None)
        if q43:
            empty_opts = [k for k, v in q43.get('options', {}).items() if not v]
            if empty_opts:
                results['C11_empty_options_preserved'] = f'PASS ({len(empty_opts)} empty)'
            else:
                results['C11_empty_options_preserved'] = 'INFO: 114 Q43 has all text options'
    else:
        results['C11_empty_options_preserved'] = 'SKIP (not 114)'

    # ── I1: image_options field exists on every question ──
    missing_io_field = [q['number'] for q in data if 'image_options' not in q]
    results['I1_image_options_field'] = 'PASS' if not missing_io_field else f'FAIL: Q{missing_io_field[:5]}'

    # ── I2: image_options filename format "{year}{q:02d}i.jpg" ──
    bad_names = []
    for q in data:
        if q.get('image_options'):
            expected = f"{year}{q['number']:02d}i.jpg"
            if q['image_options'] != expected:
                bad_names.append(f'Q{q["number"]} got={q["image_options"]} expected={expected}')
    results['I2_img_option_names'] = 'PASS' if not bad_names else f'FAIL: {"; ".join(bad_names)}'

    # ── I3: image_options_full consistent with options.D ──
    inconsistent_full = []
    for q in data:
        if q.get('image_options'):
            d_text = q.get('options', {}).get('D', '')
            d_empty = not d_text or not str(d_text).strip()
            expected_full = bool(d_empty)
            actual_full = q.get('image_options_full')
            if actual_full != expected_full:
                inconsistent_full.append(
                    f'Q{q["number"]} d_empty={d_empty} actual_full={actual_full}'
                )
    results['I3_img_full_consistent'] = 'PASS' if not inconsistent_full else f'FAIL: {"; ".join(inconsistent_full)}'

    # ── I4: non-image questions have image_options == None ──
    phantom_marks = []
    for q in data:
        empties = [k for k, v in (q.get('options') or {}).items() if not v or not str(v).strip()]
        is_img = len(empties) >= 2
        if is_img and not q.get('image_options'):
            phantom_marks.append(f'Q{q["number"]} (should be marked)')
        if not is_img and q.get('image_options'):
            phantom_marks.append(f'Q{q["number"]} (should NOT be marked)')
    results['I4_img_mark_correct'] = 'PASS' if not phantom_marks else f'FAIL: {"; ".join(phantom_marks)}'

    return results


def main():
    years = sys.argv[1:] if len(sys.argv) > 1 else ['112', '113', '114', '115']
    if '--all' in years:
        years = ['112', '113', '114', '115']

    all_pass = True
    for year in years:
        results = run_checks(year)
        fails = [k for k, v in results.items() if v.startswith('FAIL')]
        if fails:
            all_pass = False
        print(f'\n{"="*60}')
        print(f'  {year}')
        print(f'{"="*60}')
        for check, status in results.items():
            marker = 'OK' if status == 'PASS' else ('!!' if status.startswith('FAIL') else '--')
            print(f'  {marker} {check}: {status}')
        if fails:
            print(f'\n  ** {len(fails)} check(s) FAILED')
        else:
            print(f'\n  ** All checks passed')

    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
