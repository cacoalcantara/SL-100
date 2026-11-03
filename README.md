# bx100-community

Projeto aberto para documentar o protocolo local da caixa de som **BX100 / SL100 (Sabala / PicoShadow)** e permitir que ela seja configurada e conectada à internet sem a nuvem da Sabala, que foi desativada.

**Status: pesquisa inicial. Nada aqui foi validado contra um aparelho real.**

## O que existe
- `docs/PROTOCOL.md` — protocolo local (descoberta UDP, TCP 41200, quadro FF56, cifra, mensagens), derivado do app Android v1.2.3.
- `client/` — cliente de referência em Node.js (reimplementação própria): TCP em `bx100.mjs`, Bluetooth em `ble.mjs`. Testes offline: `node client/selftest.mjs` e `node client/selftest-ble.mjs`.
- `evidence/` — como reproduzir cada afirmação com o REA.

## O que ainda falta (ajude aqui)
- Validar com um BX100/SL100 real (descoberta, GetDevInfo, ConnectWIFI).
- Validar o Bluetooth em hardware (codec já escrito) e decifrar o pareamento por som.
- Descobrir se o aparelho aceita o `authCode` localmente ou só o repassa à nuvem.
- Analisar o firmware; propor um servidor substituto para as funções que dependiam da nuvem (login, luz, IA).

## Segurança e privacidade
Este repositório **não** contém chaves, credenciais nem contas da Sabala (chave Google Maps, Umeng, chave privada CloudFront, `private.der`, `credential.json`). Não envie nenhum desses dados em issues ou PRs. A chave AES do protocolo local aparece em PROTOCOL.md porque é uma constante fixa necessária à interoperabilidade.

## Direitos autorais
O repositório contém apenas especificação e código escrito do zero. Não inclua o APK, código decompilado ou recursos do app da Sabala. Interoperabilidade com aparelho que você possui; sem afiliação com a Sabala/PicoShadow.

## Licença
MIT — ver o arquivo `LICENSE`.
