

class MkRValue:
    """Base class for make rvalues"""


class MkRValueSpace(MkRValue):
    def type(self):
        return 'S'
        
    def debug_struct(self):
        return ' '

class MkRValueText(MkRValue):
    def __init__(self, text):
        self.text = text

    def type(self):
        return 'T'
        
    def debug_struct(self):
        return self.text

class MkRValueVar(MkRValue):
    def __init__(self, var):
        self.var = var

    def type(self):
        return 'V'
        
    def debug_struct(self):
        return '$' + self.var


class MkRValueExpr:
    def __init__(self, part):
        self.parts = [ part ]

    def append_part(self, part):
        if self.parts[-1].type() != 'S' or part.type() != 'S':
            self.parts.append(part)
        return self
    
    def debug_struct(self):
        retval = []
        for part in self.parts:
            retval.append(part.debug_struct())
        return retval


class MkCommand:
    """Base class for make commands"""

    def process(env):
        pass




class MkScript:
    def __init__(self, cmd):
        self.commands = [ cmd ]

    def append_command(self, cmd):
        if cmd is not None:
            self.commands.append(cmd)
        return self
    
    def debug_struct(self):
        retval = []
        for cmd in self.commands:
            cmd_struct = cmd.debug_struct()
            if cmd_struct is not None:
                retval.append(cmd_struct)
        return retval
    


class MkCmdOper(MkCommand):
    def __init__(self, var, rval_expr):
        self.var = var
        self.rval_expr = rval_expr

    def debug_struct(self):
        return [ self.var, self.debug_struct_oper(), self.rval_expr.debug_struct() ]
    
class MkCmdAppend(MkCmdOper):
    def debug_struct_oper(self):
        return '+='

class MkCmdRecursiveExpandAssign(MkCmdOper):
    def debug_struct_oper(self):
        return '='

class MkCmdSimpleExpandAssign(MkCmdOper):
    def debug_struct_oper(self):
        return ':='

class MkCmdOptAssign(MkCmdOper):
    def debug_struct_oper(self):
        return '?='


class MkCmdCondDef(MkCommand):
    def __init__(self, var, script_true, script_false):
        self.var = var
        self.script_true = script_true
        self.script_false = script_false

    def debug_struct(self):
        return ([ self.debug_struct_oper(), self.var, self.script_true.debug_struct() ]
                + ([ self.script_false.debug_struct() ] if self.script_false is not None else []))
    
class MkCmdIfdef(MkCmdCondDef):
    def debug_struct_oper(self):
        return 'ifdef'

class MkCmdIfndef(MkCmdCondDef):
    def debug_struct_oper(self):
        return 'ifndef'



class MkCmdComment(MkCommand):
    def __init__(self, comment):
        self.comment = comment

    def debug_struct(self):
        # return [ self.comment ]
        return None
    
