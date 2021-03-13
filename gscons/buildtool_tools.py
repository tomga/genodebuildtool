
import importlib.util
import importlib.machinery

import os
import re
import sys

buildtool_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
overlay_localization_pattern = re.compile('^%s/' % (buildtool_dir))
ignored_overlay_extension_pattern = re.compile(r'^\.(sc|[0-9]+)$')


def get_process_mk_overlay_fun(file_path):
    module = import_module_from_overlay(file_path)
    process_mk_overlay_fun = getattr(module, 'process_mk_overlay')
    return process_mk_overlay_fun


def get_process_lib_overlay_fun(file_path):
    module = import_module_from_overlay(file_path)
    process_lib_overlay_fun = getattr(module, 'process_lib_overlay')
    return process_lib_overlay_fun


def get_process_prog_overlay_fun(file_path):
    module = import_module_from_overlay(file_path)
    process_prog_overlay_fun = getattr(module, 'process_prog_overlay')
    return process_prog_overlay_fun


def import_module_from_overlay(file_path, register_module=False):
    relative_file_path = overlay_localization_pattern.sub('', file_path)
    overlay_base, overlay_extension = os.path.splitext(relative_file_path)
    while (ignored_overlay_extension_pattern.match(overlay_extension)):
        relative_file_path = overlay_base
        overlay_base, overlay_extension = os.path.splitext(relative_file_path)

    module_name = relative_file_path.replace('/', '.')
    #print("relative_file_path: %s" % (relative_file_path))
    #print("module_name: %s" % (module_name))

    return import_module_from_file(module_name, file_path, register_module)


def import_module_from_file(module_name, file_path, register_module=False):

    #print("imff: file_path: %s" % (file_path))
    #print("imff: module_name: %s" % (module_name))
    #print("imff: buildtool_dir: %s" % (buildtool_dir))

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
