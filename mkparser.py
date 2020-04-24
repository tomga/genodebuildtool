
import parglare
import pprint


def initialize():
    file_name = '/projects/genode/buildtool/mkparser.pg'
    grammar = parglare.Grammar.from_file(file_name)

    actions = {
        "CmdList": [lambda _, nodes: [ nodes[0] ],
                    lambda _, nodes: (nodes[0] + [ nodes[2] ] if nodes[2] is not None else nodes[0]),
                    ],
        "Command": [lambda _, nodes: [nodes[0], nodes[2], nodes[4]],
                    lambda _, nodes: [nodes[0], nodes[2], nodes[4]],
                    lambda _, nodes: [nodes[0], nodes[2], nodes[4], nodes[8]],
                    lambda _, nodes: None,
                    lambda _, nodes: None,
                    ],
        "RValueExpr": [lambda _, nodes: [ nodes[0] ],
                       lambda _, nodes: nodes[0] + [ nodes[1] ] if not (nodes[0][-1] == ' ' and nodes[1] == ' ') else nodes[0],
                      ],
        "RValuePart": [lambda _, nodes: nodes[0],
                       lambda _, nodes: '$' + nodes[1],
                      ],
        "RValueText": [lambda _, nodes: nodes[0],
                       lambda _, nodes: nodes[0],
                       lambda _, nodes: ' ',
                       lambda _, nodes: ' ',
                      ],
        }
    
    parser = parglare.Parser(grammar, ws='\r', actions=actions)
    return parser

def parse_file(mkfile):
    parser.parse_file(mkfile)
