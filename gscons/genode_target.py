


class GenodeTarget:

    def __init__(self, target_name, target_type, target_type_code, env):

        if hasattr(self, 'env'):
            # env is already cloned in a subclass
            assert env is self.env
        else:
            # cloning env
            self.env = env.Clone()

        self.target_name = target_name
        self.target_type = target_type
        self.target_type_code = target_type_code

        self.disabled_message = None
        self.usage_count = 0
        self.dep_target_objs = []
        self.dep_parent_objs = []

        self.env['ent_current_target_obj'] = self
        self.env['ent_current_target_type'] = target_type
        self.env['ent_current_target_type_code'] = target_type_code


    def is_inactive(self):
        return (self.is_disabled() or self.usage_count == 0)


    def get_inactive_message(self):
        if self.disabled_message is not None:
            return self.disabled_message
        if self.usage_count == 0:
            return "usage count is 0"
        return None


    def is_disabled(self):
        return self.disabled_message is not None


    def add_dep_targets(self, dep_targets):
        for dep_target in dep_targets:
            self.add_dep_target(dep_target)


    def add_dep_target(self, dep_target):
        if self.is_disabled():
            self.internal_add_dep_target(dep_target)
            return

        if dep_target.is_disabled():
            self.make_disabled("disabled dependencies")
            self.internal_add_dep_target(dep_target)
            return

        if self.usage_count != 0:
            dep_target.increase_use_count()
        self.internal_add_dep_target(dep_target)


    def internal_add_dep_target(self, dep_target):
        self.dep_target_objs.append(dep_target)
        dep_target.internal_add_parent_obj(self)


    def internal_add_parent_obj(self, parent_obj):
        self.dep_parent_objs.append(parent_obj)
        if (self.is_disabled() and not parent_obj.is_disabled()):
            parent_obj.make_disabled("disabled dependencies")


    def make_disabled(self, message):
        self.env['fn_debug']("make_disabled %s:%s due to %s" % (self.target_type_code, self.target_name, message))
        assert self.disabled_message is None
        self.disabled_message = message
        for dep_parent in self.dep_parent_objs:
            if not dep_parent.is_disabled():
                dep_parent.make_disabled("disabled dependencies")


    def get_disabled_dep_target_names(self):
        disabled_dep_targets = [ tgt.target_name for tgt in self.dep_target_objs
                                 if tgt.is_disabled() ]
        return disabled_dep_targets


    def increase_use_count(self):

        self.env['fn_debug']('increase_use_count: %s(%s)' % (self.target_name, str(self.usage_count)))

        self.usage_count += 1
        if (self.usage_count == 1) and not self.is_disabled():
            self.lock_deps()


    def decrease_use_count(self):
        assert self.usage_count >= 1
        if (self.usage_count == 1) and not self.is_disabled():
            self.unlock_deps()
        self.usage_count -= 1


    def lock_deps(self):
        for lib_obj in self.dep_target_objs:
            lib_obj.increase_use_count()


    def unlock_deps(self):
        for lib_obj in self.dep_target_objs:
            lib_obj.decrease_use_count()


    def process_load(self):
        raise Exception("GenodeTarget::process_load should be overridden")


    def process_target(self):

        if self.is_inactive():
            self.env['fn_info']("Skipping building %s '%s' due to %s"
                                % (self.target_type, self.target_name, self.get_inactive_message()))
            return None
        else:
            self.env['fn_debug']("not skipping %s '%s' (%s, %s)"
                                 % (self.target_type, self.target_name, self.usage_count,
                                    str(self.dep_parent_objs)))

        return self.do_process_target()


    def do_process_target(self):
        raise Exception("GenodeTarget::do_process_target should be overridden")


    def sconsify_path(self, path):
        return self.env['fn_sconsify_path'](path)


    def sc_tgt_path(self, target):
        return self.sconsify_path(self.norm_tgt_path(target))


    def norm_tgt_path(self, target):
        raise Exception("GenodeTarget::norm_tgt_path should be overridden")
