import os
import csv
import time
import string
from pathlib import Path
import pandas as pd
from tqdm import tqdm


def load_scoring_terms(csv_path):
    """Loads terms and points from the provided CSV."""
    try:
        df = pd.read_csv(csv_path)

        term_col = 'Term and/or Phrase'
        points_col = 'Points Associated with Term and/or Phrase'

        if term_col not in df.columns or points_col not in df.columns:
            raise ValueError(f"CSV must contain the columns: '{term_col}' and '{points_col}'")

        df = df.dropna(subset=[term_col, points_col])
        df[points_col] = pd.to_numeric(df[points_col], errors='coerce').fillna(0)

        return dict(zip(df[term_col].astype(str).str.lower(), df[points_col]))

    except Exception as e:
        print(f"Error reading the input CSV: {e}")
        return None


def score_text(text, terms_dict):
    """Scores a block of text using string methods instead of regex."""
    term_frequencies = {}
    total_score = 0.0

    # Normalize text for counting
    lower_text = text.lower()

    # To mimic \b (word boundaries), we can strip punctuation
    # and split into a list of words for exact matching
    words = lower_text.translate(str.maketrans('', '', string.punctuation)).split()

    for term, points in terms_dict.items():
        term_lower = term.lower()

        # Logic: If term is a single word, count in words list.
        # If it's a phrase, count occurrences in the full string.
        if ' ' in term_lower:
            # Simple manual count for phrases
            matches = lower_text.count(term_lower)
        else:
            # Exact word matching for single terms
            matches = words.count(term_lower)

        if matches > 0:
            term_frequencies[term] = matches
            total_score += (matches * float(points))

    return total_score, term_frequencies


def split_into_statements(text):
    """Splits text into statements using string splitting instead of re.split."""
    # Replace common sentence enders with a unique delimiter
    temp_text = text.replace('!', '.').replace('?', '.')
    parts = temp_text.split('.')

    # Cleaning up whitespace
    return [p.strip() for p in parts if p.strip()]


def main():
    # 1. Get user inputs
    csv_path = input("Enter the absolute path to the scoring CSV file: ").strip().strip('"').strip("'")
    folder_path = input("Enter the absolute path to the super folder: ").strip().strip('"').strip("'")

    epoch_time = int(time.time())
    output_csv = f"output_results_{epoch_time}.csv"
    error_log = f"supplementary_documentation_{epoch_time}.txt"

    # 2. Load terms
    print("\nLoading scoring parameters...")
    terms_dict = load_scoring_terms(csv_path)
    if not terms_dict:
        return

    # 3. Gather all .txt files
    path_obj = Path(folder_path)
    txt_files = list(path_obj.rglob("*.txt"))

    if not txt_files:
        print("No .txt files found.")
        return

    print(f"Found {len(txt_files)} files. Beginning analysis...")

    unreadable_files = []
    results = []

    # 4. Process files
    with tqdm(total=len(txt_files), desc="Processing Files", unit="file") as pbar:
        for file_path in txt_files:
            pbar.set_description(f"Processing: {file_path.name[:20]}...")
            try:
                # Attempt UTF-8 then CP1252
                try:
                    content = file_path.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    content = file_path.read_text(encoding='cp1252')
            except Exception as e:
                unreadable_files.append(f"{file_path} - Error: {e}")
                pbar.update(1)
                continue

            doc_score, doc_freq = score_text(content, terms_dict)
            statements = split_into_statements(content)

            statement_scores = []
            for stmt in statements:
                stmt_score, stmt_freq = score_text(stmt, terms_dict)
                if stmt_score > 0:
                    statement_scores.append({
                        "statement": (stmt[:50] + "...") if len(stmt) > 50 else stmt,
                        "score": stmt_score,
                        "frequencies": stmt_freq
                    })

            freq_str = "; ".join([f"{k} ({v})" for k, v in doc_freq.items()])

            results.append({
                "File Path": str(file_path),
                "Total File Points": doc_score,
                "Term Frequencies": freq_str if freq_str else "None",
                "Statement Breakdown": str(statement_scores) if statement_scores else "No matching statements"
            })

            pbar.update(1)

    # 5. Export results
    if results:
        pd.DataFrame(results).to_csv(output_csv, index=False)
        print(f"\nSuccess! Results saved to: {output_csv}")
    else:
        print("\nNo viable data extracted.")

    # 6. Export errors
    if unreadable_files:
        with open(error_log, 'w') as f:
            f.write("Files that could not be read:\n\n")
            for err in unreadable_files:
                f.write(f"{err}\n")
        print(f"Check {error_log} for unreadable files.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
    finally:
        input("\nPress Enter to exit...")
