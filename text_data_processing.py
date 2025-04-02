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
from transformers import MarianMTModel, MarianTokenizer

# ✅ 한영 번역기 로딩 (Helsinki-NLP)
model_name = 'Helsinki-NLP/opus-mt-ko-en'
tokenizer = MarianTokenizer.from_pretrained(model_name)
translator = MarianMTModel.from_pretrained(model_name)

def translate_korean_to_english(text):
    """Translate Korean to English using a pretrained MarianMT model."""
    batch = tokenizer.prepare_seq2seq_batch([text], return_tensors="pt", padding=True)
    gen = translator.generate(**batch)
    translated = tokenizer.batch_decode(gen, skip_special_tokens=True)
    return translated[0] if translated else text

def summarize_text_content(text, text_inference):
    """Summarize the given text content."""
    prompt = f"""Provide a concise and accurate summary of the following text, focusing on the main ideas and key details.
Limit your summary to a maximum of 150 words.

Text: {text}

Summary:"""
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
    if silent:
        if log_file:
            with open(log_file, 'a') as f:
                f.write(message + '\n')
    else:
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
    filename_en = translate_korean_to_english(filename_ko)
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words('english'))
    unwanted_words = set([...])  # 기존 unwanted 단어들 생략
    all_unwanted = unwanted_words.union(stop_words)

    # Step 1: Summary
    description = summarize_text_content(text, text_inference)
    progress.update(task_id, advance=1 / total_steps)

    # Step 2: Filename from translated filename
    filename_prompt = f"""
Based on the file name below, generate a descriptive but concise filename (max 3 words) using nouns only.
Avoid words like file, doc, pdf, text.
Filename: {filename_en}
Output only the filename:
"""
    filename_response = text_inference.create_completion(filename_prompt)
    raw_filename = filename_response['choices'][0]['text'].strip()
    filename = sanitize_filename(raw_filename, max_words=3)
    progress.update(task_id, advance=1 / total_steps)

    # Step 3: Folder name
    folder_prompt = f"""
Based on the translated filename and document summary below, generate a general topic folder name (max 2 words).
Use nouns only. No generic words like 'document', 'untitled'.
Translated Filename: {filename_en}
Summary: {description}
Category:
"""
    folder_response = text_inference.create_completion(folder_prompt)
    raw_folder = folder_response['choices'][0]['text'].strip()
    foldername = sanitize_filename(raw_folder, max_words=2)
    progress.update(task_id, advance=1 / total_steps)

    return foldername or '기타', filename or filename_ko, description
