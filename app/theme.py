"""Stylesheet aplikasi: panel instrumen terang, garis tipis, sudut tegas."""

from .config import (ACCENT, ACCENT_DARK, AMBER, BG, BORDER, CARD, CARD_ALT,
                     GREEN, INK, MONO, MUTED, RED, SURFACE, TEXT)

QSS = f"""
QMainWindow {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-family: 'Segoe UI', sans-serif; font-size: 12px; }}
QLabel {{ background: transparent; }}

/* ---------- header ---------- */
QFrame#Header {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; }}
QLabel#Logo {{
    background: {INK}; color: {SURFACE}; border-radius: 0;
    font-family: '{MONO}'; font-size: 14px; font-weight: 700;
}}
QLabel#AppTitle {{ font-size: 15px; font-weight: 700; color: {INK}; }}
QLabel#AppSub {{ font-size: 11px; color: {MUTED}; }}
QLabel#GroupTag {{
    background: transparent; border: 1px solid {INK}; border-radius: 0;
    color: {INK}; font-size: 10px; font-weight: 700; padding: 2px 7px;
}}
QLabel#GroupNames {{ font-size: 10px; color: {MUTED}; font-weight: 600; }}

QFrame#Pill {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 0; }}
QLabel#PillDot {{ font-size: 11px; }}
QLabel#PillText {{ color: {TEXT}; font-family: '{MONO}'; font-size: 10px; }}

/* ---------- strip pembacaan utama ---------- */
QFrame#ReadoutBar {{ background: {CARD}; border-bottom: 1px solid {BORDER}; }}
QFrame#ReadoutCell {{ border-right: 1px solid {BORDER}; }}
QLabel#ReadoutTitle {{ font-size: 9px; font-weight: 700; color: {MUTED}; }}
QLabel#ReadoutValue {{ font-family: '{MONO}'; font-size: 24px; font-weight: 700; color: {INK}; }}
QLabel#ReadoutValueSmall {{ font-family: '{MONO}'; font-size: 17px; font-weight: 700; color: {INK}; }}
QLabel#ReadoutUnit {{ font-family: '{MONO}'; font-size: 11px; color: {MUTED}; }}
QLabel#StatusChip {{
    font-family: '{MONO}'; font-size: 11px; font-weight: 700;
    padding: 4px 8px; border: 1px solid {BORDER}; color: {MUTED};
}}

/* ---------- panel / kartu ---------- */
QFrame#Card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 0; }}
QFrame#CardRule {{ background: {INK}; max-height: 1px; min-height: 1px; border: none; }}
QLabel#CardTitle {{ font-size: 10px; font-weight: 700; color: {INK}; }}
QLabel#CardSub {{ font-size: 10px; color: {MUTED}; }}
QLabel#ParamLabel {{ font-size: 11px; color: {TEXT}; font-weight: 600; }}
QLabel#EventLabel {{ font-size: 11px; color: {MUTED}; }}

/* seksi lipat (tingkat ketiga) */
QPushButton#SectionHead {{
    background: transparent; border: none; border-top: 1px solid {BORDER};
    border-radius: 0; padding: 7px 0 5px 0; text-align: left;
    font-size: 10px; font-weight: 700; color: {MUTED};
}}
QPushButton#SectionHead:hover {{ color: {INK}; }}
QPushButton#SectionHead:checked {{ color: {INK}; }}

/* ---------- input ---------- */
QDoubleSpinBox, QLineEdit, QComboBox {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 0;
    padding: 3px 6px; min-height: 20px; color: {TEXT};
}}
QDoubleSpinBox {{ font-family: '{MONO}'; font-size: 11px; }}
QDoubleSpinBox:focus, QLineEdit:focus, QComboBox:focus {{ border: 1px solid {INK}; }}
QDoubleSpinBox:disabled, QLineEdit:disabled, QComboBox:disabled {{
    color: #A3A7AB; background: {CARD_ALT};
}}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 14px; border: none; background: transparent; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {CARD}; border: 1px solid {INK}; selection-background-color: {CARD_ALT};
    selection-color: {INK};
}}

QSlider::groove:horizontal {{ height: 2px; background: {BORDER}; }}
QSlider::sub-page:horizontal {{ background: {INK}; }}
QSlider::handle:horizontal {{
    background: {INK}; width: 8px; height: 14px; margin: -6px 0; border-radius: 0;
}}
QSlider::handle:horizontal:hover {{ background: {ACCENT}; }}
QSlider::sub-page:horizontal:disabled {{ background: {BORDER}; }}
QSlider::handle:horizontal:disabled {{ background: #B9BCB6; }}

QCheckBox {{ spacing: 7px; }}
QCheckBox::indicator {{ width: 12px; height: 12px; border: 1px solid {INK}; background: {CARD}; }}
QCheckBox::indicator:checked {{ background: {INK}; }}
QCheckBox::indicator:disabled {{ border-color: {BORDER}; }}

QProgressBar {{
    background: {CARD_ALT}; border: 1px solid {BORDER}; border-radius: 0;
    font-family: '{MONO}'; font-size: 10px; color: {INK}; text-align: center;
}}
QProgressBar::chunk {{ background: #F2B48F; }}

/* ---------- tombol ---------- */
QPushButton {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 0;
    padding: 6px 10px; color: {TEXT}; font-weight: 600; font-size: 11px;
}}
QPushButton:hover {{ border: 1px solid {INK}; }}
QPushButton:pressed {{ background: {CARD_ALT}; }}
QPushButton#Primary {{ background: {INK}; border: 1px solid {INK}; color: {CARD}; }}
QPushButton#Primary:hover {{ background: {ACCENT}; border-color: {ACCENT}; }}
QPushButton#Hero {{
    background: {ACCENT}; border: 1px solid {ACCENT_DARK}; color: #FFFFFF;
    font-size: 13px; font-weight: 700; padding: 10px 12px;
}}
QPushButton#Hero:hover {{ background: {ACCENT_DARK}; }}
QPushButton#Danger {{ background: {CARD}; border: 1px solid {RED}; color: {RED}; }}
QPushButton#Danger:hover {{ background: {RED}; color: #FFFFFF; }}
QPushButton#HeroStop {{
    background: {RED}; border: 1px solid #8F1D1D; color: #FFFFFF;
    font-size: 13px; font-weight: 700; padding: 10px 12px;
}}
QPushButton#Warning {{ background: {CARD}; border: 1px solid {ACCENT}; color: {ACCENT_DARK}; }}
QPushButton#Warning:hover {{ background: {ACCENT}; color: #FFFFFF; }}
QPushButton#Lock {{
    background: transparent; border: 1px solid {BORDER}; padding: 2px 6px;
    font-family: '{MONO}'; font-size: 10px; font-weight: 700;
}}
QPushButton#Lock:checked {{ background: {AMBER}; border-color: {AMBER}; color: #FFFFFF; }}
QPushButton:disabled, QPushButton#Primary:disabled, QPushButton#Danger:disabled,
QPushButton#Warning:disabled, QPushButton#Hero:disabled {{
    background: {CARD_ALT}; border: 1px solid {BORDER}; color: #A3A7AB;
}}
QToolTip {{
    background: {INK}; color: {SURFACE}; border: none;
    padding: 5px 7px; font-size: 11px;
}}

/* ---------- scroll & splitter ---------- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #BFC2BC; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; }}
QScrollBar::handle:horizontal {{ background: #BFC2BC; min-width: 28px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QSplitter::handle {{ background: {BG}; }}
QSplitter::handle:horizontal {{ width: 8px; }}
QSplitter::handle:vertical {{ height: 8px; }}

/* ---------- tab: garis bawah, bukan kotak membulat ---------- */
QTabWidget::pane {{ border: none; border-top: 1px solid {BORDER}; background: {CARD}; top: -1px; }}
QTabBar::tab {{
    background: transparent; border: none; border-bottom: 2px solid transparent;
    padding: 6px 12px; margin-right: 2px; color: {MUTED}; font-weight: 600; font-size: 11px;
}}
QTabBar::tab:selected {{ color: {INK}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {INK}; }}

QTableWidget {{
    background: {CARD}; alternate-background-color: {CARD_ALT};
    border: 1px solid {BORDER}; border-radius: 0;
    gridline-color: {BORDER}; color: {TEXT}; font-family: '{MONO}'; font-size: 10px;
}}
QTableWidget::item {{ padding: 3px 4px; }}
QHeaderView::section {{
    background: {CARD}; color: {INK}; border: none;
    border-bottom: 1px solid {INK};
    padding: 4px 6px; font-size: 9px; font-weight: 700;
}}
QTableCornerButton::section {{ background: {CARD}; border: none; }}

QMessageBox {{ background: {CARD}; }}
QFileDialog {{ background: {CARD}; }}
"""

STATUS_COLORS = {"ok": GREEN, "warn": AMBER, "bad": RED, "idle": MUTED, "accent": ACCENT}
