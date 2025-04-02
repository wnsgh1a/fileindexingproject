import os

def classify_by_filename_ai(file_paths, model, silent=False, log_file=None):
    results = []

    for path in file_paths:
        filename = os.path.basename(path)

        prompt = f"""\ 
다음은 파일 이름입니다: "{filename}"
이 파일이 어떤 주제(예: 과제, 수업, 논문, 요약, 프로젝트 등)에 해당하는지 아주 간결한 한국어 분류명 하나로 대답해.
반드시 짧고 명확한 카테고리 이름만 출력하고, 다른 말은 절대 하지 마.
예시: 자료구조, 데이터베이스 정규화, 알고리즘, 논문 초안 등
정확한 주제명을 한 단어 또는 짧은 구절로 말해.
의견을 묻는 것도 아니고, 무조건 명확한 답 하나만 줘.
"""

        try:
            response = model.create_completion(prompt)
            print(f"🔍 모델 원응답: {repr(response)}")

            raw_text = response["choices"][0]["text"]
            category = raw_text.strip().split("\n")[0]  # ✅ 첫 줄만 추출해서 카테고리로 사용
        except Exception as e:
            print(f"❌ 오류: {e}")
            category = None


        if not category or len(category) < 2 or category.lower() in ["기타", "알 수 없음", "모름", "unknown"]:
            category = None

        if silent and log_file:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[파일명 분류] {filename} -> {category if category else '분류 실패'}\n")
        elif not silent:
            print(f"[파일명 분류] {filename} → {category if category else '❌ 실패'}")

        results.append({
            "file_path": path,
            "category": category
        })

    return results
