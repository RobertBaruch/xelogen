from abc import ABC
from typing import Optional, cast
from xelogen.nodes import NodeOutput
from xelogen.program import Program

_global_program: Optional[Program] = None


def global_program() -> Program:
    global _global_program
    assert _global_program is not None
    return _global_program


class Value(ABC):
    output: NodeOutput

    def __init__(self, output: NodeOutput):
        self.output = output


class IntValue(Value):
    pass


class SlotValue(Value):

    def num_children(self) -> IntValue:
        node = global_program().add_node("NumChildren")
        node["slot"] = self.output.node
        return IntValue(cast(NodeOutput, node["*"]))

    @property
    @classmethod
    def root(cls) -> "SlotValue":
        node = global_program().add_node("Root")
        return SlotValue(cast(NodeOutput, node["*"]))
