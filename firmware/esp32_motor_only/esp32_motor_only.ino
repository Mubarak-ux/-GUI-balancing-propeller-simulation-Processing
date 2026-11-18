/*
 * ============================================================================
 * ESP32 - TES MOTOR SAJA (tanpa IMU)  |  2x A2212 + ESC Readytosky 30A
 * ============================================================================
 * Motor kiri  (CCW) sinyal -> GPIO26
 * Motor kanan (CW)  sinyal -> GPIO25
 * GND sinyal ESC -> GND ESP32 (WAJIB). Daya ESC dari LiPo, bukan dari ESP32.
 *
 * Buka Serial Monitor 115200, pilih "Newline", lalu ketik perintah:
 *   M,<kiri>,<kanan>   throttle 0..100 %, contoh:  M,10,0   atau  M,0,10
 *   x                  STOP (kedua motor 0)
 *   H                  kirim 2000 us (throttle penuh) ke kedua ESC  \ kalibrasi
 *   L                  kirim 1000 us (throttle nol) ke kedua ESC    / ESC (lihat bawah)
 *   P,<kiri>,<kanan>   pulsa mentah dalam mikrodetik 1000..2000
 *
 * Failsafe: motor mati otomatis jika tidak ada perintah > CMD_TIMEOUT_MS.
 * Ketik ulang perintah (atau pakai GUI yang mengirim heartbeat) untuk lanjut.
 *
 * KALIBRASI THROTTLE ESC (jika motor tidak mau jalan):
 *   1. Lepas LiPo dari ESC. Ketik H (ESP32 kirim 2000 us), lalu pasang LiPo.
 *   2. Tunggu beep (ESC menangkap titik maks), lalu ketik L (1000 us).
 *   3. Tunggu beep konfirmasi. Selesai. Ketik x.
 *   LEPAS BALING-BALING saat kalibrasi dan uji pertama!
 * ============================================================================
 */

#define PIN_MOTOR_L      26
#define PIN_MOTOR_R      25
#define LED_PIN          2

#define ESC_FREQ_HZ      50
#define ESC_RES_BITS     16
#define ESC_MIN_US       1000
#define ESC_MAX_US       2000
#define ESC_ARM_MS       3000
#define MAX_THROTTLE_PCT 100.0f
#define CMD_TIMEOUT_MS   3000      // lebih longgar agar enak diketik manual
#define BAUD             115200

#if defined(ESP_ARDUINO_VERSION_MAJOR) && ESP_ARDUINO_VERSION_MAJOR >= 3
  #define ESC_ATTACH(pin, ch) ledcAttach(pin, ESC_FREQ_HZ, ESC_RES_BITS)
  #define ESC_WRITE(pin, ch, duty) ledcWrite(pin, duty)
#else
  #define ESC_ATTACH(pin, ch) do { ledcSetup(ch, ESC_FREQ_HZ, ESC_RES_BITS); ledcAttachPin(pin, ch); } while (0)
  #define ESC_WRITE(pin, ch, duty) ledcWrite(ch, duty)
#endif

float usL = ESC_MIN_US, usR = ESC_MIN_US;
uint32_t lastCmdMs = 0;
char cmdBuf[40];
uint8_t cmdLen = 0;

void escWriteUs(int pin, int ch, float us) {
  float period_us = 1000000.0f / ESC_FREQ_HZ;
  uint32_t duty = (uint32_t)(us / period_us * ((1UL << ESC_RES_BITS) - 1));
  ESC_WRITE(pin, ch, duty);
}

void setPulse(float l, float r) {
  usL = constrain(l, (float)ESC_MIN_US, (float)ESC_MAX_US);
  usR = constrain(r, (float)ESC_MIN_US, (float)ESC_MAX_US);
  escWriteUs(PIN_MOTOR_L, 0, usL);
  escWriteUs(PIN_MOTOR_R, 1, usR);
}

void setThrottle(float l, float r) {
  l = constrain(l, 0.0f, MAX_THROTTLE_PCT);
  r = constrain(r, 0.0f, MAX_THROTTLE_PCT);
  setPulse(ESC_MIN_US + (ESC_MAX_US - ESC_MIN_US) * l / 100.0f,
           ESC_MIN_US + (ESC_MAX_US - ESC_MIN_US) * r / 100.0f);
}

bool motorsOn() { return usL > ESC_MIN_US + 1 || usR > ESC_MIN_US + 1; }

bool calMode = false;   // true setelah 'H': 2000 us ditahan tanpa failsafe

void handleCommand(const char *s) {
  float a = 0, b = 0;
  if (s[0] != 'H') calMode = false;     // perintah lain mengakhiri mode kalibrasi
  if (s[0] == 'M' && sscanf(s + 1, " , %f , %f", &a, &b) == 2) {
    setThrottle(a, b);
    Serial.printf("OK throttle kiri=%.1f%% kanan=%.1f%% (pulsa %.0f / %.0f us)\n", a, b, usL, usR);
  } else if (s[0] == 'P' && sscanf(s + 1, " , %f , %f", &a, &b) == 2) {
    setPulse(a, b);
    Serial.printf("OK pulsa kiri=%.0f kanan=%.0f us\n", usL, usR);
  } else if (s[0] == 'x' || s[0] == 'X') {
    setPulse(ESC_MIN_US, ESC_MIN_US);
    Serial.println("STOP (1000 us)");
  } else if (s[0] == 'H') {
    calMode = true;                     // failsafe dimatikan sampai L / x / M
    setPulse(ESC_MAX_US, ESC_MAX_US);
    Serial.println("2000 us ke kedua ESC (kalibrasi maks). DITAHAN tanpa failsafe.");
    Serial.println("Sekarang nyalakan power supply, tunggu beep, lalu ketik L.");
  } else if (s[0] == 'L') {
    setPulse(ESC_MIN_US, ESC_MIN_US);
    Serial.println("1000 us ke kedua ESC (kalibrasi min)");
  } else {
    Serial.printf("Perintah tidak dikenal: '%s'\n", s);
    return;
  }
  lastCmdMs = millis();
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  ESC_ATTACH(PIN_MOTOR_L, 0);
  ESC_ATTACH(PIN_MOTOR_R, 1);
  setPulse(ESC_MIN_US, ESC_MIN_US);     // 1000 us segera

  Serial.begin(BAUD);
  delay(300);
  Serial.println();
  Serial.println("ESP32 MOTOR ONLY (tanpa IMU)");
  Serial.printf("Kiri CCW = IO%d, kanan CW = IO%d. Arming %d ms, jangan sentuh...\n",
                PIN_MOTOR_L, PIN_MOTOR_R, ESC_ARM_MS);
  delay(ESC_ARM_MS);
  Serial.println("Siap. Contoh: M,10,0  (kiri 10%)  |  x = stop  |  H/L = kalibrasi ESC");
  lastCmdMs = millis();
}

void loop() {
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

  if (!calMode && motorsOn() && (millis() - lastCmdMs) > CMD_TIMEOUT_MS) {
    setPulse(ESC_MIN_US, ESC_MIN_US);
    Serial.println("FAILSAFE: tidak ada perintah, motor dimatikan.");
  }

  digitalWrite(LED_PIN, motorsOn() ? ((millis() / 150) & 1) : ((millis() / 1000) & 1));
}
