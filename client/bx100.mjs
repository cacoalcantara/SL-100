// RECONSTRUÇÃO a partir de engenharia reversa estática do APK com.picoshadow.bx100 v1.2.3.
// NÃO é o código-fonte original. Fonte das evidências: ver arquitetura/protocolo_bx100.md
import crypto from 'node:crypto';
import dgram from 'node:dgram';
import net from 'node:net';

const KEY = Buffer.from('com.teranovo.sds'); // util/n/b.java (AES-128)
const IV = Buffer.from('shenzhenteranovo');
export const UDP_DISCOVERY_PORT = 41300, UDP_LOCAL_PORT = 4025, TCP_PORT = 41200, AP_IP = '192.168.15.1';

// util/n/a.java: Base64 padrão, mas insere um espaço após cada 15 grupos (60 chars). O decoder ignora espaços.
export function b64Enc(buf) {
  const s = buf.toString('base64');
  return s.match(/.{1,60}/g)?.join(' ') ?? '';
}
export const b64Dec = (s) => Buffer.from(s.replace(/\s+/g, ''), 'base64');

export function encryptPayload(text) {
  const c = crypto.createCipheriv('aes-128-cbc', KEY, IV);
  return b64Enc(Buffer.concat([c.update(text, 'utf8'), c.final()]));
}
export function decryptPayload(b64) {
  const d = crypto.createDecipheriv('aes-128-cbc', KEY, IV);
  return Buffer.concat([d.update(b64Dec(b64)), d.final()]).toString('utf8');
}

// util/e.java (MessageEncoder): FF 56 | len(2, BE) | payload | checksum, checksum = -(soma dos bytes do índice 2 em diante) & 0xFF
export function frame(jsonText) {
  const payload = Buffer.from(encryptPayload(jsonText));
  const out = Buffer.alloc(payload.length + 5);
  out[0] = 0xff; out[1] = 0x56; out.writeUInt16BE(payload.length, 2); payload.copy(out, 4);
  let sum = 0; for (let i = 2; i < out.length - 1; i++) sum = (sum - out[i]) & 0xff;
  out[out.length - 1] = sum; return out;
}
// util/d.java (MessageDecoder): lê FF 56 + len; payload é texto base64 cifrado
export function unframe(buf) {
  if (buf[0] !== 0xff || buf[1] !== 0x56) throw new Error('cabeçalho FF 56 ausente');
  const len = buf.readUInt16BE(2);
  return decryptPayload(buf.subarray(4, 4 + len).toString('utf8').trim());
}

export const directive = (namespace, name, payload = {}) =>
  JSON.stringify({ directive: { header: { namespace, name, messageId: '33' }, payload } });
export const getDevInfo = () => directive('app.system', 'GetDevInfo');
export const connectWifi = (ssid, password) =>
  directive('app.network', 'ConnectWIFI', { ssid, encryption: password ? 'psk' : 'open', password: password ?? '' });
export const authorize = (authCode) => directive('app.authorization', 'Authorize', { authCode });
export const setTimezone = (city, offsetField, dst = '') => directive('app.system', 'SetTimezone', { city, [offsetField]: 0, dst });

// util/k.java: descoberta UDP. Só use em rede/dispositivo SEUS.
export function discover(timeoutMs = 3000) {
  return new Promise((resolve) => {
    const found = new Map(); const s = dgram.createSocket('udp4');
    s.bind(UDP_LOCAL_PORT, () => {
      s.setBroadcast(true);
      s.send(Buffer.from('Are You BX100 Smart Device?'), UDP_DISCOVERY_PORT, '255.255.255.255');
    });
    s.on('message', (m) => {
      const t = m.toString(); if (!t.includes('BX100')) return;
      const [id, ip] = t.split(' '); const [path, mac] = id.split('.');
      const [manu, name] = path.split('/');
      found.set(mac.replace(/:/g, '').toLowerCase(), { manu, name, ip });
    });
    setTimeout(() => { s.close(); resolve([...found.entries()]); }, timeoutMs);
  });
}
export function sendDirective(ip, jsonText, waitMs = 3000) {
  return new Promise((resolve, reject) => {
    const c = net.connect(TCP_PORT, ip, () => c.write(frame(jsonText)));
    c.on('data', (d) => { try { resolve(unframe(d)); } catch (e) { reject(e); } c.end(); });
    c.on('error', reject); setTimeout(() => { c.destroy(); reject(new Error('timeout')); }, waitMs);
  });
}
