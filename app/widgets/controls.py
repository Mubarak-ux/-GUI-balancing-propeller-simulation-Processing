"""Widget kontrol: slider, kartu, dan metrik."""

from PySide6 import QtCore, QtGui, QtWidgets

from ..config import ACCENT, BORDER, CARD_ALT

Qt = QtCore.Qt


# ----------------------------------------------------------------------------
# WIDGET SLIDER + SPINBOX
# ----------------------------------------------------------------------------
class Param(QtWidgets.QWidget):
    changed = QtCore.Signal(float)

    def __init__(self, name, lo, hi, val, step, unit="", dec=2):
        super().__init__()
        self.k = 10 ** dec
        self.default = val
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lab = QtWidgets.QLabel(name)
        lab.setObjectName("ParamLabel")
        lab.setMinimumWidth(84)

        self.sl = QtWidgets.QSlider(Qt.Horizontal)
        self.sl.setRange(round(lo * self.k), round(hi * self.k))
        self.sl.setValue(round(val * self.k))
        self.sl.setMinimumHeight(18)

        self.sb = QtWidgets.QDoubleSpinBox()
        self.sb.setRange(lo, hi)
        self.sb.setDecimals(dec)
        self.sb.setSingleStep(step)
        self.sb.setValue(val)
        self.sb.setSuffix(" " + unit if unit else "")
        self.sb.setFixedWidth(96)
        self.sb.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lay.addWidget(lab)
        lay.addWidget(self.sl, 1)
        lay.addWidget(self.sb)

        self.sl.valueChanged.connect(self._from_slider)
        self.sb.valueChanged.connect(self._from_spin)

    def _from_slider(self, v):
        self.sb.blockSignals(True)
        self.sb.setValue(v / self.k)
        self.sb.blockSignals(False)
        self.changed.emit(self.sb.value())

    def _from_spin(self, v):
        self.sl.blockSignals(True)
        self.sl.setValue(round(v * self.k))
        self.sl.blockSignals(False)
        self.changed.emit(v)

    def value(self):
        return self.sb.value()

    def set_value(self, v):
        self.sb.setValue(v)

    def set_value_silent(self, v):
        """Ubah nilai tampilan tanpa memancarkan sinyal ``changed``."""
        self.sb.blockSignals(True)
        self.sl.blockSignals(True)
        self.sb.setValue(v)
        self.sl.setValue(round(self.sb.value() * self.k))
        self.sl.blockSignals(False)
        self.sb.blockSignals(False)


# ----------------------------------------------------------------------------
# KOMPONEN KARTU
# ----------------------------------------------------------------------------
class Card(QtWidgets.QFrame):
    def __init__(self, title, subtitle=None, accent=ACCENT):
        super().__init__()
        self.setObjectName("Card")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(14, 11, 14, 13)
        outer.setSpacing(9)

        head = QtWidgets.QHBoxLayout()
        head.setSpacing(8)
        bar = QtWidgets.QFrame()
        bar.setFixedSize(3, 12)
        bar.setStyleSheet(f"background:{accent}; border-radius:1px;")
        head.addWidget(bar)
        lab = QtWidgets.QLabel(title.upper())
        lab.setObjectName("CardTitle")
        f = lab.font()
        f.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 1.0)
        lab.setFont(f)
        head.addWidget(lab)
        head.addStretch(1)
        if subtitle:
            sub = QtWidgets.QLabel(subtitle)
            sub.setObjectName("CardSub")
            head.addWidget(sub)
        outer.addLayout(head)

        self.body = QtWidgets.QVBoxLayout()
        self.body.setSpacing(9)
        outer.addLayout(self.body)


class Metric(QtWidgets.QFrame):
    def __init__(self, title, accent=ACCENT, tooltip=None):
        super().__init__()
        self.setObjectName("Card")
        if tooltip:
            self.setToolTip(tooltip)
        self.setStyleSheet(f"QFrame#Card {{ background:{CARD_ALT}; border:1px solid {BORDER};"
                           f" border-radius:8px; }}")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(11, 7, 11, 8)
        lay.setSpacing(1)
        t = QtWidgets.QLabel(title.upper())
        t.setObjectName("CardTitle")
        t.setStyleSheet("font-size:9px; font-weight:700; color:#727f8f;")
        self.val = QtWidgets.QLabel("\u2014")
        self.val.setStyleSheet(
            f"font-family:'Consolas'; font-size:16px; font-weight:700; color:{accent};")
        lay.addWidget(t)
        lay.addWidget(self.val)

    def set(self, text):
        self.val.setText(text)
