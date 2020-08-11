
import copy



class MkEnvVar:
    def __init__(self, mode='recursive', value=None):
        assert mode == 'recursive' or mode == 'simple'
        self.mode = mode
        self.value = value if value is not None else MkRValueExpr()

    def is_simply_expanded(self):
        return self.mode == 'simple'

    def is_recursively_expanded(self):
        return self.mode == 'recursive'

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value



class MkEnv:
    def __init__(self):
        self.variables = {}

    def dict(self):
        return self.variables;

    def get_create_var(self, varname):
        if varname not in self.variables:
            self.variables[varname] = MkEnvVar()
        return self.variables[varname]

    def get_var(self, varname):
        return self.variables[varname]

    def set_var(self, varname, varvalue):
        self.variables[varname] = varvalue

    def check_var(self, varname):
        return varname in self.variables

    def debug_struct(self, mode):
        retval = {}
        for var in self.variables:
            if mode == 'raw':
                retval[var] = self.variables[var].get_value().debug_struct()
            elif mode == 'calculated':
                retval[var] = MkRValueExpr(self.variables[var].get_value().calculated(self)).debug_struct()
            elif mode == 'pretty':
                retval[var] = MkRValueExpr(self.variables[var].get_value().calculated(self)).value(self)
            else:
                raise Exception("Unknown debug_struct mode: '%s'" % (str(mode)))
        return retval



class MkRValue:
    """Base class for make rvalues"""

    def calculate(self, mkenv):
        return [self]

    def compactable(self):
        return False

    def compact_with(self, other):
        raise Exception("Not compactable")



class MkRValueSpace(MkRValue):
    def type(self):
        return 'SPC'

    def value(self):
        return ' '

    def compactable(self):
        return True

    def compact_with(self, other):
        pass

    def debug_struct(self):
        return ' '



class MkRValueText(MkRValue):
    def __init__(self, text):
        self.text = text

    def type(self):
        return 'TXT'

    def value(self):
        return self.text

    def compactable(self):
        return True

    def compact_with(self, other):
        self.text += other.text

    def debug_struct(self):
        return self.text



class MkRValueVar(MkRValue):
    def __init__(self, var_ident, var_expr = None):
        self.var_ident = var_ident
        self.var_expr = var_expr

    def type(self):
        return 'VAR'

    def calculate(self, mkenv):
        if self.var_expr is not None:
            raise "TODO: implement var_expr"
        if not mkenv.check_var(self.var_ident):
            return []
        rval_expr = copy.deepcopy(mkenv.get_var(self.var_ident))
        return rval_expr.get_value().calculated(mkenv)

    def value(self):
        raise Exception("MkRValueVar should have been calculated")

    def debug_struct(self):
        if self.var_expr is None:
            return '$' + self.var_ident
        else:
            return [ '$' + self.var_ident, self.var_expr.debug_struct() ]



class MkRValueFun1(MkRValue):
    def __init__(self, funname, arg):
        self.funname = funname
        self.arg = arg

    def type(self):
        return 'FN1'

    def calculate(self, mkenv):
        arg_value = self.arg.values_list(mkenv)

        result = None
        if self.funname == 'shell':
            raise Exception("TODO Implement: %s" % (self.funname))
        else:
            raise Exception("Unknown function: %s" % (self.funname))

        return result.calculated(mkenv)

    def value(self):
        raise Exception("TODO")

    def debug_struct(self):
        return ['$' + self.funname, self.arg.debug_struct()]



class MkRValueFun2(MkRValue):
    def __init__(self, funname, arg1, arg2):
        self.funname = funname
        self.arg1 = arg1
        self.arg2 = arg2

    def type(self):
        return 'FN2'

    def calculate(self, mkenv):
        arg1_value = self.arg1.values_list(mkenv)
        arg2_value = self.arg2.values_list(mkenv)

        result = None
        if self.funname == 'filter-out':
            result = MkRValueExpr.from_values_list([ v for v in arg2_value if v not in arg1_value ])
        else:
            raise Exception("Unknown function: %s" % (self.funname))

        return result.calculated(mkenv)

    def value(self):
        raise Exception("TODO")

    def debug_struct(self):
        return ['$' + self.funname, self.arg1.debug_struct(), self.arg2.debug_struct()]



