import os

from PySide6.QtWidgets import QApplication

from noite.mascot import MascotFace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_mascot_face_exposes_activity_states():
    app = QApplication.instance() or QApplication([])
    face = MascotFace()
    for state in ("idle", "thinking", "working", "done", "error"):
        face.set_state(state)
        assert face.state == state
    face.resize(132, 132)
    face.show()
    app.processEvents()
    assert face.size().width() == 132
    face.close()
