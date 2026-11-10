/**
 * ============================================================================
 * HUDIMU.PDE - Panel Status & Grafik Sudut (hanya tampilan)
 * ============================================================================
 * Teks TIDAK digambar langsung di kanvas 3D (P3D), karena di sana font
 * dirender sebagai tekstur dan terlihat kabur/"burik". HUD digambar di
 * layer 2D terpisah (PGraphics JAVA2D) dengan font sistem (Segoe UI) yang
 * dibuat pada ukuran aslinya, lalu ditempel ke layar 1:1 piksel.
 */

PGraphics hud;
PFont fUi, fUiBold, fBig, fSmall, fMono;
float hudScale = 1.0;            // ikut skala tampilan Windows (125%, 150%, ...)

void initHud() {
  hudScale = max(1.0, pixelDensity);
  fUi     = createFont("Segoe UI", 13 * hudScale, true);
  fUiBold = createFont("Segoe UI Semibold", 13 * hudScale, true);
  fSmall  = createFont("Segoe UI", 11.5 * hudScale, true);
  fBig    = createFont("Segoe UI Semibold", 44 * hudScale, true);
  fMono   = createFont("Consolas", 12 * hudScale, true);
}

// buffer dibuat pada resolusi piksel FISIK layar, lalu digambar dengan
// skala hudScale -> 1 piksel buffer = 1 piksel layar (tidak di-resample)
void ensureHudBuffer() {
  if (hud == null || hud.width != pixelWidth || hud.height != pixelHeight) {
    hud = createGraphics(pixelWidth, pixelHeight, JAVA2D);
  }
}

void drawHudIMU() {
  ensureHudBuffer();
  hud.beginDraw();
  hud.clear();
  hud.smooth(8);
  hud.textMode(MODEL);
  hud.scale(hudScale);

  hudStatusPanel(hud);
  hudHelpPanel(hud);
  if (recActive && guiConnected()) hudRecBadge(hud);
  if (showGraph) hudAngleGraph(hud);

  hud.endDraw();

  camera();
  hint(DISABLE_DEPTH_TEST);
  noLights();
  image(hud, 0, 0, width, height);
  hint(ENABLE_DEPTH_TEST);
}

// ----------------------------------------------------------------------------
// util panel
// ----------------------------------------------------------------------------
void hudPanel(PGraphics g, float x, float y, float w, float h) {
  g.fill(18, 20, 26, 225);
  g.stroke(58, 64, 78);
  g.strokeWeight(1);
  g.rect(x, y, w, h, 10);
}

void hudDot(PGraphics g, float x, float y, int c) {
  g.noStroke();
  g.fill(c);
  g.ellipse(x, y, 10, 10);
}

void hudText(PGraphics g, PFont f, String s, float x, float y, int c, int alignX, int alignY) {
  g.textFont(f, f.getSize() / hudScale);
  g.fill(c);
  g.textAlign(alignX, alignY);
  g.text(s, x, y);
}

// ----------------------------------------------------------------------------
// PANEL STATUS (kiri atas)
// ----------------------------------------------------------------------------
void hudStatusPanel(PGraphics g) {
  float x = 16, y = 16, w = 340, h = 200;
  hudPanel(g, x, y, w, h);

  boolean gui = guiConnected();
  boolean live = dataLive();
  boolean hw = srcMode.equals("hw");

  int green = color(46, 204, 113), red = color(231, 76, 60);
  int amber = color(241, 196, 15), grey = color(110, 116, 130);

  // baris 1: GUI
  hudDot(g, x + 18, y + 20, gui ? green : red);
  String guiTxt;
  if (netError != null) guiTxt = "UDP error";
  else if (!gui)        guiTxt = "Menunggu GUI Python (UDP " + UDP_PORT + ")";
  else                  guiTxt = "GUI terhubung  \u00b7  mode " + (hw ? "Hardware" : "Simulasi");
  hudText(g, fUiBold, guiTxt, x + 32, y + 20, color(235), LEFT, CENTER);

  // baris 2: Uno
  int unoC = !gui ? grey : (!hw ? grey : (hwConn ? green : amber));
  hudDot(g, x + 18, y + 42, unoC);
  String unoTxt;
  if (!gui)        unoTxt = "Uno: \u2014";
  else if (!hw)    unoTxt = "Uno tidak dipakai (mode simulasi)";
  else if (hwConn) unoTxt = String.format("Uno %s  \u00b7  %.0f Hz", hwPort, hwRate);
  else             unoTxt = hwPort.length() > 0 ? "Uno " + hwPort + "  \u00b7  menunggu data\u2026"
                                                : "Uno belum Connect di GUI";
  hudText(g, fUi, unoTxt, x + 32, y + 42, color(200), LEFT, CENTER);

  if (netError != null) {
    hudText(g, fSmall, netError, x + 16, y + 62, color(255, 130, 120), LEFT, CENTER);
  }

  g.stroke(52, 57, 70);
  g.line(x + 16, y + 74, x + w - 16, y + 74);

  // sudut besar
  hudText(g, fBig, String.format("%+.2f\u00b0", targetTheta), x + 14, y + 80,
          live ? color(0, 225, 255) : color(110), LEFT, TOP);
  hudText(g, fSmall, "Sudut batang \u03b8", x + w - 16, y + 92, color(170), RIGHT, TOP);
  if (hw && angleInv) {
    hudText(g, fSmall, "arah dibalik", x + w - 16, y + 110, color(140), RIGHT, TOP);
  }

  // detail
  float ly = y + 150;
  String l2 = loadMass > 0.0005
              ? String.format("Beban        %.0f g @ %.0f cm", loadMass * 1000, loadPos * 100)
              : "Beban        tidak ada";
  if (hw) {
    hudText(g, fMono, String.format("Offset nol   %+.2f\u00b0", angleOff), x + 16, ly, color(205), LEFT, CENTER);
    hudText(g, fMono, l2, x + 16, ly + 20, color(205), LEFT, CENTER);
  } else {
    hudText(g, fMono, String.format("Setpoint     %+.2f\u00b0", setpointTheta), x + 16, ly, color(205), LEFT, CENTER);
    hudText(g, fMono, String.format("Thrust F1/F2 %.1f / %.1f N", thrustF1, thrustF2), x + 16, ly + 20, color(205), LEFT, CENTER);
  }
  hudText(g, fSmall, "Pengaturan data di GUI Python  \u00b7  " + (int)frameRate + " FPS",
          x + 16, ly + 40, color(125), LEFT, CENTER);
}

