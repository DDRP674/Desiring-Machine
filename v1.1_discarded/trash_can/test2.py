import os


def get_files_only_scandir(path):
    """使用scandir获取文件名，性能更好"""
    files = []
    with os.scandir(path) as entries:
        for entry in entries:
            if entry.is_file():
                files.append(entry.name)
    return files

print(max(get_files_only_scandir("log")))