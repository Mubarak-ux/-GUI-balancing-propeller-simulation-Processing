/*
 * ============================================================================
 * ESP32 + IMU GY-521 (MPU6050) - TES BACA SUDUT (TAHAP 1)
 * ============================================================================
 * Tujuan tahap ini HANYA: ESP32 membaca IMU dan mengirim sudut lewat USB
 * Serial. Belum ada motor/ESC/PID.
 *
 * Format output SAMA dengan firmware Uno lama, jadi GUI Python (mode
 * Hardware) langsung bisa membaca tanpa diubah:
 *
 *     *,f1,f2,f3,f4,f5,f6,f7,f8,#        (115200 baud, diakhiri newline)
 *
 *   f1 = sudut sumbu LAIN (deg, filter komplementer)  -> untuk cek sumbu
 *   f2 = SUDUT BATANG (deg, filter komplementer)       -> dibaca GUI
 *   f3 = laju sudut batang dari gyro (deg/s)
 *   f4 = ax (g)    f5 = ay (g)    f6 = az (g)
 *   f7 = suhu sensor (degC)
 *   f8 = frekuensi loop baca IMU (Hz)
 *
 * Baris yang TIDAK diawali '*' adalah pesan teks (tampil di GUI sebagai
 * "Pesan Uno"), mis. status kalibrasi atau error I2C.
 *
 * ----------------------------------------------------------------------------
 * WIRING (ESP32 DevKit V1 / WROOM-32)
 * ----------------------------------------------------------------------------
 *   GY-521 VCC -> 3V3  (boleh juga VIN/5V, modul punya regulator sendiri)
 *   GY-521 GND -> GND
 *   GY-521 SDA -> GPIO 21
 *   GY-521 SCL -> GPIO 22
 *   GY-521 AD0 -> GND / dibiarkan (alamat 0x68). Jika AD0 ke 3V3 -> 0x69.
 *
 * ----------------------------------------------------------------------------
 * CARA PAKAI
 * ----------------------------------------------------------------------------
 *   1. Arduino IDE: Board "ESP32 Dev Module", pilih port COM ESP32, Upload.
 *      (Tidak perlu library tambahan, hanya Wire bawaan.)
 *   2. Saat menyala, DIAMKAN alat ~2 detik (kalibrasi bias gyro).
 *   3. Buka Serial Monitor/Plotter 115200, atau GUI Python mode Hardware.
 *   4. Miringkan batang: kalau yang berubah malah f1 (bukan f2), ganti
 *      BEAM_AXIS di bawah. Kalau arahnya terbalik, pakai tombol "balik
 *      arah" di GUI, atau set BEAM_SIGN = -1.
 * ============================================================================
 */

#include <Wire.h>
#include <math.h>

// ----------------------------- konfigurasi ---------------------------------
#define I2C_SDA        21
#define I2C_SCL        22
#define I2C_HZ         400000      // 400 kHz (turunkan ke 100000 jika kabel panjang)
#define MPU_ADDR       0x68        // 0x69 jika pin AD0 dihubungkan ke 3V3

#define LED_PIN        2           // D2 / GPIO2 (LED onboard DevKit V1)
#define LED_OK_MS      500         // kedip lambat  = normal (toggle tiap 500 ms)
#define LED_ERR_MS     100         // kedip cepat   = ada error baca I2C

#define BAUD           115200
#define SAMPLE_HZ      500         // laju baca IMU + update filter
#define OUTPUT_HZ      100         // laju kirim baris ke Serial

#define BEAM_AXIS      1         // 0 = putar terhadap sumbu X (roll), 1 = sumbu Y (pitch)
#define BEAM_SIGN      1        // 1 atau -1 untuk membalik arah sudut (-1: sesuai alat asli)
#define COMP_ALPHA     0.98f       // bobot gyro pada filter komplementer
#define CALIB_SAMPLES  1000        // ~2 s @ 500 Hz

// ----------------------------- register MPU6050 ----------------------------
#define REG_SMPLRT_DIV   0x19
#define REG_CONFIG       0x1A
#define REG_GYRO_CONFIG  0x1B
#define REG_ACCEL_CONFIG 0x1C
#define REG_ACCEL_XOUT_H 0x3B
#define REG_PWR_MGMT_1   0x6B
#define REG_WHO_AM_I     0x75

