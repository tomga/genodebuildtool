
import os
import parglare
import pprint


def initialize():
    parser_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = '%s/mklogparser.pg' % (parser_dir)
    grammar = parglare.Grammar.from_file(file_name)

    actions = {
        "CmdList": [lambda _, nodes: [ nodes[0] ]  if nodes[0] is not None else [],
                    lambda _, nodes: nodes[0] + [ nodes[1] ] if nodes[1] is not None else nodes[0],
                    ],
        "Command": [lambda _, nodes: [ [ "Library", nodes[1], "in", nodes[0] ], nodes[2] ],
                    lambda _, nodes: [ [ "Program", nodes[1], "in", nodes[0] ], nodes[2] ],
                    lambda _, nodes: [ [ "Commands in", nodes[0] ], nodes[1] ],
                    lambda _, nodes: [ "Nothing in", nodes[0] ],
                    lambda _, nodes: [ nodes[0], nodes[1] ],
                    lambda _, nodes: nodes[0],
                    lambda _, nodes: None,
                    lambda _, nodes: None,
                    ],
        "EnteringDir": [lambda _, nodes: nodes[1] ],
        "LeavingDir": [lambda _, nodes: nodes[1] ],

        "LibraryTitle": [lambda _, nodes: nodes[1] ],
        "ProgramTitle": [lambda _, nodes: nodes[1] ],

        "BuildCommandTitle": [lambda _, nodes: [ nodes[1], nodes[3] ] ],

        "SimpleCommand": [lambda _, nodes: nodes[0] ],

        "SimpleCommandText": [lambda _, nodes: nodes[0],
                              lambda _, nodes: nodes[0] + nodes[1],
                    ],
        "SimpleCommandPart": [lambda _, nodes: nodes[0],
                              lambda _, nodes: nodes[0],
                              lambda _, nodes: ' ',
                    ],
        }

    parser = parglare.Parser(grammar, ws='\r', actions=actions)
    return parser
