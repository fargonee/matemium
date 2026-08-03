from canvas import CanvasScene
from canvas.builder import CanvasBuilder

class TraceScene(CanvasScene):
    def _focus_on_element(self, elem):
        is_tape = elem.id in getattr(self, "_tape_content_ids", set())
        owning_tape = self._element_tape_map.get(elem.id)
        active_tape = owning_tape or getattr(self, "_active_scroll_tape", None) or getattr(self, "root_tape", None)
        with open("/home/ruhiddin/Documents/PROJECTS/math/focus_trace.log", "a") as f:
            f.write(f"FOCUS TRACE: id={elem.id}, type={elem.type}, is_tape={is_tape}, owning={getattr(owning_tape, 'id', None)}, active={getattr(active_tape, 'id', None)}\n")
        super()._focus_on_element(elem)

    def __init__(self, **kwargs):
        b = CanvasBuilder(title="CacheBust")
        tape = b.add_tape("main")
        tape.add_heading("Tape A")
        tape_b = b.add_tape("tape_b")
        tape_b.add_heading("Tape B")
        super().__init__(dsl=b.build(), **kwargs)
