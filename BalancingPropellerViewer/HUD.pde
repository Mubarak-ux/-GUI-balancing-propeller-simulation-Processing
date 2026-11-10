/**
 * ============================================================================
 * HUD.PDE - Modul Heads-Up Display (2D Overlay)
 * ============================================================================
 * Menampilkan telemetri sudut batang, setpoint, thrust motor F1 & F2,
 * beban massa, sinyal kontrol U, FPS, status koneksi UDP, dan petunjuk kontrol.
 */

// ----------------------------------------------------------------------------
// HEADS-UP DISPLAY (HUD)
// ----------------------------------------------------------------------------
void drawHUD() {
  camera();
  hint(DISABLE_DEPTH_TEST);
  noLights();

  // Panel Telemetri Pojok Kiri Atas
  fill(20, 22, 28, 220);
  stroke(55, 60, 72);
  strokeWeight(1);
  rect(16, 16, 290, 160, 8);

  // Status Badge
  noStroke();
  if (connected) {
    fill(46, 204, 113);
    rect(28, 28, 10, 10, 3);
    fill(255);
    textSize(12);
    textAlign(LEFT, CENTER);
    text("PROCESSING 3D · CONNECTED", 46, 33);
  } else {
    fill(231, 76, 60);
    rect(28, 28, 10, 10, 3);
    fill(200);
    textSize(12);
    textAlign(LEFT, CENTER);
    text("WAITING FOR PYTHON... (Port 9999)", 46, 33);
  }

  stroke(50, 54, 64);
  line(28, 48, 290, 48);

  // Parameter Dinamika
  fill(215);
  textSize(12);
  text(String.format("Sudut Batang (Theta) : %+.2f°", currentTheta), 28, 66);
  text(String.format("Target (Setpoint)     : %+.2f°", setpointTheta), 28, 86);
  text(String.format("Gaya Dorong F1 / F2   : %.1f N / %.1f N", thrustF1, thrustF2), 28, 106);
  text(String.format("Beban Tambahan        : %.2f kg (@ %.0f cm)", loadMass, loadPos * 100), 28, 126);
  text(String.format("Sinyal Kontrol U      : %+.1f %%   |  FPS: %d", controlU, (int)frameRate), 28, 146);

  // Petunjuk Kontrol & Tombol Impuls Pojok Kanan Atas
  fill(20, 22, 28, 190);
  stroke(55, 60, 72);
  rect(width - 256, 16, 240, 126, 8);
  fill(180);
  textSize(11);
  textAlign(LEFT, TOP);
  text("KONTROL NAVIGASI:", width - 244, 24);
  text("• Drag Kiri   : Orbit Kamera", width - 244, 42);
  text("• Scroll       : Zoom In / Out", width - 244, 58);
  text("• Drag Kanan  : Pan Geser", width - 244, 74);
  text("• [SPACE]      : Sentak Impuls Fisik!", width - 244, 92);
  text("• R: Reset  |  1..4: View  |  H: HUD", width - 244, 110);

  // Banner Notifikasi Gangguan saat tombol Space ditekan
  if (millis() < impulseFlashTimer) {
    fill(231, 76, 60, 230);
    noStroke();
    rect(width / 2 - 140, 20, 280, 36, 6);
    fill(255);
    textSize(13);
    textAlign(CENTER, CENTER);
    text("💥 GANGGUAN IMPULS DIBERIKAN!", width / 2, 38);
  }

  hint(ENABLE_DEPTH_TEST);
}
