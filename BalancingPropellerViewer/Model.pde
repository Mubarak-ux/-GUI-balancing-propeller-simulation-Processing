/**
 * ============================================================================
 * MODEL.PDE - Modul Geometri 3D Rakitan Balancing Propeller
 * ============================================================================
 * Menggambar komponen fisik 3D: papan alas, tiang ganda ber-chamfer,
 * poros bearing, batang berputar, balok beban dinamis, motor, baling-baling
 * dengan efek motion blur spinning disc, panah vektor thrust, dan busur derajat.
 */

// ----------------------------------------------------------------------------
// MODEL 3D RAKITAN ALAT BALANCING PROPELLER
// ----------------------------------------------------------------------------
void drawBalancingApparatus() {
  final float BEAM_HALF_LENGTH = 216.0; // 0.27 m skala 800 px/m (batang total 54 cm)
  final float MOTOR_ARM = 200.0;        // 0.25 m, poros ke pusat propeller (terukur)
  final float BEAM_WIDTH = 26.0;
  final float BEAM_HEIGHT = 12.0;

  pushMatrix();

  // 1. PAPAN ALAS KAYU
  pushMatrix();
  translate(0, 100, 0);
  fill(160, 105, 55);
  stroke(80, 50, 25);
  strokeWeight(1.2);
  box(480, 20, 130);
  popMatrix();

  // 2. MENARA DUA PELAT SEJAJAR
  fill(38, 40, 44);
  stroke(20, 22, 25);
  strokeWeight(1);

  // Pelat Depan
  pushMatrix();
  translate(0, 5, 24);
  drawTowerPlate(75, 180, 8);
  popMatrix();

  // Pelat Belakang
  pushMatrix();
  translate(0, 5, -24);
  drawTowerPlate(75, 180, 8);
  popMatrix();

  // Palang penguat
  pushMatrix();
  fill(30, 32, 35);
  translate(0, 40, 0);
  box(65, 12, 40);
  translate(0, 45, 0);
  box(65, 12, 40);
  popMatrix();

  // 3. BUSUR DERAJAT SUDUT (PROTRACTOR ARC) DI POROS TENGAH
  pushMatrix();
  translate(0, -75, 30); // Tepat di muka pelat depan
  drawProtractorArc(100.0, currentTheta, setpointTheta);
  popMatrix();

  // 4. POROS TENGAH / BEARING AXLE
  pushMatrix();
  translate(0, -75, 0);
  fill(210, 215, 225);
  stroke(140, 145, 155);
  rotateX(HALF_PI);
  drawCylinder(5, 5, 62, 16);
  popMatrix();

  // 5. BATANG PENYEIMBANG BERPUTAR (Rotating Beam)
  pushMatrix();
  translate(0, -75, 0); // Poros putar
  rotateZ(radians(-currentTheta)); // Rotasi sudut kemiringan (sinkron dengan visual 2D)

  // Flash efek saat terkena impuls
  if (millis() < impulseFlashTimer) {
    fill(240, 100, 100);
    stroke(255, 50, 50);
  } else {
    fill(32, 34, 38);
    stroke(15, 15, 18);
  }
  strokeWeight(1);
  box(BEAM_HALF_LENGTH * 2, BEAM_HEIGHT, BEAM_WIDTH);

  // Hub tengah diperlebar
  fill(45, 48, 54);
  box(36, BEAM_HEIGHT + 4, BEAM_WIDTH + 6);

  // Garis Target Setpoint (Garis Hantu Tipis Cyan)
  if (abs(setpointTheta) > 0.05) {
    pushMatrix();
    rotateZ(radians(-(setpointTheta - currentTheta)));
    stroke(0, 210, 255, 90);
    strokeWeight(1.5);
    line(-BEAM_HALF_LENGTH - 25, 0, 0, BEAM_HALF_LENGTH + 25, 0, 0);
    popMatrix();
  }

  // 6. BEBAN TAMBAHAN (LOAD MASS SLIDER) - Membesar dinamis mengikuti berat
  if (loadMass > 0.001) {
    pushMatrix();
    float loadPx = -loadPos * 800.0;

    // Normalisasi massa 0 s/d 500 gram (0.0 s/d 0.5 kg)
    float mNorm = constrain(loadMass / 0.5, 0.0, 1.0);

    // Dimensi balok membesar secara proporsional seiring bertambahnya massa
    float massW = map(mNorm, 0.0, 1.0, 18.0, 38.0); // Lebar sepanjang batang
    float massH = map(mNorm, 0.0, 1.0, 12.0, 36.0); // Tinggi balok
    float massD = map(mNorm, 0.0, 1.0, BEAM_WIDTH + 4.0, BEAM_WIDTH + 14.0); // Ketebalan Z

    // Posisikan tepat menempel di atas permukaan batang
    translate(loadPx, -BEAM_HEIGHT / 2.0 - massH / 2.0, 0);

    // Balok Beban Kuningan / Brass
    fill(218, 165, 32);
    stroke(120, 85, 20);
    strokeWeight(1);
    box(massW, massH, massD);

    // Klem pengunci di bawah balok
    fill(45, 48, 54);
    stroke(25);
    pushMatrix();
    translate(0, massH / 2.0, 0);
    box(massW + 2, 4, massD + 2);
    popMatrix();

    // Baut pengencang di atas
    fill(210, 215, 225);
    noStroke();
    pushMatrix();
    translate(0, -massH / 2.0 - 2, 0);
    drawCylinder(3.5, 3.5, 4, 12);
    popMatrix();

    // Label berat beban di atas balok (misal: 150g)
    pushMatrix();
    translate(0, -massH / 2.0 - 10, 0);
    fill(255, 220, 100);
    textSize(11);
    textAlign(CENTER, BOTTOM);
    text(String.format("%.0fg", loadMass * 1000.0), 0, 0);
    popMatrix();

    popMatrix();
  }

  // 7. MOTOR & PROPELLER KIRI (-X)
  pushMatrix();
  translate(-MOTOR_ARM, -BEAM_HEIGHT / 2, 0);
  drawMotorAndProp(prop1Rot, thrustF1, true);
  // Panah Vektor Gaya F1
  drawThrustVector(thrustF1, "F1");
  popMatrix();

  // 8. MOTOR & PROPELLER KANAN (+X)
  pushMatrix();
  translate(MOTOR_ARM, -BEAM_HEIGHT / 2, 0);
  drawMotorAndProp(prop2Rot, thrustF2, false);
  // Panah Vektor Gaya F2
  drawThrustVector(thrustF2, "F2");
  popMatrix();

  popMatrix(); // Selesai Batang

  popMatrix(); // Selesai Scene
}

