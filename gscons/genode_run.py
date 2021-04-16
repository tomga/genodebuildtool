
import os
import re
import subprocess

import SCons.Action

from gscons import mkevaluator
from gscons import mkparser
from gscons import scmkevaluator

from gscons import genode_build_helper
from gscons import genode_target
from gscons import genode_tools as tools


class GenodeBaseRun(genode_target.GenodeTarget):

    def __init__(self, run_name, env):

        self.run_name = run_name
        super().__init__(run_name, 'run', 'RUN', env)


class GenodeDisabledRun(GenodeBaseRun):

    def __init__(self, run_name, env, disabled_message):

        super().__init__(run_name, env)

        self.make_disabled(disabled_message)


    def process_load(self):
        return


class GenodeRun(GenodeBaseRun):

    def __init__(self, run_name, env,
                 run_file, run_repo):

        super().__init__(run_name, env)

        self.run_file = run_file
        self.run_repo = run_repo


    def norm_tgt_path(self, target):
        if target is None:
            target = self.target_name
        return os.path.join(self.env['RUN_LOG_DIR'], target)


    def process_load(self):

        env = self.env

        targets_cmd = self.get_run_cmd('--include %s/tool/run_build_targets' % env['BUILDTOOL_DIR'])

        targets_results = subprocess.run(targets_cmd, stdout=subprocess.PIPE,
                                         shell=True, universal_newlines=True, check=True)
        targets_output = targets_results.stdout.strip()

        targets_lines = targets_output.split('\n')
        prog_indicator = 'PROG_TARGETS: '
        prog_targets = [ l for l in targets_lines if l.startswith(prog_indicator) ]
        if len(prog_targets) != 1:
            self.make_disabled("%s" % (self.clean_output(targets_lines)))
            return

        prog_targets = prog_targets[0][len(prog_indicator):].split()

        env['fn_debug']("run '%s' require progs %s" % (self.target_name, str(prog_targets)))

        self.dep_progs = env['fn_require_progs'](self, prog_targets)


    def clean_output(self, output):
        output = [ l for l in output if not l.startswith('including ') ]
        return '|'.join(output)


    def do_process_target(self):

        env = self.env

        dep_prog_aliases = list(map(lambda t: t.get_target_alias(), self.dep_progs))

        result_log_file = self.sc_tgt_path(None)

        run_cmd = self.get_run_cmd('--skip-build --include %s/tool/run_file_copy'
                                   % env['BUILDTOOL_DIR'])
        run_cmd = "%s | tee %s | sed -e 's/^/ | /'" % (run_cmd, self.norm_tgt_path(None))

        env['RUNCOM'] = run_cmd
        run_cmd_task = env.Command(
            target = result_log_file,
            source = self.run_file,
            action = SCons.Action.Action("$RUNCOM", "$RUNCOMSTR")
        )
        env.Depends(run_cmd_task, dep_prog_aliases)

        # force to always run script
        env.AlwaysBuild(run_cmd_task)

        # avoid parallel execution of run scripts
        env.SideEffect(self.sc_tgt_path("run.lock"), run_cmd_task)

        retval = env.Alias(env['fn_run_alias_name'](self.run_name), run_cmd_task)
        env['fn_debug']('retval: %s' % (str(list(map(str, retval)))))
        return retval


    def get_run_cmd(self, custom_opts):

        env = self.env

        d = { 'build_dir': env['BUILD'],
              'genode_dir': env['GENODE_DIR'],
              'run_name': self.run_name,
              'specs': ' '.join(env['SPECS']),
              'board': ('%s' % env['BOARD']) if 'BOARD' in env else '',
              'repositories': ' '.join(env['REPOSITORIES']),
              'cross_dev_prefix': env['CROSS_DEV_PREFIX'],
              'qemu_args': env['QEMU_OPT'],
              'make': env['MAKE'],
              'ccache_opt': '--cache' if env['CCACHE'] == 'yes' else '',
              'include_opts': env['RUN_OPT'],
              'custom_opts': custom_opts,
              'run_include': '--include %s' % self.run_file,
              }

        cmd = """(cd {build_dir}
                  && {genode_dir}/tool/run/run --genode-dir {genode_dir}
                                               --name {run_name}
                                               --specs "{specs}"
                                               --board "{board}"
                                               --repositories "{repositories}" \
                                               --cross-dev-prefix "{cross_dev_prefix}"
                                               --qemu-args "{qemu_args}"
                                               --make "{make}"
                                               {ccache_opt}
                                               {include_opts}
                                               {custom_opts}
                                               {run_include}
                 )"""
        cmd = cmd.format(**d)
        cmd = cmd.replace('\n', ' ')
        cmd = ' '.join(cmd.split())
        env['fn_debug']('run_cmd: %s' % (str(cmd)))

        return cmd


    def make_disabled(self, message):
        """Make this target to never be disabled
           (until discrepancies between build run
           targets vs. required targets are resolved."""

        self.env['fn_debug']("Ignoring make_disabled for RUN target %s" % (self.target_name))
