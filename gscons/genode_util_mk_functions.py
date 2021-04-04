
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



def mkfun_select_from_ports(mkenv, args):
    repositories = mkenv.var_values('REPOSITORIES')
    port_name = args[0][0]
    mkenv.log('debug', 'mkfun_select_from_ports arg: %s' % (str(port_name)))
    mkenv.log('debug', 'repositories: %s' % (str(repositories)))

    # NOTE: here mkenv is known to be ScMkEnv instance
    env = mkenv.scons_env

    required_ports = env['fn_require_ports'](env['ent_current_target_obj'], [port_name])
    assert len(required_ports) == 1
    port_dir = required_ports[0].port_dir()

    return [port_dir]



def register_mk_functions(functions_dict):
    functions_dict['select_from_repositories'] = mkfun_select_from_repositories
    functions_dict['select_from_ports'] = mkfun_select_from_ports
