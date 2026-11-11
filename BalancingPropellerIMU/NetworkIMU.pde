/**
 * ============================================================================
 * NETWORKIMU.PDE - Penerima Telemetri UDP dari GUI Python
 * ============================================================================
 * Sketch ini TIDAK membuka port serial. Semua data (sudut, kolom mentah Uno,
 * status port, status rekam) datang dari GUI Python lewat UDP port 9999,
 * sama seperti BalancingPropellerViewer. Setiap paket dibalas "ack" supaya
 * GUI tahu Processing aktif.
 *
 * Kunci JSON yang dipakai:
 *   th, sp, load_m, load_x          (sama dengan viewer simulasi)
 *   mode  "sim" / "hw"
 *   conn  1 jika data Uno masuk
 *   port  nama port, inv, off, rate, rec, lbl
 *
 * Catatan: hanya satu program yang bisa memakai port 9999. Jalankan
 * sketch ini ATAU BalancingPropellerViewer, jangan keduanya.
 * ============================================================================
 */

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.SocketException;

final int UDP_PORT = 9999;
final int GUI_TIMEOUT_MS = 1500;

DatagramSocket socket;
final byte[] receiveBuffer = new byte[4096];
final byte[] ackBytes = "ack".getBytes();
final byte[] impulseBytes = "impulse".getBytes();
String netError = null;

int lastPacketTime = -100000;

// alamat terakhir GUI yang mengirim paket (tujuan balasan "impulse")
InetAddress lastGuiAddr = null;
int lastGuiPort = -1;

// propeler & thrust (mode simulasi)
final float PROP_WRAP_PERIOD = 360000.0;   // sinkron dengan MainWindow.PROP_WRAP
float prop1Rot = 0, prop2Rot = 0;
float lastProp1 = 0, lastProp2 = 0;
boolean havePropRef = false;
float thrustF1 = 0, thrustF2 = 0;

// data dari GUI
String srcMode = "";
boolean hwConn = false;
String hwPort = "";
boolean angleInv = false;
float angleOff = 0;
float hwRate = 0;
boolean recActive = false;
String recLabel = "";

void initNetwork() {
  try {
    socket = new DatagramSocket(UDP_PORT);
    socket.setSoTimeout(1);
    println("[UDP] Menunggu GUI di port " + UDP_PORT);
  } catch (SocketException e) {
    netError = "Port UDP " + UDP_PORT + " dipakai program lain (viewer simulasi masih jalan?)";
    println("[UDP] " + netError + ": " + e.getMessage());
  }
}

boolean guiConnected() {
  return (millis() - lastPacketTime) < GUI_TIMEOUT_MS;
}

boolean isSimMode() {
  return guiConnected() && !srcMode.equals("hw");
}

// sudut valid = GUI tersambung DAN (mode simulasi ATAU data Uno masuk)
boolean dataLive() {
  return guiConnected() && (!srcMode.equals("hw") || hwConn);
}

void pollUDP() {
  if (socket == null) return;

  String latest = null;
  InetAddress addr = null;
  int port = -1;
  while (true) {
    try {
      DatagramPacket p = new DatagramPacket(receiveBuffer, receiveBuffer.length);
      socket.receive(p);
      addr = p.getAddress();
      port = p.getPort();
      latest = new String(p.getData(), 0, p.getLength(), "UTF-8");
    } catch (Exception e) {
      break;
    }
  }
  if (latest == null) return;

  try {
    socket.send(new DatagramPacket(ackBytes, ackBytes.length, addr, port));
  } catch (Exception e) {
    // abaikan
  }
  lastGuiAddr = addr;
  lastGuiPort = port;

  try {
    JSONObject j = parseJSONObject(latest);
    if (j == null) return;
    if (j.hasKey("th"))     targetTheta = j.getFloat("th");
    if (j.hasKey("sp"))     setpointTheta = j.getFloat("sp");
    if (j.hasKey("load_m")) loadMass = j.getFloat("load_m");
    if (j.hasKey("load_x")) loadPos = j.getFloat("load_x");
    if (j.hasKey("f1"))     thrustF1 = j.getFloat("f1");
    if (j.hasKey("f2"))     thrustF2 = j.getFloat("f2");

    // sudut putar propeler kumulatif dari GUI (sama dengan Network.pde lama)
    if (j.hasKey("prop1")) {
      float p1 = j.getFloat("prop1");
      if (havePropRef) prop1Rot += circularDelta(p1, lastProp1, PROP_WRAP_PERIOD);
      lastProp1 = p1;
    }
    if (j.hasKey("prop2")) {
      float p2 = j.getFloat("prop2");
      if (havePropRef) prop2Rot -= circularDelta(p2, lastProp2, PROP_WRAP_PERIOD);
      lastProp2 = p2;
    }
    havePropRef = true;

    srcMode   = j.getString("mode", "sim");
    hwConn    = j.getInt("conn", 1) == 1;
    hwPort    = j.getString("port", "");
    angleInv  = j.getInt("inv", 0) == 1;
    angleOff  = j.getFloat("off", 0);
    hwRate    = j.getFloat("rate", 0);
    recActive = j.getInt("rec", 0) == 1;
    recLabel  = j.getString("lbl", "");
    lastPacketTime = millis();
  } catch (Exception e) {
    // paket rusak, abaikan
  }
}

// Kirim sinyal impuls ke GUI (dipanggil dari keyPressed SPACE).
// GUI membalas ACK atas paket "impulse" ini dan menerapkannya ke simulasi.
void sendImpulse() {
  if (socket == null || lastGuiAddr == null || lastGuiPort < 0) return;
  try {
    socket.send(new DatagramPacket(impulseBytes, impulseBytes.length,
                                   lastGuiAddr, lastGuiPort));
  } catch (Exception e) {
    // abaikan
  }
}

float circularDelta(float curr, float prev, float period) {
  float d = (curr - prev) % period;
  if (d > period / 2.0) d -= period;
  if (d < -period / 2.0) d += period;
  return d;
}

void closeNetwork() {
  if (socket != null && !socket.isClosed()) socket.close();
}
