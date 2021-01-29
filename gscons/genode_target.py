


class GenodeTarget:

    def __init__(self, target_name, target_type, target_type_code, env):
        self.env = env

        self.target_name = target_name
        self.target_type = target_type
        self.target_type_code = target_type_code

        self.disabled_message = None
        self.usage_count = 1
        self.dep_target_objs = None

        self.env['fn_current_target_obj'] = lambda : self
        self.env['fn_current_target_type'] = lambda : target_type
        self.env['fn_current_target_type_code'] = lambda : target_type_code


    def is_disabled(self):
        return (self.disabled_message is not None) or (self.usage_count == 0)


    def make_disabled(self, message):
        assert self.usage_count != 0
        assert self.disabled_message is None
        self.disabled_message = message
        self.unlock_deps()


    def get_disabled_message(self):
        if self.disabled_message is not None:
            return self.disabled_message
        if self.usage_count == 0:
            return "usage count is 0"
        return None


    def increase_use_count(self):
        self.usage_count += 1
        if (self.usage_count == 1) and not self.is_disabled():
            self.lock_deps()


    def decrease_use_count(self):
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
        ### handle case if target is disabled
        if self.is_disabled():
            self.env['fn_info']("Skipping building %s '%s' due to %s"
                                % (self.target_type, self.target_name, self.get_disabled_message()))
            return None

        return self.do_process_target()


    def do_process_target(self):
        raise Exception("GenodeTarget::do_process_target should be overridden")
