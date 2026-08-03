from canvas import CanvasScene
from canvas.builder import CanvasBuilder

class FocusTest(CanvasScene):
    def __init__(self, **kwargs):
        b = CanvasBuilder(title="Focus")
        tape = b.add_tape("main")
        tape.add_heading("Tape A")
        
        tape_b = b.add_tape("tape_b")
        tape_b.add_heading("Tape B")
        tape_b.add_body("Is the curtain switch clean?")
            
        super().__init__(dsl=b.build(), **kwargs)

if __name__ == "__main__":
    import os
    os.system("python -m matemium render test_camera_focus --quality preview")