const float ACC_LSB_PER_G   = 16384.0f;  // +-2 g
const float GYRO_LSB_PER_DPS = 131.0f;   // +-250 deg/s

// ----------------------------- state ---------------------------------------
float gyroBias[3] = {0, 0, 0};
float angRoll = 0, angPitch = 0;         // hasil filter komplementer (deg)
float ax_g = 0, ay_g = 0, az_g = 0, tempC = 0;
float gx_dps = 0, gy_dps = 0, gz_dps = 0;

uint32_t lastSampleUs = 0, lastOutUs = 0;
uint32_t loopCount = 0, rateT0 = 0;
float loopHz = 0;
uint32_t i2cErrors = 0;
bool imuOk = false;
uint32_t lastLedMs = 0, lastErrMs = 0;
bool ledState = false;

// Kedip LED non-blocking. Cepat selama 1 detik setelah error I2C terakhir.
void updateLed() {
  uint32_t ms = millis();
  uint32_t period = (lastErrMs && (ms - lastErrMs) < 1000) ? LED_ERR_MS : LED_OK_MS;
  if (ms - lastLedMs >= period) {
    lastLedMs = ms;
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
  }
}

// ----------------------------- I2C helper ----------------------------------
bool writeReg(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

bool readRegs(uint8_t reg, uint8_t *buf, uint8_t n) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;   // repeated start
  if (Wire.requestFrom((uint8_t)MPU_ADDR, n) != n) return false;
  for (uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}

// Baca accel + suhu + gyro sekaligus (14 byte). Gyro sudah dikurangi bias.
bool readImu() {
  uint8_t b[14];
  if (!readRegs(REG_ACCEL_XOUT_H, b, 14)) return false;
  int16_t ax = (b[0] << 8) | b[1];
  int16_t ay = (b[2] << 8) | b[3];
  int16_t az = (b[4] << 8) | b[5];
  int16_t t  = (b[6] << 8) | b[7];
  int16_t gx = (b[8] << 8) | b[9];
  int16_t gy = (b[10] << 8) | b[11];
  int16_t gz = (b[12] << 8) | b[13];
  ax_g = ax / ACC_LSB_PER_G;
  ay_g = ay / ACC_LSB_PER_G;
  az_g = az / ACC_LSB_PER_G;
  tempC = t / 340.0f + 36.53f;
  gx_dps = gx / GYRO_LSB_PER_DPS - gyroBias[0];
  gy_dps = gy / GYRO_LSB_PER_DPS - gyroBias[1];
  gz_dps = gz / GYRO_LSB_PER_DPS - gyroBias[2];
  return true;
}

// Sudut dari accelerometer saja (deg)
float accRoll()  { return atan2f(ay_g, az_g) * RAD_TO_DEG; }
float accPitch() { return atan2f(-ax_g, sqrtf(ay_g * ay_g + az_g * az_g)) * RAD_TO_DEG; }

// ----------------------------- inisialisasi --------------------------------
bool initImu() {
  uint8_t who = 0;
  if (!readRegs(REG_WHO_AM_I, &who, 1)) {
    Serial.printf("IMU tidak menjawab di alamat 0x%02X. Cek kabel SDA=%d SCL=%d, VCC, GND.\n",
                  MPU_ADDR, I2C_SDA, I2C_SCL);
    return false;
  }
  // MPU6050 asli = 0x68. Modul klon sering MPU6500/9250 (0x70/0x71/0x73) -
  // register accel/gyro sama, jadi tetap dipakai, cukup diberi info.
  if (who != 0x68) {
    Serial.printf("Info: WHO_AM_I = 0x%02X (bukan 0x68, kemungkinan chip klon). Tetap dicoba.\n", who);
  }
  bool ok = true;
  ok &= writeReg(REG_PWR_MGMT_1, 0x01);     // bangun, clock dari gyro X (lebih stabil)
  delay(100);
  ok &= writeReg(REG_CONFIG, 0x03);         // DLPF ~44 Hz (redam getaran propeller)
  ok &= writeReg(REG_SMPLRT_DIV, 0x01);     // 1 kHz / (1+1) = 500 Hz
  ok &= writeReg(REG_GYRO_CONFIG, 0x00);    // +-250 deg/s
  ok &= writeReg(REG_ACCEL_CONFIG, 0x00);   // +-2 g
  if (!ok) Serial.println("Gagal menulis konfigurasi IMU.");
  return ok;
}

void calibrateGyro() {
  Serial.println("Kalibrasi gyro: DIAMKAN alat ~2 detik...");
  float sum[3] = {0, 0, 0};
  int n = 0;
  float saved[3] = {gyroBias[0], gyroBias[1], gyroBias[2]};
  gyroBias[0] = gyroBias[1] = gyroBias[2] = 0;
  for (int i = 0; i < CALIB_SAMPLES; i++) {
    if (readImu()) {
      sum[0] += gx_dps; sum[1] += gy_dps; sum[2] += gz_dps;
      n++;
    }
    delayMicroseconds(1000000 / SAMPLE_HZ);
  }
  if (n < CALIB_SAMPLES / 2) {
    Serial.println("Kalibrasi gagal (terlalu banyak error I2C), bias lama dipakai.");
    for (int k = 0; k < 3; k++) gyroBias[k] = saved[k];
    return;
  }
  for (int k = 0; k < 3; k++) gyroBias[k] = sum[k] / n;
  Serial.printf("Bias gyro (deg/s): x=%.3f y=%.3f z=%.3f\n", gyroBias[0], gyroBias[1], gyroBias[2]);

  // sudut awal dari accelerometer supaya filter tidak start dari 0
  if (readImu()) {
    angRoll = accRoll();
    angPitch = accPitch();
  }
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Serial.begin(BAUD);
  delay(300);
  Serial.println();
  Serial.println("ESP32 IMU test - GY-521/MPU6050");

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(I2C_HZ);

  while (!(imuOk = initImu())) {
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));   // kedip saat IMU belum terdeteksi
    delay(1000);                 // coba terus sampai IMU terdeteksi
  }
  calibrateGyro();
  Serial.println("Siap. Kirim 'c' lewat Serial untuk kalibrasi ulang gyro.");
  Serial.println("Format: *,sudut_lain,SUDUT,laju_dps,ax,ay,az,suhu,loop_hz,#");

  lastSampleUs = lastOutUs = micros();
  rateT0 = millis();
}

