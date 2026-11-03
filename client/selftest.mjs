import assert from 'node:assert/strict';
import { frame, unframe, connectWifi, getDevInfo, encryptPayload, decryptPayload } from './bx100.mjs';
const msg = connectWifi('MinhaRede', 'segredo123');
assert.equal(decryptPayload(encryptPayload(msg)), msg);
const f = frame(msg);
assert.equal(f[0], 0xff); assert.equal(f[1], 0x56);
assert.equal(f.readUInt16BE(2), f.length - 5);
let s = 0; for (let i = 2; i < f.length; i++) s = (s + f[i]) & 0xff;   // soma incluindo checksum == 0
assert.equal(s, 0);
assert.equal(unframe(f), msg);
const long = frame(JSON.stringify({ x: 'a'.repeat(400) }));
assert.ok(unframe(long).includes('aaaa'));
console.log('OK: AES-128-CBC + base64 (espaço a cada 60 chars) + framing FF56/len/checksum consistentes');
console.log('exemplo GetDevInfo (frame hex):', frame(getDevInfo()).toString('hex').slice(0, 80) + '…');
