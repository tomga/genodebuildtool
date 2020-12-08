
from SCons.Script import *

from functools import partial
import os


def sconstruct():

    opts = Variables()

    opts.Add('BUILD', 'Build directory (relative from genode root)')
    opts.Add('BOARD', 'Selected board')
    opts.Add('LIB', 'Space separated libraries list to build (named for conformance with mk build)')
    opts.Add(BoolVariable('VERBOSE_OUTPUT', 'Enable verbose output', default=False))
    opts.Add('LOG_LEVEL', 'Specify log output level', default='none',
             allowed_values=('none', 'error', 'warning', 'notice', 'info', 'debug'))

    env = Environment(options = opts, ENV = os.environ)
    env.SConsignFile('%s/.sconsign' % (env['BUILD']))

    env['LIB_TARGETS'] = env['LIB'].split() if 'LIB' in env else []
    env['PROG_TARGETS'] = list(BUILD_TARGETS)  # TODO: filter when adding support for run scripts
    env['BUILD_TARGETS'] = BUILD_TARGETS
    BUILD_TARGETS.clear()

    def nodebug(txt):
        pass
    def debug(lvl, txt):
        for line in txt.splitlines():
            print('%s: %s' % (lvl, line))

    log_level = env['LOG_LEVEL']
    env['fn_debug'] = partial(debug, 'DBG') if log_level in ['debug'] else nodebug
    env['fn_info'] = partial(debug, 'INF') if log_level in ['debug', 'info'] else nodebug
    env['fn_notice'] = partial(debug, 'NOT') if log_level in ['debug', 'info', 'notice'] else nodebug
    env['fn_warning'] = partial(debug, 'WAR') if log_level in ['debug', 'info', 'notice', 'warning'] else nodebug
    env['fn_error'] = partial(debug, 'ERR') if log_level in ['debug', 'info', 'notice', 'warning', 'error'] else nodebug


    buildtool_dir = os.path.dirname(os.path.abspath(__file__))
    env['BUILDTOOL_DIR'] = buildtool_dir
    env['OVERLAYS_DIR'] = os.path.join(buildtool_dir, 'genode')

    env.Tool('genode_symlink', toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'tools')])
    env.Tool('genode_symbols', toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'tools')])
    env.Tool('genode_abi_so',  toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'tools')])
    env.Tool('genode_lib_so',  toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'tools')])
    env.Tool('genode_lib_tag', toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'tools')])
    env.Tool('genode_strip',   toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'tools')])
    env.Tool('genode_binary',  toolpath = [os.path.join(env['BUILDTOOL_DIR'], 'tools')])

    SConscript('SConscript', exports = 'env')

