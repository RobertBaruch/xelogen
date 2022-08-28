from typing import cast

from xelogen.program import Program


class Linter:
    linters: list["Linter"] = []

    def __init__(self):
        pass

    @classmethod
    def lint(cls, pgm: Program) -> int:
        warnings = 0

        for linter in cls.linters:
            warnings += linter.linter_pass(pgm)
        return warnings

    def linter_pass(self, pgm: Program) -> int:
        return 0

    @classmethod
    def register_linter(cls, linter: "Linter") -> None:
        cls.linters.append(linter)


class DynVarLinter(Linter):

    def __init__(self):
        super().__init__()

    def linter_pass(self, pgm: Program) -> int:
        warnings = 0
        for n in pgm.nodes:
            if not n.spec.name.startswith("WriteDynVar"):
                continue
            if n.inputs["name"] is None:
                print(
                    f"WARNING: Node {n.spec.name} has no name input connected.")
                warnings += 1
                continue
            node_output = n.inputs["name"]
            if not node_output:
                continue
            if node_output[0].node.spec.name != "StringInput":
                continue
            varname = node_output[0].node.content
            if varname is None:
                print(f"WARNING: Name input for {n.spec.name} is empty.")
                warnings += 1
                continue
            if cast(str, varname).find("/") == -1:
                print(
                    f"WARNING: Name input for {n.spec.name} does not have a space. "
                    "This can result in surprises. Consider adding a space.")
                warnings += 1
                continue

        return warnings


def init_linter() -> Linter:
    linter = Linter()
    Linter.register_linter(DynVarLinter())

    return linter
