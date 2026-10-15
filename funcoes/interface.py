"""Janela principal: modelo fisico + controles a esquerda, graficos a direita."""

import time
import tkinter as tk
from tkinter import ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from funcoes import modelo
from funcoes.desenho import DesenhoModelo
from funcoes.graficos import Graficos

# nome: (rotulo, minimo, maximo, passo, padrao)
PARAMETROS_PLANTA = {
    "M": ("Massa M [kg]", 0.1, 20.0, 0.1, 1.0),
    "K": ("Rigidez K [N/m]", 0.0, 200.0, 0.5, 20.0),
    "C": ("Amortecimento C [N·s/m]", 0.0, 50.0, 0.1, 2.0),
}
PARAMETROS_PID = {
    "Kp": ("Kp", 0.0, 500.0, 0.5, 50.0),
    "Ki": ("Ki", 0.0, 500.0, 0.5, 20.0),
    "Kd": ("Kd", 0.0, 100.0, 0.1, 5.0),
}
PARAMETROS_ENTRADA = {
    "ref": ("Referência r [m]", -2.0, 2.0, 0.01, 1.0),
    "x0": ("Posição inicial x0 [m]", -2.0, 2.0, 0.01, 0.5),
    "v0": ("Velocidade inicial v0 [m/s]", -10.0, 10.0, 0.05, 0.0),
}
CONTROLES_DO_MODO = {"degrau": ("ref",), "ci": ("x0", "v0")}
PARAMETROS_SIM = {
    "tf": ("Tempo final [s]", 1.0, 60.0, 0.5, 10.0),
    "vel": ("Velocidade animação [x]", 0.1, 4.0, 0.1, 1.0),
}
N_PONTOS = 2000
FPS = 30


def _limpar(x):
    """Evita nan/inf quando o sistema e instavel."""
    return np.nan_to_num(x, nan=0.0, posinf=1e6, neginf=-1e6)