// ----------------------------------------------------------------------------
// BADGE REKAM (atas tengah)
// ----------------------------------------------------------------------------
void hudRecBadge(PGraphics g) {
  float w = 280, h = 34;
  float x = width / 2 - w / 2, y = 16;
  g.noStroke();
  g.fill(200, 40, 40, 230);
  g.rect(x, y, w, h, 8);
  boolean blink = (millis() / 500) % 2 == 0;
  g.fill(255, blink ? 255 : 110);
  g.ellipse(x + 20, y + h / 2, 11, 11);
  String t = "MEREKAM" + (recLabel.length() > 0 ? "  \u00b7  " + recLabel : "");
  if (t.length() > 32) t = t.substring(0, 32) + "\u2026";
  hudText(g, fUiBold, t, x + 36, y + h / 2, color(255), LEFT, CENTER);
}

// ----------------------------------------------------------------------------
// PANEL BANTUAN (kanan atas)
// ----------------------------------------------------------------------------
void hudHelpPanel(PGraphics g) {
  float w = 270, h = 158;
  float x = width - w - 16, y = 16;
  hudPanel(g, x, y, w, h);

  hudText(g, fUiBold, "Kontrol tampilan 3D", x + 16, y + 20, color(230), LEFT, CENTER);
  String[][] rows = {
    {"Drag kiri", "orbit kamera"},
    {"Drag kanan", "geser"},
    {"Scroll", "zoom"},
    {"1 \u2013 4", "depan / samping / atas / bawah"},
    {"R", "reset kamera"},
    {"G  /  H", "grafik  /  HUD"},
  };
  for (int i = 0; i < rows.length; i++) {
    float ry = y + 46 + i * 18;
    hudText(g, fSmall, rows[i][0], x + 16, ry, color(0, 200, 235), LEFT, CENTER);
    hudText(g, fSmall, rows[i][1], x + 100, ry, color(185), LEFT, CENTER);
  }
}

// ----------------------------------------------------------------------------
// GRAFIK SUDUT 10 s (bawah)
// ----------------------------------------------------------------------------
void hudAngleGraph(PGraphics g) {
  float x = 372, w = width - x - 16;
  float h = 170;
  float y = height - h - 16;
  if (w < 220) return;
  hudPanel(g, x, y, w, h);

  float px = x + 46, pw = w - 62;
  float py = y + 34, ph = h - 50;

  float peak = 0;
  for (int i = 0; i < HIST_LEN; i++) if (histValid[i]) peak = max(peak, abs(angleHist[i]));
  float lim = max(30, ceil((peak + 5) / 10.0) * 10);

  hudText(g, fUiBold, "Sudut \u03b8 (\u00b0)", x + 16, y + 17, color(230), LEFT, CENTER);
  hudText(g, fSmall, "10 detik terakhir", x + w - 16, y + 17, color(140), RIGHT, CENTER);

  for (int k = -2; k <= 2; k++) {
    float v = lim * k / 2.0;
    float gy = map(v, -lim, lim, py + ph, py);
    g.stroke(k == 0 ? color(105, 112, 128) : color(46, 51, 62));
    g.strokeWeight(1);
    g.line(px, gy, px + pw, gy);
    hudText(g, fSmall, nf(v, 0, 0), px - 8, gy, color(150), RIGHT, CENTER);
  }

  g.noFill();
  g.stroke(0, 225, 255);
  g.strokeWeight(2);
  boolean drawing = false;
  for (int i = 0; i < HIST_LEN; i++) {
    int idx = (histIdx + i) % HIST_LEN;
    float gx = px + pw * i / (float)(HIST_LEN - 1);
    if (!histValid[idx]) {
      if (drawing) { g.endShape(); drawing = false; }
      continue;
    }
    float gy = map(constrain(angleHist[idx], -lim, lim), -lim, lim, py + ph, py);
    if (!drawing) { g.beginShape(); drawing = true; }
    g.vertex(gx, gy);
  }
  if (drawing) g.endShape();
  g.strokeWeight(1);
}
