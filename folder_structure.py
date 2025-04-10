import os
import shutil
from datetime import datetime

def get_quarter_label_from_timestamp(timestamp):
    dt = datetime.fromtimestamp(timestamp)
    year = str(dt.year)
    quarter = (dt.month - 1) // 3 + 1
    quarter_korean = f"{quarter}분기"
    return year, quarter_korean

def organize_by_year_and_quarter(base_dir, output_dir=None):
    from datetime import datetime
    if output_dir is None:
        output_dir = os.path.join(base_dir, "organized_by_quarter")

    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(base_dir):
        filepath = os.path.join(base_dir, filename)
        if not os.path.isfile(filepath):
            continue

        created_time = os.path.getctime(filepath)
        dt = datetime.fromtimestamp(created_time)
        year = str(dt.year)
        quarter = f"Q{(dt.month - 1) // 3 + 1}"

        target_dir = os.path.join(output_dir, year, quarter)
        os.makedirs(target_dir, exist_ok=True)
        shutil.move(filepath, os.path.join(target_dir, filename))
        print(f"[이동 완료] {filename} → {year}/{quarter}/")

    return output_dir  # ✅ 정리된 폴더를 반환
