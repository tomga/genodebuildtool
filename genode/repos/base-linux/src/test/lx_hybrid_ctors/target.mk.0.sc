
import os
from gscons import genode_prog
import SCons.Action
from SCons.Script import *


class GenodeBaseHwMkProg(genode_prog.GenodeMkProg):

    def do_process_target(self):

        retval = super().do_process_target()

        env = self.env.Clone()
        build_env = self.build_env

        env['CC_MARCH'] = build_env.var_value('CC_MARCH')
        env['fn_debug']("%s: %s" % ('CC_MARCH', env['CC_MARCH']))

        testlib_cc_filename = build_env.var_value('TESTLIB_SRC_CC')
        testlib_obj_filename = os.path.splitext(testlib_cc_filename)[0] + '.o'
        testlib_obj = env['fn_sc_tgt_path'](testlib_obj_filename)
        env['fn_debug']("%s: %s" % ('testlib_obj', str(testlib_obj)))

        src_files = self.get_sources([testlib_cc_filename])
        src_files = [ os.path.join(d, f) for d, f in src_files ]
        env['fn_debug']("src_files: %s -> %s" % (str([testlib_cc_filename]), str(src_files)))

        env['SHCXXCOM'] = "g++ ${CC_MARCH} -fPIC -c ${SOURCES} -o ${TARGET}"
        testlib_obj_o = env.Command(
            target=str(testlib_obj),
            source=src_files,
            action=SCons.Action.Action("$SHCXXCOM", "$SHCXXCOMSTR")
        )


        testlib_so_filename = build_env.var_value('TESTLIB_SO')
        testlib_so = env['fn_sc_tgt_path'](testlib_so_filename)

        env['LINKCOM'] = "g++ ${CC_MARCH} -shared ${SOURCES} -o ${TARGET}"
        testlib_obj_o = env.Command(
            target=str(testlib_so),
            source=testlib_obj_o,
            action=SCons.Action.Action("$LINKCOM", "$LINKCOMSTR")
        )

        return retval


def process_prog_overlay(prog_name, env, prog_mk_file, prog_mk_repo, build_env):

    prog = GenodeBaseHwMkProg(prog_name, env, prog_mk_file, prog_mk_repo, build_env)
    prog.disable_overlay()
    prog.process_load()

    return prog
