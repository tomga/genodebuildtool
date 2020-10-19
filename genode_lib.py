
import os
import re
import subprocess

# debug support
import pprint

import mkevaluator
import mkparser

import genode_tools as tools


class GenodeLib:

    def __init__(self, lib_name, env):
        self.lib_name = lib_name
        self.env = env.Clone()

        # for use in target_path
        self.relative_lib_cache_dir = self.sconsify_path(self.env['LIB_CACHE_DIR'])


    def sconsify_path(self, path):
        return self.env['fn_sconsify_path'](path)


    def target_path(self, target):
        return '#%s/%s/%s' % (self.relative_lib_cache_dir, self.lib_name, target)


    def prepare_c_env(self):
        # setup CC, CFLAGS
        raise Exception("prepare_c_env should be overridden")


    def prepare_cc_env(self):
        # setup CXX, CXXFLAGS
        raise Exception("prepare_cc_env should be overridden")


    def prepare_s_env(self):
        # setup AS, ASFLAGS
        raise Exception("prepare_s_env should be overridden")


    def prepare_ld_env(self):
        # setup LD*
        raise Exception("prepare_ld_env should be overridden")


    def build_c_objects(self):
        src_files = self.get_c_sources()
        return self.compile_c_sources(src_files)


    def build_cc_objects(self):
        src_files = self.get_cc_sources()
        return self.compile_cc_sources(src_files)


    def build_s_objects(self):
        src_files = self.get_s_sources()
        return self.compile_s_sources(src_files)


    def build_o_objects(self):
        # requires custom builder
        return []


    def compile_c_sources(self, src_files):
        return self.generic_compile(src_files)


    def compile_cc_sources(self, src_files):
        return self.generic_compile(src_files)


    def compile_s_sources(self, src_files):
        return self.generic_compile(src_files)


    def generic_compile(self, src_files):
        objs = []
        for src_file in src_files:
            tgt_file = os.path.basename(src_file)
            tgt_file = '%s.o' % (os.path.splitext(tgt_file)[0])
            print("src_file: %s, tgt_file: %s" % (src_file, tgt_file))
            obj = self.env.SharedObject(source = src_file,
                                        target = self.target_path(tgt_file))
            objs += obj
        return objs


