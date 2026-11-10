"""Widget animasi 2D (side view)."""

import math

from PySide6 import QtCore, QtGui, QtWidgets

from ..config import ACCENT, BG, BORDER, GREEN, MUTED, RED

Qt = QtCore.Qt


# ----------------------------------------------------------------------------
# WIDGET ANIMASI 2D (Sesuai Desain Asli Model 3D)
# ----------------------------------------------------------------------------
class BeamView(QtWidgets.QWidget):
    impulse_requested = QtCore.Signal(float)
    FOOTER_H = 60
    LIMIT_DEG = 30.0     # batas mekanik +/-30 deg (sinkron dengan Params.stop)
    BEAM_HALF = 0.27     # m, setengah panjang batang 54 cm (terukur)
    PROP_RADIUS = 0.127  # m, propeler 1045 = 10 inci -> jari-jari 5 inci

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setMinimumHeight(320)
        self.setToolTip("Klik pada sisi kiri atau kanan batang untuk memberi sentakan gangguan (Impuls)!")
        self.th = self.sp = self.F1 = self.F2 = 0.0
        self.m, self.x, self.Fmax, self.L = 0.0, 0.10, 8.0, 0.25
        self.p1r = self.p2r = 0.0

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            # Klik sisi yang ingin dinaikkan. Konvensi: theta+ = kanan naik,
            # jadi klik kiri -> sentak (-) (kiri naik), klik kanan -> (+).
            sgn = -1.0 if ev.position().x() < self.width() / 2 else 1.0
            self.impulse_requested.emit(sgn * 2.5)
        super().mousePressEvent(ev)

    def set_state(self, th, sp, F1, F2, m, x, p1r=0.0, p2r=0.0):
        self.th, self.sp, self.F1, self.F2 = th, sp, F1, F2
        self.m, self.x = m, x
        self.p1r, self.p2r = p1r, p2r
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        W, H = self.width(), self.height()
        Hd = H - self.FOOTER_H

        p.fillRect(self.rect(), QtGui.QColor(BG))

        outer = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QtGui.QPainterPath()
        clip.addRoundedRect(outer, 10, 10)
        p.setClipPath(clip)

        p.fillRect(0, 0, W, Hd, QtGui.QColor("#F3F5F9"))

        # Grid halus
        grid_sz = 35
        p.setPen(QtGui.QPen(QtGui.QColor("#DDE3EC"), 1))
        for x in range(0, W, grid_sz):
            p.drawLine(x, 0, x, Hd)
        for y in range(0, Hd, grid_sz):
            p.drawLine(0, y, W, y)

        # skala piksel/meter; ruang ekstra agar busur derajat & label tidak terpotong
        S = min(W / 0.82, Hd / 0.62)
        cx = W / 2.0
        cy = Hd * 0.44
        L = self.L

        ground_y = cy + 0.165 * S
        p.setPen(QtGui.QPen(QtGui.QColor("#3E7B2E"), 1.2))
        p.drawLine(QtCore.QPointF(0, ground_y), QtCore.QPointF(W, ground_y))

        # 1. BASE BIRU
        base_w = 0.54 * S
        base_h = 0.016 * S
        p.setPen(Qt.NoPen)
        p.setBrush(QtGui.QColor(ACCENT))
        p.drawRect(QtCore.QRectF(cx - base_w / 2, ground_y - base_h, base_w, base_h))

        # 2. TIANG HITAM
        pillar_w = 0.09 * S
        cut = 0.03 * S
        poly_pillar = QtGui.QPolygonF([
            QtCore.QPointF(cx - pillar_w / 2, ground_y - base_h),
            QtCore.QPointF(cx - pillar_w / 2, cy + cut),
            QtCore.QPointF(cx - pillar_w / 2 + cut, cy - cut * 0.4),
            QtCore.QPointF(cx + pillar_w / 2 - cut, cy - cut * 0.4),
            QtCore.QPointF(cx + pillar_w / 2, cy + cut),
            QtCore.QPointF(cx + pillar_w / 2, ground_y - base_h),
        ])
        p.setBrush(QtGui.QColor("#111317"))
        p.drawPolygon(poly_pillar)

        # 2b. SKALA SUDUT (busur derajat) + BATAS MEKANIK
        self._draw_angle_scale(p, cx, cy, S)

        # 3. GARIS SETPOINT
        p.save()
        p.translate(cx, cy)
        p.rotate(-self.sp)
        sp_col = QtGui.QColor(ACCENT)
        sp_col.setAlpha(200)
        p.setPen(QtGui.QPen(sp_col, 1.5, Qt.DashLine))
        p.drawLine(QtCore.QPointF(-L * S - 0.05 * S, 0), QtCore.QPointF(L * S + 0.05 * S, 0))
        p.restore()

        # 4. BATANG BERAYUN + MOTOR + BALING-BALING
        p.save()
        p.translate(cx, cy)
        p.rotate(-self.th)

        beam_thick = 0.014 * S
        beam_ext = max(0.0, self.BEAM_HALF - L) * S  # ujung batang (0.27 m) melewati motor (L)
        p.setPen(Qt.NoPen)
        p.setBrush(QtGui.QColor("#181b20"))
        p.drawRect(QtCore.QRectF(-L * S - beam_ext, -beam_thick / 2, 2 * (L * S + beam_ext), beam_thick))


        prop_len = self.PROP_RADIUS * S
        for sx, thrust, ang in ((-1, self.F1, self.p1r), (1, self.F2, self.p2r)):
            mx = sx * L * S
            p.setPen(QtGui.QPen(QtGui.QColor("#2b323c"), 1.8))
            p.drawLine(QtCore.QPointF(mx, beam_thick / 2), QtCore.QPointF(mx, -0.045 * S))

            mot_w = 0.030 * S
            mot_h = 0.024 * S
            p.setPen(QtGui.QPen(QtGui.QColor("#6B7684"), 1))
            p.setBrush(QtGui.QColor("#C4CDD8"))
            p.drawRoundedRect(QtCore.QRectF(mx - mot_w / 2, -beam_thick / 2 - mot_h - 0.004 * S, mot_w, mot_h), 2, 2)
            p.setBrush(QtGui.QColor("#8E99A6"))
            p.drawEllipse(QtCore.QPointF(mx, -beam_thick / 2 - mot_h - 0.004 * S), mot_w * 0.35, 0.005 * S)

            prop_y = -beam_thick / 2 - mot_h - 0.008 * S
            scale_visual = math.cos(math.radians(ang))
            pw = prop_len * scale_visual

            p.setPen(QtGui.QPen(QtGui.QColor("#2A2F36"), 2.2))
            p.drawLine(QtCore.QPointF(mx - pw, prop_y), QtCore.QPointF(mx + pw, prop_y))

            tip_w = 0.014 * S * scale_visual
            p.setPen(QtGui.QPen(QtGui.QColor(ACCENT), 2.2))
            p.drawLine(QtCore.QPointF(mx - pw, prop_y), QtCore.QPointF(mx - pw + tip_w, prop_y))
            p.drawLine(QtCore.QPointF(mx + pw, prop_y), QtCore.QPointF(mx + pw - tip_w, prop_y))

            p.setPen(Qt.NoPen)
            p.setBrush(QtGui.QColor("#e8edf2"))
            p.drawEllipse(QtCore.QPointF(mx, prop_y), 0.004 * S, 0.004 * S)

            t_len = (thrust / self.Fmax) * 0.07 * S
            if t_len > 3:
                p.setPen(QtGui.QPen(QtGui.QColor(GREEN), 2))
                ty0 = prop_y - 0.008 * S
                p.drawLine(QtCore.QPointF(mx, ty0), QtCore.QPointF(mx, ty0 - t_len))
                p.setPen(Qt.NoPen)
                p.setBrush(QtGui.QColor(GREEN))
                p.drawPolygon(QtGui.QPolygonF([
                    QtCore.QPointF(mx, ty0 - t_len - 5),
                    QtCore.QPointF(mx - 3.5, ty0 - t_len),
                    QtCore.QPointF(mx + 3.5, ty0 - t_len)
                ]))

        if self.m > 0:
            load_sz = (0.02 + 0.03 * self.m / 0.5) * S
            lx = -self.x * S
            p.setPen(Qt.NoPen)
            p.setBrush(QtGui.QColor(RED))
            p.drawRect(QtCore.QRectF(lx - load_sz / 2, -beam_thick / 2 - load_sz, load_sz, load_sz))

        p.restore()

        # Poros tiang
        p.setPen(QtGui.QPen(QtGui.QColor("#404854"), 1))
        p.setBrush(QtGui.QColor("#e6edf3"))
        p.drawEllipse(QtCore.QPointF(cx, cy), 0.0045 * S, 0.0045 * S)

        self._draw_footer(p, W, H, Hd)

        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QtGui.QPen(QtGui.QColor(BORDER), 1))
        p.drawRoundedRect(outer, 10, 10)

    def _draw_angle_scale(self, p, cx, cy, S):
        """Busur derajat di sisi kanan poros: tick tiap 5 deg, label tiap 15 deg,
        garis merah di batas mekanik +-LIMIT_DEG."""
        r = (self.L + 0.05) * S
        tick_col = QtGui.QColor("#9AA5B4")
        lim_col = QtGui.QColor(RED)
        font = QtGui.QFont("Segoe UI", 7)
        p.setFont(font)
        lim = int(self.LIMIT_DEG)

        # busur tipis
        p.setPen(QtGui.QPen(QtGui.QColor("#C9D1DC"), 1))
        p.setBrush(Qt.NoBrush)
        arc = QtCore.QRectF(cx - r, cy - r, 2 * r, 2 * r)
        p.drawArc(arc, -lim * 16, 2 * lim * 16)

        for deg in range(-lim, lim + 1, 5):
            a = math.radians(deg)
            ca, sa = math.cos(a), -math.sin(a)   # layar: y ke bawah
            major = deg % 15 == 0
            is_lim = abs(deg) == lim
            ln = (0.022 if major else 0.012) * S
            if is_lim:
                ln = 0.030 * S
            p.setPen(QtGui.QPen(lim_col if is_lim else tick_col, 1.6 if is_lim else 1))
            p.drawLine(QtCore.QPointF(cx + r * ca, cy + r * sa),
                       QtCore.QPointF(cx + (r - ln) * ca, cy + (r - ln) * sa))
            if major:
                tx = cx + (r + 0.022 * S) * ca
                ty = cy + (r + 0.022 * S) * sa
                p.setPen(lim_col if is_lim else QtGui.QColor(MUTED))
                p.drawText(QtCore.QRectF(tx - 16, ty - 7, 32, 14),
                           Qt.AlignCenter, f"{deg:+d}\u00b0" if deg else "0\u00b0")

        # garis batas mekanik (putus-putus) dari poros
        p.setPen(QtGui.QPen(lim_col, 1, Qt.DotLine))
        for deg in (-lim, lim):
            a = math.radians(deg)
            p.drawLine(QtCore.QPointF(cx, cy),
                       QtCore.QPointF(cx + r * math.cos(a), cy - r * math.sin(a)))

    def _draw_footer(self, p, W, H, top):
        p.setPen(Qt.NoPen)
        p.setBrush(QtGui.QColor("#F7F8FA"))
        p.drawRect(QtCore.QRectF(0, top, W, H - top))
        p.setPen(QtGui.QPen(QtGui.QColor(BORDER), 1))
        p.drawLine(QtCore.QPointF(0, top), QtCore.QPointF(W, top))

        cols = [
            ("ANGLE \u03b8", f"{self.th:+.2f}\u00b0", ACCENT),
            ("SETPOINT", f"{self.sp:+.2f}\u00b0", ACCENT),
            ("THRUST L / R", f"{self.F1:.1f} / {self.F2:.1f} N", GREEN),
            ("LOAD", f"{self.m * 1000:.0f} g @ {self.x * 100:.0f} cm" if self.m > 0 else "NO LOAD",
             RED if self.m > 0 else MUTED),
        ]
        cw = W / len(cols)
        fl = QtGui.QFont("Segoe UI", 7, QtGui.QFont.Bold)
        fv = QtGui.QFont("Consolas", 12, QtGui.QFont.Bold)
        for i, (label, val, col) in enumerate(cols):
            x0 = i * cw
            if i > 0:
                p.setPen(QtGui.QPen(QtGui.QColor(BORDER), 1))
                p.drawLine(QtCore.QPointF(x0, top + 12), QtCore.QPointF(x0, H - 12))
            p.setPen(QtGui.QColor("#7A8695"))
            p.setFont(fl)
            p.drawText(QtCore.QRectF(x0 + 16, top + 8, cw - 24, 12),
                       Qt.AlignLeft | Qt.AlignVCenter, label)
            p.setPen(QtGui.QColor(col))
            p.setFont(fv)
            p.drawText(QtCore.QRectF(x0 + 16, top + 22, cw - 24, 28),
                       Qt.AlignLeft | Qt.AlignVCenter, val)
