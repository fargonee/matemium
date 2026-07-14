from canvas import CanvasScene
from canvas.builder import CanvasBuilder

class ArbitraryTapesTest(CanvasScene):
    def __init__(self, **kwargs):
        b = CanvasBuilder(title="Arbitrary")
                
        tape_a = b.add_tape("tape_a")
        tape_a.add_heading("Tape A") 
        
        tape_b = b.add_tape("tape_b")

        tape_a.add_body("This is tape A at origin") 

        tape_b.add_heading("Tape B")
        tape_b.add_body("This is tape B at weird angle")
        
        super().__init__(dsl=b.build(), **kwargs)

if __name__ == "__main__":
    import os
    os.system("python -m matemium render test_arbitrary_tapes --quality preview")
