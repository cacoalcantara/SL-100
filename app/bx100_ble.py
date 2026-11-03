"""
Protocolo BLE do BX100/SL100, como documentado no APK (util/i.java, SpeakerManager).

RECONSTRUÇÃO a partir de engenharia reversa estática. NÃO é código-fonte original.

STATUS DE VALIDAÇÃO (2026-11-03): testado contra um aparelho SL100 real pelo
projeto. O serviço GATT documentado aqui (0000f012-...) NAO apareceu no
aparelho testado, nem em modo normal nem em modo de configuracao (apos o
long-press + aviso sonoro do botao). O que o aparelho expoe de fato e um
servico de teste de fabrica do chip Bluetooth (nome "aw_ble_test_...",
servico 00001112-...), que apenas incrementa um contador a cada leitura e
nao responde aos comandos deste protocolo. Ou seja, o pareamento real desta
unidade provavelmente NAO usa este caminho — ver bx100_sound.py e
docs/PROVISIONING.md. Este modulo fica aqui documentado e funcional (ele
conecta e envia pacotes de verdade) para quando/se um aparelho que use esse
servico aparecer, ou para outra variante/revisao de hardware.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

try:
    from bleak import BleakClient, BleakScanner
except ImportError:  # pragma: no cover - mensagem clara se faltar a dependencia
    BleakClient = None
    BleakScanner = None

SERVICE_UUID = "0000f012-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "f5e0e265-7a63-4303-9850-abd73728fba2"
WRITE_UUID = "689aab00-df3d-4aac-b19b-2dfd4a97197b"

TYPE_GET_INFO = 1
TYPE_AUTH_CODE = 2
TYPE_WIFI = 3
TYPE_TIMEZONE = 4

CHUNK = 15
CHUNK_DELAY_S = 0.320
SEP = 0xFD


def checksum(b: bytes) -> int:
    s = 0
    for byte in b[1:-1]:
        s = (s + byte) & 0xFF
    return (s - 8) & 0xFF


def total_packets(length: int) -> int:
    return (length + CHUNK - 1) // CHUNK if length else 0


def header(msg_id: int, type_: int, payload_len: int) -> bytes:
    h = bytearray([0xFF, 0x05, msg_id & 0xFF, 0x00, 0x01, type_, total_packets(payload_len), 0])
    h[7] = checksum(h)
    return bytes(h)


def data_packet(msg_id: int, index: int, data: bytes) -> bytes:
    p = bytearray(len(data) + 5)
    p[0] = 0xFE
    p[1] = len(data) + 2
    p[2] = msg_id & 0xFF
    p[3] = index
    p[4:4 + len(data)] = data
    p[-1] = checksum(p)
    return bytes(p)


def build_writes(msg_id: int, type_: int, payload: bytes = b"") -> list[bytes]:
    writes = [header(msg_id, type_, len(payload))]
    for i in range(total_packets(len(payload))):
        writes.append(data_packet(msg_id, i, payload[i * CHUNK:(i + 1) * CHUNK]))
    return writes


def get_info(msg_id: int) -> list[bytes]:
    return build_writes(msg_id, TYPE_GET_INFO)


def send_auth_code(msg_id: int, code: str) -> list[bytes]:
    return build_writes(msg_id, TYPE_AUTH_CODE, code.encode("utf-8"))


def send_wifi(msg_id: int, ssid: str, password: str = "", open_: bool = False) -> list[bytes]:
    payload = ssid.encode() + bytes([SEP]) + (b"" if open_ else password.encode()) + bytes([SEP]) + (b"open" if open_ else b"psk")
    return build_writes(msg_id, TYPE_WIFI, payload)


def send_timezone(msg_id: int, name: str, offset_seconds: int) -> list[bytes]:
    import struct
    payload = name.encode() + bytes([SEP]) + struct.pack(">i", offset_seconds)
    return build_writes(msg_id, TYPE_TIMEZONE, payload)


@dataclass
class BleResult:
    service_found: bool
    notifications: list[bytes]
    error: str | None = None


async def scan_for_device(name_filter: str = "SL100", timeout_s: float = 10.0):
    """Escaneia e devolve (endereco, nome, rssi) de dispositivos cujo nome contem name_filter."""
    if BleakScanner is None:
        raise RuntimeError("bleak nao instalado (pip install bleak)")
    devices = await BleakScanner.discover(timeout=timeout_s, return_adv=True)
    out = []
    for addr, (d, adv) in devices.items():
        if d.name and name_filter.upper() in d.name.upper():
            out.append((addr, d.name, adv.rssi))
    return out


async def try_documented_protocol(address: str, writes: list[bytes], listen_s: float = 5.0) -> BleResult:
    """Conecta no servico/caracteristicas documentados do APK e tenta a troca.
    Isso e o caminho ORIGINAL do app; no aparelho testado em 2026-11-03 ele
    nao existe (o aparelho nao anuncia o servico 0000f012)."""
    if BleakClient is None:
        return BleResult(False, [], error="bleak nao instalado (pip install bleak)")
    notifications: list[bytes] = []

    def on_notify(_sender, data):
        notifications.append(bytes(data))

    try:
        async with BleakClient(address, timeout=15.0, winrt={"use_cached_services": False}) as client:
            uuids = [s.uuid.lower() for s in client.services]
            if SERVICE_UUID not in uuids:
                return BleResult(False, [], error=f"servico {SERVICE_UUID} nao presente neste aparelho")
            await client.start_notify(NOTIFY_UUID, on_notify)
            for w in writes:
                await client.write_gatt_char(WRITE_UUID, w, response=True)
                await asyncio.sleep(CHUNK_DELAY_S)
            await asyncio.sleep(listen_s)
            return BleResult(True, notifications)
    except Exception as e:  # noqa: BLE001 - reportar qualquer falha de BLE ao chamador
        return BleResult(False, notifications, error=str(e))
