
from gscons import genode_target

class GenodeAll(genode_target.GenodeTarget):

    def __init__(self, env, lib_target_names, prog_target_names,
                 run_target_names):

        super().__init__('ALL', 'all', 'ALL', env)

        # mark self as needed to make all target also be needed
        self.increase_use_count()

        self.lib_target_names = lib_target_names
        self.prog_target_names = prog_target_names
        self.run_target_names = run_target_names

        self.env['ent_current_target_alias'] = 'ALL:ALL'


    def process_load(self):

        self.lib_targets = self.env['fn_require_libs'](self, self.lib_target_names)

        self.prog_targets = []
        for t in self.prog_target_names:
            self.prog_targets.extend(self.env['fn_require_progs'](self, [t]))

        self.run_targets = self.env['fn_require_runs'](self, self.run_target_names)


    def do_process_target(self):
        return self.env.Alias(self.env['ent_current_target_alias'],
                              self.lib_targets + self.prog_targets + self.run_targets)


    def make_disabled(self, message):
        """Make this target to never be disabled"""

        self.env['fn_debug']("Ignoring make_disabled for ALL target")
