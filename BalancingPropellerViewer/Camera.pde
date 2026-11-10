/**
 * ============================================================================
 * CAMERA.PDE - Modul Kamera 3D, Pencahayaan & Kontrol Interaksi
 * ============================================================================
 * Menangani pengaturan sudut kamera orbit 3D, pencahayaan scene,
 * rendering lantai grid acuan, serta kontrol mouse dan keyboard.
 */

// ----------------------------------------------------------------------------
// KONTROL KAMERA ORBIT
// ----------------------------------------------------------------------------
float camRotX = radians(15);   // Azimuth (sedikit miring 3D depan)
float camRotY = radians(-12);  // Elevasi (di atas meja melihat ke bawah ke poros)
float camDist = 650;           // Jarak kamera
float targetX = 0;
float targetY = -75;           // Titik fokus tepat di poros putar batang
float targetZ = 0;

float prevMouseX, prevMouseY;
boolean showHUD = true;

// ----------------------------------------------------------------------------
// SISTEM KAMERA & PENCAHAYAAN 3D
// ----------------------------------------------------------------------------
void setupCamera() {
  float eyeX = targetX + camDist * cos(camRotY) * sin(camRotX);
  float eyeY = targetY + camDist * sin(camRotY);
  float eyeZ = targetZ + camDist * cos(camRotY) * cos(camRotX);
  camera(eyeX, eyeY, eyeZ, targetX, targetY, targetZ, 0, 1, 0);
}

void setupLights() {
  ambientLight(70, 75, 85);
  directionalLight(220, 225, 230, -0.4, 0.9, -0.6);
  directionalLight(90, 95, 110, 0.6, 0.4, 0.7);
  lightSpecular(170, 175, 185);
}

// ----------------------------------------------------------------------------
// LANTAI GRID
// ----------------------------------------------------------------------------
void drawEnvironment() {
  pushMatrix();
  stroke(45, 50, 60);
  strokeWeight(1);
  noFill();

  int gridSize = 700;
  int step = 50;
  for (int x = -gridSize; x <= gridSize; x += step) {
    line(x, 110, -gridSize, x, 110, gridSize);
  }
  for (int z = -gridSize; z <= gridSize; z += step) {
    line(-gridSize, 110, z, gridSize, 110, z);
  }

  // Sumbu acuan lantai (Merah: X, Biru: Z)
  stroke(220, 60, 60, 140);
  line(-250, 109, 0, 250, 109, 0);
  stroke(60, 120, 240, 140);
  line(0, 109, -250, 0, 109, 250);
  popMatrix();
}

// ----------------------------------------------------------------------------
// INTERAKSI MOUSE & KEYBOARD
// ----------------------------------------------------------------------------
void mousePressed() {
  prevMouseX = mouseX;
  prevMouseY = mouseY;
}

void mouseDragged() {
  float dx = mouseX - prevMouseX;
  float dy = mouseY - prevMouseY;

  if (mouseButton == LEFT) {
    camRotX -= dx * 0.008;
    camRotY += dy * 0.008;
    camRotY = constrain(camRotY, -HALF_PI + 0.05, HALF_PI - 0.05);
  } else if (mouseButton == RIGHT) {
    // Pan kamera
    targetX -= dx * 0.5 * cos(camRotX);
    targetZ += dx * 0.5 * sin(camRotX);
    targetY += dy * 0.5;
  }

  prevMouseX = mouseX;
  prevMouseY = mouseY;
}

void mouseWheel(MouseEvent event) {
  float e = event.getCount();
  camDist += e * 35;
  camDist = constrain(camDist, 250, 1400);
}

void keyPressed() {
  if (key == ' ') {
    // Kirim sentakan impuls ke Python
    triggerDisturbanceImpulse();
  } else if (key == 'r' || key == 'R') {
    camRotX = radians(15);
    camRotY = radians(-12);
    camDist = 650;
    targetX = 0;
    targetY = -75;
    targetZ = 0;
  } else if (key == '1') {
    // Tampak Depan (Front View murni sejajar 2D)
    camRotX = 0;
    camRotY = 0;
    camDist = 620;
    targetX = 0;
    targetY = -75;
    targetZ = 0;
  } else if (key == '2') {
    // Tampak Samping (Side View)
    camRotX = HALF_PI;
    camRotY = 0;
    targetY = -75;
  } else if (key == '3') {
    // Tampak Atas (Top View)
    camRotX = 0;
    camRotY = -HALF_PI + 0.01;
    targetY = -75;
  } else if (key == '4') {
    // Tampak Bawah (Bottom View)
    camRotX = 0;
    camRotY = HALF_PI - 0.01;
    targetY = -75;
  } else if (key == 'h' || key == 'H') {
    showHUD = !showHUD;
  }
}
