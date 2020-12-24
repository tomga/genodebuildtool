
import os
import re
import subprocess

# debug support
import pprint

import mkevaluator
import mkparser
import scmkevaluator

import genode_build_helper

import genode_tools as tools


class GenodeLib:

    def __init__(self, lib_name, env, build_helper):
        self.lib_name = lib_name
        self.env = env

        # for use in target_path
        self.relative_lib_cache_dir = self.sconsify_path(self.env['LIB_CACHE_DIR'])

        self.build_helper = build_helper

        self.env['fn_current_target_type'] = lambda : 'lib'
        self.env['fn_current_target_alias'] = lambda : self.env['fn_lib_alias_name'](self.lib_name)
        self.env['fn_target_path'] = lambda tgt: self.target_path(tgt)

        self.post_process_actions = []
        self.env['fn_add_post_process_action'] = lambda action: self.post_process_actions.append(action)

    def sconsify_path(self, path):
        return self.env['fn_sconsify_path'](path)


    def target_path(self, target):
        if target is not None:
            return '%s/%s/%s' % (self.relative_lib_cache_dir, self.lib_name, target)
        else:
            return '%s/%s' % (self.relative_lib_cache_dir, self.lib_name)


    def build_c_objects(self):
        src_files = self.get_c_sources()
        return self.build_helper.compile_c_sources(self.env, src_files)


    def build_cc_objects(self):
        src_files = self.get_cc_sources()
        return self.build_helper.compile_cc_sources(self.env, src_files)


    def build_s_objects(self):
        src_files = self.get_s_sources()
        return self.build_helper.compile_s_sources(self.env, src_files)


    def build_binary_objects(self):
        src_files = self.get_binary_sources()
        return self.build_helper.compile_binary_sources(self.env, src_files)


    def build_o_objects(self):
        # requires custom builder
        return []



