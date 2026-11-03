# Provisionamento e dependência da nuvem

Derivado do app Android v1.2.3 (hash em `evidence/APK_SHA256.txt`). **Nada aqui foi validado em aparelho real.**

## Fluxo de configuração observado no app

1. **Descoberta** — broadcast UDP na porta 41300 (porta local 4025); em modo AP o aparelho responde em `192.168.15.1`.
2. **Conexão** — TCP na porta 41200, quadros e cifra descritos em `PROTOCOL.md`.
3. **`app.system/GetDevInfo`** — lê as informações do aparelho.
4. **`app.network/ConnectWIFI`** — envia `ssid`, `encryption` (`open` ou `psk`) e `password`.
5. **`app.authorization/Authorize`** — entrega um `authCode`.
6. **`app.system/SetTimezone`** — cidade, deslocamento e horário de verão.

O mesmo conjunto existe por Bluetooth LE (ver `PROTOCOL.md`): tipos 1 (info), 2 (`authCode`), 3 (Wi-Fi) e 4 (fuso).

## Pareamento por som (SETUP_TYPE_AI_SOUND_WAVE)

Confirmado por engenharia reversa (2026-11-03). A biblioteca nativa `libSoundAutentication_jni` (classe `com.aw.SoundAuthentication`) é um **modem acústico**: o celular converte uma string em áudio PCM (`nativeEncodeStrToPcm`) e toca pelo alto-falante; o microfone da caixa captura e decodifica. Usa tom de sincronismo e correção de erros Reed-Solomon.

String codificada (de `SWWaitActivity.java`), campos separados por `:::`:

```
ssid ::: senha ::: timezone_id ::: offset_utc_segundos ::: device_auth_code
```

- `offset_utc_segundos` = `(ZONE_OFFSET + DST_OFFSET) / 1000`
- `device_auth_code` = o **mesmo** authCode que vinha da nuvem (`GetAuthCode`)

Parâmetros do encoder: `max_str_len=128, sample_rate=16000 Hz, freq_type=0, error_correct=1, error_correct_num=4, group_symbol_num=10`. Áudio: mono, PCM 16-bit, 16000 Hz.

**Consequência:** o pareamento por som depende do mesmo `device_auth_code` da nuvem desativada. A modulação exata (string → PCM) está na `.so`; o pseudocódigo C já foi extraído (Ghidra), mas a reimplementação ainda não foi feita.

## O que dependia da nuvem

O `authCode` do passo 5 vem, no app, **somente** de uma chamada de nuvem (`GetAuthCode`). Login, lista de dispositivos, controle de luz, atualização de firmware e funções de IA também passavam pela API da nuvem, hoje desativada pela fabricante.

Consequência: com o app original não é possível completar o passo 5. Passos 1 a 4 e 6 usam só a rede local.

## Perguntas em aberto (ajude aqui)

- O aparelho valida o `authCode` ou apenas o repassa à nuvem? Se aceitar qualquer valor, o passo 5 pode ser contornado localmente.
- Para qual endereço o aparelho envia o tráfego depois de autorizado? Capturar com o aparelho real e documentar.
- Formato do pareamento por som.
- Se o Bluetooth exige bonding antes das escritas, e o formato textual das respostas.
- Firmware: obter e analisar, para propor um servidor substituto compatível.

## Limites

Este documento descreve interoperabilidade com um aparelho que o usuário possui. Não inclui chaves privadas, contas ou código da fabricante.
