import os
import time
import nltk
from datetime import datetime

from file_utils import (
    display_directory_tree,
    collect_file_paths,
    separate_files_by_type,
    read_file_data
)

from data_processing_common import (
    compute_operations,
    execute_operations,
    process_files_by_date,
    process_files_by_type,
)

from text_data_processing import process_text_files
from image_data_processing import process_image_files

from output_filter import filter_specific_output
from nexa.gguf import NexaVLMInference, NexaTextInference

def ensure_nltk_data():
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('wordnet', quiet=True)

image_inference = None
text_inference = None

def initialize_models():
    global image_inference, text_inference
    if image_inference is None or text_inference is None:
        model_path = "llava-v1.6-vicuna-7b:q4_0"
        model_path_text = "Llama3.2-3B-Instruct:q3_K_M"
        with filter_specific_output():
            image_inference = NexaVLMInference(
                model_path=model_path,
                local_path=None,
                stop_words=[],
                temperature=0.3,
                max_new_tokens=3000,
                top_k=3,
                top_p=0.2,
                profiling=False
            )
            text_inference = NexaTextInference(
                model_path=model_path_text,
                local_path=None,
                stop_words=[],
                temperature=0.5,
                max_new_tokens=3000,
                top_k=3,
                top_p=0.3,
                profiling=False
            )
        print("**----------------------------------------------**")
        print("**       Image inference model initialized      **")
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
    pointers = ['├── '] * (len(tree) - 1) + ['└── '] if tree else []
    for pointer, key in zip(pointers, tree):
        print(prefix + pointer + key)
        if tree[key]:
            extension = '│   ' if pointer == '├── ' else '    '
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

def main():
    ensure_nltk_data()
    print("-" * 50)
    print("**NOTE: Silent mode logs all outputs to a text file instead of displaying them in the terminal.")
    silent_mode = get_yes_no("Silent mode? (yes/no): ")
    log_file = 'operation_log.txt' if silent_mode else None

    input_path = input("정리할 폴더 경로 입력: ").strip()
    while not os.path.exists(input_path):
        print(f"경로가 존재하지 않습니다: {input_path}")
        input_path = input("다시 입력해주세요: ").strip()

    output_path = os.path.join(os.path.dirname(input_path), 'organized_folder')
    print(f"정리된 파일은 다음 위치에 저장됩니다: {output_path}")

    file_paths = collect_file_paths(input_path)
    display_directory_tree(input_path)

    print("모델 초기화 중...")
    initialize_models()

    image_files, text_files = separate_files_by_type(file_paths)

    # 텍스트 파일 처리
    text_tuples = []
    for fp in text_files:
        content = read_file_data(fp)
        if content:
            text_tuples.append((fp, content))

    data_images = process_image_files(image_files, image_inference, text_inference, silent=silent_mode, log_file=log_file)
    data_texts = process_text_files(text_tuples, text_inference, silent=silent_mode, log_file=log_file)

    all_data = data_images + data_texts
    renamed_files = set()
    processed_files = set()

    operations = compute_operations(
        all_data,
        output_path,
        renamed_files,
        processed_files
    )

    print("-" * 50)
    print("생성될 폴더 구조 미리보기:")
    simulated_tree = simulate_directory_tree(operations, output_path)
    print_simulated_tree(simulated_tree)
    print("-" * 50)

    if get_yes_no("위와 같이 정리를 진행할까요? (yes/no): "):
        os.makedirs(output_path, exist_ok=True)
        execute_operations(operations, dry_run=False, silent=silent_mode, log_file=log_file)
        print("정리 완료!")

if __name__ == '__main__':
    main()