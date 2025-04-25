import os
import re
from collections import defaultdict

# 🔧 전처리: 파일명을 토큰 단위로 분석 가능하게 정제
def preprocess_filename(name):
    name = os.path.splitext(os.path.basename(name))[0]
    name = re.sub(r'[_\-]+', ' ', name)
    name = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', name)
    name = re.sub(r'([0-9])([가-힣a-zA-Z])', r'\1 \2', name)
    name = re.sub(r'\s+', ' ', name).strip().lower()
    return name

# 🔍 유사도: 자카드 유사도로 유사한 토큰 기반 비교
def jaccard_similarity(a, b):
    set_a = set(preprocess_filename(a).split())
    set_b = set(preprocess_filename(b).split())
    return len(set_a & set_b) / len(set_a | set_b) if set_a | set_b else 0.0

# 🔧 그룹핑: 전처리 + 자카드 기반 그룹핑
def group_similar_filenames(file_paths, threshold=0.5):
    filenames = [os.path.basename(path) for path in file_paths]
    groups = []
    assigned = [False] * len(filenames)

    for i, fname in enumerate(filenames):
        if assigned[i]:
            continue
        group = [file_paths[i]]
        assigned[i] = True
        for j in range(i + 1, len(filenames)):
            if not assigned[j]:
                score = jaccard_similarity(fname, filenames[j])
                if score >= threshold:
                    group.append(file_paths[j])
                    assigned[j] = True
        groups.append(group)

    return groups

# 🔍 폴더명 정제
def clean_category(raw_text):
    line = raw_text.strip().split("\n")[0]
    line = re.sub(r"^\ud310\ub2e8[:：]?\s*", "", line)
    line = re.sub(r"^\ub2f5\ubcc0[:：]?\s*", "", line)
    line = re.sub(r"^\ud83d\udcc2.*?\\.docx\"\s*", "", line)
    line = re.sub(r"^\ud30c일 \uc774\ub984[:：]?\s*", "", line)
    line = re.sub(r"^\ucd9c\ub825[:：]?\s*", "", line)
    line = re.sub(r"^\uc608시 \ucd9c\ub825[:：]?\s*", "", line)
    line = re.sub(r'[\"\u201c\u201d\u2018\u2019]', '', line)
    line = re.sub(r'[\\/:*?"<>|]', '', line)

    if not re.search(r'[\uac00-\ud7a3]', line):
        return None
    if not line or line.lower() in ["\uae30\ud0c0", "\uc54c \uc218 \uc5c6음", "\ubaa8른", "unknown"] or len(line.strip()) < 2:
        return None

    return line.strip()

# ✅ 예시 추출 함수
def extract_examples_from_log(log_file_path, max_per_category=3):
    examples = defaultdict(list)
    if not os.path.exists(log_file_path):
        return []

    with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '[AI \ubd84\ub958]' in line and '→' in line:
                parts = line.strip().split('→')
                if len(parts) != 2:
                    continue
                filename = parts[0].replace('[AI \ubd84\ub958]', '').strip()
                foldername = parts[1].strip()
                if foldername and foldername.lower() not in ["\uae30\ud0c0", "\uc2e4\ud328", "\ubaa8른", "unknown"]:
                    if len(examples[foldername]) < max_per_category:
                        examples[foldername].append(filename)

    formatted_examples = []
    for folder, files in examples.items():
        formatted_examples.append(f"[{folder}] → {', '.join(files)}")

    return formatted_examples

# 🎞 그룹 단위로 AI 호출에서 분류 실행
def classify_by_filename_grouped(file_paths, model, silent=False, log_file=None):
    results = []
    grouped_files = group_similar_filenames(file_paths, threshold=0.5)

    for group in grouped_files:
        filenames = [os.path.basename(p) for p in group]

        prompt = f"""
다음은 유사한 파일 이름들의 목록입니다:
{chr(10).join(f'- {name}' for name in filenames)}

이 파일들의 공통 주제를 대표하는 **짧고 명확한 한국어 폴더명**을 한 줄로 출력하세요.

조건:
- 반드시 **의미 있는 한국어 명사**여야 하며, 최대 6글자 이내로 요약하세요.
- 설명하지 마세요. 예시는 금지.
- "기타", "모름", "출력" 같은 일반 단어는 사용하지 마세요.
- 출력은 오직 **한 줄**, 폴더명만!
"""
        try:
            response = model.create_completion(prompt)
            raw_text = response["choices"][0]["text"]
            category = clean_category(raw_text)
        except Exception as e:
            if not silent:
                print(f"❌ 오류 (LLM 응답 실패): {e}")
            category = None

        for path in group:
            results.append({
                "file_path": path,
                "foldername": category
            })

            if silent and log_file:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[파일명 그룹 분류] {os.path.basename(path)} -> {category if category else '분류 실패'}\n")
            elif not silent:
                print(f"[파일명 그룹 분류] {os.path.basename(path)} → {category if category else '❌ 실패'}")

    return results
def remove_duplicate_examples(example_lines, max_examples=50):
    seen = set()
    deduped = []
    for line in example_lines:
        if line not in seen:
            seen.add(line)
            deduped.append(line)
        if len(deduped) >= max_examples:
            break
    return deduped

# 📆 전체 일감 분류 방식
def classify_filenames_bulk(file_paths, model, silent=False, log_file=None, extra_examples=None):
    filenames = [os.path.basename(p) for p in file_paths]
    example_lines = extract_examples_from_log(log_file) if log_file else []
    if extra_examples:
        example_lines.extend(extra_examples)
    example_lines = remove_duplicate_examples(example_lines, max_examples=50)
    example_text = '\n'.join(example_lines)

    prompt = f"""
아래는 예시 데이터입니다 (최근 분류 결과):

{example_text if example_text else '없음'}

---

다음은 다양한 파일 이름들의 목록입니다. 각 파일은 특정 주제를 다룹니다:

{chr(10).join(f"- {name}" for name in filenames)}

1. 이 파일들을 주제별로 의미 있게 그룹으로 나누고,
2. 각 그룹에 짧고 명확한 **한국어 폴더명**을 붙여주세요.
3. 출력은 다음 형식으로 작성하세요:

[폴더명] → 파일1, 파일2, 파일3

조건:
- 폴더명은 반드시 **2단어 이내의 한국어 주제명**이어야 합니다.
- "기타", "알 수 없음", "모름", "출력" 등은 사용하지 마세요.
- 각 그룹은 공통 주제를 가져야 하며, 의미 없는 파일은 제외하거나 무시하세요.
"""

    try:
        response = model.create_completion(prompt)
        text = response["choices"][0]["text"].strip()
    except Exception as e:
        print(f"❌ AI 응답 오류: {e}")
        return [{"file_path": p, "foldername": None} for p in file_paths]

    results = []
    folder_blocks = re.findall(r'\[([^\[\]]+)\]\s*→\s*(.+)', text)
    mapping = {}
    for foldername, files_str in folder_blocks:
        files = [f.strip() for f in files_str.split(',')]
        for name in files:
            mapping[name] = foldername.strip()

    for path in file_paths:
        name = os.path.basename(path)
        foldername = mapping.get(name, None)
        results.append({
            "file_path": path,
            "foldername": foldername
        })
        if not silent:
            print(f"[AI 분류] {name} → {foldername if foldername else '❌ 실패'}")
        elif silent and log_file:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[AI 분류] {name} → {foldername if foldername else '실패'}\n")

    return results
