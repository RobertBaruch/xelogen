"""Datatypes and nodes."""

from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping
from enum import IntEnum, auto, unique
import functools
from typing import Any, Optional, Union, cast


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

    @property
    def element_type(self):
        """Gets the element datatype for a list datatype, or the datatype."""
        if self == Datatype.STRING_LIST:
            return Datatype.STRING
        if self == Datatype.IMPULSE_LIST:
            return Datatype.IMPULSE
        if self == Datatype.INT_LIST:
            return Datatype.INT
        return self


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


class Port(ABC):
    """Representation of an input or output port on a node."""
    node: "Node"
    name: str

    def __init__(self, node: "Node", name: str):
        self.node = node
        self.name = name

    @property
    @abstractmethod
    def datatype(self) -> Datatype:
        """Gets the datatype of the port."""

    @abstractmethod
    def __enter__(self) -> "ImpulseChain":
        """Enters an ImpulseChain context.

        Only makes sense for impulse outputs.
        """

    @abstractmethod
    def __iadd__(self, other: Union["Node", "Port"]) -> "NodeInput":
        """Handles (input) Port += Node/ (output) Port.

        Only makes sense for NodeInput += Node / NodeOutput.
        """

    @abstractmethod
    def __add__(self, other: Any) -> "Node":
        """Handles Port + Any.

        Only makes sense for NodeOutput + Any.
        """

    def __exit__(self, exc_type: ..., exc_value: ..., traceback: ...):
        pass


class NodeOutput(Port):
    """Representation of a node's output."""

    @property
    def datatype(self) -> Datatype:
        return self.node.spec.outputs[self.name]

    def __enter__(self) -> "ImpulseChain":
        if self.datatype != Datatype.IMPULSE:
            raise ValueError("with can only be used with impulse outputs.")
        return ImpulseChain(self.node, self.name)

    def __add__(self, other: Any) -> "Node":
        return self.node.try_add(other, self.node[self.name])

    def __iadd__(self, other: Union["Node", Port]) -> "NodeInput":
        raise SyntaxError("Augmented assignment cannot be applied to outputs.")


class NodeInput(Port):
    """Representation of a node's list input."""

    @property
    def datatype(self) -> Datatype:
        return self.node.spec.inputs[self.name]

    def __enter__(self) -> "ImpulseChain":
        raise ValueError("with can only be used with impulse outputs.")

    def __iadd__(self, other: Union["Node", Port]) -> "NodeInput":
        if isinstance(other, NodeInput):
            raise ValueError("Cannot augment an input with another input.")
        if not self.node[self.name].datatype.is_list():
            raise ValueError("Cannot augment a non-expandable input.")
        if isinstance(other, Node):
            output = other.first_output_of_type(self.datatype)
            self.node.append_input(self.name, output)
            return self
        self.node.append_input(self.name, cast(NodeOutput, other))
        return self

    def __add__(self, other: Any) -> "Node":
        raise SyntaxError(
            "Addition cannot be applied to inputs (did you mean +=?).")


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

    def __getitem__(self, name: str) -> Port:
        """Gets the port with the given name."""
        if name in self.spec.outputs:
            return NodeOutput(self, name)
        if name in self.spec.inputs:
            return NodeInput(self, name)
        raise IndexError(f"Port {name} is not in node {self.spec.name}.")

    def __setitem__(self, input_name: str, output: Union["Node", Port]) -> None:
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
        if isinstance(output, NodeInput):
            # We've already done the add in NodeInput.__iadd__
            return

        if input_name not in self.inputs:
            raise IndexError(
                f"Input {input_name} is not in node {self.spec.name}.")
        if isinstance(output, NodeOutput):
            self.append_input(input_name, output)
        else:
            self[input_name] = cast(Node, output).first_output_of_type(
                self[input_name].datatype)

    def append_input(self, input_name: str, output: NodeOutput) -> None:
        """Appends the given output to the given input of this node."""
        if output.datatype != self[input_name].datatype.element_type:
            raise ValueError(
                f"Connecting an output of type {output.datatype.name} "
                f"to the {input_name} input of node {self.spec.name} of type "
                f"{self[input_name].datatype.element_type.name} is not possible."
            )
        if self[input_name].datatype.is_list():
            self.inputs[input_name].append(output)
            return
        if len(self.inputs[input_name]) > 0:
            raise ValueError(f"Cannot add another {output.datatype.name} "
                             f"to input {input_name} of node {self.spec.name}.")
        self.inputs[input_name].append(output)

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
            datatype = datatype.element_type
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
        return self.try_add(other, cast(NodeOutput, self["*"]))

    @functools.singledispatchmethod
    @abstractmethod
    def try_add(self, other: Any, output: NodeOutput) -> "Node":
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
        impulse = cast(NodeOutput, node[output])
        if impulse.datatype != Datatype.IMPULSE:
            raise ValueError(f"Output {output} of node {node.spec.name} "
                             "is not an impulse.")
        self.impulse = impulse

    def __iadd__(self, other: Node) -> "ImpulseChain":
        """+= extends the chain."""
        input_name = other.first_input_impulse()
        next_output = other.first_output_impulse()
        other.append_input(input_name, self.impulse)
        self.impulse = next_output
        self.chain.append(other)
        return self
