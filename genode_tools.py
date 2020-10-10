
import hashlib
import os

def check_files(files):
    return [ file_path for file_path in files if os.path.isfile(file_path) ]    

def find_files(pattern, arg_list):
    files_to_check = [ pattern % (arg) for arg in arg_list ]
    return check_files(files_to_check)

def find_first(paths, relative_path):
    for p in paths:
        checked_file = os.path.join(p, relative_path)
        if os.path.isfile(checked_file):
            return checked_file, p
    return None, None

def file_path(relative_repo_path, repo_path):
    return os.path.join(repo_path, relative_repo_path)

def file_md5(file_path):
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()
