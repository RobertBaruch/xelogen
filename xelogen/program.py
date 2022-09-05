"""Program, which is a bunch of nodes under a slot."""

from collections.abc import MutableSequence
import functools
from typing import Any, Optional, cast

from xelogen.database import Database
from xelogen.nodes import Datatype, ImpulseChain, Node, NodeOutput, NodeSpec, Port


class OwnedNode(Node):
    """A node in the context of a program."""
    owner: "Program"

    def __init__(self, nodespec: NodeSpec, owner: "Program"):
        super().__init__(nodespec)
        self.owner = owner

    @functools.singledispatchmethod
    def try_add(self, other: Any, output: NodeOutput) -> "Node":
        raise NotImplementedError()

    @try_add.register
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

    @try_add.register
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
    database: Database = Database()
    nodes: MutableSequence[OwnedNode]

    # A unique RootNode per program.
    _root_node: Optional[OwnedNode]

    def __init__(self):
        self.nodes = []
        self._root_node = None
        ImpulseChain.init_context()

    def make_node(self, name: str) -> OwnedNode:
        """Gets an instance of a node of the given name."""
        return OwnedNode(self.database.nodespecs_by_name[name], self)

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
        for node in self.nodes:
            node.print()


class If(ImpulseChain):
    """Context for if statements.

    When the `trigger_impulse` happens, the condition is evaluated, and
    either the true chain (If) or the false chain (Else) will happen.

    An If's Else-clause must appear on the same context level as its If-clause
    and there must be no other intervening with-clause.

    ```
    with If(trigger_impulse, condition) as impulse_chain:
        # Chain when condition is true
        impulse_chain += ...
        impulse_chain += ...

    with Else() as chain2:
        # Chain when condition is false
        chain2 += ...
    ```

    Note that you are allowed to nest If and Else:

    ```
    with If(trigger, condition) as chain:  # If-1
        chain += ...
        with If(trigger2, condition2) as chain2:  # If-2
            chain2 += ...
        with Else() as chain2:  # Matches with If-2
            ...
    with Else() as chain:  # Matches with If-1
        ...
    ```

    This also means that you could even put statements between an If and
    an Else:

    ```
    with If(trigger, condition) as chain:
        ...
    statement
    statement

    with Else() as chain:
        ...
    ```
    """
    if_node: OwnedNode

    def __init__(self, trigger: Port, condition: Port):
        if not isinstance(trigger, NodeOutput):
            raise ValueError("trigger must be an output.")
        if not isinstance(condition, NodeOutput):
            raise ValueError("condition must be an output.")
        if trigger.datatype != Datatype.IMPULSE:
            raise ValueError(f"Output {trigger.name} of {trigger.nodename} "
                             "is not an impulse.")
        if condition.datatype != Datatype.BOOL:
            raise ValueError(f"Output {condition.name} of {condition.nodename} "
                             "is not a bool.")
        program = cast(OwnedNode, condition.node).owner
        self.if_node = program.add_node("If")
        self.if_node["impulse"] = trigger
        self.if_node["condition"] = condition
        super().__init__(self.if_node, "true")


class Else(ImpulseChain):
    """The Else part of an If."""

    def __init__(self):
        last_context = ImpulseChain.stack[-1].last_context
        if not isinstance(last_context, If):
            raise SyntaxError("Cannot have Else without If first.")
        super().__init__(last_context.if_node, "false")
