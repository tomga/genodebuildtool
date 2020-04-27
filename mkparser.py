
import parglare
import pprint

import mkevaluator

def initialize():
    file_name = '/projects/genode/buildtool/mkparser.pg'
    grammar = parglare.Grammar.from_file(file_name)

    actions = {
        "CmdList": [lambda _, nodes: mkevaluator.MkScript(nodes[0]),
                    lambda _, nodes: nodes[0].append_command(nodes[2]),
                    ],
        "Command": [lambda _, nodes: (mkevaluator.MkCmdAppend(nodes[0], nodes[4]) if nodes[2] == '+=' else
                                      mkevaluator.MkCmdRecursiveExpandAssign(nodes[0], nodes[4]) if nodes[2] == '=' else
                                      mkevaluator.MkCmdSimpleExpandAssign(nodes[0], nodes[4]) if nodes[2] == ':=' else
                                      mkevaluator.MkCmdOptAssign(nodes[0], nodes[4]) if nodes[2] == '?=' else
                                      "Invalid command oper %s" % (nodes[2])),
                    lambda _, nodes: (mkevaluator.MkCmdIfdef(nodes[2], nodes[4], None) if nodes[0] == 'ifdef' else
                                      mkevaluator.MkCmdIfndef(nodes[2], nodes[4], None) if nodes[0] == 'ifndef' else
                                      "Invalid conditional oper %s" % (nodes[0])),
                    lambda _, nodes: (mkevaluator.MkCmdIfdef(nodes[2], nodes[4], nodes[8]) if nodes[0] == 'ifdef' else
                                      mkevaluator.MkCmdIfndef(nodes[2], nodes[4], nodes[8]) if nodes[0] == 'ifndef' else
                                      "Invalid conditional oper %s" % (nodes[0])),
                    lambda _, nodes: None,
                    lambda _, nodes: mkevaluator.MkCmdComment(nodes[0]),
                    ],
        "RValueExpr": [lambda _, nodes: mkevaluator.MkRValueExpr([nodes[0]]),
                       lambda _, nodes: nodes[0].append_part(nodes[1]),
                      ],
        "RValuePart": [lambda _, nodes: nodes[0],
                       lambda _, nodes: mkevaluator.MkRValueVar(nodes[1]),
                      ],
        "RValueText": [lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                       lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                       lambda _, nodes: mkevaluator.MkRValueSpace(),
                       lambda _, nodes: mkevaluator.MkRValueSpace(),
                      ],
        }
    
    parser = parglare.Parser(grammar, ws='\r', actions=actions)
    return parser