class MkRValueFun3(MkRValue):
    def __init__(self, funname, arg1, arg2, arg3):
        self.funname = funname
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3

    def type(self):
        return 'FN3'

    def calculate(self, mkenv):
        arg1_value = self.arg1.values_list(mkenv)
        arg2_value = self.arg2.values_list(mkenv)
        arg3_value = self.arg3.values_list(mkenv)

        result = None
        if self.funname == '???':
            result = "???"
        else:
            raise Exception("Unknown function: %s" % (self.funname))

        return result.calculated(mkenv)

    def value(self):
        raise Exception("TODO")

    def debug_struct(self):
        return ['$' + self.funname, self.arg1.debug_struct(), self.arg2.debug_struct(), self.arg3.debug_struct()]



class MkRValueSubst(MkRValue):
    def __init__(self, var_expr, pattern, substitution):
        self.var_expr = var_expr
        self.pattern = pattern
        self.substitution = substitution

    def type(self):
        return 'SUB'

    def calculate(self, mkenv):
        arg1_value = self.arg1.values_list(mkenv)
        arg2_value = self.arg2.values_list(mkenv)

        result = None
        if self.funname == 'filter-out':
            result = MkRValueExpr.from_values_list([ v for v in arg2_value if v not in arg1_value ])
        else:
            raise Exception("Unknown function: %s" % (self.funname))

        return result.calculated(mkenv)

    def value(self):
        raise Exception("TODO")

    def debug_struct(self):
        return [self.var_expr.debug_struct(), ':',
                self.pattern.debug_struct(), self.substitution.debug_struct()]



class MkRValueExpr:
    def __init__(self, parts = None):
        self.parts = parts if parts is not None else []

    def append_part(self, part):
        if (len(self.parts) > 0
            and part.compactable()
            and self.parts[-1].type() == part.type()):
            self.parts[-1].compact_with(part)
            return self
        self.parts.append(part)
        return self

    def append_expr(self, expr):
        if len(self.parts) != 0:
            self.parts += [ MkRValueSpace() ]
        self.parts += expr.parts

    def calculated(self, mkenv):
        retval = []
        for part in self.parts:
            retval += part.calculate(mkenv)
        retval = self.compacted(retval)
        return retval

    def compacted(self, parts):
        retval = []
        for part in parts:
            if (len(retval) > 0
                and retval[-1].type() == part.type()
                and part.compactable()):
                retval[-1].compact_with(part)
            else:
                retval += [ part ]
        return retval

    def calculate_variables(self, mkenv):
        self.parts = self.calculated(mkenv)

    def value(self, mkenv):
        return "".join(map(lambda x: x.value(), self.calculated(mkenv)))

    def values_list(self, mkenv):
        return list(map(lambda x: x.value(), [e for e in self.calculated(mkenv) if e.type() != 'S']))

    def from_values_list(values_list):
        # Construct r value expression from list of text values
        retval = MkRValueExpr()
        first = True
        for t in values_list:
            if not first:
                retval.append_part(MkRValueSpace())
            retval.append_part(MkRValueText(t))
            first = False
        return retval

    def debug_struct(self):
        retval = []
        for part in self.parts:
            retval.append(part.debug_struct())
        return retval



class MkCommand:
    """Base class for make commands"""

    def process(self, mkenv):
        pass



class MkScript:
    def __init__(self, cmd):
        self.commands = []
        self.append_command(cmd)

    def append_command(self, cmd):
        if cmd is not None:
            self.commands.append(cmd)
        return self

    def process(self, mkenv):
        for cmd in self.commands:
            cmd.process(mkenv)

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

    def process(self, mkenv):
        var_value = mkenv.get_create_var(self.var)
        rval_value = copy.deepcopy(self.rval_expr)
        if var_value.is_simply_expanded():
            # using get_var does not influence calculation here
            # because if it wasn't defined earlier it wouldn't be
            # 'simply_expanded'
            rval_value.calculate_variables(mkenv)
        var_value.get_value().append_expr(rval_value)

    def debug_struct_oper(self):
        return '+='



class MkCmdRecursiveExpandAssign(MkCmdOper):
    def process(self, mkenv):
        rval_value = copy.deepcopy(self.rval_expr)
        mkenv.set_var(self.var, MkEnvVar('recursive', rval_value))

    def debug_struct_oper(self):
        return '='