// ----------------------------------------------------------------------------
// VISUALISASI PANAH VEKTOR GAYA DORONG (THRUST VECTOR ARROW)
// ----------------------------------------------------------------------------
void drawThrustVector(float thrust, String label) {
  // Panjang panah proporsional terhadap gaya (8 N max -> ~120 px)
  float arrowH = map(constrain(thrust, 0, 8), 0, 8, 10, 120);

  pushMatrix();
  translate(0, -32, 0); // Di atas propeller

  // Warna gradien dinamis: Biru/Cyan di thrust normal -> Oranye di thrust tinggi
  int rCol = (int)map(thrust, 0, 8, 40, 255);
  int gCol = (int)map(thrust, 0, 8, 200, 140);
  int bCol = (int)map(thrust, 0, 8, 255, 40);

  stroke(rCol, gCol, bCol, 220);
  strokeWeight(2.5);
  // Batang panah ke atas (-Y)
  line(0, 0, 0, 0, -arrowH, 0);

  // Kepala panah kerucut (Cone Tip)
  pushMatrix();
  translate(0, -arrowH, 0);
  fill(rCol, gCol, bCol);
  noStroke();
  drawCylinder(0, 5.5, 14, 12);
  popMatrix();

  // Label Nilai Gaya 3D Billboard
  pushMatrix();
  translate(14, -arrowH * 0.7, 0);
  fill(255);
  textSize(11);
  textAlign(LEFT, CENTER);
  text(String.format("%s: %.1f N", label, thrust), 0, 0);
  popMatrix();

  popMatrix();
}

