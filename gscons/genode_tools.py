
import fnmatch
import glob
import hashlib
import os
import re

def is_file(file_path):
    return  os.path.isfile(file_path)

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

def is_repo_file(relative_repo_path, repo_path):
    return is_file(file_path(relative_repo_path, repo_path))

def file_md5(file_path):
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def expand_lib_targets(repositories, specs, lib_targets, lib_excludes):
    lib_patterns = [ lib for lib in lib_targets if '*' in lib ]
    if len(lib_patterns) == 0:
        return lib_targets

    found_libs = []
    for repository in repositories:
        mk_list = glob.glob('%s/lib/mk/*.mk' % (repository))
        found_libs.extend([ os.path.splitext(os.path.basename(mk))[0] for mk in mk_list ])

        mk_list = glob.glob('%s/lib/mk/spec/*/*.mk' % (repository))
        # filter out those with spec not in specs
        mk_list = [ mk for mk in mk_list if os.path.basename(os.path.dirname(mk)) in specs ]
        found_libs.extend([ os.path.splitext(os.path.basename(mk))[0] for mk in mk_list ])

    found_libs = sorted(list(set(found_libs)))

    for excl in lib_excludes:
        found_libs = [ lib for lib in found_libs if not fnmatch.fnmatch(lib, excl) ]

    result = []
    processed = set([])

    for lib in lib_targets:
        if '*' not in lib:
            if lib not in processed:
                result.append(lib)
                processed.add(lib)
            continue

        all_matches = fnmatch.filter(found_libs, lib)
        new_matches = [ lib for lib in all_matches if lib not in processed ]

        result.extend(new_matches)
        processed = processed | set(new_matches)

    return result


def expand_prog_targets(repositories, prog_targets, prog_excludes):
    prog_patterns = [ prog for prog in prog_targets if '*' in prog ]
    if len(prog_patterns) == 0:
        return prog_targets

    prog_excludes = ['lib'] + prog_excludes

    specs_pattern = re.compile('/spec/.*')

    found_progs = []
    for repository in repositories:
        mk_list = glob.glob('%s/src/**/target.mk' % (repository), recursive=True)
        progs = [ mk[len(repository)+len('/src/'):-len('/target.mk')] for mk in mk_list ]
        progs = [ specs_pattern.sub('', prog) for prog in progs ]
        found_progs.extend(progs)

    found_progs = sorted(list(set(found_progs)))

    for excl in prog_excludes:
        found_progs = [ prog for prog in found_progs if not fnmatch.fnmatch(prog, excl) ]

    result = []
    processed = set([])

    for prog in prog_targets:
        if '*' not in prog:
            if prog not in processed:
                result.append(prog)
                processed.add(prog)
            continue

        all_matches = fnmatch.filter(found_progs, prog)
        new_matches = [ prog for prog in all_matches if prog not in processed ]

        result.extend(new_matches)
        processed = processed | set(new_matches)

    return result


def expand_run_targets(repositories, run_targets, run_excludes):
    run_patterns = [ run for run in run_targets if '*' in run ]
    if len(run_patterns) == 0:
        return run_targets

    found_runs = []
    for repository in repositories:
        run_list = glob.glob('%s/run/*.run' % (repository))
        found_runs.extend([ os.path.splitext(os.path.basename(run))[0] for run in run_list ])

    found_runs = sorted(list(set(found_runs)))

    for excl in run_excludes:
        found_runs = [ run for run in found_runs if not fnmatch.fnmatch(run, excl) ]

    result = []
    processed = set([])

    for run in run_targets:
        if '*' not in run:
            if run not in processed:
                result.append(run)
                processed.add(run)
            continue

        all_matches = fnmatch.filter(found_runs, run)
        new_matches = [ run for run in all_matches if run not in processed ]

        result.extend(new_matches)
        processed = processed | set(new_matches)

    return result
