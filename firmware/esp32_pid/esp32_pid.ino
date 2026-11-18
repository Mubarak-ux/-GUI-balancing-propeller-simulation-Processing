/*
 * ============================================================================
 * ESP32 + IMU GY-521 + 2 MOTOR A2212 (ESC 30A) - KONTROL PID SUDUT BATANG
 * ============================================================================
 * Turunan dari esp32_motor_test. PID berjalan DI ESP32 (loop 500 Hz); GUI hanya
 * mengirim setpoint + gain lewat heartbeat 10 Hz.
 *
 * KONVENSI (sama dengan simulasi):
 *   sudut + = sisi KANAN naik. Motor kiri = F1 (IO26, CCW), kanan = F2 (IO25, CW).
 *   u > 0 -> motor kanan naik, kiri turun.
 *   u (-100..100 %) -> throttle:  kiri  = BIAS - d,  kanan = BIAS + d
 *                      d = u/100 * R,  R = (Fmax - 8) / 2
 *   BIAS = (8 + Fmax) / 2 (tengah rentang): Fmax 15 -> 11,5 +/- 3,5 %; Fmax 10 -> 9 +/- 1 %.
 *   PID: u = Kp*e + I - Kd*(laju sudut gyro),  e = setpoint - sudut
 *        satuan: Kp %/deg, Ki %/(deg.s), Kd %/(deg/s)   (sama dengan GUI)
 *
 * PERINTAH (akhiri newline):
 *   P,<on>,<sp_raw>,<kp>,<ki>,<kd>,<dir>[,<cutoff_deg>,<cutoff_on>[,<trim>]]
 *        heartbeat PID (kirim tiap <=100 ms). cutoff_deg 29..33, cutoff_on 1/0
 *        (0 = batas mati sudut dimatikan; failsafe & data IMU tetap aktif).
 *        on=1 aktif / 0 mati, sp_raw = setpoint di bingkai sudut firmware (deg),
 *        dir = +1 / -1 (tanda bingkai tampilan GUI terhadap sudut firmware).
 *   M,<kiri>,<kanan>   manual (hanya saat PID mati)
 *   F,<pct>            F-max 8..20 % (batas PID; tes manual M tetap 0..100 %)
 *   Z                  nolkan integral PID
 *   x                  STOP (PID mati, motor 0)
 *   c                  kalibrasi gyro (alat harus diam)
 *
 * KESELAMATAN
 *   - Failsafe: tidak ada perintah > CMD_TIMEOUT_MS -> PID mati, motor 0.
 *   - Sudut |theta| > CUTOFF_DEG -> PID mati, motor 0.
 *   - Data IMU tidak masuk > IMU_STALE_MS -> PID mati, motor 0.
 *   - PID hanya boleh dinyalakan jika |theta| <= START_MAX_DEG.
 *   - PID dijepit 0..Fmax (Fmax <= 20 %). Tes manual (M) dijepit 0..100 %.
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
#define ESC_MIN_US     1000
#define ESC_MAX_US     2000
#define ESC_ARM_MS     3000
#define MIN_THROTTLE_PCT 8.0f      // F-min
#define MAX_THROTTLE_PCT 20.0f     // batas KERAS atas F-max (PID)
#define MANUAL_MAX_PCT   100.0f    // batas tes motor manual (perintah M)
#define CMD_TIMEOUT_MS 500

#define CUTOFF_DEG     32.0f       // mati jika |sudut| lebih dari ini
#define CUTOFF_MIN_DEG 29.0f       // rentang yang boleh diatur dari GUI
#define CUTOFF_MAX_DEG 33.0f
#define START_MAX_DEG  30.0f       // PID hanya boleh mulai jika |sudut| <= ini
#define SP_LIMIT_DEG   20.0f
#define IMU_STALE_MS   50
#define KP_MAX         5.0f
#define KI_MAX         3.0f
#define KD_MAX         1.5f

#define BAUD           115200
#define SAMPLE_HZ      500
#define OUTPUT_HZ      100

#define BEAM_AXIS      1
#define BEAM_SIGN      1
// Filter komplementer berbasis konstanta waktu (tidak bergantung laju loop).
// Data 18-11: getaran baling-baling membuat accel bergetar 0,21 g (motor mati
// 0,002 g). tau 0,1 s lama -> sudut ikut bergetar; tau 0,7 s meredamnya,
// sementara gyro tetap membawa gerak cepat.
#define COMP_TAU_S     0.7f
#define MPU_DLPF_CFG   0x04        // DLPF ~21 Hz (sebelumnya 0x03 = 44 Hz)
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
float beamDeg = 0, beamRate = 0, otherDeg = 0;   // bingkai firmware (setelah BEAM_SIGN)

uint32_t lastSampleUs = 0, lastOutUs = 0;
uint32_t loopCount = 0, rateT0 = 0;
float loopHz = 0;
uint32_t i2cErrors = 0;
bool imuOk = false;
uint32_t lastImuOkMs = 0;
uint32_t lastLedMs = 0, lastErrMs = 0;
bool ledState = false;

float thrL = 0, thrR = 0;
float fmaxPct = 15.0f;             // F-max aktif (8..20 %), default 15, diatur dari GUI
uint32_t lastCmdMs = 0;
char cmdBuf[64];
uint8_t cmdLen = 0;

// PID
bool  pidOn = false;
float spRaw = 0, kp = 0, ki = 0, kd = 0;
float dirS = 1.0f;
float cutoffDeg = CUTOFF_DEG;       // batas mati sudut (diatur GUI, 29..33 deg)
bool  cutoffOn = true;              // false = batas mati sudut dimatikan
float iTerm = 0, pTerm = 0, dTerm = 0, uOut = 0;
float trimU = 0;                    // feedforward/trim (%, bingkai firmware) dari GUI

// Soft-start (data 18-11: motor kiri start dari 0 langsung ke ~14 % tidak
// berputar normal / desync -> batang tidak terangkat 14 detik).
#define SPINUP_RAMP_MS  1000        // 0 -> Fmin
#define SPINUP_HOLD_MS  700         // tahan di Fmin agar kedua motor stabil berputar
#define SLEW_PCT_PER_S  40.0f       // batas laju perubahan throttle tiap motor
#define I_ZONE_DEG      6.0f        // di dalam zona integral penuh, di luar diperlambat
#define I_OUT_FACTOR    0.5f        // laju integral di luar zona (0 = mati -> error tunak tertahan)
uint32_t pidStartMs = 0;
float cmdL = 0, cmdR = 0;           // throttle setelah pembatas laju

// ----------------------------- ESC (LEDC) ----------------------------------
#define ESC_RES_BITS 16
#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  #define ESC_ATTACH(pin, ch) ledcAttach(pin, ESC_FREQ_HZ, ESC_RES_BITS)
  #define ESC_WRITE(pin, ch, duty) ledcWrite(pin, duty)
#else
  #define ESC_ATTACH(pin, ch) do { ledcSetup(ch, ESC_FREQ_HZ, ESC_RES_BITS); ledcAttachPin(pin, ch); } while (0)
  #define ESC_WRITE(pin, ch, duty) ledcWrite(ch, duty)
#endif

uint32_t usToDuty(float us) {
  float period_us = 1000000.0f / ESC_FREQ_HZ;
  return (uint32_t)(us / period_us * ((1UL << ESC_RES_BITS) - 1));
}

// ledcWrite bisa MEMBLOKIR hingga ~1 periode PWM (20 ms) -> data PID 18-11-2026
// menunjukkan loop turun dari 500 Hz ke 25 Hz (2 tulis x 20 ms) saat PID aktif.
// Solusi: loop kontrol hanya MENYIMPAN duty; penulisan ke LEDC dikerjakan task
// terpisah di core 0, jadi loop IMU + PID tetap 500 Hz.
volatile uint32_t escDutyL = 0, escDutyR = 0;
volatile bool escTaskRunning = false;
uint32_t escWriteUsMax = 0;          // diagnosa: waktu tulis LEDC terlama (us)

void escTask(void *) {
  uint32_t lastL = UINT32_MAX, lastR = UINT32_MAX;
  for (;;) {
    uint32_t l = escDutyL, r = escDutyR;
    if (l != lastL || r != lastR) {
      uint32_t t0 = micros();
      if (l != lastL) { ESC_WRITE(PIN_MOTOR_L, 0, l); lastL = l; }
      if (r != lastR) { ESC_WRITE(PIN_MOTOR_R, 1, r); lastR = r; }
      uint32_t dtw = micros() - t0;
      if (dtw > escWriteUsMax) escWriteUsMax = dtw;
    }
    vTaskDelay(pdMS_TO_TICKS(5));    // ESC hanya membaca 50 Hz; 200 Hz cukup
  }
}

// Tulis throttle kedua motor, dijepit ke 0..cap (%).
void setMotorsCap(float l, float r, float cap) {
  l = constrain(l, 0.0f, cap);
  r = constrain(r, 0.0f, cap);
  thrL = l; thrR = r;
  escDutyL = usToDuty(ESC_MIN_US + (ESC_MAX_US - ESC_MIN_US) * l / 100.0f);
  escDutyR = usToDuty(ESC_MIN_US + (ESC_MAX_US - ESC_MIN_US) * r / 100.0f);
  if (!escTaskRunning) {             // sebelum task jalan (awal setup): tulis langsung
    ESC_WRITE(PIN_MOTOR_L, 0, escDutyL);
    ESC_WRITE(PIN_MOTOR_R, 1, escDutyR);
  }
}

// PID & keadaan normal: dijepit ke F-max.
void setMotors(float l, float r) { setMotorsCap(l, r, fmaxPct); }

void pidOff(const char *why) {
  bool was = pidOn;
  pidOn = false;
  iTerm = pTerm = dTerm = uOut = 0;
  setMotors(0, 0);
  if (was && why) Serial.printf("PID MATI: %s\n", why);
  if (was) Serial.printf("Diag: loop %.0f Hz, tulis ESC terlama %lu us\n",
                         loopHz, (unsigned long)escWriteUsMax);
}

void calibrateGyro();

void handleCommand(const char *s) {
  if (s[0] == 'P' && s[1] == ',') {
    int on = 0, cOn = 1; float sp = 0, a = 0, b = 0, c = 0, d = 1, cDeg = CUTOFF_DEG, tr = 0;
    int n = sscanf(s + 2, "%d,%f,%f,%f,%f,%f,%f,%d,%f", &on, &sp, &a, &b, &c, &d, &cDeg, &cOn, &tr);
    if (n >= 6) {
      if (n >= 8) {                       // batas mati sudut dari GUI
        cutoffDeg = constrain(cDeg, CUTOFF_MIN_DEG, CUTOFF_MAX_DEG);
        cutoffOn = (cOn != 0);
      }
      if (n >= 9) trimU = constrain(tr, -60.0f, 60.0f);   // trim / feedforward
      if (on) {
        if (!pidOn) {
          // batas sudut awal hanya berlaku jika batas mati sudut AKTIF
          float startMax = min(START_MAX_DEG, cutoffDeg - 1.0f);
          if (cutoffOn && fabsf(beamDeg) > startMax) {
            static uint32_t lastMsgMs = 0;
            if (millis() - lastMsgMs > 1000) {          // jangan banjiri Serial
              lastMsgMs = millis();
              Serial.printf("PID ditolak: sudut %.1f deg di luar batas awal %.0f deg.\n", beamDeg, startMax);
            }
            lastCmdMs = millis();
            return;
          }
          iTerm = 0; pTerm = dTerm = uOut = 0;
          cmdL = thrL; cmdR = thrR;           // mulai dari throttle saat ini
          pidStartMs = millis();
          pidOn = true;
          Serial.println("PID AKTIF (soft-start ~1,7 s).");
        }
        spRaw = constrain(sp, -SP_LIMIT_DEG, SP_LIMIT_DEG);
        kp = constrain(a, 0.0f, KP_MAX);
        ki = constrain(b, 0.0f, KI_MAX);
        kd = constrain(c, 0.0f, KD_MAX);
        dirS = (d < 0) ? -1.0f : 1.0f;
      } else if (pidOn) {
        pidOff("diminta GUI");
      } else {
        setMotors(0, 0);
      }
      lastCmdMs = millis();
    }
  } else if (s[0] == 'M' && s[1] == ',') {
    if (pidOn) { Serial.println("M diabaikan: PID aktif."); return; }
    float l = 0, r = 0;
    if (sscanf(s + 2, "%f,%f", &l, &r) == 2) {
      setMotorsCap(l, r, MANUAL_MAX_PCT);   // tes manual: 0..100 %, tidak dibatasi F-max
      lastCmdMs = millis();
    }
  } else if (s[0] == 'F' && s[1] == ',') {
    float f = 0;
    if (sscanf(s + 2, "%f", &f) == 1) {
      fmaxPct = constrain(f, MIN_THROTTLE_PCT, MAX_THROTTLE_PCT);
      if (pidOn) setMotors(thrL, thrR);     // jepit ulang hanya untuk PID
      Serial.printf("F-max = %.1f %%\n", fmaxPct);
    }
  } else if (s[0] == 'Z') {                 // nolkan integral (dipakai saat trim diubah)
    iTerm = 0;
  } else if (s[0] == 'x' || s[0] == 'X') {
    pidOn = false; iTerm = pTerm = dTerm = uOut = 0;
    setMotors(0, 0);
    Serial.println("STOP motor.");
  } else if (s[0] == 'c' || s[0] == 'C') {
    pidOff(nullptr);
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
      cmdLen = 0;
    }
  }
  if ((pidOn || thrL > 0 || thrR > 0) && (millis() - lastCmdMs) > CMD_TIMEOUT_MS) {
    pidOn = false; iTerm = pTerm = dTerm = uOut = 0;
    setMotors(0, 0);
    Serial.println("FAILSAFE: tidak ada perintah, motor dimatikan.");
  }
}

// ----------------------------- LED -----------------------------------------
void updateLed() {
  uint32_t ms = millis();
  uint32_t period = (lastErrMs && (ms - lastErrMs) < 1000) ? LED_ERR_MS : LED_OK_MS;
  if (pidOn) period = 80;                       // PID aktif: kedip sangat cepat
  else if (thrL > 0 || thrR > 0) period = 150;  // manual
  if (ms - lastLedMs >= period) {
    lastLedMs = ms;
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
  }
}

// ----------------------------- PID -----------------------------------------
float slewTo(float cur, float target, float dt) {
  float step = SLEW_PCT_PER_S * dt;
  if (target > cur + step) return cur + step;
  if (target < cur - step) return cur - step;
  return target;
}

void runPid(float dt) {
  if (cutoffOn && fabsf(beamDeg) > cutoffDeg) { pidOff("sudut melebihi batas mati"); return; }
  uint32_t since = millis() - pidStartMs;

  // --- fase 1: soft-start, kedua motor naik bersama 0 -> Fmin lalu ditahan ---
  if (since < SPINUP_RAMP_MS + SPINUP_HOLD_MS) {
    float f = (since < SPINUP_RAMP_MS) ? MIN_THROTTLE_PCT * since / (float)SPINUP_RAMP_MS
                                       : MIN_THROTTLE_PCT;
    cmdL = cmdR = f;
    iTerm = pTerm = dTerm = uOut = 0;
    setMotors(cmdL, cmdR);
    return;
  }

  // --- fase 2: PID ---
  float e = spRaw - beamDeg;
  pTerm = kp * e;
  dTerm = -kd * beamRate;                      // turunan pada pengukuran (gyro)
  float uRaw = trimU + pTerm + iTerm + dTerm;
  float u = constrain(uRaw, -100.0f, 100.0f);
  // anti-windup: (1) clamping saat jenuh, (2) di luar I-zone integral DIPERLAMBAT
  // (bukan dimatikan). Data 18-11 (-10 ketiga): integral mati di luar zona ->
  // batang tertahan di -22 deg (error 12 deg) karena P saja kalah oleh torsi jatuh.
  float iRate = (fabsf(e) < I_ZONE_DEG) ? 1.0f : I_OUT_FACTOR;
  if (u == uRaw || uRaw * e < 0) iTerm += iRate * ki * e * dt;
  iTerm = constrain(iTerm, -100.0f, 100.0f);
  uOut = u;
  // Bias di TENGAH rentang kerja [Fmin, Fmax] -> ruang naik = ruang turun,
  // berapa pun F-max yang dipilih (F-max 15 -> bias 11,5 +/- 3,5 %).
  float bias = 0.5f * (MIN_THROTTLE_PCT + fmaxPct);
  float R = 0.5f * (fmaxPct - MIN_THROTTLE_PCT);
  float d = dirS * u / 100.0f * R;
  cmdL = slewTo(cmdL, bias - d, dt);           // pembatas laju: cegah lonjakan/desync
  cmdR = slewTo(cmdR, bias + d, dt);
  setMotors(cmdL, cmdR);                       // kiri turun / kanan naik saat d > 0
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
  ok &= writeReg(REG_CONFIG, MPU_DLPF_CFG);
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

  ESC_ATTACH(PIN_MOTOR_L, 0);
  ESC_ATTACH(PIN_MOTOR_R, 1);
  setMotors(0, 0);

  Serial.begin(BAUD);
  delay(300);
  Serial.println();
  Serial.println("ESP32 PID - GY-521 + 2x A2212/ESC");

  // diagnosa: berapa lama satu ledcWrite di board/core ini
  uint32_t tw = micros();
  ESC_WRITE(PIN_MOTOR_L, 0, escDutyL);
  tw = micros() - tw;
  Serial.printf("Waktu 1x tulis ESC (ledcWrite): %lu us\n", (unsigned long)tw);

  escTaskRunning = true;
  xTaskCreatePinnedToCore(escTask, "esc", 4096, nullptr, 2, nullptr, 0);
  Serial.printf("Kiri CCW = IO%d, kanan CW = IO%d. Rentang %.0f..%.0f %%, bias = tengah rentang.\n",
                PIN_MOTOR_L, PIN_MOTOR_R, MIN_THROTTLE_PCT, fmaxPct);

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(I2C_HZ);

  uint32_t t0 = millis();
  while (!(imuOk = initImu())) {
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(1000);
  }
  calibrateGyro();
  while (millis() - t0 < ESC_ARM_MS) delay(10);
  Serial.println("ESC siap (armed).");
  Serial.println("PID dikendalikan dari GUI. Format: *,sudut_lain,SUDUT,laju,ax,ay,az,suhu,loop_hz,pid_on,u,kiri%,kanan%,P,I,D,#");

  lastSampleUs = lastOutUs = micros();
  rateT0 = lastImuOkMs = millis();
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
    if (pidOn && (millis() - lastImuOkMs) > IMU_STALE_MS) pidOff("data IMU tidak masuk");
    if (i2cErrors % 100 == 1) Serial.printf("Error baca I2C (total %lu)\n", (unsigned long)i2cErrors);
    if (i2cErrors % 500 == 0) {
      Wire.end();
      Wire.begin(I2C_SDA, I2C_SCL);
      Wire.setClock(I2C_HZ);
      initImu();
    }
    return;
  }
  lastImuOkMs = millis();

  float alpha = COMP_TAU_S / (COMP_TAU_S + dt);
  angRoll  = alpha * (angRoll  + gx_dps * dt) + (1.0f - alpha) * accRoll();
  angPitch = alpha * (angPitch + gy_dps * dt) + (1.0f - alpha) * accPitch();

#if BEAM_AXIS == 0
  beamDeg = angRoll  * BEAM_SIGN; otherDeg = angPitch; beamRate = gx_dps * BEAM_SIGN;
#else
  beamDeg = angPitch * BEAM_SIGN; otherDeg = angRoll;  beamRate = gy_dps * BEAM_SIGN;
#endif

  if (pidOn) runPid(dt);

  loopCount++;
  uint32_t ms = millis();
  if (ms - rateT0 >= 1000) {
    loopHz = loopCount * 1000.0f / (ms - rateT0);
    loopCount = 0;
    rateT0 = ms;
  }

  if ((uint32_t)(now - lastOutUs) >= (1000000UL / OUTPUT_HZ)) {
    lastOutUs = now;
    Serial.printf("*,%.2f,%.2f,%.2f,%.3f,%.3f,%.3f,%.1f,%.0f,%d,%.1f,%.2f,%.2f,%.2f,%.2f,%.2f,#\n",
                  otherDeg, beamDeg, beamRate, ax_g, ay_g, az_g, tempC, loopHz,
                  pidOn ? 1 : 0, uOut, thrL, thrR, pTerm, iTerm, dTerm);
  }
}