// ----------------------------------------------------------------------------
// BUSUR DERAJAT SUDUT (PROTRACTOR ARC)
// ----------------------------------------------------------------------------
void drawProtractorArc(float radius, float curDeg, float spDeg) {
  pushMatrix();
  noFill();

  // Busur acuan -30 s/d +30 derajat (batas mekanik terukur)
  stroke(200, 210, 225, 80);
  strokeWeight(1.2);
  beginShape();
  for (int d = -30; d <= 30; d += 3) {
    float rad = radians(d);
    vertex(sin(rad) * radius, -cos(rad) * radius, 0);
  }
  endShape();

  // Tanda garis skala (Ticks) setiap 15 derajat
  for (int d = -30; d <= 30; d += 15) {
    float rad = radians(d);
    float x1 = sin(rad) * (radius - 6);
    float y1 = -cos(rad) * (radius - 6);
    float x2 = sin(rad) * (radius + 6);
    float y2 = -cos(rad) * (radius + 6);
    stroke(220, 230, 245, 140);
    line(x1, y1, 0, x2, y2, 0);
  }

  // Jarum Setpoint Target (Kuning/Amber)
  if (abs(spDeg) > 0.05) {
    float spRad = radians(spDeg);
    stroke(255, 185, 30, 180);
    strokeWeight(1.5);
    line(0, 0, 0, sin(spRad) * (radius + 8), -cos(spRad) * (radius + 8), 0);
  }

  // Jarum Sudut Aktual Batang (Cyan)
  float curRad = radians(curDeg);
  stroke(0, 230, 255, 230);
  strokeWeight(2.0);
  line(0, 0, 0, sin(curRad) * (radius + 12), -cos(curRad) * (radius + 12), 0);

  // Titik hub tengah
  fill(0, 230, 255);
  noStroke();
  ellipse(0, 0, 6, 6);

  popMatrix();
}

// ----------------------------------------------------------------------------
// PERAKITAN MOTOR & BALING-BALING (DENGAN MOTION BLUR DISC)
// ----------------------------------------------------------------------------
void drawMotorAndProp(float rotAngle, float thrust, boolean isLeft) {
  // Dudukan Motor
  fill(45, 48, 52);
  stroke(20);
  strokeWeight(1);
  box(30, 4, 30);

  // Tabung Motor Aluminium Perak
  pushMatrix();
  translate(0, -14, 0);
  fill(215, 220, 228);
  stroke(130, 135, 145);
  drawCylinder(13, 13, 22, 20);

  // Poros & Baut Peluru Atas
  translate(0, -14, 0);
  fill(240, 245, 252);
  drawCylinder(4, 5, 8, 14);
  translate(0, -4, 0);
  sphereDetail(12);
  sphere(4.5);
  popMatrix();

  // BALING-BALING
  pushMatrix();
  translate(0, -26, 0);

  final float BLADE_RADIUS = 101.6;  // 0.127 m, propeller 1045 (10 inci)
  final float BLADE_WIDTH  = 13.0;

  // EFEK MOTION BLUR SPINNING DISC (Piringan Transparan Putaran Cepat)
  float blurAlpha = map(constrain(thrust, 0, 8), 0, 8, 10, 95);
  pushMatrix();
  rotateX(HALF_PI);
  noStroke();
  fill(255, 255, 255, blurAlpha * 0.45);
  ellipse(0, 0, BLADE_RADIUS * 2, BLADE_RADIUS * 2);
  fill(250, 205, 25, blurAlpha * 0.75); // Cincin kuning di ujung
  ellipse(0, 0, BLADE_RADIUS * 2, BLADE_RADIUS * 2);
  fill(24, 26, 31); // Lubang tengah
  ellipse(0, 0, BLADE_RADIUS * 1.6, BLADE_RADIUS * 1.6);
  popMatrix();

  // Bilah Baling-baling Nyata
  rotateY(radians(rotAngle));

  // Bilah 1
  drawPropBlade(BLADE_RADIUS, BLADE_WIDTH);

  // Bilah 2
  rotateY(PI);
  drawPropBlade(BLADE_RADIUS, BLADE_WIDTH);

  // Hub Spinner Tengah
  fill(30, 32, 35);
  noStroke();
  drawCylinder(6, 6, 4, 16);

  popMatrix();
}

