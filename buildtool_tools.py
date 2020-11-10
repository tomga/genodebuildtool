
import importlib.util
import importlib.machinery

import os
import re
import sys

buildtool_dir = os.path.dirname(os.path.abspath(__file__))
overlay_localization_pattern = re.compile('^%s/' % (buildtool_dir))

def get_process_lib_overlay_fun(file_path):
    module = import_module_from_overlay(file_path)
    process_lib_overlay_fun = getattr(module, 'process_lib_overlay')
    return process_lib_overlay_fun
    

def import_module_from_overlay(file_path, register_module=False):
    relative_file_path = overlay_localization_pattern.sub('', file_path)
    module_name = relative_file_path.replace('/', '.')
    #print("relative_file_path: %s" % (relative_file_path))
    #print("module_name: %s" % (module_name))

    return import_module_from_file(module_name, file_path, register_module)


def import_module_from_file(module_name, file_path, register_module=False):
    assert "FIXIT"

    module_name = 'genode.repos.base.lib.mk.cxx0'
    #module_name = 'cxx0'
    file_path = '/projects/genode/buildtool/genode/repos/base/lib/mk/cxx0.sc'

    #spec = importlib.util.spec_from_file_location(module_name, file_path)
    spec = importlib.util.spec_from_loader(module_name,
                                           importlib.machinery.SourceFileLoader(module_name, file_path))
    #print("spec: %s" % (str(spec)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Optional; only necessary if you want to be able to import the module
    # by name later.
    if register_module:
        sys.modules[module_name] = module

    return module
