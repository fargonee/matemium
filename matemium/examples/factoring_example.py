from pathlib import Path
import sys

from manim import RIGHT, UP, Scene


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from matemium.tape import SolutionTape


class FactoringExample(Scene):
    def construct(self):
        tape = SolutionTape(
            scene=self,
            difficulty="easy",
            theme="matemium_dark",
            viewport="reel",
        )

        tape.add_problem(
            r"Solve: x^2 - 5x + 6 = 0",
            tag="Algebra",
        )
        tape.add_observation("This quadratic hides a product structure.")
        tape.add_math(
            r"x^2 - 5x + 6",
            anchor="original_expression",
        )
        tape.add_note(
            "We need two numbers that multiply to 6 and add to -5.",
            tone="hint",
        )
        tape.add_math(
            r"x^2 - 5x + 6 = (x-2)(x-3)",
            reason="because -2 and -3 multiply to 6 and add to -5",
            anchor="factored_form",
        )
        tape.callback_to(
            "original_expression",
            message="Same expression, now in a usable form.",
        )
        tape.add_math(r"(x-2)(x-3)=0")
        tape.add_concept(
            "Zero-product idea",
            "If a product is zero, at least one factor must be zero.",
            formula=r"ab=0 \Rightarrow a=0 \text{ or } b=0",
        )
        tape.capture_state("after_zero_product")
        tape.add_math(r"x-2=0 \quad \text{or} \quad x-3=0")
        tape.add_conclusion(
            "So the solutions are",
            math=r"x=2 \quad \text{or} \quad x=3",
        )
        mini_snapshot = tape.freeze_state("after_zero_product").scale(0.22).to_corner(UP + RIGHT)
        self.add(mini_snapshot)
        tape.reveal_full_tape(emphasize_anchors=["factored_form", "answer"])
