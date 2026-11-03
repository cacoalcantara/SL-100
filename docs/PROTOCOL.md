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
