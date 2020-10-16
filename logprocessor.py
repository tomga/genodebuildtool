

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


class BuildCommandGroup(BuildCommand):
    def __init__(self, tgt_type, tgt_descr, directory, cmd_list):
        super().__init__(tgt_type, tgt_descr)
        self.directory = directory
        self.cmd_list = cmd_list

    def append(self, cmd):
        self.cmd_list.append(cmd)
        return self

    def relabel(self, tgt_type, tgt_descr, directory):
        assert self.directory == '.'
        self.tgt_type = tgt_type
        self.tgt_descr = tgt_descr
        self.directory = directory
        return self

    def debug_struct(self):
        if self.tgt_type is not None or self.tgt_descr is not None:
            return [[self.tgt_type, self.tgt_descr],
                    self.directory,
                    [cmd.debug_struct() for cmd in self.cmd_list]]
        else:
            return [self.directory,
                    [cmd.debug_struct() for cmd in self.cmd_list]]
