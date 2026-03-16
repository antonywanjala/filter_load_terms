import os
import re
import csv
import time
from pathlib import Path
import pandas as pd
from tqdm import tqdm


def load_scoring_terms(csv_path):
    """Loads terms and points from the provided CSV."""
    try:
        # Read the CSV using pandas
        df = pd.read_csv(csv_path)

        # Expected column names based on your prompt
        term_col = 'Term and/or Phrase'
        points_col = 'Points Associated with Term and/or Phrase'

        if term_col not in df.columns or points_col not in df.columns:
            raise ValueError(f"CSV must contain the columns: '{term_col}' and '{points_col}'")

        # Convert to a dictionary: {term: points}
        # Drop any rows with missing terms or points, and ensure points are numeric
        df = df.dropna(subset=[term_col, points_col])
        df[points_col] = pd.to_numeric(df[points_col], errors='coerce').fillna(0)

        return dict(zip(df[term_col].astype(str).str.lower(), df[points_col]))

    except Exception as e:
        print(f"Error reading the input CSV: {e}")
        return None


def score_text(text, terms_dict):
    """Scores a given block of text based on term frequency."""
    term_frequencies = {}
    total_score = 0.0

    for term, points in terms_dict.items():
        # Use regex to find whole word/phrase matches, ignoring case
        pattern = r'\b' + re.escape(term) + r'\b'
        matches = len(re.findall(pattern, text, flags=re.IGNORECASE))

        if matches > 0:
            term_frequencies[term] = matches
            total_score += (matches * float(points))

    return total_score, term_frequencies


def split_into_statements(text):
    """Splits text into independent statements using common punctuation."""
    # Split by period, exclamation, or question mark followed by a space
    statements = re.split(r'(?<=[.!?])\s+', text)
    return [stmt.strip() for stmt in statements if stmt.strip()]


def main():
    # 1. Get user inputs
    csv_path = input("Enter the absolute path to the scoring CSV file: ").strip().strip('"').strip("'")
    folder_path = input("Enter the absolute path to the super folder containing .txt files: ").strip().strip('"').strip(
        "'")

    epoch_time = int(time.time())
    output_csv = f"output_results_{epoch_time}.csv"
    error_log = f"supplementary_documentation_{epoch_time}.txt"

    # 2. Load terms
    print("\nLoading scoring parameters...")
    terms_dict = load_scoring_terms(csv_path)
    if not terms_dict:
        return

    # 3. Gather all .txt files recursively
    print("Scanning directory for .txt files...")
    path_obj = Path(folder_path)
    txt_files = list(path_obj.rglob("*.txt"))

    if not txt_files:
        print("No .txt files found in the specified directory or its subdirectories.")
        return

    print(f"Found {len(txt_files)} files. Beginning analysis...")

    unreadable_files = []
    results = []

    # 4. Process files with a single tqdm loading bar
    # We pass the file name to the progress bar description for clarity on what is happening
    with tqdm(total=len(txt_files), desc="Processing Files", unit="file") as pbar:
        for file_path in txt_files:
            pbar.set_description(f"Processing: {file_path.name[:20]}...")
            try:
                # Attempt to read the file (handling standard encodings)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    # Fallback for Windows encoding
                    with open(file_path, 'r', encoding='cp1252') as f:
                        content = f.read()
                except Exception as e:
                    unreadable_files.append(f"{file_path} - Error: {e}")
                    pbar.update(1)
                    continue
            except Exception as e:
                unreadable_files.append(f"{file_path} - Error: {e}")
                pbar.update(1)
                continue

            # Score the entire document
            doc_score, doc_freq = score_text(content, terms_dict)

            # Score at the statement level
            statements = split_into_statements(content)
            statement_scores = []
            for stmt in statements:
                stmt_score, stmt_freq = score_text(stmt, terms_dict)
                if stmt_score > 0:
                    statement_scores.append({
                        "statement": stmt[:50] + "..." if len(stmt) > 50 else stmt,  # Truncate for cleaner output
                        "score": stmt_score,
                        "frequencies": stmt_freq
                    })

            # Format frequencies as a readable string for the CSV
            freq_str = "; ".join([f"{k} ({v})" for k, v in doc_freq.items()])

            results.append({
                "File Path": str(file_path),
                "Total File Points": doc_score,
                "Term Frequencies": freq_str if freq_str else "None",
                "Statement Breakdown": str(statement_scores) if statement_scores else "No matching statements"
            })

            pbar.update(1)

    # 5. Export successful results to CSV
    if results:
        pd.DataFrame(results).to_csv(output_csv, index=False)
        print(f"\nSuccess! Results saved to: {output_csv}")
    else:
        print("\nNo viable data extracted to save.")

    # 6. Export unreadable files to supplementary documentation
    if unreadable_files:
        with open(error_log, 'w') as f:
            f.write("The following files could not be read during the script execution:\n\n")
            for err in unreadable_files:
                f.write(f"{err}\n")
        print(f"Some files could not be read. See {error_log} for details.")


if __name__ == "__main__":
    main()
