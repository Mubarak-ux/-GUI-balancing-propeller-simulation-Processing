/**
 * ============================================================================
 * MODELIMU.PDE - Model 3D Rakitan Balancing Propeller (Hardware Asli)
 * ============================================================================
 * Geometri disalin dari BalancingPropellerViewer/Model.pde (file asli tidak
 * diubah): alas, menara, poros, batang, motor, baling-baling, busur derajat.
 *
 * Mode SIMULASI : baling-baling berputar + panah thrust (data dari GUI).
 * Mode HARDWARE : baling-baling diam, tanpa panah thrust (kecepatan motor
 *                 asli tidak terbaca dari Uno, jadi tidak dipalsukan).
 * - Ditambah modul IMU (GY-521) di tengah batang dan ESC kuning di lengan,
 *   mengikuti foto alat.
 */

final float BEAM_HALF_LENGTH = 216.0; // 0.27 m, skala 800 px/m (batang total 54 cm)
final float MOTOR_ARM = 200.0;        // 0.25 m, poros ke pusat propeller (terukur)
final float ESC1_ARM = 104.0;         // 0.130 m, poros ke pusat ESC 1 (terukur)
final float ESC2_ARM = 108.0;         // 0.135 m, poros ke pusat ESC 2 (terukur)
final float PROP_RADIUS = 101.6;      // 0.127 m, propeller 1045 (10 inci)
final int   STOP_DEG = 30;            // batas mekanik +/-30 deg (terukur)
final float FMAX_N = 8.0;             // N, thrust maks per motor (Params.Fmax)
final float BEAM_WIDTH = 26.0;
final float BEAM_HEIGHT = 12.0;

void drawApparatusIMU() {
  boolean live = dataLive();

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
  pushMatrix();
  translate(0, 5, 24);
  drawTowerPlate(75, 180, 8);
  popMatrix();
  pushMatrix();
  translate(0, 5, -24);
  drawTowerPlate(75, 180, 8);
  popMatrix();

  pushMatrix();
  fill(30, 32, 35);
  translate(0, 40, 0);
  box(65, 12, 40);
  translate(0, 45, 0);
  box(65, 12, 40);
  popMatrix();

  // 3. BUSUR DERAJAT
  pushMatrix();
  translate(0, -75, 30);
  drawProtractorArc(100.0, currentTheta);
  popMatrix();

  // 4. POROS
  pushMatrix();
  translate(0, -75, 0);
  fill(210, 215, 225);
  stroke(140, 145, 155);
  rotateX(HALF_PI);
  drawCylinder(5, 5, 62, 16);
  popMatrix();

  // 5. BATANG (mengikuti sudut IMU)
  pushMatrix();
  translate(0, -75, 0);
  rotateZ(radians(-currentTheta));   // konvensi sama dgn viewer simulasi

  if (live) {
    fill(32, 34, 38);
    stroke(15, 15, 18);
  } else {
    fill(70, 60, 60);                // data putus -> batang kemerahan
    stroke(120, 50, 50);
  }
  strokeWeight(1);
  box(BEAM_HALF_LENGTH * 2, BEAM_HEIGHT, BEAM_WIDTH);

  fill(45, 48, 54);
  stroke(15, 15, 18);
  box(36, BEAM_HEIGHT + 4, BEAM_WIDTH + 6);

  // modul IMU GY-521 di atas hub tengah
  drawImuModule(live);

  // ESC kuning di kedua lengan (seperti di foto)
  // sisi ESC 1 / ESC 2 belum dicatat; ESC 1 diasumsikan di kiri
  drawEsc(-ESC1_ARM);
  drawEsc(ESC2_ARM);

  // beban fisik (keterangan dari GUI), sisi kiri
  if (loadMass > 0.0005) drawLoadBlock();

  // motor & baling-baling
  //   simulasi : berputar mengikuti GUI + piringan blur + panah thrust
  //   hardware : diam (kecepatan motor asli tidak terbaca dari Uno)
  boolean sim = isSimMode();
  pushMatrix();
  translate(-MOTOR_ARM, -BEAM_HEIGHT / 2, 0);
  drawMotorAndProp(sim ? prop1Rot : 30, sim ? thrustF1 : 0, sim);
  if (sim) drawThrustVector(thrustF1, "F1");
  popMatrix();

  pushMatrix();
  translate(MOTOR_ARM, -BEAM_HEIGHT / 2, 0);
  drawMotorAndProp(sim ? prop2Rot : -30, sim ? thrustF2 : 0, sim);
  if (sim) drawThrustVector(thrustF2, "F2");
  popMatrix();

  popMatrix(); // batang
  popMatrix(); // scene
}

