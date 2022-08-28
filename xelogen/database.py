from collections.abc import MutableMapping

from xelogen.nodes import Canonical, NodeSpec


class Database:
    """Contains specs for all nodes."""
    nodespecs_by_name: MutableMapping[str, NodeSpec] = {}

    def add_nodespec(self, nodespec: NodeSpec) -> None:
        """Adds a NodeSpec to the database."""
        self.nodespecs_by_name[nodespec.name] = nodespec

    def __init__(self):
        for n in (
                NodeSpec("RootSlot", inputs={}, outputs={"*": Canonical.SLOT}),
                NodeSpec("NumChildren",
                         inputs={"slot": Canonical.SLOT},
                         outputs={"*": Canonical.INT}),
                NodeSpec("WriteDynVar<Int>",
                         inputs={
                             "write": Canonical.IMPULSE_LIST,
                             "slot": Canonical.SLOT,
                             "name": Canonical.STRING,
                             "value": Canonical.INT,
                         },
                         outputs={
                             "success": Canonical.IMPULSE,
                             "fail": Canonical.IMPULSE,
                         }),
                NodeSpec("Pulse", inputs={}, outputs={"*": Canonical.IMPULSE}),
                NodeSpec("StringInput",
                         inputs={},
                         outputs={"*": Canonical.STRING},
                         content_type=Canonical.STRING),
                NodeSpec("ImpulseDisplay",
                         inputs={"impulse": Canonical.IMPULSE_LIST},
                         outputs={}),
                NodeSpec("PlusOne<Int>",
                         inputs={"value": Canonical.INT},
                         outputs={"*": Canonical.INT}),
                NodeSpec("Plus<String>",
                         inputs={
                             "values": Canonical.STRING_LIST,
                         },
                         outputs={"*": Canonical.STRING}),
        ):
            self.add_nodespec(n)
