# content_classifier.py (AI가 파일명에서 주제를 뽑고, 그걸 폴더명으로 반환)

def extract_category(response):
    if not response:
        return "미분류"

    if isinstance(response, dict):
        response_text = response.get("text", "").strip()
    else:
        response_text = str(response).strip()

    lines = response_text.split('\n')
    for line in lines:
        if "카테고리:" in line:
            return line.split("카테고리:")[-1].strip()

    candidates = [line.strip() for line in lines if 2 <= len(line.strip()) <= 20]
    if candidates:
        return candidates[0]

    return "미분류"


def classify_filename_with_ai(filename, model):
    filename_lower = filename.lower()
    prompt = (
        "아래는 파일 이름입니다. 이 이름을 보고 어떤 주제(폴더명)로 정리하면 좋을지 한 단어나 두 단어로 알려줘.\n"
        "예: 정규화, 알고리즘, 자료구조, 데이터베이스 등.\n"
        f"파일 이름: {filename}\n"
        "카테고리:"
    )
    response = model.create_completion(prompt)
    print(f"[AI 응답] {filename} -> {response}")
    return extract_category(response)