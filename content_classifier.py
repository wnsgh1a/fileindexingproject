def extract_category(response):
    """
    AI 응답에서 '카테고리: ~' 또는 첫 줄을 기반으로 분류 카테고리를 추출합니다.
    """
    if not response:
        return "기타"

    if isinstance(response, dict):
        response_text = response.get("text", "").strip()
    else:
        response_text = str(response).strip()

    lines = response_text.split('\n')
    for line in lines:
        if "카테고리" in line:
            return line.replace("카테고리:", "").strip()
    return lines[0].strip() if lines and lines[0] else "기타"


def classify_filename_with_ai(filename, model):
    prompt = (
        "다음은 파일 이름입니다. 이 이름을 보고 어떤 주제(카테고리)로 분류하면 좋을지 한글로 짧게(예: 알고리즘, 정규화, 자료구조 등) 알려줘.\n"
        "반드시 사람이 이해할 수 있는 실제 주제명을 한 단어나 두 단어로 작성해주세요.\n"
        f"파일 이름: {filename}\n"
        "카테고리:"
    )
    response = model.create_completion(prompt)
    return extract_category(response)
    print("AI 응답:", response)




def classify_by_content(text, model):
    prompt = (
        "다음은 문서 내용입니다. 이 내용을 보고 어떤 주제(카테고리)로 분류하면 좋을지 한글로 짧게(예: 알고리즘, 정규화, 자료구조 등) 알려줘.\n"
        "반드시 사람이 이해할 수 있는 실제 주제명을 한 단어나 두 단어로 작성해주세요.\n"
        f"문서 내용: {text[:1000]}\n"
        "카테고리:"
    )
    response = model.create_completion(prompt)
    return extract_category(response)
    print("AI 응답:", response)



