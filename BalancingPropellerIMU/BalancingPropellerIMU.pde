/**
 * ============================================================================
 * BALANCING PROPELLER - VIEWER 3D (SIMULASI & HARDWARE)
 * ============================================================================
 * Representasi 3D alat, dipakai untuk mode Simulasi maupun Hardware. Sketch
 * ini HANYA TAMPILAN:
 *   Simulasi : GUI Python --UDP 9999--> sketch ini
 *   Hardware : Uno (firmware kating) --USB--> GUI Python --UDP 9999--> sketch ini
 *
 * Pemilihan port, kolom sudut, nol-kan, balik arah, dan perekaman data
 * semuanya diatur di GUI Python (kartu "Sumber Data").
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
  surface.setTitle("Balancing Propeller - Menunggu GUI"); 
  surface.setResizable(true);
  frameRate(60);
  initHud();
  initNetwork();
}

// Judul jendela menyesuaikan sumber data: Simulasi / Hardware / menunggu GUI.
String lastTitle = "";

void updateWindowTitle() {
  String title;
  if (!guiConnected()) {
    title = "Balancing Propeller - Menunggu GUI";
  } else if (srcMode.equals("hw")) {
    title = "Balancing Propeller - IMU Live (Hardware Asli)";
  } else {
    title = "Balancing Propeller - Simulasi";
  }
  if (!title.equals(lastTitle)) {
    surface.setTitle(title);
    lastTitle = title;
  }
}

void draw() {
  pollUDP();
  updateWindowTitle();

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
