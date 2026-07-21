#!/usr/bin/env python3
"""
Validate math question bank JSON quality.
Usage: python math/pipeline/check_quality.py
"""
import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def check_year(year: str):
    path = os.path.join(ROOT_DIR, 'data', f'{year}.json')
    if not os.path.exists(path):
        print(f'{year}: data file not found')
        return

    with open(path, encoding='utf-8') as f:
        qs = json.load(f)

    mc = [q for q in qs if q['type'] == '選擇題']
    groups = [q for q in qs if q['type'] == '題組子題']
    noncalc = [q for q in qs if q['type'] == '非選擇題']
    with_figs = [q for q in qs if q['figures']]

    print(f'=== {year}年 ===')
    print(f'  Total: {len(qs)} questions')
    print(f'  選擇題: {len(mc)}, 題組子題: {len(groups)}, 非選擇題: {len(noncalc)}')
    print(f'  With figures: {len(with_figs)}')

    # Check question numbers (選擇題 includes both 單題 and 題組子題)
    mc_nums = sorted(q['number'] for q in mc)
    group_nums = sorted(q['number'] for q in groups)
    all_mc_nums = sorted(mc_nums + group_nums)
    missing = [n for n in range(1, 26) if n not in all_mc_nums]
    if missing:
        print(f'  WARNING: Missing 選擇題: {missing}')
    else:
        print(f'  All 25 選擇題 present ✓ (22 單題 + 3 題組子題)')

    # Check group passage
    if groups:
        g = groups[0]
        print(f'  Group {g["group_id"]}: passage {len(g["passage"]) if g["passage"] else 0} chars')
        for q in groups:
            print(f'    Q{q["number"]}: {q["stem"][:50]}... figs={q["figures"]}')

    # Check figure references
    if with_figs:
        print(f'  Figure references:')
        for q in with_figs:
            print(f'    Q{q["number"]}: {q["figures"]}')

    # Check for potential issues
    issues = []
    for q in mc:
        if not q['stem']:
            issues.append(f'Q{q["number"]}: empty stem')
        opts = q.get('options', {})
        if len(opts) < 4:
            issues.append(f'Q{q["number"]}: only {len(opts)} options')
        for letter in ['A', 'B', 'C', 'D']:
            if letter not in opts:
                issues.append(f'Q{q["number"]}: missing option {letter}')

    if issues:
        print(f'  Issues:')
        for issue in issues:
            print(f'    ⚠ {issue}')
    else:
        print(f'  No issues found ✓')

    print()


def main():
    years = sys.argv[1:] if len(sys.argv) > 1 else ['115']
    for year in years:
        check_year(year)


if __name__ == '__main__':
    main()
