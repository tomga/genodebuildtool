
import genode_lib


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

        src_o = self.env.Command(
            target=target_file,
            source=cxx_internal_objs,
            action=["${MSG_MERGE}${TARGET}",
                    "${VERBOSE}${LD} ${LD_MARCH} ${KEEP_SYMBOLS_OPTS} -r ${SOURCES} ${LIBCXX_GCC} -o ${TARGET}.tmp",
                    "${MSG_CONVERT}${TARGET}",
                    "${VERBOSE}${OBJCOPY} ${LOCAL_SYMBOLS} ${REDEF_SYMBOLS} ${TARGET}.tmp ${TARGET}",
                    "${VERBOSE}${RM} ${TARGET}.tmp"],
            #action=["${LD} ${LD_MARCH} ${KEEP_SYMBOLS_OPTS} -r ${SOURCES} ${LIBCXX_GCC} -o ${TARGET}.tmp",
            #        "${OBJCOPY} ${LOCAL_SYMBOLS} ${REDEF_SYMBOLS} ${TARGET}.tmp",
            #        "${RM} ${TARGET}.tmp"],
        )

        print("src_o: %s" % (str(src_o)))
        return src_o


def process_lib_overlay(lib_name, env, lib_mk_file, lib_mk_repo, build_env):
    print("process_lib_overlay start")
    lib = GenodeCxxMkLib(lib_name, env, lib_mk_file, lib_mk_repo, build_env)
    lib.process()
    print("process_lib_overlay end")
