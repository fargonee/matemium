from canvas import CanvasScene
from canvas.builder import CanvasBuilder

class TestOverlap(CanvasScene):
    def __init__(self, **kwargs):
        b = CanvasBuilder(title="Test")
        tape = b.add_tape("main")
        
        tape.add_heading("Heading 1")
        tape.add_body("Body 1")
        tape.add_body("Body 2")
        tape.add_body("Body 3")
        
        super().__init__(dsl=b.build(), **kwargs)

if __name__ == "__main__":
    import os
    os.system("python -m matemium render test_layout_overlap --quality preview")
