
from gscons import genode_lib
import SCons.Action

class GenodeCxxMkLib(genode_lib.GenodeMkLib):

    ## hardcoded to avoid error in cxx.mk has wrong: SRC_S = supc++.o
    def get_s_sources(self):
        #src_s = self.build_env.var_values('SRC_S')
        src_s = []
        src_files = self.get_sources(src_s)
        return src_files
    def get_c_sources(self):
        #src_c = self.build_env.var_values('SRC_C')
        src_c = ['unwind.c']
        src_files = self.get_sources(src_c)
        return src_files


    def build_o_objects(self):
        self.env['fn_debug']("build_o_objects")
        cxx_src = self.build_env.var_values('CXX_SRC')
        cxx_src_files = self.get_sources(cxx_src)
        cxx_internal_objs = self.build_helper.compile_cc_sources(self.env, cxx_src_files)
        self.env['fn_debug']("build_o_objects: %s" % (str(cxx_internal_objs)))

        ## hardcoded to avoid error in cxx.mk has wrong: SRC_S = supc++.o
        #target_name = self.build_env.var_value('SRC_O')
        target_name = 'supc++.o'
        target_file = self.sc_tgt_path(target_name)

        for v in ['VERBOSE', 'MSG_MERGE', 'MSG_CONVERT',
                  'LD_MARCH', 'LIBCXX_GCC',
                  'LOCAL_SYMBOLS', 'REDEF_SYMBOLS']:
            self.env[v] = self.build_env.var_value(v)
            self.env['fn_debug']("%s: %s" % (v, self.env[v]))

        keep_symbols = self.build_env.var_values('KEEP_SYMBOLS')
        self.env['KEEP_SYMBOLS_OPTS'] = ' '.join(['-u %s' % (sym) for sym in keep_symbols])
        self.env['VERBOSE'] = ''
        self.env['RM'] = 'rm -f'

        self.env['MERGECOM'] = "${LD} ${LD_MARCH} ${KEEP_SYMBOLS_OPTS} -r ${SOURCES} ${LIBCXX_GCC} -o ${TARGET}"
        src_o_tmp = self.env.Command(
            target=str(target_file) + '.tmp',
            source=cxx_internal_objs,
            action=SCons.Action.Action("$MERGECOM", "$MERGECOMSTR")
        )

        self.env['OBJCPYCOM'] = "${OBJCOPY} ${LOCAL_SYMBOLS} ${REDEF_SYMBOLS} ${SOURCES} ${TARGET}"
        src_o = self.env.Command(
            target=target_file,
            source=str(target_file) + '.tmp',
            action=SCons.Action.Action("$OBJCPYCOM", "$OBJCPYCOMSTR")
        )

        self.env['fn_debug']("src_o: %s" % (str(src_o)))
        return src_o


def process_lib_overlay(lib_name, env, lib_mk_file, lib_mk_repo, build_env):
    env['fn_debug']("process_lib_overlay start")
    lib = GenodeCxxMkLib(lib_name, env, lib_mk_file, lib_mk_repo, build_env)
    lib.disable_overlay()
    lib.process_load()
    env['fn_debug']("process_lib_overlay end")
    return lib
