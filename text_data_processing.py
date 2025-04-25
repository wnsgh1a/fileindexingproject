import re
import os
import time
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from nltk.stem import WordNetLemmatizer
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from data_processing_common import sanitize_filename

# 필요한 nltk 리소스 다운로드
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

# ✅ 제목/첫 문단만 추출

def extract_title_or_intro(text):
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    return '\n'.join(lines[:2]) if lines else ''

def summarize_text_content(text, text_inference):
    """요약: 텍스트 내용을 간결하게 요약"""
    max_chars = 1500
    text = text[:max_chars]
    prompt = f"""
다음 글의 주제를 요약해 주세요. 최대 2문장 이내로 간단히 작성해주세요.

내용:
{text}

요약:
"""
    response = text_inference.create_completion(prompt)
    return response['choices'][0]['text'].strip()

def process_single_text_file(args, text_inference, silent=False, log_file=None):
    file_path, text = args
    start_time = time.time()
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn()
    ) as progress:
        task_id = progress.add_task(f"Processing {os.path.basename(file_path)}", total=1.0)
        foldername, filename, description = generate_text_metadata(text, file_path, progress, task_id, text_inference)
    end_time = time.time()
    message = f"File: {file_path}\nTime taken: {end_time - start_time:.2f} seconds\nDescription: {description}\nFolder name: {foldername}\nGenerated filename: {filename}\n"
    if silent and log_file:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    elif not silent:
        print(message)
    return {
        'file_path': file_path,
        'foldername': foldername,
        'filename': filename,
        'description': description
    }

def process_text_files(text_tuples, text_inference, silent=False, log_file=None):
    results = []
    for args in text_tuples:
        data = process_single_text_file(args, text_inference, silent=silent, log_file=log_file)
        results.append(data)
    return results

def generate_text_metadata(text, file_path, progress, task_id, text_inference):
    total_steps = 3
    filename_ko = os.path.splitext(os.path.basename(file_path))[0]

    # Step 1: 요약 생성
    title_or_intro = extract_title_or_intro(text)  # 핵심만 추출
    description = summarize_text_content(title_or_intro, text_inference)
    progress.update(task_id, advance=1 / total_steps)

    # Step 2: 파일명 생성
    filename_prompt = f"""
다음 파일명을 참고하여 간결하고 명확한 한글 파일명을 만들어주세요. 
3단어 이내로 구성하고, 일반적인 단어(문서, 파일 등)는 피해주세요.

기존 파일명: {filename_ko}

파일명:
"""
    filename_response = text_inference.create_completion(filename_prompt)
    raw_filename = filename_response['choices'][0]['text'].strip()
    filename = sanitize_filename(raw_filename, max_words=3)
    progress.update(task_id, advance=1 / total_steps)

    # Step 3: 폴더명 생성
    folder_prompt = f"""
다음 파일명과 문서 요약을 참고하여 해당 문서가 들어갈 주제 폴더명을 정해주세요.
❗ 폴더명은 반드시 2단어 이내의 한국어 '주제명'이어야 하며, 문장이나 설명을 쓰지 마세요.

파일명: {filename_ko}
요약: {description}

주제 폴더명 (예: 데이터 정규화, 자기 개발, 알고리즘 등):
"""
    folder_response = text_inference.create_completion(folder_prompt)
    raw_folder = folder_response['choices'][0]['text'].strip()
    foldername = sanitize_filename(raw_folder, max_words=2)
    progress.update(task_id, advance=1 / total_steps)

    if not foldername or len(foldername) < 2 or len(foldername) > 20:
        foldername = '기타'

    return foldername, filename or filename_ko, description
