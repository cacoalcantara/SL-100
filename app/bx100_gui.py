"""
bx100-community — programa Windows para configurar o BX100/SL100 localmente,
sem depender da nuvem da Sabala (desativada).

RECONSTRUÇÃO a partir de engenharia reversa estática do APK com.picoshadow.bx100
v1.2.3. NÃO é software oficial da Sabala/PicoShadow. Ver ../docs/PROTOCOL.md e
../docs/PROVISIONING.md para a origem de cada afirmação.

Rodar: python bx100_gui.py   (precisa de: pip install pycryptodome bleak)
"""
from __future__ import annotations

import asyncio
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import bx100_protocol as proto
import bx100_ble as ble
import bx100_sound as sound


class LogPane(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.text = tk.Text(self, height=14, wrap="word", state="disabled", bg="#111", fg="#ddd")
        scroll = ttk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def log(self, msg: str):
        self.text.configure(state="normal")
        self.text.insert("end", msg.rstrip() + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")


def run_async(coro, on_done=None):
    """Roda uma corrotina numa thread separada para nao travar a GUI."""
    def worker():
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(coro)
            if on_done:
                on_done(result, None)
        except Exception as e:  # noqa: BLE001
            if on_done:
                on_done(None, e)
        finally:
            loop.close()
    threading.Thread(target=worker, daemon=True).start()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("bx100-community — configuração local do BX100/SL100")
        self.geometry("760x620")

        banner = tk.Label(
            self,
            text="Reconstrução por engenharia reversa — não é app oficial da Sabala. "
                 "Use só com um aparelho seu. Veja o status de cada aba abaixo.",
            wraplength=740, justify="left", bg="#332200", fg="#ffcc66", padx=8, pady=6,
        )
        banner.pack(fill="x")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        self.log = LogPane(self)
        self.log.pack(fill="both", expand=False, padx=6, pady=(0, 6))

        nb.add(self._build_tcp_tab(nb), text="Wi-Fi / TCP (modo AP)")
        nb.add(self._build_ble_tab(nb), text="Bluetooth (BLE)")
        nb.add(self._build_sound_tab(nb), text="Pareamento por som")

        self.log.log("Pronto. Nenhum caminho foi validado contra hardware real ainda, exceto o que a aba indicar.")

    # ---------------- TCP/UDP ----------------
    def _build_tcp_tab(self, nb):
        f = ttk.Frame(nb, padding=10)
        status = tk.Label(
            f,
            text="STATUS: documentado a partir do código decompilado (util/k.java, util/e.java, util/d.java); "
                 "consistência interna verificada; AINDA NÃO testado contra um aparelho real.",
            fg="#cc8800", wraplength=700, justify="left",
        )
        status.pack(anchor="w", pady=(0, 10))

        ttk.Label(f, text="1) Conecte seu PC na rede Wi-Fi que a caixa cria (modo AP), se ela criar uma.").pack(anchor="w")
        ttk.Button(f, text="Descobrir aparelho (broadcast UDP)", command=self._do_discover).pack(anchor="w", pady=4)

        row = ttk.Frame(f)
        row.pack(fill="x", pady=8)
        ttk.Label(row, text="IP do aparelho:").grid(row=0, column=0, sticky="w")
        self.ip_var = tk.StringVar(value=proto.AP_IP)
        ttk.Entry(row, textvariable=self.ip_var, width=20).grid(row=0, column=1, sticky="w", padx=4)

        ttk.Button(f, text="GetDevInfo", command=self._do_get_dev_info).pack(anchor="w", pady=2)

        wifi_row = ttk.LabelFrame(f, text="ConnectWIFI")
        wifi_row.pack(fill="x", pady=8)
        self.ssid_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        ttk.Label(wifi_row, text="SSID:").grid(row=0, column=0, sticky="w")
        ttk.Entry(wifi_row, textvariable=self.ssid_var, width=24).grid(row=0, column=1, padx=4, pady=2)
        ttk.Label(wifi_row, text="Senha:").grid(row=1, column=0, sticky="w")
        ttk.Entry(wifi_row, textvariable=self.pass_var, width=24, show="*").grid(row=1, column=1, padx=4, pady=2)
        ttk.Button(wifi_row, text="Enviar ConnectWIFI", command=self._do_connect_wifi).grid(row=2, column=0, columnspan=2, pady=4)

        auth_row = ttk.LabelFrame(f, text="Authorize (authCode vinha da nuvem — hoje desativada)")
        auth_row.pack(fill="x", pady=8)
        self.authcode_var = tk.StringVar()
        ttk.Label(auth_row, text="authCode:").grid(row=0, column=0, sticky="w")
        ttk.Entry(auth_row, textvariable=self.authcode_var, width=30).grid(row=0, column=1, padx=4, pady=2)
        ttk.Button(auth_row, text="Enviar Authorize", command=self._do_authorize).grid(row=1, column=0, columnspan=2, pady=4)

        tz_row = ttk.LabelFrame(f, text="SetTimezone")
        tz_row.pack(fill="x", pady=8)
        self.tz_city_var = tk.StringVar(value="America/Sao_Paulo")
        self.tz_offset_var = tk.StringVar(value="-3")
        ttk.Label(tz_row, text="Timezone:").grid(row=0, column=0, sticky="w")
        ttk.Entry(tz_row, textvariable=self.tz_city_var, width=24).grid(row=0, column=1, padx=4, pady=2)
        ttk.Label(tz_row, text="Offset (h):").grid(row=1, column=0, sticky="w")
        ttk.Entry(tz_row, textvariable=self.tz_offset_var, width=8).grid(row=1, column=1, sticky="w", padx=4, pady=2)
        ttk.Button(tz_row, text="Enviar SetTimezone", command=self._do_set_timezone).grid(row=2, column=0, columnspan=2, pady=4)

        return f

    def _send_tcp(self, label: str, json_text: str):
        ip = self.ip_var.get().strip()
        self.log.log(f"{label} -> {ip}:{proto.TCP_PORT} ...")

        def task():
            try:
                resp = proto.send_directive(ip, json_text)
                self.after(0, lambda: self.log.log(f"resposta: {resp}"))
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: self.log.log(f"erro: {e}"))
        threading.Thread(target=task, daemon=True).start()

    def _do_authorize(self):
        code = self.authcode_var.get().strip()
        if not code:
            messagebox.showwarning("authCode vazio", "Informe um authCode. Lembrando: ele vinha da nuvem, hoje desativada.")
            return
        self._send_tcp("Authorize", proto.authorize(code))

    def _do_set_timezone(self):
        city = self.tz_city_var.get().strip()
        try:
            offset_s = int(round(float(self.tz_offset_var.get()) * 3600))
        except ValueError:
            messagebox.showwarning("Offset inválido", "Offset deve ser um número de horas, ex.: -3")
            return
        self._send_tcp("SetTimezone", proto.set_timezone(city, offset_s))

    def _do_discover(self):
        self.log.log("Descobrindo (broadcast UDP, 3s)...")
        def task():
            try:
                found = proto.discover(3.0)
                self.after(0, lambda: self._discover_done(found))
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: self.log.log(f"erro na descoberta: {e}"))
        threading.Thread(target=task, daemon=True).start()

    def _discover_done(self, found):
        if not found:
            self.log.log("nenhum aparelho respondeu ao broadcast.")
        for d in found:
            self.log.log(f"achado: {d.manu}/{d.name} mac={d.mac} ip={d.ip}")
            self.ip_var.set(d.ip)

    def _do_get_dev_info(self):
        self._send_tcp("GetDevInfo", proto.get_dev_info())

    def _do_connect_wifi(self):
        ssid = self.ssid_var.get().strip()
        pwd = self.pass_var.get()
        if not ssid:
            messagebox.showwarning("SSID vazio", "Informe o SSID da rede Wi-Fi.")
            return
        self._send_tcp("ConnectWIFI", proto.connect_wifi(ssid, pwd))

    # ---------------- BLE ----------------
    def _build_ble_tab(self, nb):
        f = ttk.Frame(nb, padding=10)
        status = tk.Label(
            f,
            text="STATUS: testado contra um SL100 real em 2026-11-03. O serviço documentado (0000f012) NÃO "
                 "apareceu no aparelho testado — nem em modo normal, nem após o long-press do botão de "
                 "configuração. O que o aparelho expõe é um perfil de teste de fábrica do chip Bluetooth, que "
                 "não responde a este protocolo. Pode funcionar em outra unidade/revisão; não conte com isso.",
            fg="#cc4444", wraplength=700, justify="left",
        )
        status.pack(anchor="w", pady=(0, 10))

        ttk.Button(f, text="Escanear (10s, filtra nome 'SL100')", command=self._do_ble_scan).pack(anchor="w")

        row = ttk.Frame(f)
        row.pack(fill="x", pady=8)
        ttk.Label(row, text="Endereço BLE:").grid(row=0, column=0, sticky="w")
        self.ble_addr_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.ble_addr_var, width=24).grid(row=0, column=1, padx=4)

        ttk.Button(f, text="Tentar GetDevInfo pelo protocolo documentado", command=self._do_ble_get_info).pack(anchor="w", pady=6)
        return f

    def _do_ble_scan(self):
        self.log.log("Escaneando BLE (10s)...")
        run_async(ble.scan_for_device("SL100", 10.0), self._ble_scan_done)

    def _ble_scan_done(self, result, err):
        if err:
            self.log.log(f"erro no escaneio BLE: {err}")
            return
        if not result:
            self.log.log("nenhum dispositivo 'SL100' encontrado anunciando agora.")
        for addr, name, rssi in result:
            self.log.log(f"achado: {addr} name={name!r} rssi={rssi}")
            self.ble_addr_var.set(addr)

    def _do_ble_get_info(self):
        addr = self.ble_addr_var.get().strip()
        if not addr:
            messagebox.showwarning("Endereço vazio", "Escaneie ou informe um endereço BLE primeiro.")
            return
        self.log.log(f"Conectando em {addr} e tentando GetDevInfo documentado...")
        writes = ble.get_info(msg_id=1)
        run_async(ble.try_documented_protocol(addr, writes), self._ble_result_done)

    def _ble_result_done(self, result: ble.BleResult | None, err):
        if err:
            self.log.log(f"erro: {err}")
            return
        if not result.service_found:
            self.log.log(f"protocolo documentado não respondeu: {result.error}")
            return
        self.log.log(f"OK — {len(result.notifications)} notificação(ões) recebida(s):")
        for n in result.notifications:
            self.log.log(f"  {n.hex()}")

    # ---------------- Som ----------------
    def _build_sound_tab(self, nb):
        f = ttk.Frame(nb, padding=10)
        status = tk.Label(
            f,
            text="STATUS: NÃO IMPLEMENTADO. A biblioteca nativa do pareamento por som "
                 "(libSoundAutentication_jni) já tem pseudocódigo C extraído pelo Ghidra, mas ainda não foi "
                 "interpretado. A tela do app pede para segurar o botão físico até ouvir um aviso sonoro — isso "
                 "sugere que é este o caminho real usado por esta unidade, já que o BLE documentado não bateu.",
            fg="#cc4444", wraplength=700, justify="left",
        )
        status.pack(anchor="w", pady=(0, 10))
        ttk.Button(f, text="Tentar (vai falhar, propositalmente)", command=self._do_sound).pack(anchor="w")
        return f

    def _do_sound(self):
        try:
            sound.pair_by_sound()
        except sound.SoundPairingNotImplemented as e:
            self.log.log(f"(esperado) {e}")


if __name__ == "__main__":
    App().mainloop()
