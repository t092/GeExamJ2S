import fitz
import re
import json
import os
import sys

# Define learning focus definitions
FOCUS_DEFS = {
    "歷": {
        "A": "歷 A：臺灣的歷史", "B": "歷 A：臺灣的歷史", "C": "歷 A：臺灣的歷史", 
        "D": "歷 A：臺灣的歷史", "E": "歷 A：臺灣的歷史", "F": "歷 A：臺灣的歷史",
        "G": "歷 B：中國與東亞的歷史", "H": "歷 B：中國與東亞的歷史", "I": "歷 B：中國與東亞的歷史", 
        "J": "歷 B：中國與東亞的歷史", "K": "歷 B：中國與東亞的歷史", "L": "歷 B：中國與東亞的歷史",
        "M": "歷 C：世界的歷史", "N": "歷 C：世界的歷史", "O": "歷 C：世界的歷史", 
        "P": "歷 C：世界的歷史", "Q": "歷 C：世界的歷史", "R": "歷 C：世界的歷史",
        "S": "歷 C：世界的歷史", "T": "歷 C：世界的歷史", "U": "歷 C：世界的歷史",
        "V": "歷 C：世界的歷史", "W": "歷 C：世界的歷史", "X": "歷 C：世界的歷史",
        "Y": "歷 C：世界的歷史", "Z": "歷 C：世界的歷史"
    },
    "地": {
        "A": "地 A：臺灣與在地環境",
        "B": "地 B：中國與東亞（含區域地理）",
        "C": "地 C：全球環境與世界體系"
    },
    "公": {
        "A": "公 A：社會互動與文化",
        "B": "公 B：市場與經濟",
        "C": "公 C：權力、社會與法律",
        "D": "公 D：全球連結與地球村"
    }
}

def get_learning_focus(content):
    if not content:
        return None
    subj = content[0]
    if subj not in FOCUS_DEFS:
        return None
    code = content[1:].strip()
    if not code:
        return None
    first_letter = code[0].upper()
    return FOCUS_DEFS[subj].get(first_letter, None)

def clean_text_remnants(text):
    # Remove copyright, headers, footers and page numbers
    text = re.sub(r'甄戰一點通.*?(?:\n|$)', '', text)
    text = re.sub(r'版權所有.*?(?:\n|$)', '', text)
    text = re.sub(r'All Rights Reserved.*?(?:\n|$)', '', text)
    text = re.sub(r'\d{3}年會考\(社會科詳解\).*?(?:\n|$)', '', text)
    text = re.sub(r'\d{3}年會考社會科詳解.*?(?:\n|$)', '', text)
    
    # Remove lines that are just numbers (isolated page numbers)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.isdigit():
            continue
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines).strip()

