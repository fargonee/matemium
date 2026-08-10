# Third-party notices

Matemium includes and links against third-party software. Those components are
licensed by their respective authors under their own terms; the Matemium
Source-Available License does not replace those licenses.

Principal bundled components include:

| Component | License | Project |
| --- | --- | --- |
| Manim Community Edition | MIT | https://www.manim.community/ |
| Python and its standard library | PSF License | https://www.python.org/ |
| PyInstaller bootloader | GPL-2.0-or-later with bootloader exception | https://pyinstaller.org/ |
| Tauri | Apache-2.0 OR MIT | https://tauri.app/ |
| React | MIT | https://react.dev/ |
| Monaco Editor | MIT | https://microsoft.github.io/monaco-editor/ |
| KaTeX | MIT | https://katex.org/ |
| NumPy | BSD-3-Clause | https://numpy.org/ |
| SciPy | BSD-3-Clause | https://scipy.org/ |
| Pillow | HPND | https://python-pillow.org/ |

The application also contains transitive Rust, Python, and JavaScript
dependencies recorded in `desktop/src-tauri/Cargo.lock`, the Python package
metadata, and `desktop/app/package-lock.json`. Their copyright and license
notices remain in force.

FFmpeg and a LaTeX distribution are host prerequisites for rendering and are
not bundled in the launch installers. Local AI model files are optional user
downloads and remain subject to the license shown by their model publisher.