class Controle(ttk.Frame):
    """Slider + caixa de texto sincronizados."""

    def __init__(self, master, rotulo, vmin, vmax, passo, padrao, ao_mudar):
        super().__init__(master)
        self.padrao = padrao
        self.ao_mudar = ao_mudar
        self.var = tk.DoubleVar(value=padrao)
        self.txt = tk.StringVar(value=f"{padrao:g}")

        ttk.Label(self, text=rotulo, width=24).grid(row=0, column=0, sticky="w")
        self.escala = tk.Scale(self, variable=self.var, from_=vmin, to=vmax, resolution=passo,
                               orient="horizontal", showvalue=False, length=200,
                               highlightthickness=0, command=self._do_slider)
        self.escala.grid(row=0, column=1, sticky="ew", padx=4)
        self.caixa = ttk.Entry(self, textvariable=self.txt, width=8, justify="right")
        self.caixa.grid(row=0, column=2)
        self.caixa.bind("<Return>", self._da_caixa)
        self.caixa.bind("<FocusOut>", self._da_caixa)
        self.columnconfigure(1, weight=1)

    def habilitar(self, ativo):
        self.escala.config(state="normal" if ativo else "disabled",
                           fg="black" if ativo else "gray")
        self.caixa.config(state="normal" if ativo else "disabled")

    def _do_slider(self, _):
        self.txt.set(f"{self.var.get():g}")
        self.ao_mudar()

    def _da_caixa(self, _):
        # A caixa aceita valores fora da faixa do slider.
        try:
            v = float(self.txt.get().replace(",", "."))
        except ValueError:
            self.txt.set(f"{self.var.get():g}")
            return
        if v != self.var.get():
            self.var.set(v)
            self.ao_mudar()

    def valor(self):
        return self.var.get()

    def restaurar(self):
        self.var.set(self.padrao)
        self.txt.set(f"{self.padrao:g}")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Massa-mola-amortecedor com controle PID")
        self.geometry("1500x900")
        self.state("zoomed")
        self.minsize(1100, 700)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        self._agendado = None
        self._animando = False
        self._t_anim = 0.0
        self._t_relogio = None
        self.t = np.linspace(0, 10, N_PONTOS)
        self.x = np.zeros_like(self.t)

        self._montar_esquerda()
        self._montar_direita()
        self.recalcular()

    # ---------- layout ----------
    def _montar_esquerda(self):
        esq = ttk.Frame(self, padding=8)
        esq.pack(side="left", fill="y")

        fig = Figure(figsize=(5.4, 2.4), dpi=100)
        fig.subplots_adjust(0, 0, 1, 1)
        self.desenho = DesenhoModelo(fig.add_subplot())
        self.canvas_modelo = FigureCanvasTkAgg(fig, master=esq)
        self.canvas_modelo.get_tk_widget().pack(fill="x")

        botoes = ttk.Frame(esq)
        botoes.pack(fill="x", pady=6)
        self.btn_play = ttk.Button(botoes, text="▶  Animar", command=self.alternar_animacao)
        self.btn_play.pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(botoes, text="⟲  Reiniciar animação", command=self.reiniciar_animacao)\
            .pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(botoes, text="Valores padrão", command=self.restaurar_padrao)\
            .pack(side="left", expand=True, fill="x", padx=2)

        painel = self._painel_rolavel(esq)

        self.modo = tk.StringVar(value="degrau")
        self.hz = tk.BooleanVar(value=False)
        self.controles = {}
        for titulo, grupo in (("Planta", PARAMETROS_PLANTA),
                              ("Controlador PID", PARAMETROS_PID),
                              ("Entrada", PARAMETROS_ENTRADA),
                              ("Simulação", PARAMETROS_SIM)):
            lf = ttk.LabelFrame(painel, text=titulo, padding=6)
            lf.pack(fill="x", pady=4)
            if titulo == "Entrada":
                linha = ttk.Frame(lf)
                linha.pack(fill="x", pady=(0, 2))
                for txt, val in (("Degrau na referência", "degrau"),
                                 ("Condição inicial (r = 0)", "ci")):
                    ttk.Radiobutton(linha, text=txt, value=val, variable=self.modo,
                                    command=self._trocar_modo).pack(side="left", padx=(0, 12))
            for nome, (rot, vmin, vmax, passo, pad) in grupo.items():
                c = Controle(lf, rot, vmin, vmax, passo, pad, self.agendar_recalculo)
                c.pack(fill="x", pady=1)
                self.controles[nome] = c
        self._habilitar_controles_do_modo()

        lf = ttk.LabelFrame(painel, text="Resultados", padding=6)
        lf.pack(fill="x", pady=4)
        self.lbl_metricas = tk.Text(lf, height=9, width=62, font=("Consolas", 9),
                                    relief="flat", background=self.cget("background"))
        self.lbl_metricas.pack(fill="x")

    def _painel_rolavel(self, master):
        """Frame com barra de rolagem vertical (para telas pequenas)."""
        caixa = ttk.Frame(master)
        caixa.pack(fill="both", expand=True)
        tela = tk.Canvas(caixa, highlightthickness=0, borderwidth=0)
        barra = ttk.Scrollbar(caixa, orient="vertical", command=tela.yview)
        tela.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        tela.pack(side="left", fill="both", expand=True)

        interno = ttk.Frame(tela)
        janela = tela.create_window((0, 0), window=interno, anchor="nw")
        interno.bind("<Configure>", lambda e: tela.configure(
            scrollregion=tela.bbox("all"), width=interno.winfo_reqwidth()))
        tela.bind("<Configure>", lambda e: tela.itemconfigure(janela, width=e.width))

        def rolar(e):
            tela.yview_scroll(int(-e.delta / 120), "units")
        caixa.bind("<Enter>", lambda e: tela.bind_all("<MouseWheel>", rolar))
        caixa.bind("<Leave>", lambda e: tela.unbind_all("<MouseWheel>"))
        return interno

    def _montar_direita(self):
        dir_ = ttk.Frame(self, padding=(0, 8, 8, 8))
        dir_.pack(side="left", fill="both", expand=True)

        fig = Figure(figsize=(8, 8), dpi=100)
        fig.subplots_adjust(left=0.09, right=0.98, top=0.95, bottom=0.07)
        self.graficos = Graficos(fig)
        self.canvas_graf = FigureCanvasTkAgg(fig, master=dir_)
        barra = NavigationToolbar2Tk(self.canvas_graf, dir_)
        barra.update()
        ttk.Checkbutton(barra, text="Frequência em Hz", variable=self.hz,
                        command=self.recalcular).pack(side="right", padx=8)
        self.canvas_graf.get_tk_widget().pack(fill="both", expand=True)

    def _habilitar_controles_do_modo(self):
        modo = self.modo.get()
        for m, nomes in CONTROLES_DO_MODO.items():
            for n in nomes:
                self.controles[n].habilitar(m == modo)

    def _trocar_modo(self):
        self._habilitar_controles_do_modo()
        self._t_anim = 0.0
        self.recalcular()

    # ---------- calculo ----------
    def agendar_recalculo(self):
        if self._agendado is not None:
            self.after_cancel(self._agendado)
        self._agendado = self.after(60, self.recalcular)

    def recalcular(self):
        self._agendado = None
        v = {n: c.valor() for n, c in self.controles.items()}
        M, K, C = max(v["M"], 1e-6), v["K"], v["C"]
        Kp, Ki, Kd = v["Kp"], v["Ki"], v["Kd"]
        degrau = self.modo.get() == "degrau"
        ref = v["ref"] if degrau else 0.0
        x0, v0 = (0.0, 0.0) if degrau else (v["x0"], v["v0"])

        num_p, den_p = modelo.funcao_planta(M, C, K)
        num_mf, den_mf = modelo.funcao_malha_fechada(M, C, K, Kp, Ki, Kd)

        t = np.linspace(0, max(v["tf"], 0.1), N_PONTOS)
        with np.errstate(all="ignore"):
            if degrau:
                x = modelo.resposta_degrau(num_mf, den_mf, t, ref)
                x_ma = modelo.resposta_degrau_planta(M, C, K, t, ref)
            else:
                x = modelo.resposta_livre_malha_fechada(M, C, K, Kp, Ki, Kd, t, x0, v0)
                x_ma = modelo.resposta_livre_planta(M, C, K, t, x0, v0)
        self.t, self.ref = t, ref
        self.x = _limpar(x)
        x_ma = None if x_ma is None else _limpar(x_ma)

        w = modelo.faixa_frequencia(den_p, den_mf)
        mag_mf, fase_mf = modelo.resposta_frequencia(num_mf, den_mf, w)
        mag_p, fase_p = modelo.resposta_frequencia(num_p, den_p, w)

        self.graficos.atualizar(dict(
            modo=self.modo.get(), t=t, x=self.x, x_ma=x_ma, ref=ref,
            w=w, mag_mf=mag_mf, fase_mf=fase_mf, mag_p=mag_p, fase_p=fase_p,
            wn=np.sqrt(K / M) if K > 0 else None, hz=self.hz.get(),
            polos_p=modelo.polos(den_p), polos_mf=modelo.polos(den_mf),
            zeros_mf=modelo.zeros(num_mf),
        ))
        self.desenho.definir_escala(max(np.abs(self.x).max(), abs(ref)))
        self._t_anim = min(self._t_anim, t[-1])
        self._desenhar_quadro()
        self.canvas_graf.draw_idle()

        if degrau:
            m = modelo.metricas(t, self.x, num_mf, den_mf, ref)
        else:
            m = modelo.metricas_condicao_inicial(t, self.x, den_mf)
        self._mostrar_metricas(m, M, K, C, degrau)

    def _mostrar_metricas(self, m, M, K, C, degrau):
        def f(v, un=""):
            return "   —" if v is None or np.isnan(v) else f"{v:8.4f} {un}"

        linhas = []
        if K > 0:
            wn = np.sqrt(K / M)
            zeta = C / (2 * np.sqrt(K * M))
            linhas.append(f"Planta:  ωn = {wn:.3f} rad/s ({wn / (2 * np.pi):.3f} Hz)   ζ = {zeta:.3f}")
        else:
            linhas.append("Planta:  K = 0 (sem rigidez)")
        linhas.append(f"Com PID: {'ESTÁVEL' if m['estavel'] else 'INSTÁVEL'}")
        linhas.append("")
        if degrau:
            linhas.append(f"Valor final       {f(m['valor_final'], 'm')}")
            linhas.append(f"Erro reg. perm.   {f(m['erro_rp'], 'm')}")
            linhas.append(f"Sobressinal       {f(m['sobressinal'], '%')}")
            linhas.append(f"Tempo de subida   {f(m['t_subida'], 's')}   (10–90%)")
            linhas.append(f"Tempo acomodação  {f(m['t_acomodacao'], 's')}   (±2%)")
        else:
            linhas.append(f"Desvio máximo |x| {f(m['pico'], 'm')}")
            linhas.append(f"Tempo acomodação  {f(m['t_acomodacao'], 's')}   (2% do pico)")
        linhas.append("")
        polos = ", ".join(
            f"{p.real:.2f}{p.imag:+.2f}j" if abs(p.imag) > 1e-9 else f"{p.real:.2f}"
            for p in m["polos"])
        linhas.append(f"Polos MF: {polos}")

        self.lbl_metricas.config(state="normal")
        self.lbl_metricas.delete("1.0", "end")
        self.lbl_metricas.insert("1.0", "\n".join(linhas))
        self.lbl_metricas.config(state="disabled")

    # ---------- animacao ----------
    def _desenhar_quadro(self):
        xa = np.interp(self._t_anim, self.t, self.x)
        self.desenho.atualizar(xa, self._t_anim, self.ref)
        self.graficos.mover_cursor(self._t_anim)
        self.canvas_modelo.draw_idle()

    def alternar_animacao(self):
        self._animando = not self._animando
        self.btn_play.config(text="⏸  Pausar" if self._animando else "▶  Animar")
        if self._animando:
            if self._t_anim >= self.t[-1]:
                self._t_anim = 0.0
            self._t_relogio = time.perf_counter()
            self._passo_animacao()

    def _passo_animacao(self):
        if not self._animando:
            return
        agora = time.perf_counter()
        self._t_anim += (agora - self._t_relogio) * self.controles["vel"].valor()
        self._t_relogio = agora
        if self._t_anim >= self.t[-1]:
            self._t_anim = self.t[-1]
            self.alternar_animacao()
        self._desenhar_quadro()
        self.canvas_graf.draw_idle()
        if self._animando:
            self.after(int(1000 / FPS), self._passo_animacao)

    def reiniciar_animacao(self):
        self._t_anim = 0.0
        self._t_relogio = time.perf_counter()
        self._desenhar_quadro()
        self.canvas_graf.draw_idle()

    def restaurar_padrao(self):
        for c in self.controles.values():
            c.restaurar()
        self.recalcular()

    def _fechar(self):
        self._animando = False
        self.quit()
        self.destroy()
