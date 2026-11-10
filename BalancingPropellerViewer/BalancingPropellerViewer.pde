/**
 * ============================================================================
 * BALANCING PROPELLER 3D VIEWER (PROCESSING 3D) - VERSI 2 UPGRADED
 * ============================================================================
 * Visualizer 3D real-time berkinerja tinggi pengganti Blender untuk proyek PSKD.
 * Menerima telemetri UDP dari GUI Python pada port 9999 dan membalas ACK.
 *
 * Struktur Modul PDE:
 * - BalancingPropellerViewer.pde : Main setup(), draw loop, & state telemetri utama.
 * - Network.pde                 : Protokol komunikasi UDP, parsing JSON, & ACK.
 * - Camera.pde                  : Kamera orbit 3D, pencahayaan, & event mouse/keyboard.
 * - Model.pde                   : Geometri 3D rakitan alat, motor, panah gaya, & busur derajat.
 * - HUD.pde                     : 2D Heads-Up Display overlay & status koneksi.
 * ============================================================================
 */

// ----------------------------------------------------------------------------
// STATE TELEMETRI GLOBAL
// ----------------------------------------------------------------------------
float targetTheta = 0.0;    // Sudut target batang dari Python (derajat)
float currentTheta = 0.0;   // Sudut ter-smoothing (derajat)
float prop1Rot = 0.0;       // Derajat rotasi propeler kiri
float prop2Rot = 0.0;       // Derajat rotasi propeler kanan
float setpointTheta = 0.0;  // Sudut target / setpoint
float controlU = 0.0;       // Sinyal kontrol U (%)
float loadMass = 0.0;       // Beban tambahan (kg)
float loadPos = 0.10;       // Posisi beban dari poros (m, default 10 cm)
float thrustF1 = 4.0;       // Thrust motor kiri (Newton), bias Fmax/2 = 8/2
float thrustF2 = 4.0;       // Thrust motor kanan (Newton), bias Fmax/2 = 8/2

final float SMOOTH_ALPHA = 0.45; // Faktor kehalusan gerak batang
boolean connected = false;

// Flash notifikasi saat ada impuls gangguan
int impulseFlashTimer = 0;

// ----------------------------------------------------------------------------
// SETUP
// ----------------------------------------------------------------------------
void setup() {
  size(980, 620, P3D);
  surface.setTitle("Balancing Propeller 3D Visualizer (PSKD - Versi 2)");
  smooth(8);
  frameRate(60);

  // Inisialisasi socket UDP
  initNetwork();
}

// ----------------------------------------------------------------------------
// DRAW LOOP UTAMA
// ----------------------------------------------------------------------------
void draw() {
  // 1. Polling data telemetri UDP dari Python
  pollUDP();

  connected = (millis() - lastPacketTime) < TIMEOUT_MS;

  // 2. Smoothing sudut batang (lerp)
  currentTheta += (targetTheta - currentTheta) * SMOOTH_ALPHA;

  // 3. Render 3D Scene
  background(24, 26, 31);
  setupLights();
  setupCamera();
  drawEnvironment();

  // 4. Gambar perakitan alat lengkap
  drawBalancingApparatus();

  // 5. Render HUD 2D
  if (showHUD) {
    drawHUD();
  }
}

// ----------------------------------------------------------------------------
// CLEANUP SAAT APLIKASI DITUTUP
// ----------------------------------------------------------------------------
void stop() {
  closeNetwork();
  super.stop();
}
