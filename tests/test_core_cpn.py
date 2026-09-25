"""Project Koios Python 3.14 regressions for core colored-net behavior."""

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


# Project Koios boundary tokens are immutable and hashable for SNAKES multisets.
@dataclass(frozen=True, slots=True)
class ScfRequest:
    """Identify one calculator-neutral SCF request."""

    request_id: str


@dataclass(frozen=True, slots=True)
class CalculatorExecutionRequest:
    """Identify a calculator effect requested by a pure transition."""

    calculator: str
    request_id: str


@dataclass(frozen=True, slots=True)
class ExternalCalculatorOutput:
    """Represent output supplied by an effect worker outside SNAKES."""

    calculator: str
    request_id: str
    total_energy: float


@dataclass(frozen=True, slots=True)
class QeObservation:
    """Retain a correlated QE observation for the test workflow."""

    request_id: str
    total_energy: float


@dataclass(frozen=True, slots=True)
class VaspObservation:
    """Retain a correlated VASP observation for the test workflow."""

    request_id: str
    total_energy: float


@dataclass(frozen=True, slots=True)
class ScfComparison:
    """Identify a join result without asserting energy equivalence."""

    request_id: str


def build_concurrent_join_net() -> PetriNet:
    """Build concurrent requests, explicit output bindings, and a join."""
    net = PetriNet("concurrent-join")
    net.globals["CalculatorExecutionRequest"] = CalculatorExecutionRequest
    net.globals["QeObservation"] = QeObservation
    net.globals["VaspObservation"] = VaspObservation
    net.globals["ScfComparison"] = ScfComparison
    net.add_place(
        Place("requested", [ScfRequest("run-1")], Instance(ScfRequest))
    )
    net.add_place(Place("qe_permit", [dot]))
    net.add_place(Place("vasp_permit", [dot]))
    net.add_place(
        Place(
            "qe_execution_requested",
            check=Instance(CalculatorExecutionRequest),
        )
    )
    net.add_place(
        Place(
            "vasp_execution_requested",
            check=Instance(CalculatorExecutionRequest),
        )
    )
    net.add_place(
        Place("external_outputs", check=Instance(ExternalCalculatorOutput))
    )
    net.add_place(Place("qe_ready", check=Instance(QeObservation)))
    net.add_place(Place("vasp_ready", check=Instance(VaspObservation)))
    net.add_place(
        Place("comparison_ready", check=Instance(ScfComparison))
    )

    # Pure projection transitions emit requests but perform no calculator work.
    net.add_transition(Transition("project_qe"))
    net.add_input("requested", "project_qe", Test(Variable("request")))
    net.add_input("qe_permit", "project_qe", Value(dot))
    net.add_output(
        "qe_execution_requested",
        "project_qe",
        Expression("CalculatorExecutionRequest('qe', request.request_id)"),
    )

    net.add_transition(Transition("project_vasp"))
    net.add_input("requested", "project_vasp", Test(Variable("request")))
    net.add_input("vasp_permit", "project_vasp", Value(dot))
    net.add_output(
        "vasp_execution_requested",
        "project_vasp",
        Expression("CalculatorExecutionRequest('vasp', request.request_id)"),
    )

    # Recording transitions bind only matching externally supplied outputs.
    net.add_transition(
        Transition(
            "record_qe_external_output",
            Expression(
                "execution_request.calculator == 'qe' and "
                "external_output.calculator == 'qe' and "
                "execution_request.request_id == external_output.request_id"
            ),
        )
    )
    net.add_input(
        "qe_execution_requested",
        "record_qe_external_output",
        Variable("execution_request"),
    )
    net.add_input(
        "external_outputs",
        "record_qe_external_output",
        Variable("external_output"),
    )
    net.add_output(
        "qe_ready",
        "record_qe_external_output",
        Expression(
            "QeObservation(external_output.request_id, "
            "external_output.total_energy)"
        ),
    )

    net.add_transition(
        Transition(
            "record_vasp_external_output",
            Expression(
                "execution_request.calculator == 'vasp' and "
                "external_output.calculator == 'vasp' and "
                "execution_request.request_id == external_output.request_id"
            ),
        )
    )
    net.add_input(
        "vasp_execution_requested",
        "record_vasp_external_output",
        Variable("execution_request"),
    )
    net.add_input(
        "external_outputs",
        "record_vasp_external_output",
        Variable("external_output"),
    )
    net.add_output(
        "vasp_ready",
        "record_vasp_external_output",
        Expression(
            "VaspObservation(external_output.request_id, "
            "external_output.total_energy)"
        ),
    )

    # The join compares identities only; scientific energy comparison is separate.
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
        """Keep literal values while names are substituted on Python 3.14."""
        expression = Expression("request_id == 'run-1'")

        expression.substitute(Substitution(request_id="candidate_id"))

        self.assertEqual(str(expression), "(candidate_id == 'run-1')")

    def test_external_outputs_are_correlated_before_joining(self) -> None:
        """Require matching effect outputs before enabling the observation join."""
        for branch_order in (
            ("project_qe", "project_vasp"),
            ("project_vasp", "project_qe"),
        ):
            with self.subTest(branch_order=branch_order):
                net = build_concurrent_join_net()

                for transition_name in branch_order:
                    transition = net.transition(transition_name)
                    self.assertEqual(len(transition.modes()), 1)
                    transition.fire(transition.modes()[0])

                self.assertEqual(
                    net.transition("record_qe_external_output").modes(),
                    [],
                )
                self.assertEqual(
                    net.transition("record_vasp_external_output").modes(),
                    [],
                )
                self.assertEqual(net.transition("compare").modes(), [])

                unmatched_output = ExternalCalculatorOutput(
                    "qe",
                    "other-run",
                    -1.0,
                )
                net.place("external_outputs").add(unmatched_output)
                self.assertEqual(
                    net.transition("record_qe_external_output").modes(),
                    [],
                )

                net.place("external_outputs").add(
                    ExternalCalculatorOutput("vasp", "run-1", -10.84)
                )
                net.place("external_outputs").add(
                    ExternalCalculatorOutput("qe", "run-1", -22.84)
                )

                for transition_name in (
                    "record_vasp_external_output",
                    "record_qe_external_output",
                ):
                    transition = net.transition(transition_name)
                    self.assertEqual(len(transition.modes()), 1)
                    transition.fire(transition.modes()[0])

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
                self.assertIn(unmatched_output, net.place("external_outputs"))
                self.assertTrue(
                    net.place("qe_execution_requested").is_empty()
                )
                self.assertTrue(
                    net.place("vasp_execution_requested").is_empty()
                )
                self.assertTrue(net.place("qe_ready").is_empty())
                self.assertTrue(net.place("vasp_ready").is_empty())


if __name__ == "__main__":
    unittest.main()
