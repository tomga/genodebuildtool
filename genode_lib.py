
import os
import re
import subprocess

# debug support
import pprint

import mkevaluator
import mkparser

import genode_build_helper

import genode_tools as tools


class GenodeLib:

    def __init__(self, lib_name, env, build_helper):
        self.lib_name = lib_name
        self.env = env.Clone()

        # for use in target_path
        self.relative_lib_cache_dir = self.sconsify_path(self.env['LIB_CACHE_DIR'])

        self.build_helper = build_helper

        self.env['fn_target_path'] = lambda tgt: self.target_path(tgt)


    def sconsify_path(self, path):
        return self.env['fn_sconsify_path'](path)


    def target_path(self, target):
        return '%s/%s/%s' % (self.relative_lib_cache_dir, self.lib_name, target)


    def build_c_objects(self):
        src_files = self.get_c_sources()
        return self.build_helper.compile_c_sources(self.env, src_files)


    def build_cc_objects(self):
        src_files = self.get_cc_sources()
        return self.build_helper.compile_cc_sources(self.env, src_files)


    def build_s_objects(self):
        src_files = self.get_s_sources()
        return self.build_helper.compile_s_sources(self.env, src_files)


    def build_o_objects(self):
        # requires custom builder
        return []



class GenodeMkLib(GenodeLib):
    def __init__(self, lib_name, env,
                 lib_mk_file, lib_mk_repo,
                 build_env):
        self.build_env = mkevaluator.MkEnv(mk_cache=build_env.mk_cache,
                                           parent_env=build_env)
        self.lib_mk_file = lib_mk_file
        self.lib_mk_repo = lib_mk_repo
        self.build_env.var_set('REP_DIR', self.lib_mk_repo)

        super().__init__(lib_name, env, genode_build_helper.GenodeMkBuildHelper(self.build_env))


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

        self.env['fn_info']("Parsing build rules for library '%s' from '%s'" % (self.lib_name, self.lib_mk_file))
        lib_mk = mkcache.get_parsed_mk(self.lib_mk_file)
        #self.env['fn_debug'](pprint.pformat(lib_mk.debug_struct(), width=180))
        lib_mk.process(self.build_env)
        #self.env['fn_debug'](pprint.pformat(self.build_env.debug_struct('pretty'), width=200))


        ### register library dependencies
        dep_libs = self.build_env.var_values('LIBS')
        if len(dep_libs) > 0:
            dep_lib_targets = self.env['fn_require_libs'](dep_libs)


        ### handle include import-<lib>.mk files
        for dep_lib in dep_libs:
            dep_lib_import_mk_file, dep_lib_import_mk_repo = tools.find_first(self.env['REPOSITORIES'], 'lib/import/import-%s.mk' % (dep_lib))
            if dep_lib_import_mk_file is not None:
                self.env['fn_info']("processing import-%s file: %s" % (dep_lib, dep_lib_import_mk_file))
                dep_lib_import_mk = mkcache.get_parsed_mk(dep_lib_import_mk_file)
                dep_lib_import_mk.process(self.build_env)




        ### handle include global.mk
        global_mk_file = '%s/mk/global.mk' % (self.env['BASE_DIR'])
        global_mk = mkcache.get_parsed_mk(global_mk_file)
        global_mk.process(self.build_env)
        #self.env['fn_debug'](pprint.pformat(self.build_env.debug_struct('pretty'), width=200))


        repositories = self.env['REPOSITORIES']
        specs = self.env['SPECS']
        self.env['fn_debug']("REPOSITORIES: %s" % (str(repositories)))
        self.env['fn_debug']("SPECS: %s" % (str(specs)))

        ### handle shared library settings

        ## find <lib> symbols file with repo
        symbols_file = None
        symbols_repo = None
        for repository in repositories:
            for spec in specs:
                test_symbols_file = 'lib/symbols/spec/%s/%s' % (spec, self.lib_name)
                if tools.is_repo_file(test_symbols_file, repository):
                    symbols_file = tools.file_path(test_symbols_file, repository)
                    symbols_repo = repository
                    break
            if symbols_file is not None:
                break

            test_symbols_file = 'lib/symbols/%s' % (self.lib_name)
            if tools.is_repo_file(test_symbols_file, repository):
                symbols_file = tools.file_path(test_symbols_file, repository)
                symbols_repo = repository
                break

        shared_lib = (symbols_file is not None
                      or self.build_env.var_value('SHARED_LIB') == 'yes')

        #self.env['fn_debug']("SYMBOLS_FILE: %s" % (str(symbols_file)))
        #self.env['fn_debug']("SHARED_LIB: %s" % (str(shared_lib)))


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



        self.env['fn_debug'](pprint.pformat(self.build_env.debug_struct('pretty'), width=200))


        ### handle include generic.mk functionality



        ### common code

        all_inc_dir = self.build_env.var_values('ALL_INC_DIR')
        all_inc_dir = [ path for path in all_inc_dir if os.path.isdir(path) ]
        all_inc_dir = [ self.sconsify_path(path) for path in all_inc_dir ]

        self.env.AppendUnique(CPPPATH=all_inc_dir)
        self.env['fn_debug']('CPPPATH: %s' % (self.env['CPPPATH']))

        self.build_helper.prepare_c_env(self.env)
        self.build_helper.prepare_cc_env(self.env)
        self.build_helper.prepare_s_env(self.env)
        self.build_helper.prepare_ld_env(self.env)

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

        lib_targets = []

        if symbols_file is not None:

            ### handle <lib>.abi.so generation

            abi_so = '%s.abi.so' % (self.lib_name)

            symbols_file = self.sconsify_path(os.path.join(symbols_repo, symbols_file))
            #self.env['fn_debug']('SYMBOLS_FILE: %s' % (symbols_file))
            symbols_lnk = '%s.symbols' % (self.lib_name)
            #self.env['fn_debug']('SYMBOLS_LNK: %s' % (symbols_lnk))

            # TODO: test correctness of changes of this link
            symbols_lnk_tgt = self.env.SymLink(source = symbols_file,
                                               target = self.target_path(symbols_lnk))

            ### handle <lib>.symbols.s
            symbols_asm = '%s.symbols.s' % (self.lib_name)
            symbols_asm_tgt = self.env.Symbols(source = symbols_lnk_tgt,
                                               target = self.target_path(symbols_asm))

            ### handle <lib>.symbols.o
            # assumes prepare_s_env() was already executed
            symbols_obj_tgt = self.build_helper.generic_compile(self.env, map(str, symbols_asm_tgt))

            ### handle <lib>.abi.so
            for v in ['LD_OPT', 'LIB_SO_DEPS', 'LD_SCRIPT_SO']:
                self.env[v] = self.build_env.var_value(v)
            abi_so_tgt = self.env.LibAbiSo(source = symbols_obj_tgt,
                                           target = self.target_path(abi_so))

            lib_targets.append(abi_so_tgt)


        lib_so = None
        install_so = None
        debug_so = None
        lib_checked = None
        lib_a = None

        if shared_lib:
            if len(objects) + len(dep_libs) == 0:
                lib_so = "%s.lib.so" % (self.lib_name)
                install_so = "%s/%s" % (self.build_env.var_value('INSTALL_DIR'), lib_so)
                debug_so = "%s/%s" % (self.build_env.var_value('DEBUG_DIR'), lib_so)
        else:
            lib_a = "%s.lib.a" % (self.lib_name)

        if lib_so is not None and abi_so is not None:
            lib_checked = "%s.lib.checked" % (self.lib_name)

        self.env['fn_debug']('LIB: %s %s' % (self.lib_name, 'shared' if shared_lib else 'static'))

        if shared_lib:
            # ARCHIVES += ldso_so_support.lib.a
            pass

        # TODO: LIB_IS_DYNAMIC_LINKER

        # TODO: STATIC_LIBS

        # NOTICE: LIB_SO_DEPS seems to be an artifact of the past

        # TODO: ENTRY_POINT ?= 0x0

        if lib_a is not None:
            lib_targets.append(self.env.StaticLibrary(target=self.target_path(lib_a),
                                                      source=objects))


        return self.env.Alias(self.env['fn_lib_alias_name'](self.lib_name), lib_targets)


    def get_sources(self, files):
        src_files = []
        for src_file in files:
            file_paths = self.build_env.find_vpaths(src_file)
            existing_file_paths = [ f for f in file_paths if os.path.isfile(os.path.join(f, src_file)) ]
            if len(existing_file_paths) != 1:
                self.env['fn_notice']("expected exactly one vpath for %s but exist %s from %s found" % (src_file, str(existing_file_paths), str(file_paths)))
            src_file = os.path.join(existing_file_paths[0], src_file)
            src_file = self.sconsify_path(src_file)
            src_files.append(src_file)
        return src_files


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
