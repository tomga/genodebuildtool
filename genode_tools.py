
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
            return checked_file
    return None

