import os
import shutil
import hashlib
import difflib
from datetime import datetime
from collections import defaultdict, deque
from docx import Document  # 추가: .docx 텍스트 추출용

# ✅ 삭제 후보군 디렉토리 경로
CANDIDATE_DIR = r"C:\Users\qazws\Desktop\삭제후보"
GUBOJEON_DIR = os.path.join(CANDIDATE_DIR, "구버전")
DUPLICATE_DIR = os.path.join(CANDIDATE_DIR, "중복파일")

# ✅ 해시값 계산 (전체 파일 해시)
def calculate_file_hash(file_path):
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            sha256.update(f.read())  # 전체 파일 해시 계산
        return sha256.hexdigest()
    except Exception as e:
        print(f"Error hashing {file_path}: {e}")
        return None

# ✅ 파일 이동 함수
def move_to_category(file_path, category, reason=""):
    category_dir = os.path.join(CANDIDATE_DIR, category)
    os.makedirs(category_dir, exist_ok=True)

    destination = os.path.join(category_dir, os.path.basename(file_path))
    base, ext = os.path.splitext(destination)
    counter = 1

    while os.path.exists(destination):
        destination = f"{base}_{counter}{ext}"
        counter += 1

    shutil.move(file_path, destination)
    print(f"✅ {os.path.basename(file_path)} → {category_dir} 이유: {reason}")

# ✅ 파일명 정제 함수
def simplify_filename(filename):
    import re
    name, _ = os.path.splitext(filename.lower())
    # 버전 패턴 제거 (v2, ver3, v_4, ver.5 등)
    name = re.sub(r"(ver|v)?[\._\-]?[0-9]+(\.[0-9]+)?", "", name)
    keywords = ["rev", "판본", "draft", "수정본", "최종", "복사본"]
    for keyword in keywords:
        name = name.replace(keyword, "")
    return name.strip().replace("_", "").replace(" ", "")

# ✅ .docx 내용 추출 함수
def extract_docx_text(path):
    try:
        doc = Document(path)
        return "\n".join([p.text for p in doc.paragraphs])
    except:
        return ""

# ✅ 텍스트 유사도 비교 함수 (.docx 전용)
def is_content_similar(file1, file2, threshold=0.85):
    try:
        text1 = extract_docx_text(file1)
        text2 = extract_docx_text(file2)
        similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
        return similarity >= threshold
    except:
        return False

# ✅ 유사도 기반 파일 클러스터 구성 함수
def build_similarity_clusters(similarity_groups):
    visited = set()
    clusters = []

    for file in similarity_groups:
        if file in visited:
            continue
        cluster = set()
        queue = deque([file])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            cluster.add(current)
            queue.extend(similarity_groups[current] - visited)
        if cluster:
            clusters.append(cluster)
    return clusters

# ✅ 전체 검사 기반 정리 함수 (중복 + 구버전)
def isolate_all(directory):
    print(f"\n📌 전체 폴더 기반 중복 및 구버전 정리 시작: {directory}\n")

    file_paths = []
    file_hashes = defaultdict(list)
    file_groups = defaultdict(list)
    duplicate_hashes = set()

    # ✅ 하위 디렉토리까지 파일 수집
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            if not os.path.isfile(path):
                continue

            file_paths.append(path)
            file_hash = calculate_file_hash(path)
            if file_hash:
                file_hashes[file_hash].append(path)

    # 2. 중복 정리 (해시가 같으면 무조건 중복으로 간주)
    for hash_value, hash_group in file_hashes.items():
        if len(hash_group) <= 1:
            continue
        duplicate_hashes.update(hash_group)
        latest = max(hash_group, key=lambda x: os.path.getmtime(x))
        for f in hash_group:
            if f != latest:
                move_to_category(f, "중복파일", reason="전체 검사 기반 중복파일 정리")

    # 3. 구버전 정리용 그룹화 (중복 파일 제외)
    for path in file_paths:
        if not os.path.isfile(path) or path in duplicate_hashes:
            continue
        simplified = simplify_filename(os.path.basename(path))
        file_groups[simplified].append(path)

    # 4. 구버전 정리 (유사도 기반 클러스터링 → 최신만 유지)
    for group, files in file_groups.items():
        if len(files) <= 1:
            continue
        similarity_graph = defaultdict(set)
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                if is_content_similar(files[i], files[j]):
                    similarity_graph[files[i]].add(files[j])
                    similarity_graph[files[j]].add(files[i])

        # 🧩 유사도가 연결되지 않은 단독 파일도 포함되도록 보완
        all_related = set()
        for k, v in similarity_graph.items():
            all_related.add(k)
            all_related.update(v)
        unclustered = set(files) - all_related
        for f in unclustered:
            similarity_graph[f] = set()

        clusters = build_similarity_clusters(similarity_graph)
        for cluster in clusters:
            latest = max(cluster, key=lambda x: os.path.getmtime(x))
            for f in cluster:
                if f != latest:
                    move_to_category(f, "구버전", reason="내용 유사 기반 구버전 정리")

    print("\n✅ 전체 정리가 완료되었습니다.\n")
