import os
import time
import re
from difflib import get_close_matches
from datetime import datetime
from file_utils import (
    display_directory_tree,
    collect_file_paths,
    separate_files_by_type,
    read_file_data
)

from data_processing_common import (
    compute_operations,
    execute_operations
)

from text_data_processing import (
    process_text_files
)

from output_filter import filter_specific_output
from nexa.gguf import NexaTextInference
from content_classifier import classify_by_filename_grouped

def normalize_korean_foldername(text):
    """한글 폴더명에서 공백/특수기호/밑줄 제거하여 병합 정확도 향상"""
    return re.sub(r'[\s_]', '', text.strip())

def normalize_foldername(foldername, existing_names, threshold=0.8):
    """기존 폴더명과 유사하면 병합 (전처리 포함)"""
    simplified_input = normalize_korean_foldername(foldername)
    simplified_existing = {name: normalize_korean_foldername(name) for name in existing_names}

    for orig_name, simplified in simplified_existing.items():
        if get_close_matches(simplified_input, [simplified], n=1, cutoff=threshold):
            return orig_name  # 기존 폴더명으로 병합
    return foldername  # 새 폴더명 사용

def ensure_nltk_data():
    import nltk
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('wordnet', quiet=True)

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
    pointers = ['\u251c\u2500\u2500 '] * (len(tree) - 1) + ['\u2514\u2500\u2500 '] if tree else []
    for pointer, key in zip(pointers, tree):
        print(prefix + pointer + key)
        if tree[key]:
            extension = '\u2502   ' if pointer == '\u251c\u2500\u2500 ' else '    '
            print_simulated_tree(tree[key], prefix + extension)

def get_yes_no(prompt):
    while True:
        response = input(prompt).strip().lower()
        if response in ('yes', 'y'):
            return True
        elif response in ('no', 'n'):
            return False
        elif response == '/exit':
            print("Exiting program.")
            exit()
        else:
            print("Please enter 'yes' or 'no'. To exit, type '/exit'.")

def get_quarter_path(file_path):
    created_time = os.path.getctime(file_path)
    dt = datetime.fromtimestamp(created_time)
    year = str(dt.year)
    quarter = (dt.month - 1) // 3 + 1
    return os.path.join(year, f"{quarter}분기")

def main():
    ensure_nltk_data()
    dry_run = True
    print("-" * 50)
    print("**NOTE: Silent mode logs all outputs to a text file instead of displaying them in the terminal.")
    silent_mode = get_yes_no("Would you like to enable silent mode? (yes/no): ")
    log_file = 'operation_log.txt' if silent_mode else None

    while True:
        if not silent_mode:
            print("-" * 50)
        input_path = input("Enter the path of the directory you want to organize: ").strip()
        while not os.path.exists(input_path):
            message = f"Input path {input_path} does not exist. Please enter a valid path."
            if silent_mode:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(message + '\n')
            else:
                print(message)
            input_path = input("Enter the path of the directory you want to organize: ").strip()

        output_path = input("Enter the path to store organized files and folders (press Enter to use 'organized_folder' in the input directory): ").strip()
        if not output_path:
            output_path = os.path.join(os.path.dirname(input_path), 'organized_folder')

        file_paths = collect_file_paths(input_path)
        from folder_structure import organize_by_year_and_quarter
        input_path = organize_by_year_and_quarter(input_path, output_dir=output_path)
        file_paths = collect_file_paths(input_path)

        initialize_models()

        filename_classified = classify_by_filename_grouped(file_paths, text_inference, silent=silent_mode, log_file=log_file)

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

        print("-" * 50)
        print("Proposed directory structure:")
        print(os.path.abspath(output_path))
        simulated_tree = simulate_directory_tree(operations, output_path)
        print_simulated_tree(simulated_tree)
        print("-" * 50)

        if get_yes_no("Would you like to proceed with these changes? (yes/no): "):
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
        else:
            print("Operation canceled by the user.")

        if not get_yes_no("Would you like to organize another directory? (yes/no): "):
            break

if __name__ == '__main__':
    main()
