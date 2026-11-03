"""
bx100-community — interface por linha de comando.

Alternativa sem GUI (e sem precisar de .exe) para configurar o BX100/SL100
localmente. Mesma base de protocolo do bx100_gui.py.

Exemplos:
    python bx100_cli.py discover
    python bx100_cli.py get-info --ip 192.168.15.1
    python bx100_cli.py connect-wifi --ip 192.168.15.1 --ssid casa --password segredo
    python bx100_cli.py authorize --ip 192.168.15.1 --auth-code ABC123
    python bx100_cli.py set-timezone --ip 192.168.15.1 --city America/Sao_Paulo --offset -3
    python bx100_cli.py ble-scan
    python bx100_cli.py sound-payload --ssid casa --password segredo --auth-code ABC123

STATUS: ver README.md. O caminho Wi-Fi/TCP ainda nao foi validado contra um
aparelho real; o BLE documentado nao bateu com o hardware testado; o som so
monta o payload (nao gera audio ainda).
"""
from __future__ import annotations

import argparse
import asyncio
import sys

import bx100_protocol as proto
import bx100_ble as ble
import bx100_sound as sound


def cmd_discover(args):
    print(f"Descobrindo por broadcast UDP ({args.timeout}s)...")
    found = proto.discover(args.timeout)
    if not found:
        print("nenhum aparelho respondeu.")
        return
    for d in found:
        print(f"  {d.manu}/{d.name}  mac={d.mac}  ip={d.ip}")


def cmd_get_info(args):
    print(f"GetDevInfo -> {args.ip}:{proto.TCP_PORT}")
    print("resposta:", proto.send_directive(args.ip, proto.get_dev_info(), args.timeout))


def cmd_connect_wifi(args):
    print(f"ConnectWIFI ssid={args.ssid!r} -> {args.ip}")
    print("resposta:", proto.send_directive(args.ip, proto.connect_wifi(args.ssid, args.password), args.timeout))


def cmd_authorize(args):
    print(f"Authorize -> {args.ip}")
    print("resposta:", proto.send_directive(args.ip, proto.authorize(args.auth_code), args.timeout))


def cmd_set_timezone(args):
    offset_s = int(round(args.offset * 3600))
    print(f"SetTimezone city={args.city} offset={offset_s}s -> {args.ip}")
    print("resposta:", proto.send_directive(args.ip, proto.set_timezone(args.city, offset_s), args.timeout))


def cmd_ble_scan(args):
    print(f"Escaneando BLE ({args.timeout}s, filtro '{args.name}')...")
    results = asyncio.run(ble.scan_for_device(args.name, args.timeout))
    if not results:
        print("nenhum dispositivo encontrado anunciando agora.")
        return
    for addr, name, rssi in results:
        print(f"  {addr}  name={name!r}  rssi={rssi}")


def cmd_ble_try(args):
    print(f"Tentando protocolo BLE documentado em {args.address} ...")
    writes = ble.get_info(msg_id=1)
    result = asyncio.run(ble.try_documented_protocol(args.address, writes))
    if not result.service_found:
        print("protocolo documentado nao respondeu:", result.error)
        return
    print(f"OK — {len(result.notifications)} notificacao(oes):")
    for n in result.notifications:
        print("  ", n.hex())


def cmd_sound_payload(args):
    payload = sound.build_payload(
        ssid=args.ssid, password=args.password,
        timezone_id=args.city, offset_seconds=sound.utc_offset_seconds(args.offset),
        device_auth_code=args.auth_code,
    )
    print("Payload que o app codificaria em som (SETUP_TYPE_AI_SOUND_WAVE):")
    print(" ", payload)
    print("Parametros:", sound.SoundEncoderParams())
    print("Obs.: a geracao do audio (nativeEncodeStrToPcm) ainda nao foi reimplementada.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Configuracao local do BX100/SL100 (reconstrucao por engenharia reversa).")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_ip(sp):
        sp.add_argument("--ip", default=proto.AP_IP, help="IP do aparelho (padrao: %(default)s)")
        sp.add_argument("--timeout", type=float, default=3.0)

    sp = sub.add_parser("discover", help="descoberta por broadcast UDP")
    sp.add_argument("--timeout", type=float, default=3.0)
    sp.set_defaults(func=cmd_discover)

    sp = sub.add_parser("get-info", help="GetDevInfo")
    add_ip(sp); sp.set_defaults(func=cmd_get_info)

    sp = sub.add_parser("connect-wifi", help="ConnectWIFI")
    add_ip(sp)
    sp.add_argument("--ssid", required=True)
    sp.add_argument("--password", default="")
    sp.set_defaults(func=cmd_connect_wifi)

    sp = sub.add_parser("authorize", help="Authorize (authCode vinha da nuvem)")
    add_ip(sp)
    sp.add_argument("--auth-code", required=True)
    sp.set_defaults(func=cmd_authorize)

    sp = sub.add_parser("set-timezone", help="SetTimezone")
    add_ip(sp)
    sp.add_argument("--city", default="America/Sao_Paulo")
    sp.add_argument("--offset", type=float, default=-3, help="offset UTC em horas")
    sp.set_defaults(func=cmd_set_timezone)

    sp = sub.add_parser("ble-scan", help="escaneia dispositivos BLE")
    sp.add_argument("--name", default="SL100")
    sp.add_argument("--timeout", type=float, default=10.0)
    sp.set_defaults(func=cmd_ble_scan)

    sp = sub.add_parser("ble-try", help="tenta o protocolo BLE documentado num endereco")
    sp.add_argument("address")
    sp.set_defaults(func=cmd_ble_try)

    sp = sub.add_parser("sound-payload", help="monta o payload do pareamento por som")
    sp.add_argument("--ssid", required=True)
    sp.add_argument("--password", default="")
    sp.add_argument("--city", default="America/Sao_Paulo")
    sp.add_argument("--offset", type=float, default=-3)
    sp.add_argument("--auth-code", default="<authCode-da-nuvem>")
    sp.set_defaults(func=cmd_sound_payload)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except Exception as e:  # noqa: BLE001 - CLI: reportar erro de forma limpa
        print(f"erro: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