// ----------------------------- loop ----------------------------------------
void loop() {
  // perintah sederhana dari Serial Monitor
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'c' || c == 'C') calibrateGyro();
  }

  updateLed();

  uint32_t now = micros();
  if ((uint32_t)(now - lastSampleUs) < (1000000UL / SAMPLE_HZ)) return;
  float dt = (now - lastSampleUs) * 1e-6f;
  lastSampleUs = now;
  if (dt > 0.1f) dt = 0.1f;      // jaga-jaga setelah jeda panjang

  if (!readImu()) {
    i2cErrors++;
    lastErrMs = millis() | 1;    // tandai waktu error (|1 agar tidak 0)
    if (i2cErrors % 100 == 1) Serial.printf("Error baca I2C (total %lu)\n", (unsigned long)i2cErrors);
    if (i2cErrors % 500 == 0) {  // coba pulihkan bus + sensor
      Wire.end();
      Wire.begin(I2C_SDA, I2C_SCL);
      Wire.setClock(I2C_HZ);
      initImu();
    }
    return;
  }

  // filter komplementer: gyro (halus, tapi drift) + accel (absolut, tapi bising)
  angRoll  = COMP_ALPHA * (angRoll  + gx_dps * dt) + (1.0f - COMP_ALPHA) * accRoll();
  angPitch = COMP_ALPHA * (angPitch + gy_dps * dt) + (1.0f - COMP_ALPHA) * accPitch();

  loopCount++;
  uint32_t ms = millis();
  if (ms - rateT0 >= 1000) {
    loopHz = loopCount * 1000.0f / (ms - rateT0);
    loopCount = 0;
    rateT0 = ms;
  }

  if ((uint32_t)(now - lastOutUs) >= (1000000UL / OUTPUT_HZ)) {
    lastOutUs = now;
#if BEAM_AXIS == 0
    float beam = angRoll,  other = angPitch, rate = gx_dps;
#else
    float beam = angPitch, other = angRoll,  rate = gy_dps;
#endif
    beam *= BEAM_SIGN;
    rate *= BEAM_SIGN;
    Serial.printf("*,%.2f,%.2f,%.2f,%.3f,%.3f,%.3f,%.1f,%.0f,#\n",
                  other, beam, rate, ax_g, ay_g, az_g, tempC, loopHz);
  }
}
