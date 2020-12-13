
import os

import mkevaluator

import buildtool_tools
import genode_tools as tools


# wrappers for mkevaluator.MkEnv and mkevaluator.MkCache that allow
# making overlays over included makefiles

class ScMkEnv(mkevaluator.MkEnv):
    def __init__(self, scons_env, mk_cache = None, parent_env = None):
        super().__init__(mk_cache, parent_env)
        self.scons_env = scons_env


class ScMkOverlay(mkevaluator.MkCommand):
    def __init__(self, overlay_file_path, mk_file_path, overlay_fun):
        self.overlay_file_path = overlay_file_path
        self.mk_file_path = mk_file_path
        self.overlay_fun = overlay_fun

    def process(self, mkenv):
        self.overlay_fun(self.mk_file_path, mkenv)

    def debug_struct(self):
        return ([ "overlay: '%s'" % self.overlay_file_path ])


# same api as mkevaluator.MkCache (it would be nice to have common
# parent interface class)
class ScMkCache:
    def __init__(self, env, mkcache):
        self.env = env
        self.mkcache = mkcache
        self.overlays_info = {}

    def get_parsed_mk(self, makefile, no_overlay=False):

        env = self.env

        if no_overlay:
            # asked explicitely for makefile
            return self.mkcache.get_parsed_mk(makefile)


        if makefile in self.overlays_info:
            # already processed
            overlay_info = self.overlays_info[makefile]
            if not overlay_info['overlay_found']:
                return self.mkcache.get_parsed_mk(makefile)

            return overlay_info['overlay']


        env['fn_debug']('get_parsed_mk: %s' % makefile)
        mk_file_path = env['fn_localize_path'](makefile)
        overlay_info_file_path = os.path.join(env['OVERLAYS_DIR'], '%s.ovr' % (mk_file_path))
        env['fn_debug']("Checking overlays info file %s" % (overlay_info_file_path))
        if not os.path.isfile(overlay_info_file_path):
            # no overlays info file - fallback to default mk processing
            self.overlays_info[makefile] = { 'overlay_found': False }
            return self.mkcache.get_parsed_mk(makefile)

        env['fn_info']("Found overlays info file %s" % (overlay_info_file_path))

        mk_file_md5 = tools.file_md5(mk_file_path)
        env['fn_info']("program mk '%s' hash: '%s'" % (mk_file_path, mk_file_md5))

        overlay_file_name = None
        with open(overlay_info_file_path, "r") as f:
            for line in f:
                if line.startswith(mk_file_md5):
                    ovr_data = line.split()
                    if len(ovr_data) < 2:
                        env['fn_error']("ERROR: invalid overlay entry in '%s':" % (overlay_info_file_path))
                        env['fn_error']("     : %s" % (line))
                        quit()
                    overlay_file_name = ovr_data[1]
        if overlay_file_name is None:
            env['fn_error']("ERROR: overlay not found in '%s' for hash '%s':" % (overlay_info_file_path, mk_file_md5))
            quit()

        overlay_file_path = os.path.join(os.path.dirname(overlay_info_file_path), overlay_file_name)

        env['fn_debug']("Checking overlay file %s" % (overlay_file_path))
        if not os.path.isfile(overlay_file_path):
            env['fn_error']("ERROR: missing overlay file '%s' mentioned metioned  in '%s':" % (overlay_file_path, overlay_info_file_path))
            quit()

        env['fn_notice']("Found overlay file '%s' for mk '%s'" % (overlay_file_path, mk_file_path))

        overlay_type = os.path.splitext(overlay_file_path)[1]
        if overlay_type == '.mk':
            parsed_makefile = self.mkcache.get_parsed_mk(overlay_file_path)
            self.overlays_info[makefile] = { 'overlay_found': True,
                                             'overlay_type': '.mk',
                                             'overlay': parsed_makefile }
            return parsed_makefile

        if overlay_type == '.sc':
            mk_overlay_fun = buildtool_tools.get_process_mk_overlay_fun(overlay_file_path)
            mk_overlay = ScMkOverlay(overlay_file_path, makefile, mk_overlay_fun)
            self.overlays_info[makefile] = { 'overlay_found': True,
                                             'overlay_type': '.sc',
                                             'overlay': mk_overlay }
            return mk_overlay

        env['fn_error']("ERROR: unsupported overlay type: '%s' ('%s') for mk '%s'"
                        % (overlay_type, overlay_file_path, mk_file_path))
        quit()
