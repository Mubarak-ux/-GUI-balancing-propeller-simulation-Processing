"""Entry point aplikasi."""

import sys

from PySide6 import QtGui, QtWidgets

from .config import BG, CARD, TEXT
from .main_window import MainWindow
from .theme import QSS


def _light_palette():
    """Palet terang eksplisit agar tidak terpengaruh dark mode OS.

    Style "Fusion" tetap mengambil warna dasar dari QPalette sistem
    (termasuk saat Windows diset dark mode), sehingga widget native
    seperti QTableWidget/QHeaderView bisa tampil gelap walau stylesheet
    kita sudah menata warna lain. Palet ini memaksa semua role warna
    dasar tetap terang.
    """
    pal = QtGui.QPalette()
    pal.setColor(QtGui.QPalette.Window, QtGui.QColor(BG))
    pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(TEXT))
    pal.setColor(QtGui.QPalette.Base, QtGui.QColor(CARD))
    pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(BG))
    pal.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(CARD))
    pal.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(TEXT))
    pal.setColor(QtGui.QPalette.Text, QtGui.QColor(TEXT))
    pal.setColor(QtGui.QPalette.Button, QtGui.QColor(CARD))
    pal.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(TEXT))
    pal.setColor(QtGui.QPalette.BrightText, QtGui.QColor("#ffffff"))
    pal.setColor(QtGui.QPalette.Highlight, QtGui.QColor("#2F6FED"))
    pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#ffffff"))
    pal.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor("#98A2B3"))
    return pal


def run(seed=None, initial_mode="sim"):
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(_light_palette())
    app.setStyleSheet(QSS)
    window = MainWindow(seed=seed, initial_mode=initial_mode)
    window.show_fitted()
    return app.exec()