def parse_explanation_pdf(pdf_path):
    print(f"Reading PDF from: {pdf_path}")
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    doc.close()
    
    # Split text into question blocks
    # A block starts with "\n{number}. 答案" or similar
    # We use regex split but keep the question numbers
    q_starts = list(re.finditer(r'(?:^|\n)(\d{1,2})\s*\.\s*(?:答案|詳解|參考解答|\n|\r)', full_text))
    print(f"Found {len(q_starts)} question blocks in PDF.")
    
    blocks = {}
    for i in range(len(q_starts)):
        start_idx = q_starts[i].start()
        qnum = int(q_starts[i].group(1))
        end_idx = q_starts[i+1].start() if i + 1 < len(q_starts) else len(full_text)
        block_text = full_text[start_idx:end_idx].strip()
        blocks[qnum] = block_text
        
    parsed_results = {}
    for qnum in range(1, 55):
        if qnum not in blocks:
            print(f"WARNING: Question {qnum} block not found in PDF!")
            continue
        block = blocks[qnum]
        
        # 1. Answer extraction
        ans_match = re.search(r'(?:答案|參考解答)\s*：\s*\(?([A-DＡ-Ｄ])\)?', block)
        if ans_match:
            ans = ans_match.group(1)
            full_width_map = {"Ａ": "A", "Ｂ": "B", "Ｃ": "C", "Ｄ": "D"}
            ans = full_width_map.get(ans, ans)
        else:
            ans = None
            print(f"WARNING: Question {qnum} answer not found!")
            
        # 2. Split into explanation and learning content
        parts = block.split("學習內容：")
        explanation_part = parts[0]
        learning_part = parts[1] if len(parts) > 1 else ""
        
        # Clean explanation text
        exp = explanation_part.strip()
        exp = re.sub(r'^\d+\s*\.\s*(?:答案|參考解答|詳解)\s*：\s*\(?[A-DＡ-Ｄ]\)?\s*', '', exp)
        exp = re.sub(r'^詳解\s*：\s*', '', exp)
        exp = clean_text_remnants(exp)
        
        # Clean and parse learning contents
        learning_contents = []
        if learning_part:
            learning_part = clean_text_remnants(learning_part)
            raw_lines = [l.strip() for l in learning_part.split('\n') if l.strip()]
            
            # Merge lines that don't start with a subject prefix
            merged_lines = []
            for line in raw_lines:
                if line[0] in ['地', '歷', '公']:
                    merged_lines.append(line)
                else:
                    if merged_lines:
                        merged_lines[-1] += " " + line
                    else:
                        merged_lines.append(line)
                        
            # Split by 頓號 '、' if they contain multiple distinct codes
            for line in merged_lines:
                if '、' in line:
                    sub_parts = line.split('、')
                    is_list_of_codes = all(sp.strip() and sp.strip()[0] in ['地', '歷', '公'] for sp in sub_parts)
                    if is_list_of_codes:
                        for sp in sub_parts:
                            learning_contents.append(sp.strip())
                    else:
                        learning_contents.append(line)
                else:
                    learning_contents.append(line)
                    
        # subjects & focuses mapping
        subjects = set()
        focuses = set()
        for lc in learning_contents:
            if lc and lc[0] in ['地', '歷', '公']:
                subjects.add("地理" if lc[0] == '地' else "歷史" if lc[0] == '歷' else "公民")
                focus = get_learning_focus(lc)
                if focus:
                    focuses.add(focus)
                    
        parsed_results[qnum] = {
            "number": qnum,
            "answer": ans,
            "explanation": exp,
            "learning_contents": learning_contents,
            "subjects": sorted(list(subjects)),
            "learning_focuses": sorted(list(focuses))
        }
        
    return parsed_results

def merge_to_json(json_path, parsed_data):
    if not os.path.exists(json_path):
        print(f"ERROR: JSON file not found at: {json_path}")
        return False
        
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
        
    print(f"Loaded {len(questions)} questions from JSON.")
    
    updated_count = 0
    for q in questions:
        qnum = q.get("number")
        if qnum in parsed_data:
            p = parsed_data[qnum]
            q["answer"] = p["answer"]
            q["explanation"] = p["explanation"]
            q["subject"] = p["subjects"][0] if p["subjects"] else None
            q["learning_contents"] = p["learning_contents"]
            q["learning_focuses"] = p["learning_focuses"]
            updated_count += 1
            
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully updated {updated_count} questions in JSON.")
    return True

def run_self_verification(json_path):
    print("Running verification checks...")
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
        
    errors = []
    for q in questions:
        qnum = q.get("number")
        # Check answer
        ans = q.get("answer")
        if not ans or ans not in ["A", "B", "C", "D"]:
            errors.append(f"Q{qnum}: Invalid or missing answer '{ans}'")
            
        # Check explanation
        exp = q.get("explanation")
        if not exp or len(exp) < 10:
            errors.append(f"Q{qnum}: Short or missing explanation")
        if "PAGE" in exp or "版權所有" in exp or "EDTung" in exp:
            errors.append(f"Q{qnum}: Explanation contains footer/header remnants")
            
        # Check subject
        subj = q.get("subject")
        if not subj or subj not in ["地理", "歷史", "公民"]:
            errors.append(f"Q{qnum}: Invalid or missing subject '{subj}'")
            
        # Check learning content and focuses
        lc = q.get("learning_contents")
        lf = q.get("learning_focuses")
        if not lc:
            errors.append(f"Q{qnum}: Missing learning contents")
        if not lf:
            errors.append(f"Q{qnum}: Missing learning focuses")
            
    if errors:
        print(f"Verification FAILED with {len(errors)} errors:")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  - ... and {len(errors) - 10} more errors.")
        return False
    else:
        print("Verification PASSED! All 54 questions are verified successfully.")
        return True

if __name__ == "__main__":
    year = "115"
    if len(sys.argv) > 1:
        year = sys.argv[1]
        
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_path = os.path.join(project_root, f"{year}會考社會科詳解.pdf")
    json_path = os.path.join(project_root, "data", f"{year}.json")
    
    parsed_data = parse_explanation_pdf(pdf_path)
    if parsed_data:
        success = merge_to_json(json_path, parsed_data)
        if success:
            run_self_verification(json_path)
