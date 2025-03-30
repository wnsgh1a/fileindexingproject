import os
import time
import shutil
from datetime import datetime
from file_utils import collect_file_paths, read_file_data, display_directory_tree
from content_classifier import classify_by_content, classify_filename_with_ai
from output_filter import filter_specific_output
from nexa.gguf import NexaTextInference

def ensure_nltk_data():
    import nltk
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)

def get_yes_no(prompt):
    while True:
        response = input(prompt + " (yes/no): ").strip().lower()
        if response in ('yes', 'y'):
            return True
        elif response in ('no', 'n'):
            return False
        elif response == '/exit':
            print("프로그램을 종료합니다.")
            exit()
        else:
            print("'yes' 또는 'no'로 대답해주세요. 종료하려면 '/exit' 입력.")

def extract_year_month(file_path):
    timestamp = os.path.getctime(file_path)
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m")

def create_output_path(base_output_path, year_month, category):
    # 폴더명에서 파일 시스템에 안 되는 문자 제거
    category = str(category).replace("/", "_").replace("\\", "_").strip()
    folder = os.path.join(base_output_path, year_month, category)
    os.makedirs(folder, exist_ok=True)
    return folder

def organize_files_by_name_and_content(file_paths, output_path, model, silent=False, log_file=None):
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        year_month = extract_year_month(file_path)

        # 1차 분류: 파일명 기반
        category = classify_filename_with_ai(file_name, model)

        # 2차 분류: 내용 기반
        if category == '기타':
            content = read_file_data(file_path)
            if content:
                category = classify_by_content(content, model)
            else:
                category = '기타'

        target_folder = create_output_path(output_path, year_month, category)
        new_path = os.path.join(target_folder, file_name)
        shutil.copy2(file_path, new_path)

        if not silent:
            print(f"{file_name} → {year_month}/{category}/")
        elif log_file:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"{file_name} → {year_month}/{category}/\n")

def initialize_model():
    model_path_text = "Llama3.2-3B-Instruct:q3_K_M"
    with filter_specific_output():
        model = NexaTextInference(
            model_path=model_path_text,
            local_path=None,
            stop_words=[],
            temperature=0.5,
            max_new_tokens=2000,
            top_k=3,
            top_p=0.3,
            profiling=False
        )
    print("텍스트 모델이 초기화되었습니다.")
    return model

def main():
    ensure_nltk_data()

    print("파일 정리를 시작합니다.")
    silent_mode = get_yes_no("출력 내용을 파일로 저장하는 silent 모드를 활성화할까요?")
    log_file = 'operation_log.txt' if silent_mode else None

    input_path = input("정리할 폴더 경로를 입력하세요: ").strip()
    while not os.path.exists(input_path):
        print("유효하지 않은 경로입니다.")
        input_path = input("정리할 폴더 경로를 다시 입력하세요: ").strip()

    output_path = input("정리된 파일을 저장할 경로를 입력하세요 (엔터 시 기본 경로 사용): ").strip()
    if not output_path:
        output_path = os.path.join(os.path.dirname(input_path), '정리된_폴더')

    file_paths = collect_file_paths(input_path)
    if not file_paths:
        print("정리할 파일이 없습니다.")
        return

    print("모델을 불러오는 중입니다...")
    model = initialize_model()

    print("파일 분류 및 복사 중...")
    organize_files_by_name_and_content(file_paths, output_path, model, silent_mode, log_file)

    print("\n정리가 완료되었습니다!")
    print(f"정리된 경로: {output_path}")
    if not silent_mode:
        display_directory_tree(output_path)
    print("AI 응답:", response)


if __name__ == '__main__':
    main()
