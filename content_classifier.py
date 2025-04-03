import os
import re
import difflib

# 🔧 그룹핑: 유사한 파일명끼리 그룹으로 묶기
def group_similar_filenames(file_paths, threshold=0.7):
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
                ratio = difflib.SequenceMatcher(None, fname, filenames[j]).ratio()
                if ratio >= threshold:
                    group.append(file_paths[j])
                    assigned[j] = True
        groups.append(group)

    return groups

# 🔍 폴더명 정제
def clean_category(raw_text):
    line = raw_text.strip().split("\n")[0]
    line = re.sub(r"^답변[:：]?\s*", "", line)
    line = re.sub(r"^답을 입력하세요[:：]?\s*", "", line)
    line = re.sub(r"^\ud83d\udcc2.*?\.docx\"\s*", "", line)
    line = re.sub(r"^파일 이름[:：]?\s*", "", line)
    line = re.sub(r'[\"“”‘’]', '', line)
    line = re.sub(r'[\\/:*?"<>|]', '', line)

    if not re.search(r'[가-힣]', line):
        return None
    if not line or line.lower() in ["기타", "알 수 없음", "모름", "unknown"] or len(line.strip()) < 2:
        return None

    return line.strip()

# 🎯 그룹 단위로 AI 호출하여 분류 실행
def classify_by_filename_grouped(file_paths, model, silent=False, log_file=None):
    results = []
    grouped_files = group_similar_filenames(file_paths, threshold=0.8)

    for group in grouped_files:
        filenames = [os.path.basename(p) for p in group]

        prompt = f"""
다음은 유사한 파일 이름들의 목록입니다:
{chr(10).join(f'- {name}' for name in filenames)}

이 파일들의 공통된 주제 하나를 짧은 한국어 폴더명으로 알려주세요.
"의미상으로 공통된 주제"가 있는 거 같은 경우 하나로 묶으세요.
조건:
- 반드시 **한국어**로 출력하세요.
- 절대 설명하지 말고
- 딱 한 줄로, 의미 있는 주제 하나만 (예: 자료구조, 데이터베이스 정규화, 알고리즘)
- 기타/모름/답을 입력하세요 등은 절대 안됨
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
