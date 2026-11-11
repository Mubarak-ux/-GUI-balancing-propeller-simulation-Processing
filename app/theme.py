"""Stylesheet aplikasi."""

from .config import (ACCENT, ACCENT_DARK, BG, CARD, CARD_ALT, BORDER, MUTED,
                     SURFACE, TEXT)

QSS = f"""
QMainWindow {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 12px; }}
QLabel {{ background: transparent; }}

QFrame#Header {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; }}
QLabel#Logo {{
    background: {ACCENT}; color: #ffffff; border-radius: 8px;
    font-size: 15px; font-weight: 800;
}}
QLabel#AppTitle {{ font-size: 15px; font-weight: 700; color: #1B2430; }}
QLabel#AppSub {{ font-size: 11px; color: {MUTED}; }}
QLabel#GroupTag {{
    background: #E9F0FE; border: 1px solid #C5D8FD; border-radius: 7px;
    color: {ACCENT_DARK}; font-size: 10px; font-weight: 700; padding: 3px 9px;
}}
QLabel#GroupNames {{
    font-family: 'Segoe UI', sans-serif; font-size: 10px;
    color: #46505E; font-weight: 600;
}}

QFrame#Pill {{ background: #E9F0FE; border: 1px solid #C5D8FD; border-radius: 14px; }}
QLabel#PillDot {{ color: {ACCENT}; font-size: 12px; }}
QLabel#PillText {{ color: {ACCENT_DARK}; font-size: 10px; font-weight: 700; }}

QFrame#Card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; }}
QLabel#CardTitle {{ font-size: 10px; font-weight: 700; color: {MUTED}; }}
QLabel#CardSub {{ font-size: 10px; color: #98A2B3; }}
QLabel#ParamLabel {{ font-size: 11px; color: #46505E; font-weight: 600; }}
QLabel#EventLabel {{ font-size: 11px; color: {MUTED}; }}

QDoubleSpinBox {{
    background: #FBFCFE; border: 1px solid #D5DCE5; border-radius: 6px;
    padding: 3px 6px; min-height: 20px; color: {TEXT};
    font-family: 'Consolas', monospace; font-size: 11px;
}}
QDoubleSpinBox:focus {{ border-color: {ACCENT}; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 14px; border: none; background: transparent; }}

QSlider::groove:horizontal {{ height: 3px; background: #DCE2EA; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {ACCENT}; width: 12px; height: 12px; margin: -5px 0;
    border-radius: 7px; border: 2px solid {CARD};
}}
QSlider::handle:horizontal:hover {{ background: {ACCENT_DARK}; }}

QPushButton {{
    background: #EEF1F5; border: 1px solid #D5DCE5; border-radius: 7px;
    padding: 7px 11px; color: #374151; font-weight: 600; font-size: 11px;
}}
QPushButton:hover {{ background: #E4E9F0; border-color: #C3CBD6; }}
QPushButton:pressed {{ background: #DDE3EB; }}
QPushButton#Primary {{ background: {ACCENT}; border-color: {ACCENT_DARK}; color: #ffffff; }}
QPushButton#Primary:hover {{ background: {ACCENT_DARK}; }}
QPushButton#Danger {{ background: #FDECEC; border-color: #F3C2C0; color: #B42318; }}
QPushButton#Danger:hover {{ background: #FBDCDC; }}
QPushButton#Warning {{ background: #E9F0FE; border-color: #C5D8FD; color: {ACCENT_DARK}; }}
QPushButton#Warning:hover {{ background: #DCE8FD; }}
QPushButton#Lock {{
    background: transparent; border: 1px solid #D5DCE5; border-radius: 6px;
    padding: 2px 4px; font-size: 13px;
}}
QPushButton#Lock:hover {{ background: #EEF1F5; border-color: #C3CBD6; }}
QPushButton#Lock:checked {{
    background: #FFF4D6; border-color: #E9D48A;
}}
QPushButton:disabled, QPushButton#Primary:disabled, QPushButton#Danger:disabled,
QPushButton#Warning:disabled {{
    background: #F1F3F6; border-color: #E1E5EB; color: #A8B0BC;
}}
QToolTip {{
    background: {CARD}; color: {TEXT}; border: 1px solid {BORDER};
    padding: 5px 7px; font-size: 11px;
}}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C9D1DB; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: #AEB8C5; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QSplitter::handle {{ background: {BG}; }}
QSplitter::handle:horizontal {{ width: 10px; }}
QSplitter::handle:vertical {{ height: 10px; }}

QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 8px; top: -1px; background: {CARD}; }}
QTabBar::tab {{
    background: {CARD_ALT}; border: 1px solid {BORDER}; border-bottom: none;
    border-top-left-radius: 7px; border-top-right-radius: 7px;
    padding: 5px 14px; margin-right: 2px; color: {MUTED}; font-weight: 600; font-size: 11px;
}}
QTabBar::tab:selected {{ background: {CARD}; color: {ACCENT_DARK}; }}
QTabBar::tab:hover {{ color: {ACCENT_DARK}; }}

QTableWidget {{
    background: {CARD}; alternate-background-color: {CARD_ALT};
    border: 1px solid {BORDER}; border-radius: 6px;
    gridline-color: {BORDER}; color: {TEXT}; font-size: 10px;
    selection-background-color: #E9F0FE; selection-color: {TEXT};
}}
QTableWidget::item {{ padding: 3px 4px; }}
QHeaderView::section {{
    background: {CARD_ALT}; color: {MUTED}; border: none;
    border-bottom: 1px solid {BORDER}; border-right: 1px solid {BORDER};
    padding: 4px 6px; font-size: 9px; font-weight: 700;
}}
QTableCornerButton::section {{ background: {CARD_ALT}; border: none; }}

QMessageBox {{ background: {CARD}; }}
QFileDialog {{ background: {CARD}; }}
"""
