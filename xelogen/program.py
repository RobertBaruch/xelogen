from collections.abc import MutableSequence
from typing import Any, Optional

from xelogen.database import Database
from xelogen.nodes import Canonical, Node, NodeSpec


class OwnedNode(Node):
    owner: "Program"

    def __init__(self, nodespec: NodeSpec, owner: "Program"):
        super().__init__(nodespec)
        self.owner = owner

    def try_add(self, output_name: str, other: Any) -> "Node":
        if isinstance(other,
                      int) and self.output_type(output_name) == Canonical.INT:
            new_node = self.owner.add_node("PlusOne<Int>")
            new_node["value"] = self
            return new_node
        raise ValueError(f"Cannot add value of type {type(other)} "
                         f"to node {self.spec.name} output {output_name}.")

    def print(self):
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
        node = self.make_node(name)
        node.id = len(self.nodes)
        self.nodes.append(node)
        return node

    def root(self) -> Node:
        if self._root_node is None:
            self._root_node = self.add_node("RootSlot")
        return self._root_node

    def print(self):
        for n in self.nodes:
            n.print()
