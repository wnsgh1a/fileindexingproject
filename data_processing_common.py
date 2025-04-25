import os
import shutil
import re
import datetime
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

def sanitize_filename(name, max_length=50, max_words=5):
    """Clean up and sanitize folder names."""
    name = os.path.splitext(name)[0]
    name = re.sub(r'[^\w\s가-힣]', '', name).strip()
    name = re.sub(r'[\s_]+', '_', name)
    name = name.lower()
    name = name.strip('_')
    words = name.split('_')
    limited_words = [word for word in words if word]
    limited_words = limited_words[:max_words]
    limited_name = '_'.join(limited_words)
    return limited_name[:max_length] if limited_name else '분류안됨'

def process_files_by_date(file_paths, output_path, dry_run=False, silent=False, log_file=None):
    """Organize files into year/month folders."""
    operations = []
    for file_path in file_paths:
        mod_time = os.path.getmtime(file_path)
        mod_datetime = datetime.datetime.fromtimestamp(mod_time)
        year = mod_datetime.strftime('%Y')
        month = mod_datetime.strftime('%m월')
        dir_path = os.path.join(output_path, year, month)
        new_file_path = os.path.join(dir_path, os.path.basename(file_path))
        operations.append({
            'source': file_path,
            'destination': new_file_path,
            'link_type': 'hardlink',
        })
    return operations

def process_files_by_type(file_paths, output_path, dry_run=False, silent=False, log_file=None):
    """Organize files by file type."""
    operations = []
    image_exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')
    text_exts = ('.txt', '.md', '.docx', '.doc', '.pdf', '.xls', '.xlsx', '.csv', '.ppt', '.pptx')

    for file_path in file_paths:
        if os.path.basename(file_path).startswith('.'):
            continue
        ext = os.path.splitext(file_path)[1].lower()
        if ext in image_exts:
            folder = '이미지'
        elif ext in text_exts:
            folder = '문서'
        else:
            folder = '기타'

        dir_path = os.path.join(output_path, folder)
        new_file_path = os.path.join(dir_path, os.path.basename(file_path))
        operations.append({
            'source': file_path,
            'destination': new_file_path,
            'link_type': 'hardlink',
        })
    return operations

def compute_operations(data_list, output_path, renamed_files, processed_files, preserve_filename=True):
    """Create hardlink copy operation list, preserving original filenames if specified."""
    operations = []
    for data in data_list:
        file_path = data['file_path']
        if file_path in processed_files:
            continue
        processed_files.add(file_path)

        folder_name = data['foldername']

        if preserve_filename:
            new_file_name = os.path.basename(file_path)
        else:
            new_file_name = data['filename'] + os.path.splitext(file_path)[1]

        dir_path = os.path.join(output_path, folder_name)
        new_file_path = os.path.join(dir_path, new_file_name)

        counter = 1
        while new_file_path in renamed_files:
            name, ext = os.path.splitext(new_file_name)
            new_file_path = os.path.join(dir_path, f"{name}_{counter}{ext}")
            counter += 1

        operation = {
            'source': file_path,
            'destination': new_file_path,
            'link_type': 'hardlink',
            'folder_name': folder_name,
            'new_file_name': new_file_name
        }
        operations.append(operation)
        renamed_files.add(new_file_path)

    return operations

def execute_operations(operations, dry_run=False, silent=False, log_file=None):
    """Move files according to the operations."""
    total = len(operations)
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        transient=True
    ) as progress:
        task = progress.add_task("Organizing Files...", total=total)
        for op in operations:
            src = op['source']
            dst = op['destination']
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                if not dry_run:
                    shutil.move(src, dst)
                msg = f"Moved file from '{src}' to '{dst}'"
            except Exception as e:
                msg = f"Error moving file from '{src}' to '{dst}': {e}"
            if not silent:
                print(msg)
            elif log_file:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(msg + '\n')
            progress.advance(task)
