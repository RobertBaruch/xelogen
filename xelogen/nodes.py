"""Datatypes and nodes."""

from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping
from enum import IntEnum, auto, unique
from typing import Any, Optional, Union


@unique
class Datatype(IntEnum):
    """Basic datatypes.

    The _LIST datatype is for inputs that can take more than one signal of the
    same type. IMPULSE_LIST is for all impulse inputs. All other _LIST types
    are for inputs that can be expanded (e.g. the Plus, Mul, etc. nodes).
    """
    IMPULSE = auto()
    IMPULSE_LIST = auto()
    FLOAT = auto()
    INT = auto()
    INT_LIST = auto()
    STRING = auto()
    STRING_LIST = auto()
    SLOT = auto()

    def is_list(self) -> bool:
        """Determines whether this is a list datatype."""
        return self in [
            Datatype.IMPULSE_LIST, Datatype.STRING_LIST, Datatype.INT_LIST
        ]

    def element_type(self):
        """Gets the element datatype for a list datatype."""
        if self == Datatype.STRING_LIST:
            return Datatype.STRING
        if self == Datatype.IMPULSE_LIST:
            return Datatype.IMPULSE
        if self == Datatype.INT_LIST:
            return Datatype.INT
        raise ValueError(f"Type {self.name} is not a list.")


class NodeSpec:
    """The specification for a node."""
    name: str
    inputs: Mapping[str, Datatype]
    outputs: Mapping[str, Datatype]
    content_type: Optional[Datatype]

    def __init__(self,
                 name: str,
                 inputs: Mapping[str, Datatype],
                 outputs: Mapping[str, Datatype],
                 content_type: Optional[Datatype] = None) -> None:
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.content_type = content_type


class NodeOutput:
    """Representation of a node's output."""
    node: "Node"
    name: str

    def __init__(self, node: "Node", name: str):
        self.node = node
        self.name = name

    @property
    def datatype(self) -> Datatype:
        """Gets the datatype of the output."""
        return self.node.output_type(self.name)

    def __enter__(self) -> "ImpulseChain":
        if self.datatype != Datatype.IMPULSE:
            raise ValueError("with can only be used with impulse outputs.")
        return ImpulseChain(self.node, self.name)

    def __exit__(self, exc_type: ..., exc_value: ..., traceback: ...):
        pass

    def __add__(self, other: Any) -> "Node":
        return self.node.try_add(self.name, other)


class ListInput:
    """Representation of a node's list input."""
    node: "Node"
    name: str

    def __init__(self, node: "Node", name: str):
        self.node = node
        self.name = name

    @property
    def datatype(self) -> Datatype:
        """Gets the element datatype of the input."""
        return self.node.input_type(self.name).element_type()

    def __enter__(self) -> "ImpulseChain":
        raise ValueError("with can only be used with impulse outputs.")

    def __exit__(self, exc_type: ..., exc_value: ..., traceback: ...):
        pass

    def __iadd__(self, other: Union["Node", NodeOutput]) -> "ListInput":
        print(f"iadd a {type(other)}")
        if not self.node.input_type(self.name).is_list():
            raise ValueError("Cannot add an input to a non-list input")
        if isinstance(other, Node):
            output = other.first_output_of_type(self.datatype)
            print(f"Got an output {repr(output)}")
            self.node.add_input(self.name, output)
            return self
        self.node.add_input(self.name, other)
        return self

    def __add__(self, other: Any) -> "Node":
        return NotImplemented


