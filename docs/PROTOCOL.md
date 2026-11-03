# Protocolo app ↔ BX100 (reconstruído por análise estática; NÃO validado contra hardware)
**Descoberta (UDP)** — app envia `Are You BX100 Smart Device?` (27 bytes) em broadcast para :41300 a partir da porta :4025. Resposta contendo "BX100": `<fabricante>/<nome>.<MAC> <ip>` (tokens separados por espaço; MAC sem `:` e em minúsculas). Janela de 3 s.
**Transporte (TCP :41200)** — quadro: `FF 56 | tamanho(2B, big-endian) | payload | checksum(1B)`. checksum = −Σ(bytes do índice 2 ao fim do payload) mod 256. Buffer de leitura 640 bytes (payload ≤ 636).
**Payload** — JSON → AES-128-CBC/PKCS5 → Base64 (com um espaço a cada 60 caracteres; o decoder tolera espaços).
Chave AES = `com.teranovo.sds` (16 bytes), IV = `shenzhenteranovo` (util/n/b.java). Constantes fixas no APK, sem segredo por dispositivo.
**Mensagens** (`{"directive":{"header":{"namespace","name","messageId":"33"},"payload":{…}}}`):
| namespace/name | payload | Origem |
|---|---|---|
| app.system/GetDevInfo | {} | util/h.java |
| app.network/ConnectWIFI | ssid, encryption(open\|psk), password | util/h.java |
| wifi/sta_mode | ssid, encryption, password (fluxo AP SL100) | e/c/l.java |
| app.authorization/Authorize | authCode | util/h.java |
| app.system/SetTimezone | city, <campo de offset>, dst | util/h.java |
Resposta do dispositivo: mesmo quadro, mesma cifra (decodificada em util/d.java). Um segundo caminho (ChargerManager/SpeakerManager, util/i.java) usa BLE com quadros binários próprios (tipos 1–4, separador 0xFD) — **só parcialmente analisado**.
**Modo AP**: o app conecta ao Wi-Fi do aparelho, que responde em 192.168.15.1; depois envia as credenciais do Wi-Fi doméstico.

## Bluetooth LE (reconstruído de util/i.java `SpeakerManager` + activity/BleConditionActivity.java; parcialmente confirmado em hardware real, ver nota no fim)
**Nome anunciado:** `SL100-BLE` ou `SL200-BLE` (lista exata usada pelo app: `BleConditionActivity.java:106`, `h.h().a("SL100-BLE,SL200-BLE", ...)`).
**GATT:** serviço `00001112-0000-1000-8000-00805F9B34FB`; a mesma característica `00003334-0000-1000-8000-00805F9B34FB` é usada para escrita e notificação (`BleConditionActivity.java:103-105`, campos `h.A`/`h.B`/`h.C` do SDK do fabricante em `b/c/a/b/h.java`). **Correção:** uma versão anterior deste documento citava os UUIDs `0000f012-...`, `f5e0e265-...` e `689aab00-...` — esses valores não existem em nenhum lugar do código decompilado (conferido com busca textual completa) e foram removidos. Não sabemos a origem do engano; não os use.
**Mensagem = 1 cabeçalho + N pacotes** (N = ⌈bytes / 15⌉), escritos em sequência com **320 ms** entre os pacotes de dados; `msgId` sobe 0‥255 a cada mensagem.
- Cabeçalho (8 bytes): `FF 05 msgId 00 01 tipo N checksum`
- Pacote de dados: `FE (n+2) msgId índice dados[≤15] checksum`
- checksum: soma dos bytes do índice 1 até o penúltimo, menos 8, módulo 256 (vale para os dois formatos e para as respostas)
| tipo | função | dados |
|---|---|---|
| 1 | pedir informações do aparelho | nenhum (N = 0) |
| 2 | enviar `authCode` | texto do código |
| 3 | enviar Wi-Fi | `ssid` `FD` `senha` `FD` `open\|psk` (senha vazia se open) |
| 4 | fuso horário | nome da zona `FD` offset em segundos, 4 bytes **big-endian** |
**Respostas** (notificação): mesmo formato. Se `N = 0` no cabeçalho, é só confirmação do tipo (2, 3 ou 4); para o tipo 1 vêm N pacotes FE cujo conteúdo, juntado por índice, é um texto com as informações do aparelho (campos do app: id, modelo, idioma, localização, versão do firmware e da placa). O app descarta respostas cujo `msgId` ou checksum não bate.
Implementação: `client/ble.mjs`; teste: `node client/selftest-ble.mjs`.
**Incerto:** o formato exato do texto de resposta do tipo 1 e a exigência de pareamento/bond do sistema para escrever ou receber notificações (o app não pede bond; um aparelho real pode exigir).

**Nota de validação em hardware (03/11/2026, Windows + Python/bleak, SL100 real):** conseguimos, uma vez, escanear e conectar na caixa real logo após o long-press de setup, e o GATT devolvido bateu exatamente com o serviço/característica acima (`00001112`/`00003334`) — confirmando que vêm do código certo. Não conseguimos completar um round-trip (enviar `GetDevInfo` e ler a resposta): a assinatura da notificação falhou com "Write Not Permitted", e depois de um ciclo de parear/desparear pelo Windows e resetar o aparelho, ele parou de anunciar por BLE nas tentativas seguintes (nem o scanner de alto nível nem o `BluetoothLEAdvertisementWatcher` de baixo nível o viram de novo). Hipóteses não confirmadas: (a) a característica exige vínculo BLE real antes de aceitar escrita no descritor de notificação, e o pareamento do Windows nesse hardware mistura o perfil BLE com perfis Bluetooth clássico (A2DP/AVRCP), atrapalhando; (b) o aparelho só anuncia por BLE numa janela curta após o long-press, ou mudou de comportamento por lembrar de um pareamento anterior com o mesmo PC. Quem tiver um celular Android disponível pode validar isso de forma mais confiável capturando o HCI snoop log durante o uso do app original — a parte BLE local não depende da nuvem, só o `authCode` (tipo 2) depende.
