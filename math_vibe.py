from pathlib import Path
import sys

from manim import BLUE, Circle, DOWN, GREEN, LEFT, ORANGE, RIGHT, Scene, Square, Text, UP, VGroup


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from matemium.tape import SolutionTape


class MathVibeTapeShowcase(Scene):
    def construct(self):
        tape = SolutionTape(
            scene=self,
            difficulty="medium",
            theme="matemium_dark",
            viewport="reel",
        )

        tape.add_problem(
            r"How many distinct prime bases appear in 7^3 + 14^3 + 21^3?",
            subtitle="Rewrite, factor, and read the prime structure.",
            tag="Number Theory",
        )
        tape.add_observation("All three terms are multiples of 7, so a common factor is waiting.")
        tape.add_text(
            "A good first move is to expose the hidden 7 inside 14 and 21.",
            label="Plan",
            anchor="plan",
        )
        tape.add_math(
            r"7^3 + 14^3 + 21^3",
            label="Given",
            anchor="given_expression",
        )
        tape.underline("given_expression")
        tape.add_step(
            "Rewrite the larger terms",
            content="Replace 14 with 7 \\cdot 2 and 21 with 7 \\cdot 3.",
            math=r"7^3 + (7 \cdot 2)^3 + (7 \cdot 3)^3",
            anchor="rewritten_terms",
        )
        tape.callback_to(
            "plan",
            message="This plan is exactly what we are applying now.",
        )
        tape.add_math(
            r"7^3 + 7^3 \cdot 2^3 + 7^3 \cdot 3^3",
            reason="(ab)^3 = a^3 b^3",
            anchor="expanded_powers",
        )
        tape.box("expanded_powers")
        tape.add_note(
            "Now the repeated factor is explicit, so the expression is easier to compress.",
            tone="insight",
        )
        tape.add_math(
            r"7^3 \left(1 + 2^3 + 3^3\right)",
            reason="factor out the common 7^3",
            anchor="factored_once",
        )
        tape.flash("factored_once")
        tape.focus_card("factored_once", caption="This factorization is the structural turning point.")
        tape.capture_state("after_factoring_out_7")

        tape.add_math(
            r"7^3 \left(1 + 8 + 27\right)",
            reason="evaluate the small powers",
        )
        tape.add_math(
            r"7^3 \cdot 36",
            reason="add inside the parentheses",
            anchor="before_prime_factorization",
        )
        tape.dim_except("before_prime_factorization")
        tape.add_concept(
            "Prime-base reading rule",
            "Once the expression is written as a product of prime powers, the distinct bases are visible immediately.",
            formula=r"36 = 2^2 \cdot 3^2",
            anchor="prime_rule",
        )
        tape.callback_to(
            "prime_rule",
            message="This tells us what to do with 36 next.",
        )
        tape.add_math(
            r"7^3 \cdot 2^2 \cdot 3^2",
            reason="prime factorize 36",
            anchor="prime_factorized",
        )

        icon = VGroup(
            Circle(radius=0.22, color=BLUE),
            Square(side_length=0.3, color=GREEN).shift(LEFT * 0.45),
            Square(side_length=0.3, color=ORANGE).shift(RIGHT * 0.45),
        )
        tape.add_mobject(icon, row_type="diagram", anchor="prime_icon")
        tape.add_check(
            text="The only prime bases now showing are 2, 3, and 7.",
            math=r"\{2,3,7\}",
            anchor="prime_set",
        )
        tape.highlight("prime_set", label="No new prime base appears beyond these three.", style="glow")
        tape.capture_state("before_conclusion")

        tape.add_conclusion(
            "So the number of distinct prime bases is",
            math=r"3",
        )

        mini_state = tape.freeze_state("after_factoring_out_7").scale(0.18).to_corner(UP + RIGHT)
        mini_rows = tape.freeze_rows(["given_expression", "factored_once", "answer"]).scale(0.22).to_corner(UP + LEFT)
        self.add(mini_state, mini_rows)

        tape.scroll_to("given_expression")
        tape.scroll_by(-1.0)
        tape.return_to_current()

        current_view = tape.freeze_current_view().scale(0.17).to_corner(DOWN + LEFT)
        full_tape = tape.freeze_full_tape().scale(0.12).to_corner(DOWN + RIGHT)
        self.add(current_view, full_tape)

        tape.reveal_full_tape(emphasize_anchors=["factored_once", "prime_factorized", "answer"])


class MathVibeTapeReplay(Scene):
    def construct(self):
        tape = SolutionTape(
            scene=self,
            difficulty="easy",
            theme="matemium_dark",
            viewport="reel",
            animate_by_default=False,
        )

        tape.add_problem(
            r"Solve: x^2 - 5x + 6 = 0",
            tag="Replay Test",
        )
        tape.add_observation("We look for a product form first.")
        tape.add_math(r"x^2 - 5x + 6", anchor="original")
        tape.add_note("Two numbers must multiply to 6 and add to -5.", tone="hint")
        tape.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)", anchor="factored")
        tape.highlight("factored", label="This is the key algebraic move.", style="box")
        tape.capture_state("after_factoring")
        tape.add_math(r"(x-2)(x-3)=0")
        tape.add_concept(
            "Zero-product idea",
            "If a product is zero, at least one factor is zero.",
            formula=r"ab=0 \Rightarrow a=0 \text{ or } b=0",
        )
        tape.add_conclusion("The solutions are", math=r"x=2 \quad \text{or} \quad x=3")

        tape.restore_state("after_factoring")
        tape.replay_from("after_factoring")
