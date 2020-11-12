
import os
import re
import subprocess

# debug support
import pprint

import mkevaluator
import mkparser

import genode_build_helper

import genode_tools as tools


class GenodeProg:

    def __init__(self, prog_name, env, build_helper, prog_base_path):
        self.prog_name = prog_name
        self.env = env.Clone()

        # for use in target_path
        self.relative_src_dir = self.env['fn_localize_path'](prog_base_path)
        self.relative_prog_dir = self.sconsify_path(os.path.join(env['BUILD'], prog_name))

        self.build_helper = build_helper

        self.env['fn_target_path'] = lambda tgt: self.target_path(tgt)


    def sconsify_path(self, path):
        return self.env['fn_sconsify_path'](path)


    def target_path(self, target):
        return '%s/%s' % (self.relative_prog_dir, target)


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



class GenodeMkProg(GenodeProg):
    def __init__(self, prog_name, env,
                 prog_mk_file, prog_mk_repo,
                 build_env):
        self.build_env = mkevaluator.MkEnv(mk_cache=build_env.mk_cache,
                                           parent_env=build_env)
        self.prog_mk_file = prog_mk_file
        self.prog_mk_repo = prog_mk_repo
        self.build_env.var_set('REP_DIR', self.prog_mk_repo)

        prog_mk_path = os.path.dirname(prog_mk_file)
        super().__init__(prog_name, env,
                         genode_build_helper.GenodeMkBuildHelper(self.build_env),
                         prog_mk_path)


    def process(self):
        #import rpdb2
        #rpdb2.start_embedded_debugger('password')

        mkcache = self.build_env.get_mk_cache()


        ### handle include <prog>.mk

        self.env['fn_info']("Parsing build rules for program '%s' from '%s'" % (self.prog_name, self.prog_mk_file))
        prog_mk = mkcache.get_parsed_mk(self.prog_mk_file)
        #self.env['fn_debug'](pprint.pformat(prog_mk.debug_struct(), width=180))
        prog_mk.process(self.build_env)
        #self.env['fn_debug'](pprint.pformat(self.build_env.debug_struct('pretty'), width=200))


        ### register program dependencies
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


        ### skipping $(SPEC_FILES) as they are already included
        #
        # NOTE: passing this option is not documented


        ### handle include global.mk
        global_mk_file = '%s/mk/global.mk' % (self.env['BASE_DIR'])
        global_mk = mkcache.get_parsed_mk(global_mk_file)
        global_mk.process(self.build_env)
        #self.env['fn_debug'](pprint.pformat(self.build_env.debug_struct('pretty'), width=200))


        repositories = self.env['REPOSITORIES']
        specs = self.env['SPECS']
        self.env['fn_debug']("REPOSITORIES: %s" % (str(repositories)))
        self.env['fn_debug']("SPECS: %s" % (str(specs)))

        ### ### handle shared program settings
        ### 
        ### ## find <prog> symbols file with repo
        ### symbols_file = None
        ### symbols_repo = None
        ### for repository in repositories:
        ###     for spec in specs:
        ###         test_symbols_file = 'prog/symbols/spec/%s/%s' % (spec, self.prog_name)
        ###         if tools.is_repo_file(test_symbols_file, repository):
        ###             symbols_file = tools.file_path(test_symbols_file, repository)
        ###             symbols_repo = repository
        ###             break
        ###     if symbols_file is not None:
        ###         break
        ### 
        ###     test_symbols_file = 'prog/symbols/%s' % (self.prog_name)
        ###     if tools.is_repo_file(test_symbols_file, repository):
        ###         symbols_file = tools.file_path(test_symbols_file, repository)
        ###         symbols_repo = repository
        ###         break
        ### 
        ### shared_prog = (symbols_file is not None
        ###               or self.build_env.var_value('SHARED_PROG') == 'yes')
        ### 
        ### #self.env['fn_debug']("SYMBOLS_FILE: %s" % (str(symbols_file)))
        ### #self.env['fn_debug']("SHARED_PROG: %s" % (str(shared_prog)))
        ### 
        ### 
        ### ### handle proggcc
        ### # TODO cache results or maybe set unconditionally
        ### if shared_prog:
        ###     ##PROGGCC = $(shell $(CC) $(CC_MARCH) -print-proggcc-file-name)
        ###     cmd = "%s %s -print-proggcc-file-name" % (self.build_env.var_value('CC'),
        ###                                              self.build_env.var_value('CC_MARCH'))
        ###     results = subprocess.run(cmd, stdout=subprocess.PIPE,
        ###                              shell=True, universal_newlines=True, check=True)
        ###     output = results.stdout
        ###     self.build_env.var_set('PROGGCC', output)
        ### 
        ### 
        ### 
        ### self.env['fn_debug'](pprint.pformat(self.build_env.debug_struct('pretty'), width=200))


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
        #self.env['fn_debug']('cc_objs: %s' % (str(cc_objs)))

        s_objs = self.build_s_objects()
        objects += s_objs

        o_objs = self.build_o_objects()
        objects += o_objs

        # for compatibility with make build (it won't work for special
        # cases like: a.cpp a.bbb.cpp as in make sources are sorted
        # but here object files
        objects = list(sorted(objects, key=lambda x: str(x)))

        prog_targets = []

        ### if symbols_file is not None:
        ### 
        ###     ### handle <prog>.abi.so generation
        ### 
        ###     abi_so = '%s.abi.so' % (self.prog_name)
        ### 
        ###     symbols_file = self.sconsify_path(os.path.join(symbols_repo, symbols_file))
        ###     #self.env['fn_debug']('SYMBOLS_FILE: %s' % (symbols_file))
        ###     symbols_lnk = '%s.symbols' % (self.prog_name)
        ###     #self.env['fn_debug']('SYMBOLS_LNK: %s' % (symbols_lnk))
        ### 
        ###     # TODO: test correctness of changes of this link
        ###     symbols_lnk_tgt = self.env.SymLink(source = symbols_file,
        ###                                        target = self.target_path(symbols_lnk))
        ### 
        ###     ### handle <prog>.symbols.s
        ###     symbols_asm = '%s.symbols.s' % (self.prog_name)
        ###     symbols_asm_tgt = self.env.Symbols(source = symbols_lnk_tgt,
        ###                                        target = self.target_path(symbols_asm))
        ### 
        ###     ### handle <prog>.symbols.o
        ###     # assumes prepare_s_env() was already executed
        ###     symbols_obj_tgt = self.build_helper.generic_compile(self.env, map(str, symbols_asm_tgt))
        ### 
        ###     ### handle <prog>.abi.so
        ###     for v in ['LD_OPT', 'PROG_SO_DEPS', 'LD_SCRIPT_SO']:
        ###         self.env[v] = self.build_env.var_value(v)
        ###     abi_so_tgt = self.env.ProgAbiSo(source = symbols_obj_tgt,
        ###                                    target = self.target_path(abi_so))
        ### 
        ###     prog_targets.append(abi_so_tgt)


        prog_so = None
        install_so = None
        debug_so = None
        prog_checked = None
        prog_a = None

        ### if shared_prog:
        ###     if len(objects) + len(dep_progs) == 0:
        ###         prog_so = "%s.prog.so" % (self.prog_name)
        ###         install_so = "%s/%s" % (self.build_env.var_value('INSTALL_DIR'), prog_so)
        ###         debug_so = "%s/%s" % (self.build_env.var_value('DEBUG_DIR'), prog_so)
        ### else:
        ###     prog_a = "%s.prog.a" % (self.prog_name)

        ### if prog_so is not None and abi_so is not None:
        ###     prog_checked = "%s.prog.checked" % (self.prog_name)

        ### self.env['fn_debug']('PROG: %s %s' % (self.prog_name, 'shared' if shared_prog else 'static'))

        ### if shared_prog:
        ###     # ARCHIVES += ldso_so_support.prog.a
        ###     pass

        ### # TODO: PROG_IS_DYNAMIC_LINKER
        ### 
        ### # TODO: STATIC_PROGS
        ### 
        ### # NOTICE: PROG_SO_DEPS seems to be an artifact of the past
        ### 
        ### # TODO: ENTRY_POINT ?= 0x0

        if prog_a is not None:
            prog_targets.append(self.env.StaticProgram(target=self.target_path(prog_a),
                                                       source=objects))

        prog_targets += objects
        self.env['fn_notice']('prog_targets: %s' % (str(list(map(str, prog_targets)))))

        retval = self.env.Alias(self.env['fn_prog_alias_name'](self.prog_name), prog_targets)
        self.env['fn_notice']('retval: %s' % (str(list(map(str, retval)))))
        return retval


    def get_sources(self, files):
        src_files = []
        for src_file in files:
            file_paths = self.build_env.find_vpaths(src_file)
            existing_file_paths = [ f for f in file_paths if os.path.isfile(os.path.join(f, src_file)) ]

            self.env['fn_debug']('get_sources: default %s' % (os.path.join(self.relative_src_dir, src_file)))
            if (len(existing_file_paths) == 0
                and os.path.isfile(os.path.join(self.relative_src_dir, src_file))):
                existing_file_paths += [self.relative_src_dir]

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
