
from SCons.Script import *

import os


def sconstruct():

    opts = Variables()

    opts.Add('BUILD', 'Build directory (relative from genode root)')

    env = Environment(options = opts, ENV = os.environ)

    SConscript('SConscript', exports = 'env')

