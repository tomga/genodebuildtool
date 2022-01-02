
from SCons.Script import *

from functools import partial
import os


def sconstruct():

    opts = Variables()

    opts.Add('BUILD', 'Build directory (relative from genode root)')
    opts.Add('BOARD', 'Selected board')
    opts.Add('KERNEL', 'Selected kernel')
    opts.Add('LIB', 'Space separated libraries list to build (alias for LIB_TARGETS for compatibility)', default='')
    opts.Add('LIB_TARGETS', 'Space separated libraries list to build', default='')
    opts.Add('LIB_EXCLUDES', 'Space separated libraries list to not build', default='')
    opts.Add('PROG_TARGETS', 'Space separated programs list to build', default='')
    opts.Add('PROG_EXCLUDES', 'Space separated programs list to not build', default='')
    opts.Add('RUN_TARGETS', 'Space separated run scenarios list to build', default='')
    opts.Add('RUN_EXCLUDES', 'Space separated run scripts list to not build', default='')
    opts.Add(BoolVariable('VERBOSE_OUTPUT', 'Enable verbose output', default=False))
    opts.Add('LOG_LEVEL', 'Specify log output level', default='info',
             allowed_values=('none', 'error', 'warning', 'notice', 'info', 'debug', 'trace'))

    opts.Add(BoolVariable('PORT_AUTO_UPDATE', 'Automatically update ports', default=False))

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


    if env['LIB_TARGETS'] != '' and env['LIB'] != '':
        env['fn_error']("LIB_TARGETS and LIB (compatibility option) cannot be provided simutlanously")
        quit()

    compatibilityProgTargets = [t for t in BUILD_TARGETS if not t.startswith('run/')]
    if env['PROG_TARGETS'] != '' and len(compatibilityProgTargets) != 0:
        env['fn_error']("PROG_TARGETS and compatibility prog targets cannot be provided simutlanously")
        quit()

    compatibilityRunTargets = [t[4:] for t in BUILD_TARGETS if t.startswith('run/')]
    if env['RUN_TARGETS'] != '' and len(compatibilityRunTargets) != 0:
        env['fn_error']("RUN_TARGETS and compatibility run targets cannot be provided simutlanously")
        quit()


    env['LIB_TARGETS'] = env['LIB_TARGETS'].split() if env['LIB_TARGETS'] != '' else env['LIB'].split()
    env['LIB_EXCLUDES'] = env['LIB_EXCLUDES'].split()
    env['PROG_TARGETS'] = env['PROG_TARGETS'].split() if env['PROG_TARGETS'] != '' else compatibilityProgTargets
    env['PROG_EXCLUDES'] = env['PROG_EXCLUDES'].split()
    env['RUN_TARGETS'] = env['RUN_TARGETS'].split() if env['RUN_TARGETS'] != '' else compatibilityRunTargets
    env['RUN_EXCLUDES'] = env['RUN_EXCLUDES'].split()
    env['BUILD_TARGETS'] = BUILD_TARGETS
    BUILD_TARGETS.clear()


    buildtool_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env['BUILDTOOL_DIR'] = buildtool_dir
    env['OVERLAYS_DIR'] = os.path.join(buildtool_dir, 'genode')

    env.Tool('genode_symlink',   toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_copy',      toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_symbols',   toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_abi_so',    toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_lib_so',    toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_check_abi', toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_lib_tag',   toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_strip',     toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])
    env.Tool('genode_binary',    toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'gscons/tools')])

    env.Decider('MD5-timestamp')

    SConscript('SConscript', exports = 'env')

