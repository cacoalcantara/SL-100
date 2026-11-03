// RECONSTRUÇÃO a partir de engenharia reversa estática do APK com.picoshadow.bx100 v1.2.3
// (classes util/i.java "SpeakerManager" + activity/BleConditionActivity.java, linhas 102-106).
// GATT (serviço/característica) confirmado uma vez em hardware real (SL100); round-trip completo ainda não. Ver docs/PROTOCOL.md.
export const DEVICE_NAMES = ['SL100-BLE', 'SL200-BLE'];
export const SERVICE_UUID = '00001112-0000-1000-8000-00805f9b34fb';
export const NOTIFY_UUID  = '00003334-0000-1000-8000-00805f9b34fb';
export const WRITE_UUID   = '00003334-0000-1000-8000-00805f9b34fb'; // mesma característica da notificação
export const TYPE = { GET_INFO: 1, AUTH_CODE: 2, WIFI: 3, TIMEZONE: 4 };
export const CHUNK = 15, CHUNK_DELAY_MS = 320, SEP = 0xfd;

// checksum: soma dos bytes do índice 1 até o penúltimo, menos 8, em 8 bits
export const checksum = (b) => { let s = 0; for (let i = 1; i < b.length - 1; i++) s = (s + b[i]) & 0xff; return (s - 8) & 0xff; };
export const totalPackets = (len) => Math.ceil(len / CHUNK);

// cabeçalho de 8 bytes: FF 05 msgId 00 01 tipo totalPacotes checksum
export function header(msgId, type, payloadLen) {
  const h = Buffer.from([0xff, 0x05, msgId & 0xff, 0x00, 0x01, type, totalPackets(payloadLen), 0]);
  h[7] = checksum(h); return h;
}
// pacote de dados: FE (n+2) msgId índice dados(≤15) checksum
export function dataPacket(msgId, index, data) {
  const p = Buffer.alloc(data.length + 5);
  p[0] = 0xfe; p[1] = data.length + 2; p[2] = msgId & 0xff; p[3] = index; data.copy(p, 4);
  p[p.length - 1] = checksum(p); return p;
}
// devolve a sequência de escritas na característica WRITE (esperar CHUNK_DELAY_MS entre os pacotes de dados)
export function buildWrites(msgId, type, payload = Buffer.alloc(0)) {
  const writes = [header(msgId, type, payload.length)];
  for (let i = 0; i < totalPackets(payload.length); i++) writes.push(dataPacket(msgId, i, payload.subarray(i * CHUNK, (i + 1) * CHUNK)));
  return writes;
}
export const getInfo = (id) => buildWrites(id, TYPE.GET_INFO);
export const sendAuthCode = (id, code) => buildWrites(id, TYPE.AUTH_CODE, Buffer.from(code));
export const sendWifi = (id, ssid, password, open = false) =>
  buildWrites(id, TYPE.WIFI, Buffer.concat([Buffer.from(ssid), Buffer.from([SEP]), Buffer.from(open ? '' : password), Buffer.from([SEP]), Buffer.from(open ? 'open' : 'psk')]));
export function sendTimezone(id, name, offsetSeconds) {
  const t = Buffer.alloc(4); t.writeInt32BE(offsetSeconds); // big-endian
  return buildWrites(id, TYPE.TIMEZONE, Buffer.concat([Buffer.from(name), Buffer.from([SEP]), t]));
}
// Resposta (notificações): cabeçalho FF.. (tipo, total) e depois FE.. com o texto (tipo 1) ou só confirmação (total 0)
export class Reassembler {
  constructor() { this.msgId = null; this.type = 0; this.total = 0; this.parts = new Map(); }
  push(buf) {
    if (buf.length < 6 || checksum(buf) !== buf[buf.length - 1]) return null;
    if (buf[0] === 0xff && buf.length >= 8 && buf[3] === 0 && buf[4] === 1) {
      this.msgId = buf[2]; this.type = buf[5]; this.total = buf[6]; this.parts = new Map();
      return this.total === 0 ? { type: this.type, ack: true } : null;
    }
    if (buf[0] === 0xfe && buf[2] === this.msgId) {
      this.parts.set(buf[3], buf.subarray(4, 4 + buf[1] - 2));
      if (this.parts.size === this.total) {
        const text = Buffer.concat([...Array(this.total).keys()].map((i) => this.parts.get(i))).toString();
        return { type: this.type, text };
      }
    }
    return null;
  }
}
