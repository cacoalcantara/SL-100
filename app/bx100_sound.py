"""
Pareamento por som (modem acustico) do BX100/SL100 — SETUP_TYPE_AI_SOUND_WAVE.

MECANISMO (confirmado por engenharia reversa estatica, 2026-11-03):
A biblioteca nativa libSoundAutentication_jni (classe Java com.aw.SoundAuthentication)
e um MODEM ACUSTICO. O celular converte uma string de configuracao em audio PCM
(`nativeEncodeStrToPcm`) e toca pelo alto-falante; o microfone da caixa captura e
decodifica (`nativeDecodePcmToStr`). Usa tom de sincronismo ("start tone") e
correcao de erros Reed-Solomon.

Fonte: SWWaitActivity.java (lado Java) + functions/ do Ghidra (lado nativo).

--- O QUE JA E CONHECIDO (100%) ---

String codificada (SWWaitActivity.java:94), campos separados por ":::"
    ssid ::: senha ::: timezone_id ::: offset_utc_segundos ::: device_auth_code
onde:
    - timezone_id         = ID da timezone (ex.: "America/Sao_Paulo")
    - offset_utc_segundos = (ZONE_OFFSET + DST_OFFSET) / 1000, em segundos (b.c.a.b.k.b())
    - device_auth_code    = DEVICE_AUTH_CODE do SharedPreferences (util/l.java) —
                            o MESMO authCode que vinha da nuvem GetAuthCode.

Parametros do encoder (SWWaitActivity.java:98 -> setEnDecoderParameters):
    max_str_len=128, sample_rate=16000, freq_type=0,
    error_correct=1, error_correct_num=4, group_symbol_num=10

Reproducao do audio (SWWaitActivity.java): AudioTrack mono, PCM 16-bit, 16000 Hz,
MODE_STREAM, tocando o short[] devolvido por nativeEncodeStrToPcm.

--- O QUE AINDA FALTA ---

A modulacao em si (string -> PCM) esta dentro da .so, em assembly/pseudocodigo C
(ver codigo_descompilado/ghidra_linux/*/libSoundAutentication_jni/). Reimplementar
o FSK + Reed-Solomon exatos a partir do pseudocodigo ainda NAO foi feito, entao
este modulo monta o payload correto mas NAO gera o audio final.

CONSEQUENCIA: como o ultimo campo e o device_auth_code (da nuvem desativada), o
pareamento por som tem a mesma limitacao do BLE/TCP — sem um authCode valido, nao
da para completar a configuracao pelo caminho original. Ver docs/PROVISIONING.md.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

SEP = ":::"

# Parametros fixos observados no app (SWWaitActivity.java:98)
MAX_STR_LEN = 128
SAMPLE_RATE = 16000
FREQ_TYPE = 0
ERROR_CORRECT = 1
ERROR_CORRECT_NUM = 4
GROUP_SYMBOL_NUM = 10


@dataclass
class SoundEncoderParams:
    max_str_len: int = MAX_STR_LEN
    sample_rate: int = SAMPLE_RATE
    freq_type: int = FREQ_TYPE
    error_correct: int = ERROR_CORRECT
    error_correct_num: int = ERROR_CORRECT_NUM
    group_symbol_num: int = GROUP_SYMBOL_NUM


def utc_offset_seconds(offset_hours: float) -> int:
    """Converte um offset de fuso em horas (ex.: -3) para segundos, como o app faz."""
    return int(round(offset_hours * 3600))


def build_payload(ssid: str, password: str, timezone_id: str,
                  offset_seconds: int, device_auth_code: str) -> str:
    """Monta a string EXATA que o app codifica em som (SWWaitActivity.java:94).
    Este formato e conhecido e correto; so a modulacao para PCM e que falta."""
    return SEP.join([ssid, password, timezone_id, str(offset_seconds), device_auth_code])


class SoundPairingNotImplemented(NotImplementedError):
    pass


def encode_str_to_pcm(_payload: str, _params: SoundEncoderParams | None = None):
    """Equivalente a nativeEncodeStrToPcm: string -> short[] PCM 16000 Hz mono.
    NAO IMPLEMENTADO: a modulacao FSK+Reed-Solomon esta na .so e ainda nao foi
    reimplementada a partir do pseudocodigo do Ghidra."""
    raise SoundPairingNotImplemented(
        "A modulacao string->PCM (nativeEncodeStrToPcm) ainda nao foi reimplementada. "
        "Pseudocodigo em codigo_descompilado/ghidra_linux/*/libSoundAutentication_jni/. "
        "Payload montado com sucesso; falta so gerar o audio."
    )


if __name__ == "__main__":
    # Demonstra a parte que JA funciona: montar o payload exato do app.
    tz = time.strftime("%Z") or "America/Sao_Paulo"
    payload = build_payload(
        ssid="minha-rede",
        password="senha123",
        timezone_id="America/Sao_Paulo",
        offset_seconds=utc_offset_seconds(-3),
        device_auth_code="<authCode-da-nuvem>",
    )
    print("Payload que o app codificaria em som:")
    print(" ", payload)
    print("Parametros do encoder:", SoundEncoderParams())
