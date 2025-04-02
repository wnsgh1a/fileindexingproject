import os
import time

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

from text_data_processing import (
    process_text_files
)

from output_filter import filter_specific_output
from nexa.gguf import NexaTextInference

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
                local_path=r"C:\\Users\\qazws\\git연습용\\fileindexer\\models\\Llama-3.2-3B-Instruct-IQ3_M.gguf",
                stop_words=[],
                temperature=0.5,
                max_new_tokens=3000,
                top_k=3,
                top_p=0.3,
                profiling=False
            )

        print("✅ 텍스트 모델 로컬 로딩 완료!")
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

def get_mode_selection():
    while True:
        print("Please choose the mode to organize your files:")
        print("1. By Content")
        print("2. By Date")
        print("3. By Type")
        response = input("Enter 1, 2, or 3 (or type '/exit' to exit): ").strip()
        if response == '/exit':
            print("Exiting program.")
            exit()
        elif response == '1':
            return 'content'
        elif response == '2':
            return 'date'
        elif response == '3':
            return 'type'
        else:
            print("Invalid selection. Please enter 1, 2, or 3. To exit, type '/exit'.")

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

        message = f"Input path successfully uploaded: {input_path}"
        if silent_mode:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
        else:
            print(message)
        if not silent_mode:
            print("-" * 50)

        output_path = input("Enter the path to store organized files and folders (press Enter to use 'organized_folder' in the input directory): ").strip()
        if not output_path:
            output_path = os.path.join(os.path.dirname(input_path), 'organized_folder')

        message = f"Output path successfully set to: {output_path}"
        if silent_mode:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
        else:
            print(message)
        if not silent_mode:
            print("-" * 50)

        start_time = time.time()
        file_paths = collect_file_paths(input_path)
        end_time = time.time()

        message = f"Time taken to load file paths: {end_time - start_time:.2f} seconds"
        if silent_mode:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
        else:
            print(message)
        if not silent_mode:
            print("-" * 50)
            print("Directory tree before organizing:")
            display_directory_tree(input_path)
            print("*" * 50)

        while True:
            mode = get_mode_selection()
            if mode == 'content':
                if not silent_mode:
                    print("Checking if the model is already downloaded. If not, downloading it now.")
                initialize_models()

                if not silent_mode:
                    print("*" * 50)
                    print("The file upload was successful. Processing may take a few minutes.")
                    print("*" * 50)

                _, text_files = separate_files_by_type(file_paths)
                text_tuples = []
                for fp in text_files:
                    text_content = read_file_data(fp)
                    if text_content is None:
                        message = f"Unsupported or unreadable text file format: {fp}"
                        if silent_mode:
                            with open(log_file, 'a', encoding='utf-8') as f:
                                f.write(message + '\n')
                        else:
                            print(message)
                        continue
                    text_tuples.append((fp, text_content))

                data_texts = process_text_files(text_tuples, text_inference, silent=silent_mode, log_file=log_file)
                renamed_files = set()
                processed_files = set()
                operations = compute_operations(
                    data_texts,
                    output_path,
                    renamed_files,
                    processed_files,
                    preserve_filename=True  # ⭐ 파일명 원본 유지
                )
            elif mode == 'date':
                operations = process_files_by_date(file_paths, output_path, dry_run=False, silent=silent_mode, log_file=log_file)
            elif mode == 'type':
                operations = process_files_by_type(file_paths, output_path, dry_run=False, silent=silent_mode, log_file=log_file)
            else:
                print("Invalid mode selected.")
                return

            print("-" * 50)
            message = "Proposed directory structure:"
            if silent_mode:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(message + '\n')
            else:
                print(message)
                print(os.path.abspath(output_path))
                simulated_tree = simulate_directory_tree(operations, output_path)
                print_simulated_tree(simulated_tree)
                print("-" * 50)

            proceed = get_yes_no("Would you like to proceed with these changes? (yes/no): ")
            if proceed:
                os.makedirs(output_path, exist_ok=True)
                message = "Performing file operations..."
                if silent_mode:
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(message + '\n')
                else:
                    print(message)
                execute_operations(
                    operations,
                    dry_run=False,
                    silent=silent_mode,
                    log_file=log_file
                )
                message = "The files have been organized successfully."
                if silent_mode:
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write("-" * 50 + '\n' + message + '\n' + "-" * 50 + '\n')
                else:
                    print("-" * 50)
                    print(message)
                    print("-" * 50)
                break
            else:
                another_sort = get_yes_no("Would you like to choose another sorting method? (yes/no): ")
                if another_sort:
                    continue
                else:
                    print("Operation canceled by the user.")
                    break

        another_directory = get_yes_no("Would you like to organize another directory? (yes/no): ")
        if not another_directory:
            break

if __name__ == '__main__':
    main()
