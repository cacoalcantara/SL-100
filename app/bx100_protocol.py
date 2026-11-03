"""
Protocolo local TCP/UDP do BX100/SL100 (Sabala/PicoShadow).

RECONSTRUÇÃO a partir de engenharia reversa estática do APK com.picoshadow.bx100
v1.2.3 (classes util/e.java, util/d.java, util/k.java, util/n/b.java). NÃO é
código-fonte original. Evidências: ../docs/PROTOCOL.md e ../docs/PROVISIONING.md.

STATUS DE VALIDAÇÃO (2026-11-03): este caminho (TCP 41200 / UDP 41300, modo AP
da caixa) ainda NÃO foi testado contra um aparelho real. Só a consistência
interna foi verificada (cifra, quadro e checksum fecham com eles mesmos).
"""
from __future__ import annotations

import socket
import struct
import json
import time
from dataclasses import dataclass

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

KEY = b"com.teranovo.sds"      # util/n/b.java — AES-128, constante no APK
IV = b"shenzhenteranovo"

UDP_DISCOVERY_PORT = 41300
UDP_LOCAL_PORT = 4025
TCP_PORT = 41200
AP_IP = "192.168.15.1"


def b64_enc(data: bytes) -> str:
    """util/n/a.java: Base64 padrão com espaço a cada 60 caracteres."""
    import base64
    s = base64.b64encode(data).decode("ascii")
    return " ".join(s[i:i + 60] for i in range(0, len(s), 60))


def b64_dec(s: str) -> bytes:
    import base64
    return base64.b64decode(s.replace(" ", "").replace("\n", ""))


def encrypt_payload(text: str) -> str:
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    ct = cipher.encrypt(pad(text.encode("utf-8"), AES.block_size))
    return b64_enc(ct)


def decrypt_payload(b64: str) -> str:
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    pt = unpad(cipher.decrypt(b64_dec(b64)), AES.block_size)
    return pt.decode("utf-8")


def frame(json_text: str) -> bytes:
    """util/e.java: FF 56 | len(2B, BE) | payload | checksum.
    checksum = -(soma dos bytes do indice 2 em diante) mod 256."""
    payload = encrypt_payload(json_text).encode("ascii")
    out = bytearray(5 + len(payload))
    out[0] = 0xFF
    out[1] = 0x56
    struct.pack_into(">H", out, 2, len(payload))
    out[4:4 + len(payload)] = payload
    s = 0
    for b in out[2:-1]:
        s = (s - b) & 0xFF
    out[-1] = s
    return bytes(out)


def unframe(buf: bytes) -> str:
    """util/d.java: le FF 56 + len; payload e texto base64 cifrado."""
    if buf[0] != 0xFF or buf[1] != 0x56:
        raise ValueError("cabecalho FF 56 ausente")
    length = struct.unpack_from(">H", buf, 2)[0]
    payload = buf[4:4 + length].decode("ascii", errors="replace").strip()
    return decrypt_payload(payload)


def _directive(namespace: str, name: str, payload: dict | None = None) -> str:
    return json.dumps({
        "directive": {
            "header": {"namespace": namespace, "name": name, "messageId": "33"},
            "payload": payload or {},
        }
    })


def get_dev_info() -> str:
    return _directive("app.system", "GetDevInfo")


def connect_wifi(ssid: str, password: str = "") -> str:
    return _directive("app.network", "ConnectWIFI", {
        "ssid": ssid,
        "encryption": "psk" if password else "open",
        "password": password,
    })


def authorize(auth_code: str) -> str:
    return _directive("app.authorization", "Authorize", {"authCode": auth_code})


def set_timezone(city: str, offset_seconds: int = 0, dst: str = "") -> str:
    return _directive("app.system", "SetTimezone", {"city": city, "offset": offset_seconds, "dst": dst})


@dataclass
class DiscoveredDevice:
    mac: str
    manu: str
    name: str
    ip: str


def discover(timeout_s: float = 3.0) -> list[DiscoveredDevice]:
    """util/k.java: descoberta por broadcast UDP. Use só em rede/aparelho seus."""
    found: dict[str, DiscoveredDevice] = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(0.5)
    try:
        s.bind(("", UDP_LOCAL_PORT))
    except OSError:
        s.bind(("", 0))  # porta local ocupada; segue em porta efemera
    s.sendto(b"Are You BX100 Smart Device?", ("255.255.255.255", UDP_DISCOVERY_PORT))

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            data, addr = s.recvfrom(2048)
        except socket.timeout:
            continue
        text = data.decode("utf-8", errors="replace")
        if "BX100" not in text:
            continue
        try:
            ident, ip = text.split(" ", 1)
            path, mac = ident.split(".", 1)
            manu, name = path.split("/", 1)
        except ValueError:
            continue
        key = mac.replace(":", "").lower()
        found[key] = DiscoveredDevice(mac=mac, manu=manu, name=name, ip=ip.strip())
    s.close()
    return list(found.values())


def send_directive(ip: str, json_text: str, wait_s: float = 3.0, port: int = TCP_PORT) -> str:
    """Conecta via TCP, envia um quadro, devolve a resposta decifrada."""
    with socket.create_connection((ip, port), timeout=wait_s) as c:
        c.sendall(frame(json_text))
        c.settimeout(wait_s)
        data = c.recv(4096)
        if not data:
            raise ConnectionError("conexao fechada sem resposta")
        return unframe(data)


if __name__ == "__main__":
    # autoteste offline: cifra/decifra e quadro/desquadro devem fechar com eles mesmos
    msg = get_dev_info()
    f = frame(msg)
    back = unframe(f)
    assert json.loads(back) == json.loads(msg), "autoteste de consistencia falhou"
    print("OK: AES-128-CBC + base64 + quadro FF56/len/checksum consistentes")
    print("quadro GetDevInfo (hex):", f.hex())
