
from SCons.Script import *

import os


def sconstruct():

    opts = Variables()

    opts.Add('BUILD', 'Build directory (relative from genode root)')

    env = Environment(options = opts, ENV = os.environ)
    env.SConsignFile('%s/.sconsign' % (env['BUILD']))

    buildtool_dir = os.path.dirname(os.path.abspath(__file__))
    env['BUILDTOOL_DIR'] = buildtool_dir
    env['OVERLAYS_DIR'] = os.path.join(buildtool_dir, 'genode')

    SConscript('SConscript', exports = 'env')

