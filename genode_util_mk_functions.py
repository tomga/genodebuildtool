
import os

def mkfun_select_from_repositories(mkenv, args):
    repositories = mkenv.get_var('REPOSITORIES').get_value().values_list(mkenv)
    print('repositories: %s' % (str(repositories)))
    file_pattern = args[0][0]
    print('arg: %s' % (str(file_pattern)))
    for repository in repositories:
        checked_file = os.path.join(repository, file_pattern)
        if os.path.isfile(checked_file):
            print('return: %s' % (str([checked_file])))
            return [checked_file]
    print('return: %s' % (str([])))
    return []



def register_mk_functions(functions_dict):
    functions_dict['select_from_repositories'] = mkfun_select_from_repositories
