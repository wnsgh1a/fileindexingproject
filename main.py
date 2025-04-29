import os
import time
import re
from difflib import get_close_matches
from datetime import datetime
from file_utils import collect_file_paths, read_file_data
from data_processing_common import compute_operations, execute_operations
from text_data_processing import process_text_files
from output_filter import filter_specific_output
from nexa.gguf import NexaTextInference
from content_classifier import classify_filenames_bulk, extract_examples_from_log, remove_duplicate_examples
from fileremover import isolate_all as process_delete_candidates

def normalize_korean_foldername(text):
    return re.sub(r'[\s_]', '', text.strip())

def normalize_foldername(foldername, existing_names, threshold=0.65):
    simplified_input = normalize_korean_foldername(foldername)
    simplified_existing = {name: normalize_korean_foldername(name) for name in existing_names}
    for orig_name, simplified in simplified_existing.items():
        if get_close_matches(simplified_input, [simplified], n=1, cutoff=threshold):
            return orig_name
    return foldername

def ensure_nltk_data():
    import nltk
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('wordnet', quiet=True)

def simulate_directory_tree(operations, base_path):
    tree = {}
    for op in operations:
        rel_path = os.path.relpath(op['destination'], base_path)
        parts = rel_path.split(os.sep)
        current_level = tree
        for part in parts:
            if part not in current_level:
                current_level[part] = {}
            current_level = current_level[part]
    return tree

def print_simulated_tree(tree, prefix=''):
    pointers = ['├── '] * (len(tree) - 1) + ['└── '] if tree else []
    for pointer, key in zip(pointers, tree):
        print(prefix + pointer + key)
        if tree[key]:
            extension = '│   ' if pointer == '├── ' else '    '
            print_simulated_tree(tree[key], prefix + extension)

def get_quarter_path(file_path):
    created_time = os.path.getctime(file_path)
    dt = datetime.fromtimestamp(created_time)
    year = str(dt.year)
    quarter = (dt.month - 1) // 3 + 1
    return os.path.join(year, f"{quarter}분기")

text_inference = None

def initialize_models():
    global text_inference
    if text_inference is None:
        with filter_specific_output():
            text_inference = NexaTextInference(
                model_path=None,
                local_path=r"C:\\models\\ggml-model-Q4_K_M.gguf",
                stop_words=[],
                temperature=0.0,
                max_new_tokens=256,
                top_k=3,
                top_p=0.3,
                profiling=False
            )
        print("\u2705 텍스트 모델 로컬 로드 완료!")
        print("**----------------------------------------------**")
        print("**       Text inference model initialized       **")
        print("**----------------------------------------------**")

def main(auto_mode=False):
    ensure_nltk_data()
    print("-" * 50)
    print("**NOTE: Silent mode logs all outputs to a text file instead of displaying them in the terminal.")
    silent_mode = True
    log_file = 'operation_log.txt'
    print("-" * 50)

    if auto_mode:
        input_path = r"C:\\Users\\qazws\\OneDrive\\바탕 화면\\연습용"
        output_path = os.path.join(os.path.dirname(input_path), 'organized_folder')
        print(f"[Auto Mode] Input path: {input_path}")
        print(f"[Auto Mode] Output path: {output_path}")
    else:
        input_path = input("Enter the path of the directory you want to organize: ").strip()
        while not os.path.exists(input_path):
            print(f"Input path {input_path} does not exist. Please enter a valid path.")
            input_path = input("Enter the path of the directory you want to organize: ").strip()

        output_path = input("Enter the path to store organized files and folders (press Enter to use 'organized_folder' in the input directory): ").strip()
        if not output_path:
            output_path = os.path.join(os.path.dirname(input_path), 'organized_folder')

    print("-" * 50)

    # ✅ 분류 먼저!
    file_paths = collect_file_paths(input_path)
    initialize_models()

    examples = extract_examples_from_log(log_file)
    examples = remove_duplicate_examples(examples, max_examples=50)

    filename_classified = classify_filenames_bulk(file_paths, text_inference, silent=silent_mode, log_file=log_file, extra_examples=examples)

    text_files_for_content = []
    for item in filename_classified:
        if item["foldername"] is None:
            text_content = read_file_data(item["file_path"])
            if text_content:
                text_files_for_content.append((item["file_path"], text_content))

    content_classified = process_text_files(text_files_for_content, text_inference, silent=silent_mode, log_file=log_file)

    final_classification = []
    existing_names = set()
    for item in filename_classified:
        base_foldername = item["foldername"]
        if not base_foldername:
            matched = next((c for c in content_classified if c["file_path"] == item["file_path"]), None)
            if matched:
                base_foldername = matched["foldername"]

        if base_foldername:
            base_foldername = normalize_foldername(base_foldername, existing_names)
            existing_names.add(base_foldername)
            quarter_path = get_quarter_path(item["file_path"])
            full_folder_path = os.path.join(quarter_path, base_foldername)
            final_classification.append({
                "file_path": item["file_path"],
                "foldername": full_folder_path
            })

    operations = compute_operations(
        final_classification,
        output_path,
        renamed_files=set(),
        processed_files=set(),
        preserve_filename=True
    )

    # ✅ 분류 완료 후, 삭제 후보 정리!
    print("Processing delete candidates (duplicate and old versions)...")
    process_delete_candidates(input_path)
    print("Delete candidate processing completed.")
    print("-" * 50)

    print("Proposed directory structure:")
    print(os.path.abspath(output_path))
    simulated_tree = simulate_directory_tree(operations, output_path)
    print_simulated_tree(simulated_tree)
    print("-" * 50)

    os.makedirs(output_path, exist_ok=True)
    execute_operations(
        operations,
        dry_run=False,
        silent=silent_mode,
        log_file=log_file
    )

    print("-" * 50)
    print("The files have been organized successfully.")
    print("-" * 50)

if __name__ == '__main__':
    import sys
    auto_mode = False
    if len(sys.argv) > 1 and sys.argv[1] == "auto":
        auto_mode = True
    main(auto_mode)
