
from SCons.Script import *

from functools import partial
import os


def sconstruct():

    opts = Variables()

    opts.Add('BUILD', 'Build directory (relative from genode root)')
    opts.Add('BOARD', 'Selected board')
    opts.Add('KERNEL', 'Selected kernel')
    opts.Add('LIB', 'Space separated libraries list to build', default='')
    opts.Add('LIB_EXCLUDES', 'Space separated libraries list to not build', default='')
    opts.Add('PROG_EXCLUDES', 'Space separated programs list to not build', default='')
    opts.Add(BoolVariable('VERBOSE_OUTPUT', 'Enable verbose output', default=False))
    opts.Add('LOG_LEVEL', 'Specify log output level', default='info',
             allowed_values=('none', 'error', 'warning', 'notice', 'info', 'debug', 'trace'))

    opts.Add(BoolVariable('DEV_ONLY_EXPAND_TARGETS',
                          'Internal option to just print expanded targets lists', default=False))

    env = Environment(options = opts, ENV = os.environ)

    Help(opts.GenerateHelpText(env))
    if GetOption('help'):
        return

    if 'BUILD' not in env:
        print("Required parameter BUILD is not specified. Quit.")
        quit()

    env.SConsignFile('%s/.sconsign' % (env['BUILD']))

    env['SHELL'] = 'bash'

    env['LIB_TARGETS'] = env['LIB'].split()
    env['PROG_TARGETS'] = list(BUILD_TARGETS)  # TODO: filter when adding support for run scripts
    env['LIB_EXCLUDES'] = env['LIB_EXCLUDES'].split()
    env['PROG_EXCLUDES'] = env['PROG_EXCLUDES'].split()
    env['BUILD_TARGETS'] = BUILD_TARGETS
    BUILD_TARGETS.clear()

    def nodebug(txt):
        pass
    def debug(lvl, txt):
        for line in txt.splitlines():
            print('%s: %s' % (lvl, line))

    log_level = env['LOG_LEVEL']
    env['fn_trace'] = partial(debug, 'TRC') if log_level in ['trace'] else nodebug
    env['fn_debug'] = partial(debug, 'DBG') if log_level in ['trace', 'debug'] else nodebug
    env['fn_info'] = partial(debug, 'INF') if log_level in ['trace', 'debug', 'info'] else nodebug
    env['fn_notice'] = partial(debug, 'NOT') if log_level in ['trace', 'debug', 'info', 'notice'] else nodebug
    env['fn_warning'] = partial(debug, 'WAR') if log_level in ['trace', 'debug', 'info', 'notice', 'warning'] else nodebug
    env['fn_error'] = partial(debug, 'ERR') if log_level in ['trace', 'debug', 'info', 'notice', 'warning', 'error'] else nodebug


    buildtool_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env['BUILDTOOL_DIR'] = buildtool_dir
    env['OVERLAYS_DIR'] = os.path.join(buildtool_dir, 'genode')

    env.Tool('genode_symlink',   toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_symbols',   toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_abi_so',    toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_lib_so',    toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_check_abi', toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_lib_tag',   toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_strip',     toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_binary',    toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])

    env.Decider('MD5-timestamp')

    SConscript('SConscript', exports = 'env')

