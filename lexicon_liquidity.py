import os
import csv
import time
import sys
from collections import defaultdict

# --- FIX FOR FIELD SIZE LIMIT ERROR ---
max_int = sys.maxsize
while max_int > 0:
    try:
        csv.field_size_limit(max_int)
        break
    except OverflowError:
        max_int = int(max_int / 10)

try:
    from tqdm import tqdm
except ImportError:
    print("Error: 'tqdm' library is required to run this script.")
    print("Please install it using: pip install tqdm")
    sys.exit(1)

ARTICLES = {"a", "an", "the"}
PREPOSITIONS = {
    "aboard", "about", "above", "across", "after", "against", "along", "amid",
    "among", "anti", "around", "as", "at", "before", "behind", "below",
    "beneath", "beside", "besides", "between", "beyond", "but", "by",
    "concerning", "considering", "despite", "down", "during", "except",
    "excepting", "excluding", "following", "for", "from", "in", "inside",
    "into", "like", "minus", "near", "of", "off", "on", "onto", "opposite",
    "outside", "over", "past", "per", "plus", "regarding", "round", "save",
    "since", "than", "through", "to", "toward", "towards", "under",
    "underneath", "unlike", "until", "up", "upon", "versus", "via", "with",
    "within", "without"
}
INDEFINITE_PRONOUNS = {
    "all", "another", "any", "anybody", "anyone", "anything", "both", "each",
    "either", "everybody", "everyone", "everything", "few", "many", "neither",
    "nobody", "none", "nothing", "one", "several", "some", "somebody",
    "someone", "something"
}
STOP_WORDS = ARTICLES | PREPOSITIONS | INDEFINITE_PRONOUNS


def is_valid_term(term, min_n, max_n, target_words=None, avoid_words=None):
    words = term.split()
    if not (min_n <= len(words) <= max_n):
        return False
    if not "".join(words).isalnum():
        return False

    has_target_match = False
    for word in words:
        w_lower = word.lower()

        # 1. Enforce words to avoid
        if avoid_words and w_lower in avoid_words:
            return False

        # 2. Enforce standard stop word filtering
        if w_lower in STOP_WORDS and not word.istitle():
            return False

        # 3. Track target words inclusion
        if target_words and w_lower in target_words:
            has_target_match = True

    # 4. If target words were specified, at least one must be present in the phrase
    if target_words and not has_target_match:
        return False

    return True


def load_word_list_from_csv(csv_path):
    """Utility to load a simple list of individual words from column A of a CSV file."""
    word_set = set()
    if not csv_path or not os.path.isfile(csv_path):
        return word_set

    encodings = ['utf-8-sig', 'utf-8', 'mac_roman', 'utf-16']
    for enc in encodings:
        try:
            with open(csv_path, "r", encoding=enc) as f:
                content = f.read()
            if '\x00' in content and enc != 'utf-16':
                continue

            content = content.replace('\r\n', '\n').replace('\r', '\n')
            lines = [line for line in content.split('\n') if line.strip()]
            reader = csv.reader(lines)

            for row in tqdm(reader, desc=f"Loading Word List ({enc})", unit="row", leave=False):
                if not row or not row.strip():
                    continue
                # Isolate column A tokens, strip punctuation, split into separate words
                for word in row.strip().split():
                    clean_word = word.strip(".,!?;:()\"'").lower()
                    if clean_word:
                        word_set.add(clean_word)
            return word_set
        except Exception:
            continue
    return word_set


def load_target_substrings(target_csv_path):
    target_substrings = set()
    encodings = ['utf-8-sig', 'utf-8', 'mac_roman', 'utf-16']
    file_read = False
    last_error = None

    for enc in encodings:
        try:
            with open(target_csv_path, "r", encoding=enc) as f:
                content = f.read()

            file_read = True
            if '\x00' in content and enc != 'utf-16':
                continue

            content = content.replace('\r\n', '\n').replace('\r', '\n')
            lines = [line for line in content.split('\n') if line.strip()]
            reader = csv.reader(lines)

            for row in tqdm(reader, desc=f"Loading Target Substrings ({enc})", unit="row", leave=False):
                if not row:
                    continue
                clean_sub = row.strip().lower()
                if clean_sub:
                    target_substrings.add(clean_sub)

            if target_substrings:
                print(f"Successfully loaded {len(target_substrings)} target substrings! (Encoding: {enc})")
                return target_substrings

        except Exception as e:
            last_error = e
            continue

    print("\n" + "=" * 50 + "\n--- DIAGNOSTIC ERROR REPORT ---\n")
    if not file_read:
        print(f"CRITICAL SYSTEM ERROR: Blocked from reading target CSV. Error: {last_error}")
    else:
        print("CRITICAL FORMAT ERROR: Read complete, but no valid text strings found in first column.")
    print("=" * 50 + "\n")
    return target_substrings