class GenodeMkLib(GenodeLib):
    def __init__(self, lib_name, env,
                 lib_mk_file, lib_mk_repo,
                 build_env):
        super().__init__(lib_name, env)
        self.lib_mk_file = lib_mk_file
        self.lib_mk_repo = lib_mk_repo
        self.build_env = mkevaluator.MkEnv(mk_cache=build_env.mk_cache,
                                           parent_env=build_env)
        self.build_env.var_set('REP_DIR', self.lib_mk_repo)


    def process(self):
        #import rpdb2
        #rpdb2.start_embedded_debugger('password')

        ### TODO calculate SYMBOLS
        # SYMBOLS_DIRS = $(foreach REP,$(REPOSITORIES),$(addprefix $(REP)/lib/symbols/spec/,$(SPECS)) $(REP)/lib/symbols)

        mkcache = self.build_env.get_mk_cache()

        ### handle base-libs.mk
        base_libs_mk_file = '%s/mk/base-libs.mk' % (self.env['BASE_DIR'])
        base_libs_mk = mkcache.get_parsed_mk(base_libs_mk_file)
        base_libs_mk.process(self.build_env)


        ### skipping util.inc as it is implemented in python


        ### skipping $(SPEC_FILES) as they are already included
        #
        # NOTE: passing this option is not documented


        ### handle include <lib>.mk
        self.build_env.var_set('called_from_lib_mk', 'yes')

        print("Parsing build rules for library '%s' from '%s'" % (self.lib_name, self.lib_mk_file))
        lib_mk = mkcache.get_parsed_mk(self.lib_mk_file)
        #pprint.pprint(lib_mk.debug_struct(), width=180)
        lib_mk.process(self.build_env)
        #pprint.pprint(self.build_env.debug_struct('pretty'), width=200)


        ### handle include import-<lib>.mk files
        dep_libs = self.build_env.var_values('LIBS')
        for dep_lib in dep_libs:
            dep_lib_import_mk_file, dep_lib_import_mk_repo = tools.find_first(self.env['REPOSITORIES'], 'lib/import/import-%s.mk' % (dep_lib))
            if dep_lib_import_mk_file is not None:
                print("processing import-%s file: %s" % (dep_lib, dep_lib_import_mk_file))
                dep_lib_import_mk = mkcache.get_parsed_mk(dep_lib_import_mk_file)
                dep_lib_import_mk.process(self.build_env)


        ### handle include global.mk
        global_mk_file = '%s/mk/global.mk' % (self.env['BASE_DIR'])
        global_mk = mkcache.get_parsed_mk(global_mk_file)
        global_mk.process(self.build_env)
        #pprint.pprint(self.build_env.debug_struct('pretty'), width=200)


        ### handle shared library settings

        symbols_file = self.build_env.var_value('SYMBOLS')
        shared_lib = len(symbols_file) > 0

        if shared_lib:
            self.build_env.var_set('SHARED_LIB', 'yes')

            ### TODO - symbols link file
            # $(LIB).symbols:
            #    $(VERBOSE)ln -sf $(SYMBOLS) $@
            ### handle <lib>.symbols.s


        ### handle libgcc
        # TODO cache results or maybe set unconditionally
        if shared_lib:
            ##LIBGCC = $(shell $(CC) $(CC_MARCH) -print-libgcc-file-name)
            cmd = "%s %s -print-libgcc-file-name" % (self.build_env.var_value('CC'),
                                                     self.build_env.var_value('CC_MARCH'))
            results = subprocess.run(cmd, stdout=subprocess.PIPE,
                                     shell=True, universal_newlines=True, check=True)
            output = results.stdout
            self.build_env.var_set('LIBGCC', output)



        pprint.pprint(self.build_env.debug_struct('pretty'), width=200)


        ### handle include generic.mk functionality



        ### common code

        all_inc_dir = self.build_env.var_values('ALL_INC_DIR')
        all_inc_dir = [ path for path in all_inc_dir if os.path.isdir(path) ]
        all_inc_dir = [ self.sconsify_path(path) for path in all_inc_dir ]

        self.env.AppendUnique(CPPPATH=all_inc_dir)
        print('CPPPATH: %s' % (self.env['CPPPATH']))

        self.prepare_c_env()
        self.prepare_cc_env()
        self.prepare_s_env()
        self.prepare_ld_env()

        objects = []

        ### handle c compilation
        # $(VERBOSE)$(CC) $(CC_DEF) $(CC_C_OPT) $(INCLUDES) -c $< -o $@

        c_objs = self.build_c_objects()
        objects += c_objs


        ### handle cxx compilation
        # $(VERBOSE)$(CXX) $(CXX_DEF) $(CC_CXX_OPT) $(INCLUDES) -c $< -o $@

        cc_objs = self.build_cc_objects()
        objects += cc_objs

        s_objs = self.build_s_objects()
        objects += s_objs

        o_objs = self.build_o_objects()
        objects += o_objs

        # for compatibility with make build (it won't work for special
        # cases like: a.cpp a.bbb.cpp as in make sources are sorted
        # but here object files
        objects = list(sorted(objects, key=lambda x: str(x)))

        lib_so = None
        abi_so = None
        install_so = None
        debug_so = None
        lib_checked = None
        lib_a = None

        if shared_lib:
            abi_so = '%s.abi.so' % (self.lib_name)
            if len(objects) + len(dep_libs) == 0:
                lib_so = "%s.lib.so" % (self.lib_name)
                install_so = "%s/%s" % (self.build_env.var_value('INSTALL_DIR'), lib_so)
                debug_so = "%s/%s" % (self.build_env.var_value('DEBUG_DIR'), lib_so)
        else:
            lib_a = "%s.lib.a" % (self.lib_name)

        if lib_so is not None and abi_so is not None:
            lib_checked = "%s.lib.checked" % (self.lib_name)

        print('LIB: %s %s' % (self.lib_name, 'shared' if shared_lib else 'static'))

        if shared_lib:
            # ARCHIVES += ldso_so_support.lib.a
            pass

        # TODO: LIB_IS_DYNAMIC_LINKER

        # TODO: STATIC_LIBS

        # NOTICE: LIB_SO_DEPS seems to be an artifact of the past

        # TODO: ENTRY_POINT ?= 0x0

        if lib_a is not None:
            return self.env.StaticLibrary(target=self.target_path(lib_a),
                                          source=objects)


    def get_sources(self, files):
        src_files = []
        for src_file in files:
            file_paths = self.build_env.find_vpaths(src_file)
            existing_file_paths = [ f for f in file_paths if os.path.isfile(os.path.join(f, src_file)) ]
            if len(existing_file_paths) != 1:
                print("expected exactly one vpath for %s but exist %s from %s found" % (src_file, str(existing_file_paths), str(file_paths)))
            src_file = os.path.join(existing_file_paths[0], src_file)
            src_file = self.sconsify_path(src_file)
            src_files.append(src_file)
        return src_files


    def prepare_c_env(self):
        self.env['CC'] = self.build_env.var_value('CC')

        cc_def = self.build_env.var_values('CC_DEF')
        self.env.AppendUnique(CFLAGS=cc_def)
        #print('CFLAGS: %s' % (self.env['CFLAGS']))

        cc_opt_dep_to_remove = self.build_env.var_value('CC_OPT_DEP')
        cc_c_opt = self.build_env.var_value('CC_C_OPT')
        cc_c_opt = cc_c_opt.replace(cc_opt_dep_to_remove, '')
        self.env.AppendUnique(CFLAGS=cc_c_opt.split())
        #print('CFLAGS: %s' % (self.env['CFLAGS']))


    def prepare_cc_env(self):
        self.env['CXX'] = self.build_env.var_value('CXX')

        cxx_def = self.build_env.var_values('CXX_DEF')
        self.env.AppendUnique(CXXFLAGS=cxx_def)
        #print('CXXFLAGS: %s' % (self.env['CXXFLAGS']))

        cc_opt_dep_to_remove = self.build_env.var_value('CC_OPT_DEP')
        cc_cxx_opt = self.build_env.var_value('CC_CXX_OPT')
        cc_cxx_opt = cc_cxx_opt.replace(cc_opt_dep_to_remove, '')
        self.env.AppendUnique(CXXFLAGS=cc_cxx_opt.split())
        #print('CXXFLAGS: %s' % (self.env['CXXFLAGS']))


    def prepare_s_env(self):
        self.env['AS'] = self.build_env.var_value('AS')

        #cxx_def = self.build_env.var_values('CXX_DEF')
        #self.env.AppendUnique(CXXFLAGS=cxx_def)
        ##print('CXXFLAGS: %s' % (self.env['CXXFLAGS']))
        #
        #cc_opt_dep_to_remove = self.build_env.var_value('CC_OPT_DEP')
        #cc_cxx_opt = self.build_env.var_value('CC_CXX_OPT')
        #cc_cxx_opt = cc_cxx_opt.replace(cc_opt_dep_to_remove, '')
        #self.env.AppendUnique(CXXFLAGS=cc_cxx_opt.split())
        ##print('CXXFLAGS: %s' % (self.env['CXXFLAGS']))


    def prepare_ld_env(self):
        self.env['LD'] = self.build_env.var_value('LD')
        self.env['NM'] = self.build_env.var_value('NM')
        self.env['OBJCOPY'] = self.build_env.var_value('OBJCOPY')
        self.env['RANLIB'] = self.build_env.var_value('RANLIB')
        self.env['AR'] = self.build_env.var_value('AR')
        self.env['LIBPREFIX'] = ''
        # NOTICE: reproducible builds require D - so it would be -rcsD
        self.env['ARFLAGS'] = '-rcs'
        # NOTICE: rm is not needed because scons unlinks target before
        #         build (at least for static libraries)
        # self.env['ARCOM'] = 'rm -f $TARGET\n$AR $ARFLAGS $TARGET $SOURCES'
        # NOTICE: following disables executing ranlib by scons
        self.env['RANLIBCOM'] = ""
        self.env['RANLIBCOMSTR'] = ""


    def get_c_sources(self):
        src_c = self.build_env.var_values('SRC_C')
        src_files = self.get_sources(src_c)
        return src_files


    def get_cc_sources(self):
        src_cc = self.build_env.var_values('SRC_CC')
        src_files = self.get_sources(src_cc)
        return src_files


    def get_s_sources(self):
        src_s = self.build_env.var_values('SRC_S')
        src_files = self.get_sources(src_s)
        return src_files
