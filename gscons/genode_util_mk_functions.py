
import os

def mkfun_select_from_repositories(mkenv, args):
    repositories = mkenv.var_values('REPOSITORIES')
    file_pattern = args[0][0]
    #mkenv.log('debug', 'mkfun_select_from_repositories arg: %s' % (str(file_pattern)))
    #mkenv.log('debug', 'repositories: %s' % (str(repositories)))
    if file_pattern.startswith('/'):
        mkenv.log('warning', 'select_from_repositories pattern starting with /: %s'
                  % (str(file_pattern)))
        file_pattern = file_pattern[1:]
    for repository in repositories:
        checked_file = os.path.join(repository, file_pattern)
        if os.path.exists(checked_file):
            #mkenv.log('debug', 'return: %s' % (str([checked_file])))
            return [checked_file]
    #mkenv.log('debug', 'return: %s' % (str([])))
    return []



def register_mk_functions(functions_dict):
    functions_dict['select_from_repositories'] = mkfun_select_from_repositories
