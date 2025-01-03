
import parglare
import pprint
import os

from gscons import mkevaluator

def initialize():
    parser_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = '%s/mkparser.pg' % (parser_dir)
    grammar = parglare.Grammar.from_file(file_name)

    actions = {
        "CmdList": [lambda _, nodes: mkevaluator.MkScript(nodes[0]),
                    lambda _, nodes: nodes[0].append_command(nodes[2]),
                    ],
        "Command": [lambda _, nodes: (nodes[1].set_rval_var(nodes[0]) if nodes[1] is not None else
                                      mkevaluator.MkCmdExpr(nodes[0])),
                    lambda _, nodes: (mkevaluator.MkCmdExport(nodes[2]) if nodes[3] is None else
                                      nodes[3].set_rval_var(nodes[2]).set_export(True)),
                    lambda _, nodes: mkevaluator.MkCmdExport(nodes[2], unexport=True),
                    lambda _, nodes: nodes[0],
                    lambda _, nodes: nodes[0],
                    lambda _, nodes: nodes[0],
                    lambda _, nodes: nodes[0],
                    lambda _, nodes: None,
                    lambda _, nodes: mkevaluator.MkCmdComment(nodes[0]),
                    ],
        "CmdAssign": [lambda _, nodes: nodes[0].set_rval_expr(nodes[1]),
                      ],
        "CmdOper": [lambda _, nodes: mkevaluator.MkCmdAppend(),
                    lambda _, nodes: mkevaluator.MkCmdRecursiveExpandAssign(),
                    lambda _, nodes: mkevaluator.MkCmdSimpleExpandAssign(),
                    lambda _, nodes: mkevaluator.MkCmdOptAssign(),
                    ],
        "CondCmd": [lambda _, nodes: mkevaluator.MkCmdCond(nodes[0], nodes[2], None),
                    lambda _, nodes: mkevaluator.MkCmdCond(nodes[0], nodes[2], nodes[6]),
                    lambda _, nodes: mkevaluator.MkCmdCond(nodes[0], nodes[2], mkevaluator.MkScript(nodes[6])),
                    ],
        "Condition": [lambda _, nodes: (mkevaluator.MkCondIfdef(nodes[2]) if nodes[0] == 'ifdef' else
                                        mkevaluator.MkCondIfndef(nodes[2]) if nodes[0] == 'ifndef' else
                                        "Invalid conditional oper %s" % (nodes[0])),
                      lambda _, nodes: (mkevaluator.MkCondIfeq(nodes[3], nodes[5]) if nodes[0] == 'ifeq' else
                                        mkevaluator.MkCondIfneq(nodes[3], nodes[5]) if nodes[0] == 'ifneq' else
                                        "Invalid conditional oper %s" % (nodes[0])),
                      ],
        "IncludeCmd": [lambda _, nodes: mkevaluator.MkCmdInclude(nodes[2]),
                       lambda _, nodes: mkevaluator.MkCmdInclude(nodes[2], optional=True),
                      ],
        "VPathCmd": [lambda _, nodes: mkevaluator.MkCmdVpath(nodes[2], nodes[4]),
                    ],
        "RuleCmd": [lambda _, nodes: mkevaluator.MkCmdRule(nodes[0], nodes[2]),
                    lambda _, nodes: nodes[0].append_command(nodes[2])
                    ],
        "WSOPT": [lambda _, nodes: nodes[0],
                  lambda _, nodes: "",
                  ],
        "OptValueExpr": [lambda _, nodes: nodes[0],
                         lambda _, nodes: mkevaluator.MkRValueExprText(""),
                         ],
        "ValueExpr": [lambda _, nodes: nodes[0],
                      lambda _, nodes: mkevaluator.MkRValueExprText(nodes[0]),
                      lambda _, nodes: nodes[0].join_with(nodes[1]),
                      lambda _, nodes: nodes[0].append_text(nodes[1]),
                      lambda _, nodes: nodes[0].append_text(nodes[1]).join_with(nodes[2]).append_text(nodes[3]),
                      ],
        "NoCommaOptValueExpr": [lambda _, nodes: nodes[0],
                                lambda _, nodes: mkevaluator.MkRValueExprText(""),
                                ],
        "NoCommaValueExpr": [lambda _, nodes: nodes[0],
                             lambda _, nodes: mkevaluator.MkRValueExprText(nodes[0]),
                             lambda _, nodes: mkevaluator.MkRValueExprText(nodes[0]),
                             lambda _, nodes: nodes[0].join_with(nodes[1]),
                             lambda _, nodes: nodes[0].append_text(nodes[1]),
                             lambda _, nodes: nodes[0].append_text(nodes[1]),
                             lambda _, nodes: nodes[0].append_text(nodes[1]).join_with(nodes[2]).append_text(nodes[3]),
                             ],
        "SafeValueExpr": [lambda _, nodes: mkevaluator.MkRValueExprText(nodes[0]),
                          lambda _, nodes: nodes[0].append_text(nodes[1]),
                          lambda _, nodes: nodes[0].append_text(nodes[1]).join_with(nodes[2]).append_text(nodes[3]),
                          ],
        "SafeValuePart": [lambda _, nodes: nodes[0],
                          lambda _, nodes: nodes[0],
                          ],

        }

    parser = parglare.Parser(grammar, ws='\r', actions=actions, debug=False)
    # parser = parglare.Parser(grammar, ws='\r', debug=False)
    # parser = parglare.Parser(grammar, ws='\r', debug=True)
    return parser
