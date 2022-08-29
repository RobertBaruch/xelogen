# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring

from typing import Optional, cast
import unittest
from xelogen.nodes import Node, NodeInput, NodeOutput, Port
from xelogen.program import Else, If, Program


class XelogenTestCase(unittest.TestCase):

    def assert_contains(self, inport: Port, outport: Port) -> None:
        if not isinstance(inport, NodeInput):
            raise ValueError("Can't assert that an output contains something.")
        if not isinstance(outport, NodeOutput):
            raise ValueError(
                "Can't assert that an input contains another input.")
        inputs = inport.node.inputs[inport.name]
        other_id = outport.node.id
        self.assertIn(
            other_id, [x.node.id for x in inputs],
            f"Input '{inport.name}' of {inport.node.id}:<{inport.node.name}> does not "
            f"contain output '{outport.name}' of {outport.node.id}:<{outport.node.name}>, "
            "but should.")

    def assert_not_contains(self, inport: Port, outport: Port) -> None:
        if not isinstance(inport, NodeInput):
            raise ValueError("Can't assert that an output contains something.")
        if not isinstance(outport, NodeOutput):
            raise ValueError(
                "Can't assert that an input contains another input.")
        inputs = inport.node.inputs[inport.name]
        other_id = outport.node.id
        self.assertNotIn(
            other_id, [x.node.id for x in inputs],
            f"Input '{inport.name}' of {inport.node.id}:<{inport.node.name}> "
            f"contains output '{outport.name}' of {outport.node.id}:<{outport.node.name}>, "
            "but should not.")


class TestIf(XelogenTestCase):

    def test_if(self):
        pgm = Program()

        pulse = pgm.add_node("Pulse")
        true_node = pgm.add_node("BoolInput")
        impulse_display = pgm.add_node("ImpulseDisplay")
        true_node.content = True
        with If(pulse["*"], true_node["*"]) as true:
            true += impulse_display

        if_node = next((n for n in pgm.nodes if n.name == "If"), None)
        assert if_node is not None
        self.assert_contains(if_node["impulse"], pulse["*"])
        self.assert_contains(if_node["condition"], true_node["*"])
        self.assert_contains(impulse_display["impulse"], if_node["true"])

    def test_else(self):
        pgm = Program()

        pulse = pgm.add_node("Pulse")
        true_node = pgm.add_node("BoolInput")
        impulse_display = pgm.add_node("ImpulseDisplay")
        true_node.content = True
        with If(pulse["*"], true_node["*"]) as _:
            pass
        with Else() as false:
            false += impulse_display

        if_node = next((n for n in pgm.nodes if n.name == "If"), None)
        if_node = cast(Node, if_node)
        self.assert_contains(impulse_display["impulse"], if_node["false"])

    def test_bare_else_fails(self):
        _ = Program()

        def erroring_with():
            with Else() as _:
                pass

        self.assertRaises(SyntaxError, erroring_with)

    def test_double_else_fails(self):
        pgm = Program()

        pulse = pgm.add_node("Pulse")
        true_node = pgm.add_node("BoolInput")
        impulse_display = pgm.add_node("ImpulseDisplay")
        true_node.content = True
        with If(pulse["*"], true_node["*"]) as _:
            pass
        with Else() as false:
            false += impulse_display

        def erroring_with():
            with Else() as _:
                pass

        self.assertRaises(SyntaxError, erroring_with)

    def test_if_else_if_else_succeeds(self):
        pgm = Program()

        pulse = pgm.add_node("Pulse")
        pulse2 = pgm.add_node("Pulse")
        true_node = pgm.add_node("BoolInput")
        impulse_display = pgm.add_node("ImpulseDisplay")
        impulse_display2 = pgm.add_node("ImpulseDisplay")
        true_node.content = True

        if_node: Optional[Node] = None
        with If(pulse["*"], true_node["*"]) as true1:
            if_node = true1.chain[0]
        with Else() as false1:
            false1 += impulse_display

        if_node2: Optional[Node] = None
        with If(pulse2["*"], true_node["*"]) as true2:
            if_node2 = true2.chain[0]
        with Else() as false2:
            false2 += impulse_display2

        self.assert_contains(impulse_display2["impulse"], if_node2["false"])
        self.assert_not_contains(impulse_display2["impulse"], if_node["true"])
        self.assert_not_contains(impulse_display2["impulse"], if_node["false"])

    def test_nested_else(self):
        pgm = Program()

        pulse = pgm.add_node("Pulse")
        true_node = pgm.add_node("BoolInput")
        impulse_display = pgm.add_node("ImpulseDisplay")
        impulse_display2 = pgm.add_node("ImpulseDisplay")
        true_node.content = True

        if_node: Optional[Node] = None
        if_node2: Optional[Node] = None
        with If(pulse["*"], true_node["*"]) as true1:
            if_node = true1.chain[0]
            with If(true1.last, true_node["*"]) as true2:
                if_node2 = true2.chain[0]
                true2 += impulse_display2
        with Else() as false1:
            false1 += impulse_display

        self.assert_contains(impulse_display["impulse"], if_node["false"])
        self.assert_contains(impulse_display2["impulse"], if_node2["true"])
        self.assert_not_contains(impulse_display["impulse"], if_node2["false"])


if __name__ == '__main__':
    unittest.main()
