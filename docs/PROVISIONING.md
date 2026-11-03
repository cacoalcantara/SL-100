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

O app também contém uma biblioteca nativa de pareamento por som (`libSoundAutentication_jni`). Ela está desmontada, mas **não foi interpretada**; o formato do sinal sonoro é desconhecido.

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
