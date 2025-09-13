from PyQt6.QtCore import QObject, QEvent
from PyQt6.QtWidgets import QApplication, QComboBox, QSpinBox

_guard_installed = False


class _GlobalWheelGuard(QObject):
    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.Type.Wheel and isinstance(
                obj, (QComboBox, QSpinBox)
            ):
                if not obj.hasFocus():
                    return True
        except Exception:
            pass
        return super().eventFilter(obj, event)


def install_global_wheel_guard():
    global _guard_installed
    if _guard_installed:
        return
    app = QApplication.instance()
    if not app:
        return
    guard = _GlobalWheelGuard(app)
    app.installEventFilter(guard)
    _guard_installed = True
