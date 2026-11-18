/*
 * ============================================================================
 * ESP32 + IMU GY-521 + 2 MOTOR A2212 (ESC 30A) - TES MOTOR / UKUR Fmax
 * ============================================================================
 * Turunan dari esp32_imu_test. Tambahan: tiap motor digerakkan MANUAL dari
 * GUI (slider throttle) untuk mengukur gaya dorong F1 / F2. Belum ada PID.
 *
 * OUTPUT (ke GUI, tidak berubah dari esp32_imu_test):
 *     *,f1,f2,f3,f4,f5,f6,f7,f8,#        (115200 baud)
 *   Baris tanpa '*' = pesan teks.
 *
 * PERINTAH (dari GUI / Serial Monitor, akhiri newline):
 *   c            kalibrasi ulang bias gyro (alat harus diam)
 *   M,<L>,<R>    throttle motor kiri & kanan dalam persen 0..100
 *                contoh: M,35.5,0
 *   x            STOP: kedua motor 0
 *
 * KESELAMATAN
 *   - Boot: ESC di-ARM dengan pulsa 1000 us selama ~3 s, motor diam.
 *   - FAILSAFE: tidak ada perintah 'M' selama CMD_TIMEOUT_MS -> motor 0.
 *     GUI harus mengirim 'M' berulang (heartbeat) selama motor berputar.
 *   - Throttle dibatasi MAX_THROTTLE_PCT.
 *   - LEPAS BALING-BALING atau jauhkan tangan saat uji pertama!
 *
 * ----------------------------------------------------------------------------
 * WIRING
 * ----------------------------------------------------------------------------
 *   IMU : SDA -> GPIO21, SCL -> GPIO22, VCC -> 3V3, GND -> GND
 *   ESC kiri  (motor CCW) sinyal -> GPIO26
 *   ESC kanan (motor CW)  sinyal -> GPIO25
 *   GND ESC (kabel sinyal) HARUS disambung ke GND ESP32.
 *   Daya ESC dari baterai LiPo (JANGAN dari ESP32). Kabel merah 5V BEC ESC
 *   tidak perlu dihubungkan ke ESP32 (lepas/biarkan) agar tidak bentrok
 *   dengan USB.
 * ============================================================================
 */

#include <Wire.h>
#include <math.h>

// ----------------------------- konfigurasi ---------------------------------
#define I2C_SDA        21
#define I2C_SCL        22
#define I2C_HZ         400000
#define MPU_ADDR       0x68

#define PIN_MOTOR_L    26          // motor kiri  CCW
#define PIN_MOTOR_R    25          // motor kanan CW
#define LED_PIN        2
#define LED_OK_MS      500
#define LED_ERR_MS     100

#define ESC_FREQ_HZ    50
#define ESC_MIN_US     1000        // throttle 0 %
#define ESC_MAX_US     2000        // throttle 100 %
#define ESC_ARM_MS     3000        // lama kirim 1000 us saat boot
#define MAX_THROTTLE_PCT 100.0f    // batas atas keselamatan (turunkan jika perlu)
#define CMD_TIMEOUT_MS 500         // failsafe

#define BAUD           115200
#define SAMPLE_HZ      500
#define OUTPUT_HZ      100

#define BEAM_AXIS      1
#define BEAM_SIGN      1
#define COMP_ALPHA     0.98f
#define CALIB_SAMPLES  1000

// ----------------------------- register MPU6050 ----------------------------
#define REG_SMPLRT_DIV   0x19
#define REG_CONFIG       0x1A
#define REG_GYRO_CONFIG  0x1B
#define REG_ACCEL_CONFIG 0x1C
#define REG_ACCEL_XOUT_H 0x3B
#define REG_PWR_MGMT_1   0x6B
#define REG_WHO_AM_I     0x75

const float ACC_LSB_PER_G   = 16384.0f;
const float GYRO_LSB_PER_DPS = 131.0f;

// ----------------------------- state ---------------------------------------
float gyroBias[3] = {0, 0, 0};
float angRoll = 0, angPitch = 0;
float ax_g = 0, ay_g = 0, az_g = 0, tempC = 0;
float gx_dps = 0, gy_dps = 0, gz_dps = 0;

uint32_t lastSampleUs = 0, lastOutUs = 0;
uint32_t loopCount = 0, rateT0 = 0;
float loopHz = 0;
uint32_t i2cErrors = 0;
bool imuOk = false;
uint32_t lastLedMs = 0, lastErrMs = 0;
bool ledState = false;

float thrL = 0, thrR = 0;          // throttle aktif (%)
uint32_t lastCmdMs = 0;
bool failsafeActive = false;
char cmdBuf[40];
uint8_t cmdLen = 0;

// ----------------------------- ESC (LEDC) ----------------------------------
#define ESC_RES_BITS 16
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  #define ESC_ATTACH(pin, ch) ledcAttach(pin, ESC_FREQ_HZ, ESC_RES_BITS)
  #define ESC_WRITE(pin, ch, duty) ledcWrite(pin, duty)
#else
  #define ESC_ATTACH(pin, ch) do { ledcSetup(ch, ESC_FREQ_HZ, ESC_RES_BITS); ledcAttachPin(pin, ch); } while (0)
  #define ESC_WRITE(pin, ch, duty) ledcWrite(ch, duty)
#endif

void escWriteUs(int pin, int ch, float us) {
  float period_us = 1000000.0f / ESC_FREQ_HZ;
  uint32_t duty = (uint32_t)(us / period_us * ((1UL << ESC_RES_BITS) - 1));
  ESC_WRITE(pin, ch, duty);
}

