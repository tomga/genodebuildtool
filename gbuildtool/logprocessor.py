

from gbuildtool import cmd_cleaner

class BuildCommand:
    def __init__(self, tgt_type, tgt_descr):
        self.tgt_type = tgt_type
        self.tgt_descr = tgt_descr
        pass



class SimpleBuildCommand(BuildCommand):
    def __init__(self, tgt_type, tgt_descr, cmd_lines):
        super().__init__(tgt_type, tgt_descr)
        self.cmd_lines = cmd_lines

    def debug_struct(self):
        if self.tgt_type is not None or self.tgt_descr is not None:
            return [[self.tgt_type, self.tgt_descr], self.cmd_lines]
        else:
            return [self.cmd_lines]

    def process(self, save_fun, run_dir, abs_dir, rel_dir):

        #print("logprocessor::process: %s" % (str(self.debug_struct())))
        clean_commands = cmd_cleaner.commands_clean(self.cmd_lines,
                                                    run_dir, abs_dir, rel_dir)

        for cmd, src, tgt, orig, cmd_noincsort in clean_commands:
            save_fun(tgt, src, orig, cmd, cmd_noincsort)




class BuildCommandGroup(BuildCommand):
    def __init__(self, tgt_type, tgt_descr, run_dir, cmd_list):
        super().__init__(tgt_type, tgt_descr)
        self.run_dir = run_dir
        self.cmd_list = cmd_list

    def append(self, cmd):
        self.cmd_list.append(cmd)
        return self

    def prepend_list(self, cmd_group):
        self.cmd_list = cmd_group.cmd_list + self.cmd_list
        return self

    def set_target(self, tgt_type, tgt_descr):
        self.tgt_type = tgt_type
        self.tgt_descr = tgt_descr
        return self

    def set_run_dir(self, run_dir):
        assert self.run_dir == '.'
        self.run_dir = run_dir
        return self

    def relabel(self, tgt_type, tgt_descr, run_dir):
        assert self.run_dir == '.'
        self.tgt_type = tgt_type
        self.tgt_descr = tgt_descr
        self.run_dir = run_dir
        return self

    def debug_struct(self):
        if self.tgt_type is not None or self.tgt_descr is not None:
            return [[self.tgt_type, self.tgt_descr],
                    self.run_dir,
                    [cmd.debug_struct() for cmd in self.cmd_list]]
        else:
            return [self.run_dir,
                    [cmd.debug_struct() for cmd in self.cmd_list]]


    def process(self, save_fun, run_dir, abs_dir, rel_dir):
        for cmd in self.cmd_list:
            cmd.process(save_fun, self.run_dir, abs_dir, rel_dir)
