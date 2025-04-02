# 📁 Local File Organizer (AI 기반 로컬 파일 자동 정리 도구)

AI 모델을 활용해 파일을 이름 또는 내용 기반으로 자동 분류하고  
작성일 기준, 프로젝트 단위로 정리하는 Python 기반 로컬 파일 정리 프로그램입니다.

---

## 📌 주요 기능

- 파일명을 AI로 분석하여 의미 있는 프로젝트명/카테고리 도출
- 내용 기반 보조 분류 (파일명 분석 실패 시)
- 프로젝트 단위로 자동 폴더 생성 및 정리
- `yyyy.MM` → 한글 주제 → 파일 확장자별 하위 폴더 구조 정리
- PPT, DOCX, PDF, TXT, 이미지 등 다수의 포맷 지원
- 파일명은 절대 변경하지 않음
- GUI 없이 CLI 기반으로 작동

---

## ⚙️ 개발 환경

- Windows 11 + Anaconda
- Python 3.12
- Conda 환경: `local_file_organizer`

---

## 🛠️ 1. Conda 환경 설정

```bash
# Conda 환경 생성
conda create --name local_file_organizer python=3.12

# Conda 환경 활성화
conda activate local_file_organizer
📦 2. 필수 패키지 설치
📄 requirements.txt 설치

pip install -r requirements.txt
🔧 추가 설치 필요한 모듈 (필수)
아래는 requirements.txt에 포함되지 않지만 직접 설치가 필요한 패키지입니다:


pip install python-pptx transformers sentencepiece torch sacremoses