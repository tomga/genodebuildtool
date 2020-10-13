
import genode_lib
import SCons.Action

class GenodeCxxMkLib(genode_lib.GenodeMkLib):
    def build_o_objects(self):
        print("build_o_objects")
        cxx_src = self.build_env.var_values('CXX_SRC')
        cxx_src_files = self.get_sources(cxx_src)
        cxx_internal_objs = self.compile_cc_sources(cxx_src_files)
        print("build_o_objects: %s" % (str(cxx_internal_objs)))

        target_name = self.build_env.var_value('SRC_O')
        target_file = self.target_path(target_name)

        for v in ['VERBOSE', 'MSG_MERGE', 'MSG_CONVERT',
                  'LD_MARCH', 'LIBCXX_GCC',
                  'LOCAL_SYMBOLS', 'REDEF_SYMBOLS']:
            self.env[v] = self.build_env.var_value(v)
            print("%s: %s" % (v, self.env[v]))

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

        print("src_o: %s" % (str(src_o)))
        return src_o


def process_lib_overlay(lib_name, env, lib_mk_file, lib_mk_repo, build_env):
    print("process_lib_overlay start")
    lib = GenodeCxxMkLib(lib_name, env, lib_mk_file, lib_mk_repo, build_env)
    return lib.process()
    print("process_lib_overlay end")
