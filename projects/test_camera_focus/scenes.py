from canvas import CanvasScene
from canvas.builder import CanvasBuilder

class FocusTest(CanvasScene):
    def __init__(self, **kwargs):
        b = CanvasBuilder(title="Focus")
        tape = b.add_tape("main")
        tape.add_heading("Tape A")
        
        tb = b.add_tape("tape_b", position=(15, 10, -5), rotation=(45, 60, 30))
        with b.in_object_space(tb):
            tape.add_heading("Tape B")
            tape.add_body("Is camera here?")
            
        super().__init__(dsl=b.build(), **kwargs)

if __name__ == "__main__":
    import os
    os.system("python -m matemium render test_camera_focus --quality preview")
