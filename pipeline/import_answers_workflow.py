#!/usr/bin/env python3
"""
Automated workflow to import answers and explanations for a given year.
Usage:
  python pipeline/import_answers_workflow.py <year>
"""
import sys
import os
import subprocess

def run_command(args):
    print(f"Running: {' '.join(args)}")
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: Command failed with return code {result.returncode}")
        print("Stdout:")
        print(result.stdout)
        print("Stderr:")
        print(result.stderr)
        return False, result.stdout + "\n" + result.stderr
    return True, result.stdout

def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline/import_answers_workflow.py <year>")
        sys.exit(1)
        
    year = sys.argv[1]
    
    # Find project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Check explanation PDF exists
    pdf_path = os.path.join(project_root, f"{year}會考社會科詳解.pdf")
    if not os.path.exists(pdf_path):
        print(f"ERROR: Explanation PDF not found: {pdf_path}")
        sys.exit(1)
        
    print(f"=== Starting Import Workflow for Year {year} ===")
    
    # Step 1: Parse Questions
    text_path = os.path.join(project_root, "pipeline", "output", f"{year}_text.txt")
    if not os.path.exists(text_path):
        print(f"ERROR: Question text file not found: {text_path}")
        sys.exit(1)
        
    success, stdout = run_command([sys.executable, "pipeline/parse_questions.py", text_path])
    if not success:
        print("Aborting workflow at Step 1 (parse_questions).")
        sys.exit(1)
    print("Step 1 (parse_questions) completed successfully.")
    
    # Step 2: Merge Figure Pages
    success, stdout = run_command([sys.executable, "pipeline/merge_figures.py"])
    if not success:
        print("Aborting workflow at Step 2 (merge_figures).")
        sys.exit(1)
    print("Step 2 (merge_figures) completed successfully.")
    
    # Step 3: Import Explanations
    success, stdout = run_command([sys.executable, "pipeline/import_explanations.py", year])
    if not success:
        print("Aborting workflow at Step 3 (import_explanations).")
        sys.exit(1)
    print("Step 3 (import_explanations) completed successfully.")
    
    # Step 4: Validate
    success, stdout = run_command([sys.executable, "pipeline/check_groups.py", year])
    if not success:
        print("Aborting workflow at Step 4 (check_groups validation failed).")
        sys.exit(1)
    print("Step 4 (check_groups) completed successfully.")
    
    print(f"\n=== WORKFLOW SUCCESSFUL FOR YEAR {year} ===")
    print("All steps completed and verified successfully!")

if __name__ == "__main__":
    main()
