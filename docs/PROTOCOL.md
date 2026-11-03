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

## Bluetooth LE (reconstruído de util/i.java, `SpeakerManager`; não validado em hardware)
**GATT:** serviço `0000f012-0000-1000-8000-00805f9b34fb`; escrita `689aab00-df3d-4aac-b19b-2dfd4a97197b`; notificação `f5e0e265-7a63-4303-9850-abd73728fba2` (o app liga `setCharacteristicNotification` e escreve o descritor).
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
