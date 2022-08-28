from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping
from enum import IntEnum, auto, unique
from typing import Any, Optional, Union


@unique
class Canonical(IntEnum):
    IMPULSE = auto()
    IMPULSE_LIST = auto()
    FLOAT = auto()
    INT = auto()
    STRING = auto()
    STRING_LIST = auto()
    SLOT = auto()

    def is_list(self) -> bool:
        return self in [Canonical.IMPULSE_LIST, Canonical.STRING_LIST]

    def is_list_of(self, other: "Canonical") -> bool:
        if not self.is_list():
            return False
        if self == Canonical.STRING_LIST:
            return other == Canonical.STRING
        if self == Canonical.IMPULSE_LIST:
            return other == Canonical.IMPULSE
        return False

    def element_type(self):
        if self == Canonical.STRING_LIST:
            return Canonical.STRING
        if self == Canonical.IMPULSE_LIST:
            return Canonical.IMPULSE
        raise ValueError(f"Type {self.name} is not a list.")


class NodeSpec:
    name: str
    inputs: Mapping[str, Canonical]
    outputs: Mapping[str, Canonical]
    content_type: Optional[Canonical]

    def __init__(self,
                 name: str,
                 inputs: Mapping[str, Canonical],
                 outputs: Mapping[str, Canonical],
                 content_type: Optional[Canonical] = None) -> None:
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

    def output_type(self) -> Canonical:
        return self.node.output_type(self.name)

    def __enter__(self) -> "ImpulseChain":
        if self.output_type() != Canonical.IMPULSE:
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

    def input_type(self) -> Canonical:
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
            output = other.first_output_of_type(self.input_type())
            print(f"Got an output {repr(output)}")
            self.node.add_input(self.name, output)
            return self
        self.node.add_input(self.name, other)
        return self

    def __add__(self, other: Any) -> "Node":
        return NotImplemented


class Node(ABC):
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
            print(
                f"Returning a list of {self.spec.inputs[output_or_list_input]}")
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
            print(f"Input {input_name} output {repr(output)}")
            self[input_name] = output.first_output_of_type(
                self.input_type(input_name))

    def input_type(self, input_name: str) -> Canonical:
        return self.spec.inputs[input_name]

    def output_type(self, output_name: str) -> Canonical:
        return self.spec.outputs[output_name]

    # def set_input(self, input_name: str, output: NodeOutput) -> None:
    #     if self.input_type(input_name) != output.output_type():
    #         raise ValueError(
    #             f"Connecting an output of type {output.output_type()} "
    #             f"to the {input_name} input of node {self.spec.name} of type "
    #             f"{self.input_type(input_name)} is not possible.")
    #     self.inputs[input_name] = [output]

    def add_input(self, input_name: str, output: NodeOutput) -> None:
        if self.input_type(input_name).is_list():
            if output.output_type() != self.input_type(
                    input_name).element_type():
                raise ValueError(
                    f"Connecting an output of type {output.output_type()} "
                    f"to the {input_name} input of node {self.spec.name} of type "
                    f"{self.input_type(input_name).element_type()} is not possible."
                )
            self.inputs[input_name].append(output)
            return

        if self.input_type(input_name) != output.output_type():
            raise ValueError(
                f"Connecting an output of type {output.output_type()} "
                f"to the {input_name} input of node {self.spec.name} of type "
                f"{self.input_type(input_name)} is not possible.")
        if len(self.inputs[input_name]) > 0:
            raise ValueError(f"Cannot add another {output.output_type()} "
                             f"to input {input_name} of node {self.spec.name}.")
        self.inputs[input_name].append(output)

    def get_output(self, output: str) -> NodeOutput:
        return NodeOutput(self, output)

    def get_only_output(self) -> NodeOutput:
        return self.get_output("*")

    def first_input_impulse(self) -> str:
        """Gets the name of the first input impulse in this Node."""
        n = next((name for (name, datatype) in self.spec.inputs.items()
                  if datatype == Canonical.IMPULSE_LIST), None)
        if not n:
            raise ValueError(f"Node {self.spec.name} has no input impulses.")
        return n

    def first_output_impulse(self) -> NodeOutput:
        """Gets the first output impulse in this Node."""
        return self.first_output_of_type(Canonical.IMPULSE)

    def first_output_of_type(self, t: Canonical) -> NodeOutput:
        """Gets the first output of the given type."""
        if t.is_list():
            t = t.element_type()
        n = next((name for (name, datatype) in self.spec.outputs.items()
                  if datatype == t), None)
        if not n:
            raise ValueError(f"Node {self.spec.name} has no output of type "
                             f"{t.name}.")
        return NodeOutput(self, n)

    @property
    def content(self) -> Any:
        return self._content

    @content.setter
    def content(self, value: Any):
        if not self.spec.content_type:
            raise ValueError(
                f"Node {self.spec.name} does not have content to set.")
        if self.spec.content_type == Canonical.STRING:
            if not isinstance(value, str):
                raise ValueError(
                    f"Node {self.spec.name} can only take content of type "
                    f"{self.spec.content_type}, and {type(value)} is not compatible"
                )
            self._content = value
            return
        raise ValueError(
            f"Don't know how to handle content type {self.spec.content_type} "
            f"in node {self.spec.name}")

    @abstractmethod
    def try_add(self, output_name: str, other: Any) -> "Node":
        """Attempts to add the given other value to the given output.

        Returns the new node implementing the addition that has been added
          to the program.
        Raises ValueError if the addition couldn't be made.
        """


class ImpulseChain:
    """
    A context manager for a default chain of impulses.

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
        n = node.get_output(output)
        if n.output_type() != Canonical.IMPULSE:
            raise ValueError(f"Output {output} of node {node.spec.name} "
                             "is not an impulse.")
        self.impulse = n

    def __iadd__(self, other: Node) -> "ImpulseChain":
        input_name = other.first_input_impulse()
        next_output = other.first_output_impulse()
        other.add_input(input_name, self.impulse)
        self.impulse = next_output
        self.chain.append(other)
        return self
