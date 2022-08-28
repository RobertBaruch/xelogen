# pytest

import unittest
from xelogen.nodes import NodeInput, NodeOutput, Port
from xelogen.program import If, Program


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
            f"contain output '{outport.name}' of {outport.node.id}:<{outport.node.name}>"
        )


class TestIf(XelogenTestCase):

    def test_if(self):
        pgm = Program()

        pulse = pgm.add_node("Pulse")
        true_node = pgm.add_node("BoolInput")
        impulse_display = pgm.add_node("ImpulseDisplay")
        true_node.content = True
        with If(pulse["*"], true_node["*"]) as true_path:
            true_path += impulse_display

        if_node = next((n for n in pgm.nodes if n.name == "If"), None)
        assert if_node is not None
        self.assert_contains(if_node["impulse"], pulse["*"])
        self.assert_contains(if_node["condition"], true_node["*"])
        self.assert_contains(impulse_display["impulse"], if_node["true"])


if __name__ == '__main__':
    unittest.main()
