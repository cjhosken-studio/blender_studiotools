import sys
import bpy # type: ignore

_qt = False

try:
    import PySide6
    _qt = True
except:
    pass


_qt_app = None
_timer = None

def process_qt_events():
    global _qt_app
    if _qt_app:
        _qt_app.processEvents()

    return 0.01  # Run every 10ms

def register():
    global _qt, _qt_app, _timer

    if _qt:
        from PySide6.QtWidgets import QApplication

        if QApplication.instance():
            _qt_app = QApplication.instance()
        else:
            _qt_app = QApplication(sys.argv)

        _timer = bpy.app.timers.register(process_qt_events, persistent=True)

def unregister():
    global _qt_app, _timer

    if _qt:
        if _timer is not None:
            bpy.app.timers.unregister(_timer)
            _timer = None

        if _qt_app is not None:
            _qt_app.quit()
            _qt_app = None