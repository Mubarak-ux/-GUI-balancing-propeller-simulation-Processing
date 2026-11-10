/**
 * ============================================================================
 * BALANCING PROPELLER - IMU LIVE VIEWER (HARDWARE ASLI)
 * ============================================================================
 * Representasi 3D alat ASLI. Sketch ini HANYA TAMPILAN:
 *   Uno (firmware kating) --USB--> GUI Python --UDP 9999--> sketch ini
 *
 * Pemilihan port, kolom sudut, nol-kan, balik arah, dan perekaman data
 * semuanya diatur di GUI Python (kartu "Sumber Data", mode Hardware).
 *
 * Struktur modul:
 * - BalancingPropellerIMU.pde : setup(), draw()
 * - NetworkIMU.pde            : penerima UDP + balasan ACK
 * - CameraIMU.pde             : kamera orbit, lampu, lantai, keyboard/mouse
 * - ModelIMU.pde              : model 3D (disalin dari BalancingPropellerViewer)
 * - HudIMU.pde                : panel status & grafik sudut (layer 2D tajam)
 * ============================================================================
 */

float targetTheta = 0.0;     // sudut dari GUI (deg, sudah dipetakan & di-nol-kan)
float currentTheta = 0.0;    // sudut ter-smoothing untuk model 3D
float setpointTheta = 0.0;
float loadMass = 0.0;        // kg, keterangan beban fisik dari GUI
float loadPos = 0.10;        // m
final float SMOOTH_ALPHA = 0.45;

// riwayat sudut untuk grafik (60 fps x 10 s)
final int HIST_LEN = 600;
float[] angleHist = new float[HIST_LEN];
boolean[] histValid = new boolean[HIST_LEN];
int histIdx = 0;

void settings() {
  size(1120, 700, P3D);
  pixelDensity(displayDensity());   // layar HiDPI (125%/150%) -> tetap tajam
  smooth(8);
}

void setup() {
  surface.setTitle("Balancing Propeller - IMU Live (Hardware Asli)");
  surface.setResizable(true);
  frameRate(60);
  initHud();
  initNetwork();
}

void draw() {
  pollUDP();

  boolean live = dataLive();
  angleHist[histIdx] = targetTheta;
  histValid[histIdx] = live;
  histIdx = (histIdx + 1) % HIST_LEN;

  currentTheta += (targetTheta - currentTheta) * SMOOTH_ALPHA;

  background(24, 26, 31);
  setupLights();
  setupCamera();
  drawEnvironment();
  drawApparatusIMU();

  if (showHUD) drawHudIMU();
}

void exit() {
  closeNetwork();
  super.exit();
}