// ----------------------------------------------------------------------------
// MODUL IMU (PCB biru GY-521 + chip MPU6050 + LED status)
// ----------------------------------------------------------------------------
void drawImuModule(boolean live) {
  pushMatrix();
  translate(0, -BEAM_HEIGHT / 2 - 3 - 2, 0);
  fill(30, 70, 160);
  stroke(15, 35, 90);
  strokeWeight(1);
  box(22, 2, 16);                      // PCB

  translate(0, -2, 0);
  fill(25);
  noStroke();
  box(7, 2, 7);                        // chip MPU6050

  // LED: hijau = data masuk, merah = putus
  pushMatrix();
  translate(8, -1, 5);
  if (live) fill(60, 255, 120);
  else fill(255, 60, 60);
  sphereDetail(8);
  sphere(1.8);
  popMatrix();

  popMatrix();
}

// balok beban (disalin dari Model.pde), posisi -loadPos dari poros
void drawLoadBlock() {
  pushMatrix();
  float mNorm = constrain(loadMass / 0.5, 0.0, 1.0);
  float massW = map(mNorm, 0.0, 1.0, 18.0, 38.0);
  float massH = map(mNorm, 0.0, 1.0, 12.0, 36.0);
  float massD = map(mNorm, 0.0, 1.0, BEAM_WIDTH + 4.0, BEAM_WIDTH + 14.0);
  translate(-loadPos * 800.0, -BEAM_HEIGHT / 2.0 - massH / 2.0, 0);

  fill(218, 165, 32);
  stroke(120, 85, 20);
  strokeWeight(1);
  box(massW, massH, massD);

  fill(45, 48, 54);
  stroke(25);
  pushMatrix();
  translate(0, massH / 2.0, 0);
  box(massW + 2, 4, massD + 2);
  popMatrix();

  pushMatrix();
  translate(0, -massH / 2.0 - 10, 0);
  fill(255, 220, 100);
  textSize(11);
  textAlign(CENTER, BOTTOM);
  text(String.format("%.0fg", loadMass * 1000.0), 0, 0);
  popMatrix();
  popMatrix();
}

// ESC kuning dengan kabel
void drawEsc(float x) {
  pushMatrix();
  translate(x, -BEAM_HEIGHT / 2 - 5, 0);
  fill(240, 200, 30);
  stroke(140, 110, 10);
  strokeWeight(1);
  box(36, 8, 18);
  popMatrix();

  stroke(40, 80, 200);
  strokeWeight(1.5);
  float dir = x > 0 ? 1 : -1;
  float yTop = -BEAM_HEIGHT / 2 - 1;
  line(x + dir * 18, yTop, -4, dir * (MOTOR_ARM - 16), yTop, -4);
  line(x + dir * 18, yTop, 4, dir * (MOTOR_ARM - 16), yTop, 4);
}

// ----------------------------------------------------------------------------
// BUSUR DERAJAT
// ----------------------------------------------------------------------------
void drawProtractorArc(float radius, float curDeg) {
  pushMatrix();
  noFill();

  stroke(200, 210, 225, 80);
  strokeWeight(1.2);
  beginShape();
  for (int d = -STOP_DEG; d <= STOP_DEG; d += 3) {
    float rad = radians(d);
    vertex(sin(rad) * radius, -cos(rad) * radius, 0);
  }
  endShape();

  for (int d = -STOP_DEG; d <= STOP_DEG; d += 15) {
    float rad = radians(d);
    stroke(220, 230, 245, 140);
    line(sin(rad) * (radius - 6), -cos(rad) * (radius - 6), 0,
         sin(rad) * (radius + 6), -cos(rad) * (radius + 6), 0);
  }

  float curRad = radians(constrain(curDeg, -STOP_DEG, STOP_DEG));
  stroke(0, 230, 255, 230);
  strokeWeight(2.0);
  line(0, 0, 0, sin(curRad) * (radius + 12), -cos(curRad) * (radius + 12), 0);

  fill(0, 230, 255);
  noStroke();
  ellipse(0, 0, 6, 6);
  popMatrix();
}

