"""All the nodes known to Xelogen."""

from collections.abc import MutableMapping

from xelogen.nodes import Datatype, NodeSpec


class Database:
    """Contains specs for all nodes."""
    nodespecs_by_name: MutableMapping[str, NodeSpec]

    def add_nodespec(self, nodespec: NodeSpec) -> None:
        """Adds a NodeSpec to the database."""
        self.nodespecs_by_name[nodespec.name] = nodespec

    def __init__(self):
        self.nodespecs_by_name = {}
        for spec in (
                NodeSpec("RootSlot", inputs={}, outputs={"*": Datatype.SLOT}),
                NodeSpec("NumChildren",
                         inputs={"slot": Datatype.SLOT},
                         outputs={"*": Datatype.INT}),
                NodeSpec("WriteDynVar<Int>",
                         inputs={
                             "write": Datatype.IMPULSE_LIST,
                             "slot": Datatype.SLOT,
                             "name": Datatype.STRING,
                             "value": Datatype.INT,
                         },
                         outputs={
                             "success": Datatype.IMPULSE,
                             "fail": Datatype.IMPULSE,
                         }),
                NodeSpec("Pulse", inputs={}, outputs={"*": Datatype.IMPULSE}),
                NodeSpec("StringInput",
                         inputs={},
                         outputs={"*": Datatype.STRING},
                         content_type=Datatype.STRING),
                NodeSpec("IntInput",
                         inputs={},
                         outputs={"*": Datatype.INT},
                         content_type=Datatype.INT),
                NodeSpec("BoolInput",
                         inputs={},
                         outputs={"*": Datatype.BOOL},
                         content_type=Datatype.BOOL),
                NodeSpec("ImpulseDisplay",
                         inputs={"impulse": Datatype.IMPULSE_LIST},
                         outputs={}),
                NodeSpec("PlusOne<Int>",
                         inputs={"value": Datatype.INT},
                         outputs={"*": Datatype.INT}),
                NodeSpec("Plus<String>",
                         inputs={
                             "values": Datatype.STRING_LIST,
                         },
                         outputs={"*": Datatype.STRING}),
                NodeSpec("Plus<Int>",
                         inputs={
                             "values": Datatype.INT_LIST,
                         },
                         outputs={"*": Datatype.INT}),
                NodeSpec("If",
                         inputs={
                             "impulse": Datatype.IMPULSE_LIST,
                             "condition": Datatype.BOOL,
                         },
                         outputs={
                             "true": Datatype.IMPULSE,
                             "false": Datatype.IMPULSE
                         }),
        ):
            self.add_nodespec(spec)