class Node(ABC):
    """A node."""
    spec: NodeSpec
    inputs: MutableMapping[str, list[NodeOutput]]
    _content: Any
    id: int = -1

    def __init__(self, nodespec: NodeSpec):
        self.spec = nodespec
        self.inputs = {}
        self._content = None
        for i in nodespec.inputs.keys():
            self.inputs[i] = []

    def __getitem__(self,
                    output_or_list_input: str) -> Union[ListInput, NodeOutput]:
        """Gets the output or list input with the given name."""
        if output_or_list_input in self.spec.outputs:
            return self.get_output(output_or_list_input)
        if output_or_list_input in self.spec.inputs and self.spec.inputs[
                output_or_list_input].is_list():
            return ListInput(self, output_or_list_input)
        raise IndexError(
            f"Output or list input {output_or_list_input} is not in node "
            f"{self.spec.name}.")

    def __setitem__(self, input_name: str, output: Union["Node", NodeOutput,
                                                         ListInput]) -> None:
        """Sets the input with the given name to the given output.

        Connecting an output to the given input:
            node1[input] = node2[output]
        If node2[output] is an impulse, then the impulse will be added to the
        input.

        Special syntax to connect an output of a node to the given
        input, where the output selected is the first one matching the given
        input's type:
            node1[input] = node2
        """
        if isinstance(output, ListInput):
            # We've already done the add in ListInput.__iadd__
            return

        if input_name not in self.inputs:
            raise IndexError(
                f"Input {input_name} is not in node {self.spec.name}.")
        if isinstance(output, NodeOutput):
            self.add_input(input_name, output)
        else:
            self[input_name] = output.first_output_of_type(
                self.input_type(input_name))

    def input_type(self, input_name: str) -> Datatype:
        """Gets the input datatype for the given input."""
        return self.spec.inputs[input_name]

    def output_type(self, output_name: str) -> Datatype:
        """Gets the output datatype for the given output."""
        return self.spec.outputs[output_name]

    def add_input(self, input_name: str, output: NodeOutput) -> None:
        """Adds the given output to the given input of this node."""
        if self.input_type(input_name).is_list():
            if output.datatype != self.input_type(input_name).element_type():
                raise ValueError(
                    f"Connecting an output of type {output.datatype.name} "
                    f"to the {input_name} input of node {self.spec.name} of type "
                    f"{self.input_type(input_name).element_type().name} is not possible."
                )
            self.inputs[input_name].append(output)
            return

        if self.input_type(input_name) != output.datatype:
            raise ValueError(
                f"Connecting an output of type {output.datatype.name} "
                f"to the {input_name} input of node {self.spec.name} of type "
                f"{self.input_type(input_name).name} is not possible.")
        if len(self.inputs[input_name]) > 0:
            raise ValueError(f"Cannot add another {output.datatype.name} "
                             f"to input {input_name} of node {self.spec.name}.")
        self.inputs[input_name].append(output)

    def get_output(self, output: str) -> NodeOutput:
        """Gets the given output for this node."""
        return NodeOutput(self, output)

    def get_only_output(self) -> NodeOutput:
        """Gets the only output for this node, which is always named '*'."""
        return self.get_output("*")

    def first_input_impulse(self) -> str:
        """Gets the name of the first input impulse in this Node."""
        first = next((name for (name, datatype) in self.spec.inputs.items()
                      if datatype == Datatype.IMPULSE_LIST), None)
        if not first:
            raise ValueError(f"Node {self.spec.name} has no input impulses.")
        return first

    def first_output_impulse(self) -> NodeOutput:
        """Gets the first output impulse in this Node."""
        return self.first_output_of_type(Datatype.IMPULSE)

    def first_output_of_type(self, datatype: Datatype) -> NodeOutput:
        """Gets the first output of the given type."""
        if datatype.is_list():
            datatype = datatype.element_type()
        first = next((name for (name, output_type) in self.spec.outputs.items()
                      if output_type == datatype), None)
        if not first:
            raise ValueError(f"Node {self.spec.name} has no output of type "
                             f"{datatype.name}.")
        return NodeOutput(self, first)

    @property
    def content(self) -> Any:
        """Gets the content of this node."""
        return self._content

    @content.setter
    def content(self, value: Any):
        """Sets the content of this node (if it has a content)."""
        if not self.spec.content_type:
            raise ValueError(
                f"Node {self.spec.name} does not have content to set.")
        if self.spec.content_type == Datatype.STRING:
            if not isinstance(value, str):
                raise ValueError(
                    f"Node {self.spec.name} can only take content of type "
                    f"{self.spec.content_type.name}, and {type(value)} is not compatible"
                )
            self._content = value
            return
        if self.spec.content_type == Datatype.INT:
            if not isinstance(value, int):
                raise ValueError(
                    f"Node {self.spec.name} can only take content of type "
                    f"{self.spec.content_type.name}, and {type(value)} is not compatible"
                )
            self._content = value
            return
        raise ValueError(
            f"Don't know how to handle content type {self.spec.content_type.name} "
            f"in node {self.spec.name}")

    def __add__(self, other: Any) -> "Node":
        """Handles Node + x."""
        return self.try_add("*", other)

    @abstractmethod
    def try_add(self, output_name: str, other: Any) -> "Node":
        """Attempts to add the given other value to the given output.

        Returns the new node implementing the addition that has been added
          to the program.
        Raises ValueError if the addition couldn't be made.
        """


class ImpulseChain:
    """A context for a default chain of impulses.

    The default chain is defined by appending nodes to the current chain.
    The first output impulse of the previous node is sent to the first
    input impulse of the appended node.

    The first impulse in the chain is defined by the passed-in arguments
    to the constructor.
    """
    impulse: NodeOutput
    chain: list[Node]

    def __init__(self, node: Node, output: str):
        self.chain = []
        impulse = node.get_output(output)
        if impulse.datatype != Datatype.IMPULSE:
            raise ValueError(f"Output {output} of node {node.spec.name} "
                             "is not an impulse.")
        self.impulse = impulse

    def __iadd__(self, other: Node) -> "ImpulseChain":
        """+= extends the chain."""
        input_name = other.first_input_impulse()
        next_output = other.first_output_impulse()
        other.add_input(input_name, self.impulse)
        self.impulse = next_output
        self.chain.append(other)
        return self