// ----------------------------------------------------------------------------
// MOTOR & BALING-BALING (disalin dari Model.pde, + piringan blur saat berputar)
// ----------------------------------------------------------------------------
void drawMotorAndProp(float rotAngle, float thrust, boolean spinning) {
  fill(45, 48, 52);
  stroke(20);
  strokeWeight(1);
  box(30, 4, 30);

  pushMatrix();
  translate(0, -14, 0);
  fill(215, 220, 228);
  stroke(130, 135, 145);
  drawCylinder(13, 13, 22, 20);
  translate(0, -14, 0);
  fill(240, 245, 252);
  drawCylinder(4, 5, 8, 14);
  translate(0, -4, 0);
  sphereDetail(12);
  sphere(4.5);
  popMatrix();

  pushMatrix();
  translate(0, -26, 0);
  final float BLADE_RADIUS = PROP_RADIUS;
  final float BLADE_WIDTH  = 13.0;

  if (spinning) {
    // efek motion blur: piringan transparan, makin pekat saat thrust besar
    float blurAlpha = map(constrain(thrust, 0, FMAX_N), 0, FMAX_N, 10, 95);
    pushMatrix();
    rotateX(HALF_PI);
    noStroke();
    fill(255, 255, 255, blurAlpha * 0.45);
    ellipse(0, 0, BLADE_RADIUS * 2, BLADE_RADIUS * 2);
    fill(250, 205, 25, blurAlpha * 0.75);
    ellipse(0, 0, BLADE_RADIUS * 2, BLADE_RADIUS * 2);
    fill(24, 26, 31);
    ellipse(0, 0, BLADE_RADIUS * 1.6, BLADE_RADIUS * 1.6);
    popMatrix();
  }

  rotateY(radians(rotAngle));
  drawPropBlade(BLADE_RADIUS, BLADE_WIDTH);
  rotateY(PI);
  drawPropBlade(BLADE_RADIUS, BLADE_WIDTH);
  fill(30, 32, 35);
  noStroke();
  drawCylinder(6, 6, 4, 16);
  popMatrix();
}

// panah gaya dorong (disalin dari Model.pde, label teks dihapus agar tidak kabur;
// nilai F1/F2 ditampilkan tajam di HUD)
void drawThrustVector(float thrust, String label) {
  float arrowH = map(constrain(thrust, 0, FMAX_N), 0, FMAX_N, 10, 120);
  pushMatrix();
  translate(0, -32, 0);
  int rCol = (int)map(thrust, 0, FMAX_N, 40, 255);
  int gCol = (int)map(thrust, 0, FMAX_N, 200, 140);
  int bCol = (int)map(thrust, 0, FMAX_N, 255, 40);
  stroke(rCol, gCol, bCol, 220);
  strokeWeight(2.5);
  line(0, 0, 0, 0, -arrowH, 0);
  pushMatrix();
  translate(0, -arrowH, 0);
  fill(rCol, gCol, bCol);
  noStroke();
  drawCylinder(0, 5.5, 14, 12);
  popMatrix();
  strokeWeight(1);
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
// GEOMETRI PELAT TIANG & SILINDER (disalin dari Model.pde)
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

void drawCylinder(float rTop, float rBottom, float h, int sides) {
  float halfH = h / 2.0;
  beginShape(QUAD_STRIP);
  for (int i = 0; i <= sides; i++) {
    float a = TWO_PI / sides * i;
    vertex(sin(a) * rTop, -halfH, cos(a) * rTop);
    vertex(sin(a) * rBottom, halfH, cos(a) * rBottom);
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
