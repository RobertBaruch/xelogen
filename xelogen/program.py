"""Program, which is a bunch of nodes under a slot."""

from collections.abc import MutableSequence
import functools
from typing import Any, Optional, cast

from xelogen.database import Database
from xelogen.nodes import Datatype, Node, NodeOutput, NodeSpec


class OwnedNode(Node):
    """A node in the context of a program."""
    owner: "Program"

    def __init__(self, nodespec: NodeSpec, owner: "Program"):
        super().__init__(nodespec)
        self.owner = owner

    def try_add(self, output_name: str, other: Any) -> Node:
        return self._try_add(other, self[output_name])

    @functools.singledispatchmethod
    def _try_add(self, other: Any, output: NodeOutput) -> Node:
        raise NotImplementedError()

    @_try_add.register
    def _(self, other: int, output: NodeOutput) -> Node:
        if output.datatype == Datatype.INT:
            if other == 1:
                new_node = self.owner.add_node("PlusOne<Int>")
                new_node["value"] = self
                return new_node
            new_node = self.owner.add_node("Plus<Int>")
            int_input = self.owner.add_node("IntInput")
            int_input.content = other
            new_node["values"] += self
            new_node["values"] += int_input
            return new_node
        raise ValueError(f"Cannot add integer {other} "
                         f"to node {self.spec.name} output {output.name}.")

    @_try_add.register
    def _(self, other: Node, output: NodeOutput) -> Node:
        arg = cast(NodeOutput, other["*"])
        if arg.datatype != output.datatype:
            raise ValueError("Cannot add different type nodes together.")
        if output.datatype == Datatype.STRING:
            new_node = self.owner.add_node("Plus<String>")
            new_node["values"] += other["*"]
            new_node["values"] += output
            return new_node
        raise ValueError(
            f"Don't know how to add two {output.datatype.name} nodes.")

    def print(self):
        """Prints a node, for debugging."""
        print(f"{self.id} {self.spec.name}")
        if self.content is not None:
            print(f"    {repr(self.content)}")
            return
        for input_name, output_from in self.inputs.items():
            print(f"    {input_name} from [", end="")
            for output in output_from:
                print(
                    f"{output.node.id}<{output.node.spec.name}>:{output.name}, ",
                    end="")
            print("]")


class Program:
    """All the nodes inside a program slot."""
    db: Database
    nodes: MutableSequence[OwnedNode]

    # A unique RootNode per program.
    _root_node: Optional[OwnedNode]

    def __init__(self):
        self.db = Database()
        self.nodes = []
        self._root_node = None

    def make_node(self, name: str) -> OwnedNode:
        """Gets an instance of a node of the given name."""
        return OwnedNode(self.db.nodespecs_by_name[name], self)

    def add_node(self, name: str) -> OwnedNode:
        """Adds a new node of the given name to the program."""
        node = self.make_node(name)
        node.id = len(self.nodes)
        self.nodes.append(node)
        return node

    def root(self) -> Node:
        """Utility to get a RootSlot node."""
        if self._root_node is None:
            self._root_node = self.add_node("RootSlot")
        return self._root_node

    def print(self):
        """Print the program, for debugging."""
        for n in self.nodes:
            n.print()
