import assert from 'node:assert/strict';
import { header, dataPacket, sendWifi, getInfo, sendTimezone, checksum, Reassembler, buildWrites } from './ble.mjs';
const h = header(7, 3, 31);
assert.deepEqual([...h.subarray(0, 7)], [0xff, 0x05, 7, 0, 1, 3, 3]);          // 31 bytes -> 3 pacotes
assert.equal(h[7], (((0x05 + 7 + 0 + 1 + 3 + 3) & 0xff) - 8) & 0xff);
const w = sendWifi(7, 'MinhaRede', 'segredo123');
assert.equal(w.length, 1 + 2); assert.ok(w.slice(1).every((p) => p[0] === 0xfe && checksum(p) === p[p.length - 1]));
assert.equal(getInfo(1).length, 1);                                              // só cabeçalho, 0 pacotes
assert.equal(sendTimezone(2, 'America/Fortaleza', -10800).length > 1, true);
// ida e volta: o remontador lê o que o codificador produz (resposta simulada com texto de 40 bytes)
const txt = Buffer.from('{"id":"abc","model":"BX100","fw":"1.0.0"}');
const r = new Reassembler(); let out = null;
for (const p of buildWrites(9, 1, txt)) out = r.push(p) ?? out;
assert.equal(out.text, txt.toString());
console.log('OK: BLE header/packets/checksum/remontagem consistentes');