def main():
    print("=== PHASE 1: TEXT PARSING & GLOBAL TEXT ANALYSIS ===")

    default_dir = "placeholder"
    user_dir = input(f"Enter the absolute path to the super-folder containing .txt files [{default_dir}]: ").replace(
        ">?", "").strip().strip("'\"")
    root_dir = user_dir if user_dir else default_dir

    folder_filter = input("Enter a substring to filter parent super-folder names (leave blank for all): ").replace(">?",
                                                                                                                   "").strip() or "responses"

    try:
        budget_input = input("Enter a global point budget (e.g., 1000): ").replace(">?", "").strip()
        global_budget = float(budget_input) if budget_input else 1000.0
    except ValueError:
        global_budget = 1000.0

    # --- INPUT REGION FOR GLOBAL WORD LISTS FILTERS ---
    print("\n--- OPTIONAL WORD LIST FILTERING ---")
    target_words_input = input("Enter absolute path to TARGET words CSV (leave blank to skip): ").replace(">?",
                                                                                                          "").strip().strip(
        "'\"")
    avoid_words_input = input("Enter absolute path to WORDS TO AVOID CSV (leave blank to skip): ").replace(">?",
                                                                                                           "").strip().strip(
        "'\"")

    target_words = load_word_list_from_csv(target_words_input) if target_words_input else set()
    avoid_words = load_word_list_from_csv(avoid_words_input) if avoid_words_input else set()

    if target_words:
        print(f"Loaded {len(target_words)} required target words criteria.")
    if avoid_words:
        print(f"Loaded {len(avoid_words)} blacklisted avoid words criteria.\n")

    txt_files = []
    if os.path.isdir(root_dir):
        for root, dirs, files in os.walk(root_dir):
            if folder_filter and folder_filter not in os.path.basename(root):
                continue
            for file in files:
                if file.endswith(".txt"):
                    txt_files.append(os.path.join(root, file))

    if not txt_files:
        print(f"No .txt documents found matching rules under workspace path: {root_dir}")
        return

    raw_rows_accumulator = []
    global_counts = defaultdict(int)

    for file_path in tqdm(txt_files, desc="Parsing Text Files", unit="file"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            epoch_now = int(time.time())
            paragraphs = content.split('\n\n')

            for p_idx, para in enumerate(paragraphs):
                if not para.strip():
                    continue

                p_text = para.strip()
                p_text = p_text.replace(". ", ".\n").replace("! ", "!\n").replace("? ", "?\n")
                statements = [s.strip() for s in p_text.split("\n") if s.strip()]

                for s_idx, stmt in enumerate(statements):
                    words = [w.strip(".,!?;:()\"'") for w in stmt.split() if w.strip()]

                    for window in range(1, 15):
                        for i in range(len(words) - window + 1):
                            phrase = " ".join(words[i:i + window])
                            if not phrase:
                                continue

                            raw_rows_accumulator.append({
                                "abs file path of .txt": file_path,
                                "epoch of row entry": epoch_now,
                                "Word, Phrase, Substr": phrase,
                                "Length (in char)": len(phrase),
                                "Length in Words": window,
                                "Paragraph Index": p_idx,
                                "Intra-Statement Index": i,
                                "Inter Statement Index": s_idx,
                            })
                            global_counts[phrase] += 1
        except Exception:
            continue

    if not raw_rows_accumulator:
        print("No terms extracted from document targets.")
        return

    processed_rows = []
    for row in tqdm(raw_rows_accumulator, desc="Processing Rows", unit="row"):
        term = row["Word, Phrase, Substr"]
        g_freq = global_counts[term]

        pts_qty = g_freq * 1.5
        tot_val = pts_qty * row["Length (in char)"]

        row["Global Quantity of Times Substr Appears in .txt"] = g_freq
        row["Points based on quantity"] = pts_qty
        row["Total Value"] = tot_val
        processed_rows.append(row)

    sum_total_value = sum(r["Total Value"] for r in processed_rows) or 1.0
    for row in processed_rows:
        row["Budget Allocated"] = (row["Total Value"] / sum_total_value) * global_budget

    master_csv_path = os.path.join(root_dir, f"global_text_analysis_{time.time()}.csv")
    headers_m1 = [
        "abs file path of .txt", "epoch of row entry", "Word, Phrase, Substr",
        "Length (in char)", "Length in Words", "Paragraph Index", "Intra-Statement Index",
        "Inter Statement Index", "Global Quantity of Times Substr Appears in .txt",
        "Points based on quantity", "Total Value", "Budget Allocated"
    ]

    with open(master_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers_m1)
        writer.writeheader()
        for row in tqdm(processed_rows, desc="Writing to CSV", unit="row"):
            writer.writerow(row)

    print(f"\nSuccess! Catalog generated across files at:\n{master_csv_path}\n")

    print("=== PHASE 2: PHRASE LENGTH FILTERING ===")
    target_csv = input(
        f"Enter the absolute path to the master CSV or Press Enter for most recent to be used: >? ").replace(">?",
                                                                                                             "").strip().strip(
        "'\"")
    if not target_csv:
        target_csv = master_csv_path

    try:
        min_in = input("Enter the minimum phrase length (e.g., 2): >? ").replace(">?", "").strip()
        min_length = int(min_in) if min_in else 2

        max_in = input("Enter the maximum phrase length (e.g., 14): >? ").replace(">?", "").strip()
        max_length = int(max_in) if max_in else 14
    except ValueError:
        min_length, max_length = 2, 14

    if min_length > max_length:
        min_length, max_length = max_length, min_length

    print(f"\nReading, filtering (Lengths {min_length} to {max_length}), and processing the input CSV...")

    term_frequencies = {}
    file_scores = defaultdict(float)

    if os.path.exists(target_csv):
        # We perform a quick count of total rows first so tqdm can calculate accurate completion time
        with open(target_csv, "r", encoding="utf-8") as f:
            total_rows = sum(1 for _ in f) - 1  # Minus header row

        with open(target_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in tqdm(reader, total=total_rows, desc="Filtering Rows", unit="row"):
                term = row["Word, Phrase, Substr"]

                # Dynamic application of Target Word and Avoid Word processing lists here
                if not is_valid_term(term, min_length, max_length, target_words, avoid_words):
                    continue

                f_path = row["abs file path of .txt"]
                if term not in term_frequencies:
                    term_frequencies[term] = int(row["Global Quantity of Times Substr Appears in .txt"])
                file_scores[f_path] += float(row["Points based on quantity"])

    base_dir = os.path.dirname(target_csv) if os.path.dirname(target_csv) else root_dir
    t_stamp = time.time()
    term_csv_path = os.path.join(base_dir, f"filtered_term_frequencies_n{min_length}-{max_length}_{t_stamp}.csv")
    file_csv_path = os.path.join(base_dir, f"filtered_file_value_scores_n{min_length}-{max_length}_{t_stamp}.csv")

    print("Writing Filtered Term Frequencies CSV...")
    with open(term_csv_path, "w", newline="", encoding="utf-8") as f1:
        w1 = csv.writer(f1)
        w1.writerow(["Term/Phrase/Word", "Global Frequency"])
        sorted_terms = sorted(term_frequencies.items(), key=lambda x: x, reverse=True)
        for row in tqdm(sorted_terms, desc="Writing Terms CSV", unit="row"):
            w1.writerow(row)

    print("Writing Filtered File Value Scores CSV...")
    with open(file_csv_path, "w", newline="", encoding="utf-8") as f2:
        w2 = csv.writer(f2)
        w2.writerow(["Text File Path", "Total Point Value (Load)"])
        sorted_files = sorted(file_scores.items(), key=lambda x: x, reverse=True)
        for row in tqdm(sorted_files, desc="Writing File Scores CSV", unit="row"):
            w2.writerow(row)

    print("\nSuccess!")
    print(f"1. Filtered Terms Summary saved to: {term_csv_path}")
    print(f"2. Filtered File Scores saved to:   {file_csv_path}\n")

    print("=== PHASE 3: TARGETED VOCABULARY MATCHING & CONSOLIDATION ===")
    vocab_csv_input = input("Enter the absolute path to the CSV containing your target substrings: ").replace(">?",
                                                                                                              "").strip().strip(
        "'\"")

    if not vocab_csv_input or not os.path.isfile(vocab_csv_input):
        print("Skipping Target Substring matching phases. Selected path does not exist.")
        return

    target_substrings = load_target_substrings(vocab_csv_input)
    if not target_substrings:
        return

    print("Scanning master CSV... matching target substrings dynamically...")
    file_substring_counts = defaultdict(lambda: defaultdict(int))
    global_substring_counts = defaultdict(int)
    master_rows_cache = []

    with open(master_csv_path, "r", encoding="utf-8") as f:
        total_master_rows = sum(1 for _ in f) - 1

    with open(master_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in tqdm(reader, total=total_master_rows, desc="Caching Master & Tracking Substrings", unit="row"):
            m_term = str(row["Word, Phrase, Substr"]).strip().lower()
            f_path = row["abs file path of .txt"]
            master_rows_cache.append(row)

            for substring in target_substrings:
                if substring == m_term or (len(substring.split()) > 1 and substring in m_term):
                    file_substring_counts[f_path][substring] += 1
                    global_substring_counts[substring] += 1

    unique_counts = sorted(list(set(global_substring_counts.values())), reverse=True)
    points_map = {count: max(1, 100 - r_idx) for r_idx, count in enumerate(unique_counts)}

    file_totals = defaultdict(int)
    for f_path, subs in tqdm(file_substring_counts.items(), desc="Calculating File Totals", unit="file"):
        for sub, cnt in subs.items():
            file_totals[f_path] += (cnt * points_map[global_substring_counts[sub]])

    final_consolidated_rows = []
    for row in tqdm(master_rows_cache, desc="Building Consolidated Dataset", unit="row"):
        m_term = str(row["Word, Phrase, Substr"]).strip().lower()
        f_path = row["abs file path of .txt"]

        for substring in target_substrings:
            if substring == m_term or (len(substring.split()) > 1 and substring in m_term):
                sub_g_qty = global_substring_counts[substring]
                sub_base_pts = points_map[sub_g_qty]
                freq_in_file = file_substring_counts[f_path][substring]
                score_contrib = freq_in_file * sub_base_pts
                f_total_score = file_totals[f_path]

                final_consolidated_rows.append({
                    "Word, Phrase, Substr": row["Word, Phrase, Substr"],
                    "Target Substring (Lowercase)": substring,
                    "abs file path of .txt": f_path,
                    "Global Substring Frequency": sub_g_qty,
                    "Substring Point Value (Base)": sub_base_pts,
                    "Frequency in this File": freq_in_file,
                    "Score Contributed to File": score_contrib,
                    "File Total Score": f_total_score,
                    "Points based on quantity": row["Points based on quantity"],
                    "Total Point Value (Load)": f_total_score,
                    "epoch of row entry": row["epoch of row entry"],
                    "Length (in char)": row["Length (in char)"],
                    "Length in Words": row["Length in Words"],
                    "Paragraph Index": row["Paragraph Index"],
                    "Intra-Statement Index": row["Intra-Statement Index"],
                    "Inter Statement Index": row["Inter Statement Index"],
                    "Total Value": row["Total Value"]
                })

    final_consolidated_rows.sort(key=lambda x: x["File Total Score"], reverse=True)
    consolidated_output_path = os.path.join(base_dir, f"targeted_substring_analysis_consolidated_{time.time()}.csv")

    headers_m9 = [
        "Word, Phrase, Substr", "Target Substring (Lowercase)", "abs file path of .txt",
        "Global Substring Frequency", "Substring Point Value (Base)", "Frequency in this File",
        "Score Contributed to File", "File Total Score", "Points based on quantity",
        "Total Point Value (Load)", "epoch of row entry", "Length (in char)", "Length in Words",
        "Paragraph Index", "Intra-Statement Index", "Inter Statement Index",
        "Total Value"
    ]

    with open(consolidated_output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers_m9)
        writer.writeheader()
        for row in tqdm(final_consolidated_rows, desc="Writing Consolidated CSV", unit="row"):
            writer.writerow(row)

    print(f"\nSuccess! Consolidated targeted analysis saved to:\n{consolidated_output_path}")

    # --- PHASE 4: PROMINENT FILE RANKING ENDMATTER ---
    print("\n=== PHASE 4: PROMINENT FILE RANKING ===")
    if file_totals:
        print("Aggregating points and isolating top document targets...")
        sorted_files = sorted(file_totals.items(), key=lambda x: x, reverse=True)
        ranking_csv_path = os.path.join(base_dir, f"prominent_files_ranking_{time.time()}.csv")

        with open(ranking_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["abs file path of .txt", "Total Accumulated Points"])
            for fp, score in tqdm(sorted_files, desc="Writing Rankings CSV", unit="file"):
                writer.writerow([fp, score])

        print(f"Success! File prominence ranking generated at:\n{ranking_csv_path}")
    else:
        print("Skipping Phase 4: No target substring matches found to rank.")


if __name__ == "__main__":
    main()
