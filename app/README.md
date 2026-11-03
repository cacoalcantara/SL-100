# bx100-community — programa Windows (GUI)

Programa de desktop (Python + Tkinter) para configurar o BX100/SL100 localmente, sem a nuvem da Sabala (desativada). Reconstrução por engenharia reversa estática do APK `com.picoshadow.bx100` v1.2.3 — **não** é software oficial da Sabala/PicoShadow.

## Rodar

Interface gráfica:

```bash
cd app
pip install -r requirements.txt
python bx100_gui.py
```

Ou por linha de comando (sem GUI):

```bash
python bx100_cli.py discover
python bx100_cli.py get-info --ip 192.168.15.1
python bx100_cli.py connect-wifi --ip 192.168.15.1 --ssid casa --password segredo
python bx100_cli.py sound-payload --ssid casa --password segredo --auth-code ABC123
```

Precisa de Python 3.10+ no Windows (ou Linux/macOS — a aba BLE usa `bleak`, multiplataforma; a aba Wi-Fi/TCP não depende de SO).

## Três abas, três status diferentes

| Aba | O que faz | Validado contra hardware real? |
|---|---|---|
| **Wi-Fi / TCP (modo AP)** | Descoberta UDP (porta 41300) + comandos TCP (porta 41200): `GetDevInfo`, `ConnectWIFI` | **Não.** Só a consistência interna do protocolo foi verificada (cifra, quadro, checksum fecham com eles mesmos). |
| **Bluetooth (BLE)** | Conecta no serviço GATT documentado (`0000f012-...`) e envia os pacotes do protocolo | **Testado em 2026-11-03 contra um SL100 real — e o serviço documentado não existe nesse aparelho.** O que ele expõe é um perfil de teste de fábrica do chip BLE, sem relação com o app. Pode funcionar em outra unidade/revisão de hardware; não conte com isso nesta. |
| **Pareamento por som** | Monta o payload exato (`ssid:::senha:::tz:::offset:::authCode`); **não** gera o áudio | **Mecanismo confirmado, geração de áudio não implementada.** É um modem acústico (`libSoundAutentication_jni`): o app toca um som codificando a config, o microfone da caixa decodifica. O formato da string é conhecido; a modulação FSK+Reed-Solomon ainda não foi reimplementada a partir do pseudocódigo. Depende do mesmo authCode da nuvem. |

## Arquivos

- `bx100_protocol.py` — núcleo TCP/UDP (sem dependência de GUI; pode ser importado por outro script ou por um clone em outra linguagem).
- `bx100_ble.py` — protocolo BLE documentado (codec de pacotes + conexão via `bleak`).
- `bx100_sound.py` — espaço reservado para o pareamento por som; levanta erro claro até ser implementado.
- `bx100_gui.py` — a interface.

## Segurança e escopo

Use só com um aparelho que você possui. Nenhuma credencial ou dado pessoal é coletado ou enviado para qualquer lugar fora do seu aparelho/rede local. Chave e IV AES são constantes públicas, embutidas no APK original (não são segredo deste projeto).
