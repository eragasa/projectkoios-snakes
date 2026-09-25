"""Python 3.14 regression baseline for core colored-net behavior."""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from snakes.nets import (
    Expression,
    PetriNet,
    Place,
    Substitution,
    Test,
    Transition,
    Value,
    Variable,
    dot,
)
from snakes.typing import Instance


@dataclass(frozen=True, slots=True)
class ScfRequest:
    request_id: str


@dataclass(frozen=True, slots=True)
class QeObservation:
    request_id: str


@dataclass(frozen=True, slots=True)
class VaspObservation:
    request_id: str


@dataclass(frozen=True, slots=True)
class ScfComparison:
    request_id: str


def build_concurrent_join_net() -> PetriNet:
    """Build two independently enabled branches followed by a join."""
    net = PetriNet("concurrent-join")
    net.globals["QeObservation"] = QeObservation
    net.globals["VaspObservation"] = VaspObservation
    net.globals["ScfComparison"] = ScfComparison
    net.add_place(
        Place("requested", [ScfRequest("run-1")], Instance(ScfRequest))
    )
    net.add_place(Place("qe_permit", [dot]))
    net.add_place(Place("vasp_permit", [dot]))
    net.add_place(Place("qe_ready", check=Instance(QeObservation)))
    net.add_place(Place("vasp_ready", check=Instance(VaspObservation)))
    net.add_place(
        Place("comparison_ready", check=Instance(ScfComparison))
    )

    net.add_transition(Transition("project_qe"))
    net.add_input("requested", "project_qe", Test(Variable("request")))
    net.add_input("qe_permit", "project_qe", Value(dot))
    net.add_output(
        "qe_ready",
        "project_qe",
        Expression("QeObservation(request.request_id)"),
    )

    net.add_transition(Transition("project_vasp"))
    net.add_input("requested", "project_vasp", Test(Variable("request")))
    net.add_input("vasp_permit", "project_vasp", Value(dot))
    net.add_output(
        "vasp_ready",
        "project_vasp",
        Expression("VaspObservation(request.request_id)"),
    )

    net.add_transition(
        Transition(
            "compare",
            Expression(
                "qe_observation.request_id == vasp_observation.request_id"
            ),
        )
    )
    net.add_input("qe_ready", "compare", Variable("qe_observation"))
    net.add_input("vasp_ready", "compare", Variable("vasp_observation"))
    net.add_output(
        "comparison_ready",
        "compare",
        Expression("ScfComparison(qe_observation.request_id)"),
    )
    return net


class CoreColoredNetTest(unittest.TestCase):
    def test_expression_substitution_preserves_constants(self) -> None:
        expression = Expression("request_id == 'run-1'")

        expression.substitute(Substitution(request_id="candidate_id"))

        self.assertEqual(str(expression), "(candidate_id == 'run-1')")

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

                self.assertIn(
                    ScfRequest("run-1"),
                    net.place("requested"),
                )
                self.assertIn(
                    ScfComparison("run-1"),
                    net.place("comparison_ready"),
                )
                self.assertTrue(net.place("qe_ready").is_empty())
                self.assertTrue(net.place("vasp_ready").is_empty())


if __name__ == "__main__":
    unittest.main()