class MkCmdSimpleExpandAssign(MkCmdOper):
    def process(self, mkenv):
        rval_value = copy.deepcopy(self.rval_expr)
        rval_value.calculate_variables(mkenv)
        mkenv.set_var(self.var, MkEnvVar('simple', rval_value))

    def debug_struct_oper(self):
        return ':='



class MkCmdOptAssign(MkCmdOper):
    def process(self, mkenv):
        if mkenv.check_var(self.var):
            return
        rval_value = copy.deepcopy(self.rval_expr)
        mkenv.set_var(self.var, MkEnvVar('recursive', rval_value))

    def debug_struct_oper(self):
        return '?='



class MkCmdCond(MkCommand):
    def __init__(self, condition, script_true, script_false):
        self.condition = condition
        self.script_true = script_true
        self.script_false = script_false

    def process(self, mkenv):
        if self.condition.check_cond(mkenv):
            self.script_true.process(mkenv)
        elif self.script_false is not None:
            self.script_false.process(mkenv)

    def debug_struct(self):
        return ([ self.condition.debug_struct(), self.script_true.debug_struct() ]
                + ([ self.script_false.debug_struct() ] if self.script_false is not None else []))


class MkCmdInclude(MkCommand):
    def __init__(self, rval_expr, optional=False):
        self.rval_expr = rval_expr
        self.optional = optional

    def process(self, mkenv):
        rval_value = copy.deepcopy(self.rval_expr)
        rval_value.calculate_variables(mkenv)
        rval_value.calculate_variables(mkenv)
        print("TODO: include%s %s" % (" (optional)" if self.optional else "", str(rval_value.parts)))


    def debug_struct(self):
        return ([ "-" if self.optional else "" + "include" ]
                + [ self.rval_expr.debug_struct() ])


class MkCmdVpath(MkCommand):
    def __init__(self, rval_pattern, rval_path):
        self.rval_pattern = rval_pattern
        self.rval_path = rval_path

    def process(self, mkenv):
        rval_pattern_value = copy.deepcopy(self.rval_pattern)
        rval_pattern_value.calculate_variables(mkenv)
        rval_path_value = copy.deepcopy(self.rval_path)
        rval_path_value.calculate_variables(mkenv)
        print("TODO: vpath%s %s" % (" (optional)" if self.optional else "", str(rval_value.parts)))


    def debug_struct(self):
        return ([ "include" ]
                + [ self.rval_pattern.debug_struct() ]
                + [ self.rval_path.debug_struct() ])


class MkCondition:
    """Base class for make conditions"""

    def check_cond(self, mkenv):
        pass


class MkCondDef(MkCondition):
    def __init__(self, var):
        self.var = var

    def debug_struct(self):
        return [ self.debug_struct_oper(), self.var ]


class MkCondIfdef(MkCondDef):
    def check_cond(self, mkenv):
        return mkenv.check_var(self.var)

    def debug_struct_oper(self):
        return 'ifdef'


class MkCondIfndef(MkCondDef):
    def check_cond(self, mkenv):
        return not mkenv.check_var(self.var)

    def debug_struct_oper(self):
        return 'ifndef'



class MkCondEq(MkCondition):
    def __init__(self, left_expr, right_expr):
        self.left_expr = left_expr
        self.right_expr = right_expr

    def check_cond(self, mkenv):
        left = self.left_expr.calculated(mkenv)
        right = self.right_expr.calculated(mkenv)
        return self.check_cond_oper(left, right)


    def debug_struct(self):
        return [ self.debug_struct_oper(),
                 self.left_expr.debug_struct(),
                 self.right_expr.debug_struct() ]


class MkCondIfeq(MkCondEq):
    def check_cond_oper(self, left, right):
        return left == right

    def debug_struct_oper(self):
        return 'ifeq'


class MkCondIfneq(MkCondEq):
    def check_cond_oper(self, left, right):
        return not (left == right)

    def debug_struct_oper(self):
        return 'ifneq'



class MkCmdComment(MkCommand):
    def __init__(self, comment):
        self.comment = comment

    def process(self, mkenv):
        pass

    def debug_struct(self):
        # return [ self.comment ]
        return None