class GenodeMkLib(GenodeLib):
    def __init__(self, lib_name, env,
                 lib_mk_file, lib_mk_repo,
                 build_env):

        lib_env = env.Clone()

        self.build_env = scmkevaluator.ScMkEnv(lib_env,
                                               mk_cache=build_env.mk_cache,
                                               parent_env=build_env)
        self.lib_mk_file = lib_mk_file
        self.lib_mk_repo = lib_mk_repo
        self.build_env.var_set('REP_DIR', self.lib_mk_repo)

        super().__init__(lib_name, lib_env,
                         genode_build_helper.GenodeMkBuildHelper(self.build_env))

        self.no_overlay = False


    def disable_overlay(self):
        self.no_overlay = True


    def process(self):
        #import rpdb2
        #rpdb2.start_embedded_debugger('password')

        ### TODO calculate SYMBOLS
        # SYMBOLS_DIRS = $(foreach REP,$(REPOSITORIES),$(addprefix $(REP)/lib/symbols/spec/,$(SPECS)) $(REP)/lib/symbols)

        mkcache = self.build_env.get_mk_cache()

        ### # remember value of rep_inc_dir and reset it to empty; it is
        ### # important to put those remembered values to end of list
        ### # after processing locally imported makefiles to preserve
        ### # sequence of include path like in mk build
        ### global_rep_inc_dir = self.build_env.var_values('REP_INC_DIR')
        ### self.build_env.var_set('REP_INC_DIR', '')

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
        # overlays for <lib>.mk are already handled on a different level
        lib_mk = mkcache.get_parsed_mk(self.lib_mk_file, no_overlay=self.no_overlay)
        #self.env['fn_debug'](pprint.pformat(lib_mk.debug_struct(), width=180))
        lib_mk.process(self.build_env)
        #self.env['fn_debug'](pprint.pformat(self.build_env.debug_struct('pretty'), width=200))


        specs = self.env['SPECS']
        self.env['fn_debug']("SPECS: %s" % (str(specs)))


        requires = self.build_env.var_values('REQUIRES')
        missing_specs = [ req for req in requires if req not in specs ]
        if len(missing_specs) > 0:
            self.env['fn_info']("Skipping building library '%s' due to missing specs: %s"
                                % (self.lib_name, ' '.join(missing_specs)))
            return self.env.Alias(self.env['fn_lib_alias_name'](self.lib_name), [])


        ### register library dependencies
        direct_dep_libs = self.build_env.var_values('LIBS')
        if len(direct_dep_libs) > 0:
            dep_lib_targets = self.env['fn_require_libs'](direct_dep_libs)

        all_direct_dep_libs = direct_dep_libs + []

        ### add ldso_so_support as a dependency
        #
        # NOTE: in case of libraries such as ld (on linux) which are
        #       not compiled and linked but created using symbols this
        #       dependency is not needed but it is added here for full
        #       compatibility
        shared_lib_defined = self.build_env.check_var('SHARED_LIB')
        if shared_lib_defined:
            ldso_support_lib_target = self.env['fn_require_libs'](['ldso_so_support'])
            all_direct_dep_libs.append('ldso_so_support')

        ### calculate list of library dependencies (recursively complete)
        lib_deps = []
        for dep_lib in all_direct_dep_libs:
            dep_lib_deps = self.env['fn_get_lib_info'](dep_lib)['lib_deps']
            lib_deps.extend(dep_lib_deps)
        lib_deps = sorted(list(set(lib_deps)))
        self.env['fn_debug']("all_direct_dep_libs: '%s'" % (str(all_direct_dep_libs)))
        self.env['fn_debug']("lib_deps: '%s'" % (str(lib_deps)))

        lib_so_deps = []
        lib_a_deps = []
        for lib in lib_deps:
            if self.env['fn_get_lib_info'](lib)['type'] == 'a':
                lib_a_deps.append(lib)
            else:
                lib_so_deps.append(lib)

        ### create links to shared library dependencies
        dep_shlib_links = self.build_helper.create_dep_lib_links(
            self.env, self.target_path(None), lib_so_deps)


        ### handle include global.mk
        global_mk_file = '%s/mk/global.mk' % (self.env['BASE_DIR'])
        global_mk = mkcache.get_parsed_mk(global_mk_file)
        global_mk.process(self.build_env)
        #self.env['fn_debug'](pprint.pformat(self.build_env.debug_struct('pretty'), width=200))


        ### handle include import-<lib>.mk files
        for dep_lib in all_direct_dep_libs:
            dep_lib_import_mk_file, dep_lib_import_mk_repo = tools.find_first(self.env['REPOSITORIES'], 'lib/import/import-%s.mk' % (dep_lib))
            if dep_lib_import_mk_file is not None:
                self.env['fn_info']("processing import-%s file: %s" % (dep_lib, dep_lib_import_mk_file))
                dep_lib_import_mk = mkcache.get_parsed_mk(dep_lib_import_mk_file)
                dep_lib_import_mk.process(self.build_env)


        ### # fix rep_inc_dir content - important to be before processing global.mk
        ### current_rep_inc_dir = self.build_env.var_values('REP_INC_DIR')
        ### full_rep_inc_dir = current_rep_inc_dir + global_rep_inc_dir
        ### #self.env['fn_debug']('--- %s' % self.lib_name)
        ### #self.env['fn_debug']('global_rep_inc_dir: %s' % (str(global_rep_inc_dir)))
        ### #self.env['fn_debug']('current_rep_inc_dir: %s' % (str(current_rep_inc_dir)))
        ### #self.env['fn_debug']('full_rep_inc_dir: %s' % (str(full_rep_inc_dir)))
        ### self.build_env.var_set('REP_INC_DIR', ' '.join(full_rep_inc_dir))
        ### #self.env['fn_debug']('REP_INC_DIR: %s' % (str(self.build_env.var_values('REP_INC_DIR'))))


        ### handle include global.mk again
        # global.mk has to be processed again due to handling of
        # ALL_INC_DIR which is calculated using HOST_INC_DIR that can
        # be modified in import-<lib>.mk files like in
        # import-syscall-linux.mk. It cannot be processed only after
        # inclusiono of import-<lib>.mk files as values set in it are
        # required in some import-<lib>.mk files like CUSTOM_HOST_CC
        # in import-lx_hybrid.mk
        global_mk.process(self.build_env)


        repositories = self.env['REPOSITORIES']
        self.env['fn_debug']("REPOSITORIES: %s" % (str(repositories)))


        ### handle shared library settings

        ## find <lib> symbols file with repo
        symbols_file = None
        symbols_repo = None
        symbols_file_path = None
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
        if symbols_file is not None:
            symbols_file_path = os.path.join(symbols_repo, symbols_file)

        if self.build_env.check_var('SYMBOLS'):
            symbols_full_path = self.build_env.var_value('SYMBOLS')
            symbols_file_path = self.env['fn_localize_path'](symbols_full_path)

        shared_lib = (symbols_file_path is not None
                      or self.build_env.var_value('SHARED_LIB') == 'yes')

        self.env['fn_debug']("SYMBOLS_FILE: %s" % (str(symbols_file_path)))
        self.env['fn_debug']("SHARED_LIB: %s" % (str(shared_lib)))


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
            self.env['LIBGCC'] = output



        self.env['fn_debug'](pprint.pformat(self.build_env.debug_struct('pretty'), width=200))


        ### handle include generic.mk functionality



        ### common code

        all_inc_dir = self.build_env.var_values('ALL_INC_DIR')
        all_inc_dir = [ path for path in all_inc_dir if os.path.isdir(path) ]
        all_inc_dir = [ self.sconsify_path(path) for path in all_inc_dir ]

        self.env.AppendUnique(CPPPATH=all_inc_dir)
        self.env['fn_debug']('CPPPATH: %s' % (self.env['CPPPATH']))

        self.build_helper.prepare_env(self.env)

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

        binary_objs = self.build_binary_objects()
        objects += binary_objs

        o_objs = self.build_o_objects()
        objects += o_objs

        # for compatibility with make build (it won't work for special
        # cases like: a.cpp a.bbb.cpp as in make sources are sorted
        # but here object files
        objects = list(sorted(objects, key=lambda x: str(x)))

        lib_targets = []

        # lib_type as abi/so/a information is put into libraries info
        # registry for use by other libraries and programs that depend
        # on it
        lib_type = None

        abi_so = None

        symbols_file = None
        if symbols_file_path is not None:

            ### handle <lib>.abi.so generation

            abi_so = '%s.abi.so' % (self.lib_name)

            symbols_file = self.sconsify_path(symbols_file_path)
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
            symbols_obj_tgt = self.build_helper.generic_compile(self.env, map(str, symbols_asm_tgt), 'ASFLAGS')

            ### handle <lib>.abi.so
            for v in ['LD_OPT', 'LIB_SO_DEPS', 'LD_SCRIPT_SO']:
                self.env[v] = self.build_env.var_value(v)
            abi_so_tgt = self.env.LibAbiSo(source = symbols_obj_tgt,
                                           target = self.target_path(abi_so))

            lib_targets.append(abi_so_tgt)
            lib_type = 'abi'


        lib_so = None
        lib_a = None

        if shared_lib:
            if len(objects) + len(direct_dep_libs) != 0:
                lib_so = "%s.lib.so" % (self.lib_name)
                if lib_type is None:
                    # prefere announcing 'abi' over 'so'
                    lib_type = 'so'
        else:
            lib_a = "%s.lib.a" % (self.lib_name)
            lib_type = 'a'

        self.env['fn_debug']('LIB: %s %s' % (self.lib_name, 'shared' if shared_lib else 'static'))


        if lib_so is not None:
            # ARCHIVES += ldso_so_support.lib.a
            pass

        # TODO: LIB_IS_DYNAMIC_LINKER

        # TODO: STATIC_LIBS

        # NOTICE: LIB_SO_DEPS seems to be an artifact of the past

        lib_so_tgt = None
        if lib_so is not None:
            # handle entry point
            entry_point_defined = self.build_env.check_var('ENTRY_POINT')
            if entry_point_defined:
                entry_point = self.build_env.var_value('ENTRY_POINT')
            else:
                entry_point = '0x0'
            self.env['ENTRY_POINT'] = entry_point


            lib_cache_dir = self.build_helper.get_lib_cache_dir(self.env)
            dep_archives = []
            for dep_lib in lib_a_deps:
                a_file_name = '%s.lib.a' % (dep_lib)
                a_path = self.build_helper.target_lib_path(lib_cache_dir, dep_lib, a_file_name)
                dep_archives.append(a_path)
            # sort libs with paths for compatibility with mk build
            dep_archives = list(sorted(dep_archives))
            self.env['fn_debug']('dep_archives: %s' % (str(dep_archives)))


            for v in ['LD_OPT', 'LIB_SO_DEPS', 'LD_SCRIPT_SO']:
                self.env[v] = self.build_env.var_value(v)
            lib_so_tgt = self.env.LibSo(source = dep_shlib_links + dep_archives + objects,
                                        target = self.target_path(lib_so))

            lib_targets.append(lib_so_tgt)

            # stripped shared library
            strip_tgt = self.env.Strip(target=self.target_path('%s.stripped' % (lib_so)),
                                       source=lib_so_tgt)
            lib_targets.append(strip_tgt)

            # symlink to stripped version
            inst_lib_tgt = self.env.SymLink(source=strip_tgt,
                                            target=self.sconsify_path(os.path.join(self.env['INSTALL_DIR'], lib_so)))
            lib_targets.append(inst_lib_tgt)

            # symlink to debug version
            dbg_lib_tgt = self.env.SymLink(source = lib_so_tgt,
                                           target = self.sconsify_path(os.path.join(self.env['DEBUG_DIR'], lib_so)))
            lib_targets.append(dbg_lib_tgt)


        if (lib_so_tgt is not None and symbols_file is not None):
            lib_checked = "%s.lib.checked" % (self.lib_name)
            check_abi_tgt = self.env.CheckAbi(target=self.target_path(lib_checked),
                                              source=[ lib_so_tgt, symbols_file ])

            lib_targets.append(check_abi_tgt)


        if lib_a is not None:
            lib_targets.append(self.env.StaticLibrary(target=self.target_path(lib_a),
                                                      source=objects))
            lib_type = 'a'


        lib_tag = "%s.lib.tag" % (self.lib_name)
        lib_tag_tgt = self.env.LibTag(source = lib_targets,
                                      target = self.target_path(lib_tag))
        lib_targets.append(lib_tag_tgt)


        if shared_lib:
            lib_deps = [self.lib_name]
        else:
            lib_deps.append(self.lib_name)

        self.env['fn_register_lib_info'](self.lib_name, { 'type': lib_type,
                                                          'lib_deps': lib_deps })

        ## execute post_process_actions
        for action in self.post_process_actions:
            action()

        return self.env.Alias(self.env['fn_lib_alias_name'](self.lib_name), lib_targets)


    def get_sources(self, files):
        src_files = []
        for src_file in files:
            file_paths = self.build_env.find_vpaths(src_file)
            if src_file.startswith('/'):
                file_paths = [ os.path.dirname(src_file) ]
                src_file = os.path.basename(src_file)
            existing_file_paths = [ f for f in file_paths if os.path.isfile(os.path.join(f, src_file)) ]
            if len(existing_file_paths) == 0:
                self.env['fn_error']("expected exactly one vpath for %s but none from %s found" % (src_file, str(file_paths)))
                quit()
            if len(existing_file_paths) != 1:
                self.env['fn_notice']("expected exactly one vpath for %s but exist %s from %s found" % (src_file, str(existing_file_paths), str(file_paths)))
            src_file_path = self.sconsify_path(existing_file_paths[0])
            src_files.append((src_file_path, src_file))
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


    def get_binary_sources(self):
        src_bin = self.build_env.var_values('SRC_BIN')
        src_files = self.get_sources(src_bin)
        return src_files
