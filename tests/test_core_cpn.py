"""Python 3.14 regression baseline for core colored-net behavior."""

from __future__ import annotations

import unittest

from snakes.nets import (
    Expression,
    PetriNet,
    Place,
    Test,
    Transition,
    Value,
    Variable,
    dot,
)


def build_concurrent_join_net() -> PetriNet:
    """Build two independently enabled branches followed by a join."""
    net = PetriNet("concurrent-join")
    net.add_place(Place("requested", ["run-1"]))
    net.add_place(Place("qe_permit", [dot]))
    net.add_place(Place("vasp_permit", [dot]))
    net.add_place(Place("qe_ready"))
    net.add_place(Place("vasp_ready"))
    net.add_place(Place("comparison_ready"))

    net.add_transition(Transition("project_qe"))
    net.add_input("requested", "project_qe", Test(Variable("request")))
    net.add_input("qe_permit", "project_qe", Value(dot))
    net.add_output(
        "qe_ready",
        "project_qe",
        Expression("('qe', request)"),
    )

    net.add_transition(Transition("project_vasp"))
    net.add_input("requested", "project_vasp", Test(Variable("request")))
    net.add_input("vasp_permit", "project_vasp", Value(dot))
    net.add_output(
        "vasp_ready",
        "project_vasp",
        Expression("('vasp', request)"),
    )

    net.add_transition(
        Transition(
            "compare",
            Expression("qe_observation[1] == vasp_observation[1]"),
        )
    )
    net.add_input("qe_ready", "compare", Variable("qe_observation"))
    net.add_input("vasp_ready", "compare", Variable("vasp_observation"))
    net.add_output(
        "comparison_ready",
        "compare",
        Expression("('comparison', qe_observation[1])"),
    )
    return net


class CoreColoredNetTest(unittest.TestCase):
    def test_independent_branches_join_in_either_order(self) -> None:
        for branch_order in (
            ("project_qe", "project_vasp"),
            ("project_vasp", "project_qe"),
        ):
            with self.subTest(branch_order=branch_order):
                net = build_concurrent_join_net()

                self.assertEqual(len(net.transition("project_qe").modes()), 1)
                self.assertEqual(len(net.transition("project_vasp").modes()), 1)
                self.assertEqual(net.transition("compare").modes(), [])

                first = net.transition(branch_order[0])
                first.fire(first.modes()[0])
                self.assertEqual(net.transition("compare").modes(), [])

                second = net.transition(branch_order[1])
                second.fire(second.modes()[0])
                comparison_modes = net.transition("compare").modes()
                self.assertEqual(len(comparison_modes), 1)

                net.transition("compare").fire(comparison_modes[0])

                self.assertIn("run-1", net.place("requested"))
                self.assertIn(
                    ("comparison", "run-1"),
                    net.place("comparison_ready"),
                )
                self.assertTrue(net.place("qe_ready").is_empty())
                self.assertTrue(net.place("vasp_ready").is_empty())


if __name__ == "__main__":
    unittest.main()
