/**
 * ============================================================================
 * NETWORK.PDE - Modul Komunikasi Telemetri UDP
 * ============================================================================
 * Menangani penerimaan paket telemetri JSON dari Python di port 9999,
 * mengirimkan balasan ACK, serta mengirimkan event gangguan impuls.
 */

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.SocketException;

// ----------------------------------------------------------------------------
// KONFIGURASI JARINGAN UDP
// ----------------------------------------------------------------------------
final int UDP_PORT = 9999;
DatagramSocket socket;
final byte[] receiveBuffer = new byte[2048];
final byte[] ackBytes = "ack".getBytes();
final byte[] impulseBytes = "impulse".getBytes();

InetAddress lastSenderAddr = null;
int lastSenderPort = -1;

int lastPacketTime = 0;
final int TIMEOUT_MS = 1500;

float lastProp1 = 0.0;
float lastProp2 = 0.0;
float deltaP1 = 0.0;
float deltaP2 = 0.0;
final float PROP_WRAP_PERIOD = 360000.0;

void initNetwork() {
  try {
    socket = new DatagramSocket(UDP_PORT);
    socket.setSoTimeout(1);
    println("[UDP] Server aktif di port " + UDP_PORT);
  } catch (SocketException e) {
    println("[UDP] Gagal membuka port " + UDP_PORT + ": " + e.getMessage());
  }
}

void pollUDP() {
  if (socket == null) return;

  boolean gotData = false;
  String latestJSON = null;

  while (true) {
    try {
      DatagramPacket packet = new DatagramPacket(receiveBuffer, receiveBuffer.length);
      socket.receive(packet);

      lastSenderAddr = packet.getAddress();
      lastSenderPort = packet.getPort();
      latestJSON = new String(packet.getData(), 0, packet.getLength(), "UTF-8");
      gotData = true;
    } catch (Exception e) {
      break;
    }
  }

  if (gotData && lastSenderAddr != null && lastSenderPort > 0) {
    // Balas ACK
    try {
      DatagramPacket ack = new DatagramPacket(ackBytes, ackBytes.length, lastSenderAddr, lastSenderPort);
      socket.send(ack);
    } catch (Exception e) {
      // Abaikan
    }

    // Parse JSON
    try {
      JSONObject json = parseJSONObject(latestJSON);
      if (json != null) {
        if (json.hasKey("th"))     targetTheta   = json.getFloat("th");
        if (json.hasKey("sp"))     setpointTheta = json.getFloat("sp");
        if (json.hasKey("u"))      controlU      = json.getFloat("u");
        if (json.hasKey("load_m")) loadMass      = json.getFloat("load_m");
        if (json.hasKey("load_x")) loadPos       = json.getFloat("load_x");
        if (json.hasKey("f1"))     thrustF1      = json.getFloat("f1");
        if (json.hasKey("f2"))     thrustF2      = json.getFloat("f2");

        if (json.hasKey("prop1")) {
          float p1 = json.getFloat("prop1");
          deltaP1 = circularDelta(p1, lastProp1, PROP_WRAP_PERIOD);
          lastProp1 = p1;
          prop1Rot += deltaP1;
        }

        if (json.hasKey("prop2")) {
          float p2 = json.getFloat("prop2");
          deltaP2 = circularDelta(p2, lastProp2, PROP_WRAP_PERIOD);
          lastProp2 = p2;
          prop2Rot -= deltaP2;
        }

        lastPacketTime = millis();
      }
    } catch (Exception e) {
      // Abaikan paket tidak lengkap
    }
  }
}

void triggerDisturbanceImpulse() {
  impulseFlashTimer = millis() + 400;
  if (socket != null && lastSenderAddr != null && lastSenderPort > 0) {
    try {
      DatagramPacket p = new DatagramPacket(impulseBytes, impulseBytes.length, lastSenderAddr, lastSenderPort);
      socket.send(p);
      println("[IMPULSE] Perintah gangguan impuls terkirim ke Python!");
    } catch (Exception e) {
      println("[IMPULSE] Gagal kirim: " + e.getMessage());
    }
  }
}

float circularDelta(float curr, float prev, float period) {
  float d = (curr - prev) % period;
  if (d > period / 2.0) d -= period;
  if (d < -period / 2.0) d += period;
  return d;
}

void closeNetwork() {
  if (socket != null && !socket.isClosed()) {
    socket.close();
  }
}
