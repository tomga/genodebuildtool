
import os
import parglare
import pprint

from logprocessor import *


def initialize():
    parser_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = '%s/mklogparser.pg' % (parser_dir)
    grammar = parglare.Grammar.from_file(file_name)

    actions = {
        "CmdList": [lambda _, nodes: BuildCommandGroup(None, None, '.',
                                                       [ nodes[0] ]  if nodes[0] is not None else []),
                    lambda _, nodes: nodes[0].append(nodes[1]) if nodes[1] is not None else nodes[0],
                    ],
        "Command": [lambda _, nodes: nodes[2].relabel("Library", nodes[1], nodes[0]),
                    lambda _, nodes: nodes[2].relabel("Program", nodes[1], nodes[0]),
                    lambda _, nodes: nodes[1].relabel(None, None, nodes[0]),
                    lambda _, nodes: BuildCommandGroup(None, None, nodes[0], []),
                    lambda _, nodes: SimpleBuildCommand(nodes[0][0], nodes[0][1], nodes[1]),
                    lambda _, nodes: SimpleBuildCommand(None, None, nodes[0]),
                    lambda _, nodes: None,
                    lambda _, nodes: None,
                    ],
        "EnteringDir": [lambda _, nodes: nodes[1] ],
        "LeavingDir": [lambda _, nodes: nodes[1] ],

        "LibraryTitle": [lambda _, nodes: nodes[1] ],
        "ProgramTitle": [lambda _, nodes: nodes[1] ],

        "BuildCommandTitle": [lambda _, nodes: [ nodes[1], nodes[3] ] ],

        "SimpleCommandList": [lambda _, nodes: [ nodes[0] ],
                              lambda _, nodes: nodes[0] + [ nodes[1] ],
                              ],
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
