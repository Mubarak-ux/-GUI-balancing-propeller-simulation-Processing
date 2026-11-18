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

    def set_locked(self, locked):
        """Kunci/buka input: slider & spinbox dinonaktifkan, label tetap jelas."""
        self.sl.setEnabled(not locked)
        self.sb.setEnabled(not locked)


# ----------------------------------------------------------------------------
# KOMPONEN KARTU
# ----------------------------------------------------------------------------
class Card(QtWidgets.QFrame):
    """Panel putih bersudut tegas. Judul huruf kapital + garis tinta tipis
    di bawahnya (tingkat hierarki: judul panel)."""

    def __init__(self, title, subtitle=None, accent=None):
        super().__init__()
        self.setObjectName("Card")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 12)
        outer.setSpacing(8)

        head = QtWidgets.QHBoxLayout()
        head.setSpacing(8)
        lab = QtWidgets.QLabel(title.upper())
        lab.setObjectName("CardTitle")
        f = lab.font()
        f.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 1.2)
        lab.setFont(f)
        head.addWidget(lab)
        head.addStretch(1)
        if subtitle:
            sub = QtWidgets.QLabel(subtitle)
            sub.setObjectName("CardSub")
            head.addWidget(sub)
        self.head = head          # akses header dari luar (mis. tombol gembok)
        outer.addLayout(head)
        rule = QtWidgets.QFrame()
        rule.setObjectName("CardRule")
        outer.addWidget(rule)

        self.body = QtWidgets.QVBoxLayout()
        self.body.setSpacing(8)
        outer.addLayout(self.body)


class Section(QtWidgets.QWidget):
    """Seksi lipat untuk pengaturan tingkat ketiga (jarang diubah).
    Isi diletakkan di ``self.grid`` (QGridLayout, 4 kolom)."""

    def __init__(self, title, expanded=False):
        super().__init__()
        self._title = title.upper()
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 0)
        lay.setSpacing(4)
        self.btn = QtWidgets.QPushButton()
        self.btn.setObjectName("SectionHead")
        self.btn.setCheckable(True)
        self.btn.setChecked(expanded)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.toggled.connect(self._toggle)
        lay.addWidget(self.btn)
        self.content = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(self.content)
        self.grid.setContentsMargins(0, 0, 0, 6)
        self.grid.setHorizontalSpacing(6)
        self.grid.setVerticalSpacing(6)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(3, 1)
        lay.addWidget(self.content)
        self._toggle(expanded)

    def _toggle(self, on):
        self.content.setVisible(on)
        self.btn.setText(("▾  " if on else "▸  ") + self._title)

    def add(self, widget, row, col=0, rowspan=1, colspan=4):
        self.grid.addWidget(widget, row, col, rowspan, colspan)


class Readout(QtWidgets.QFrame):
    """Satu sel pembacaan utama: judul kecil, angka besar monospace, satuan."""

    def __init__(self, title, unit="", small=False, tooltip=None, last=False):
        super().__init__()
        if not last:
            self.setObjectName("ReadoutCell")
        if tooltip:
            self.setToolTip(tooltip)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(14, 7, 14, 8)
        lay.setSpacing(0)
        t = QtWidgets.QLabel(title.upper())
        t.setObjectName("ReadoutTitle")
        f = t.font()
        f.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 1.0)
        t.setFont(f)
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(4)
        self.val = QtWidgets.QLabel("—")
        self.val.setObjectName("ReadoutValueSmall" if small else "ReadoutValue")
        u = QtWidgets.QLabel(unit)
        u.setObjectName("ReadoutUnit")
        row.addWidget(self.val)
        row.addWidget(u, 0, Qt.AlignBottom)
        row.addStretch(1)
        lay.addWidget(t)
        lay.addLayout(row)

    def set(self, text, color=None):
        self.val.setText(text)
        self.val.setStyleSheet(f"color:{color};" if color else "")


class Metric(QtWidgets.QFrame):
    """Tile metrik respons: judul kecil + nilai monospace, tanpa kotak membulat."""

    def __init__(self, title, accent=None, tooltip=None):
        super().__init__()
        if tooltip:
            self.setToolTip(tooltip)
        self.setStyleSheet(f"QFrame {{ background:{CARD_ALT}; border:none;"
                           f" border-left:2px solid {BORDER}; }}")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(9, 5, 9, 6)
        lay.setSpacing(0)
        t = QtWidgets.QLabel(title.upper())
        t.setStyleSheet("border:none; font-size:9px; font-weight:700; color:#6A6F75;")
        self.val = QtWidgets.QLabel("—")
        self.val.setStyleSheet("border:none; font-family:'Consolas'; font-size:15px;"
                               " font-weight:700; color:#16191D;")
        lay.addWidget(t)
        lay.addWidget(self.val)

    def set(self, text):
        self.val.setText(text)