void setMotors(float l, float r) {
  l = constrain(l, 0.0f, MAX_THROTTLE_PCT);
  r = constrain(r, 0.0f, MAX_THROTTLE_PCT);
  thrL = l; thrR = r;
  escWriteUs(PIN_MOTOR_L, 0, ESC_MIN_US + (ESC_MAX_US - ESC_MIN_US) * l / 100.0f);
  escWriteUs(PIN_MOTOR_R, 1, ESC_MIN_US + (ESC_MAX_US - ESC_MIN_US) * r / 100.0f);
}

void handleCommand(const char *s) {
  if (s[0] == 'M' && s[1] == ',') {
    float l = 0, r = 0;
    if (sscanf(s + 2, "%f,%f", &l, &r) == 2) {
      setMotors(l, r);
      lastCmdMs = millis();
      if (failsafeActive) { failsafeActive = false; Serial.println("Failsafe selesai, perintah motor diterima."); }
    }
  } else if (s[0] == 'x' || s[0] == 'X') {
    setMotors(0, 0);
    Serial.println("STOP motor.");
  } else if (s[0] == 'c' || s[0] == 'C') {
    setMotors(0, 0);             // kalibrasi butuh alat diam
    calibrateGyro();
  }
}

void readSerialCommands() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (cmdLen > 0) { cmdBuf[cmdLen] = 0; handleCommand(cmdBuf); cmdLen = 0; }
    } else if (cmdLen < sizeof(cmdBuf) - 1) {
      cmdBuf[cmdLen++] = c;
    } else {
      cmdLen = 0;                // baris terlalu panjang -> buang
    }
  }
  // failsafe: tidak ada perintah terbaru -> matikan motor
  if ((thrL > 0 || thrR > 0) && (millis() - lastCmdMs) > CMD_TIMEOUT_MS) {
    setMotors(0, 0);
    failsafeActive = true;
    Serial.println("FAILSAFE: tidak ada perintah, motor dimatikan.");
  }
}

// ----------------------------- LED -----------------------------------------
void updateLed() {
  uint32_t ms = millis();
  uint32_t period = (lastErrMs && (ms - lastErrMs) < 1000) ? LED_ERR_MS : LED_OK_MS;
  if (thrL > 0 || thrR > 0) period = 150;      // kedip cepat = motor aktif
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
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((uint8_t)MPU_ADDR, n) != n) return false;
  for (uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}

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

float accRoll()  { return atan2f(ay_g, az_g) * RAD_TO_DEG; }
float accPitch() { return atan2f(-ax_g, sqrtf(ay_g * ay_g + az_g * az_g)) * RAD_TO_DEG; }

bool initImu() {
  uint8_t who = 0;
  if (!readRegs(REG_WHO_AM_I, &who, 1)) {
    Serial.printf("IMU tidak menjawab di alamat 0x%02X. Cek kabel SDA=%d SCL=%d, VCC, GND.\n",
                  MPU_ADDR, I2C_SDA, I2C_SCL);
    return false;
  }
  if (who != 0x68) {
    Serial.printf("Info: WHO_AM_I = 0x%02X (bukan 0x68, kemungkinan chip klon). Tetap dicoba.\n", who);
  }
  bool ok = true;
  ok &= writeReg(REG_PWR_MGMT_1, 0x01);
  delay(100);
  ok &= writeReg(REG_CONFIG, 0x03);
  ok &= writeReg(REG_SMPLRT_DIV, 0x01);
  ok &= writeReg(REG_GYRO_CONFIG, 0x00);
  ok &= writeReg(REG_ACCEL_CONFIG, 0x00);
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
  if (readImu()) {
    angRoll = accRoll();
    angPitch = accPitch();
  }
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // ESC: sinyal 1000 us SEGERA agar ESC tidak menerima sinyal liar
  ESC_ATTACH(PIN_MOTOR_L, 0);
  ESC_ATTACH(PIN_MOTOR_R, 1);
  setMotors(0, 0);

  Serial.begin(BAUD);
  delay(300);
  Serial.println();
  Serial.println("ESP32 motor test - GY-521 + 2x A2212/ESC");
  Serial.printf("Motor kiri CCW = IO%d, kanan CW = IO%d. Arming ESC %d ms...\n",
                PIN_MOTOR_L, PIN_MOTOR_R, ESC_ARM_MS);

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(I2C_HZ);

  uint32_t t0 = millis();
  while (!(imuOk = initImu())) {
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(1000);
  }
  calibrateGyro();                       // sambil menunggu, ESC sudah menerima 1000 us
  while (millis() - t0 < ESC_ARM_MS) delay(10);
  Serial.println("ESC siap (armed).");
  Serial.println("Perintah: M,<kiri%>,<kanan%> | x = stop | c = kalibrasi gyro");
  Serial.println("Format: *,sudut_lain,SUDUT,laju_dps,ax,ay,az,suhu,loop_hz,#");

  lastSampleUs = lastOutUs = micros();
  rateT0 = millis();
}

// ----------------------------- loop ----------------------------------------
void loop() {
  readSerialCommands();
  updateLed();

  uint32_t now = micros();
  if ((uint32_t)(now - lastSampleUs) < (1000000UL / SAMPLE_HZ)) return;
  float dt = (now - lastSampleUs) * 1e-6f;
  lastSampleUs = now;
  if (dt > 0.1f) dt = 0.1f;

  if (!readImu()) {
    i2cErrors++;
    lastErrMs = millis() | 1;
    if (i2cErrors % 100 == 1) Serial.printf("Error baca I2C (total %lu)\n", (unsigned long)i2cErrors);
    if (i2cErrors % 500 == 0) {
      Wire.end();
      Wire.begin(I2C_SDA, I2C_SCL);
      Wire.setClock(I2C_HZ);
      initImu();
    }
    return;
  }

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