void drawPropBlade(float len, float w) {
  float yellowTipStart = len * 0.78;
  noStroke();

  fill(36, 38, 42);
  beginShape(QUADS);
  vertex(5, -0.8, -w * 0.25);
  vertex(yellowTipStart, -0.6, -w * 0.45);
  vertex(yellowTipStart,  0.6,  w * 0.45);
  vertex(5,  0.8,  w * 0.25);
  endShape();

  fill(250, 205, 25);
  beginShape(QUADS);
  vertex(yellowTipStart, -0.6, -w * 0.45);
  vertex(len, -0.2, -w * 0.15);
  vertex(len,  0.2,  w * 0.15);
  vertex(yellowTipStart,  0.6,  w * 0.45);
  endShape();
}

// ----------------------------------------------------------------------------
// GEOMETRI PELAT TIANG DENGAN CHAMFER
// ----------------------------------------------------------------------------
void drawTowerPlate(float w, float h, float th) {
  float halfW = w / 2.0;
  float halfH = h / 2.0;
  float chamfer = 16.0;

  pushMatrix();
  translate(0, 0, -th / 2.0);

  beginShape();
  vertex(-halfW, halfH, th);
  vertex(halfW, halfH, th);
  vertex(halfW, -halfH + chamfer, th);
  vertex(halfW - chamfer, -halfH, th);
  vertex(-halfW + chamfer, -halfH, th);
  vertex(-halfW, -halfH + chamfer, th);
  endShape(CLOSE);

  beginShape();
  vertex(-halfW, halfH, 0);
  vertex(halfW, halfH, 0);
  vertex(halfW, -halfH + chamfer, 0);
  vertex(halfW - chamfer, -halfH, 0);
  vertex(-halfW + chamfer, -halfH, 0);
  vertex(-halfW, -halfH + chamfer, 0);
  endShape(CLOSE);

  box(w, h, th);
  popMatrix();
}

// ----------------------------------------------------------------------------
// HELPER SILINDER
// ----------------------------------------------------------------------------
void drawCylinder(float rTop, float rBottom, float h, int sides) {
  float halfH = h / 2.0;

  beginShape(QUAD_STRIP);
  for (int i = 0; i <= sides; i++) {
    float a = TWO_PI / sides * i;
    float x1 = sin(a) * rTop;
    float z1 = cos(a) * rTop;
    float x2 = sin(a) * rBottom;
    float z2 = cos(a) * rBottom;
    vertex(x1, -halfH, z1);
    vertex(x2,  halfH, z2);
  }
  endShape();

  if (rTop > 0) {
    beginShape(TRIANGLE_FAN);
    vertex(0, -halfH, 0);
    for (int i = 0; i <= sides; i++) {
      float a = TWO_PI / sides * i;
      vertex(sin(a) * rTop, -halfH, cos(a) * rTop);
    }
    endShape();
  }

  if (rBottom > 0) {
    beginShape(TRIANGLE_FAN);
    vertex(0, halfH, 0);
    for (int i = sides; i >= 0; i--) {
      float a = TWO_PI / sides * i;
      vertex(sin(a) * rBottom, halfH, cos(a) * rBottom);
    }
    endShape();
  }
}
