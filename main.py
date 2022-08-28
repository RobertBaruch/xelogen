"""What a main looks like."""

from absl import app

from xelogen.lint import Linter, init_linter
from xelogen.program import Program


def main(_):
    """An example main."""
    init_linter()

    pgm = Program()

    pulse = pgm.add_node("Pulse")
    root = pgm.root()
    num_children = pgm.add_node("NumChildren")
    write = pgm.add_node("WriteDynVar<Int>")
    string = pgm.add_node("StringInput")
    addone = pgm.add_node("PlusOne<Int>")

    num_children["slot"] = root
    addone["value"] = num_children

    string.content = "World/Meow"
    concat = pgm.add_node("Plus<String>")
    concat["values"] += string
    concat["values"] += string

    write["write"] = pulse
    write["name"] = concat
    extra = addone["*"] + 1
    write["value"] = extra + 2

    with write["success"] as chain:
        chain += write

    Linter.lint(pgm)

    print("Done!")
    pgm.print()


if __name__ == '__main__':
    app.run(main)  # type: ignore
