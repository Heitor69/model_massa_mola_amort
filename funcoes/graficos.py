"""Graficos do lado direito: x(t), resposta em frequencia e mapa de polos."""

import numpy as np

COR_MF = "#2a78d6"       # malha fechada (com PID)
COR_PLANTA = "#eb6834"   # planta sem controle
COR_REF = "#8a8984"
COR_TEXTO = "#52514e"
COR_GRADE = "#e4e3df"
COR_INSTAVEL = "#e34948"


def _estilo(ax):
    ax.grid(True, which="major", color=COR_GRADE, lw=0.6)
    ax.grid(True, which="minor", color=COR_GRADE, lw=0.3, alpha=0.5)
    ax.tick_params(colors=COR_TEXTO, labelsize=8)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(COR_GRADE)
    ax.xaxis.label.set_color(COR_TEXTO)
    ax.yaxis.label.set_color(COR_TEXTO)


def _limites(ax_set, *series, minimo=1.0):
    v = np.concatenate([np.ravel(s) for s in series])
    v = v[np.isfinite(v)]
    lo, hi = (v.min(), v.max()) if v.size else (0, 1)
    folga = 0.08 * (hi - lo) if hi - lo > 1e-12 else minimo
    ax_set(lo - folga, hi + folga)


class Graficos:
    def __init__(self, fig):
        gs = fig.add_gridspec(3, 2, height_ratios=[1.3, 1, 1], width_ratios=[1.6, 1],
                              hspace=0.6, wspace=0.28)
        self.ax_t = fig.add_subplot(gs[0, :])
        self.ax_mag = fig.add_subplot(gs[1, 0])
        self.ax_fase = fig.add_subplot(gs[2, 0], sharex=self.ax_mag)
        self.ax_polos = fig.add_subplot(gs[1:, 1])

        # Tempo
        self.l_ref, = self.ax_t.plot([], [], color=COR_REF, lw=1.2, ls="--", label="referência r")
        self.l_ma, = self.ax_t.plot([], [], color=COR_PLANTA, lw=1.5, alpha=0.85,
                                    label="sem controle")
        self.l_x, = self.ax_t.plot([], [], color=COR_MF, lw=2, label="com PID")
        self.cursor = self.ax_t.axvline(0, color=COR_TEXTO, lw=0.8, alpha=0.6)
        self.banda = None
        self.ax_t.set_xlabel("t [s]", fontsize=9)
        self.ax_t.set_ylabel("x [m]", fontsize=9)
        self.leg_t = None

        # Frequencia
        self.l_mag_mf, = self.ax_mag.semilogx([], [], color=COR_MF, lw=2, label="com PID  X/R")
        self.l_mag_p, = self.ax_mag.semilogx([], [], color=COR_PLANTA, lw=2, label="planta  X/F")
        self.ax_mag.set_title("Amplitude por frequência", fontsize=10, loc="left")
        self.ax_mag.set_ylabel("|H| [dB]", fontsize=9)
        self.ax_mag.legend(loc="lower left", fontsize=8, frameon=False)

        self.l_fase_mf, = self.ax_fase.semilogx([], [], color=COR_MF, lw=2)
        self.l_fase_p, = self.ax_fase.semilogx([], [], color=COR_PLANTA, lw=2)
        self.ax_fase.set_title("Fase por frequência", fontsize=10, loc="left")
        self.ax_fase.set_ylabel("fase [°]", fontsize=9)

        # Polos
        ax = self.ax_polos
        ax.set_title("Mapa de polos e zeros (plano s)", fontsize=10, loc="left")
        ax.set_xlabel("Re(s)", fontsize=9)
        ax.set_ylabel("Im(s)", fontsize=9)
        ax.axhline(0, color=COR_TEXTO, lw=0.8)
        ax.axvline(0, color=COR_TEXTO, lw=0.8)
        self.p_planta, = ax.plot([], [], "x", color=COR_PLANTA, ms=9, mew=2, label="polos planta")
        self.p_mf, = ax.plot([], [], "x", color=COR_MF, ms=10, mew=2.4, label="polos com PID")
        self.z_mf, = ax.plot([], [], "o", mfc="none", color=COR_MF, ms=9, mew=1.8,
                             label="zeros com PID")
        ax.legend(loc="upper left", fontsize=8, frameon=False)
        self.regiao_instavel = None

        self.linhas_wn = []
        for a in (self.ax_t, self.ax_mag, self.ax_fase, self.ax_polos):
            _estilo(a)

    def atualizar(self, d):
        """d: dicionario com os resultados calculados na interface."""
        self._atualizar_tempo(d)
        self._atualizar_frequencia(d)
        self._atualizar_polos(d)

    def _atualizar_tempo(self, d):
        t, x, x_ma, ref = d["t"], d["x"], d["x_ma"], d["ref"]
        ax = self.ax_t
        self.l_x.set_data(t, x)
        self.l_ref.set_data([t[0], t[-1]], [ref, ref])
        if x_ma is None:
            self.l_ma.set_data([], [])
        else:
            self.l_ma.set_data(t, x_ma)
        if self.banda is not None:
            self.banda.remove()
            self.banda = None
        if d["modo"] == "degrau":
            ax.set_title("Deslocamento no tempo — degrau na referência", fontsize=10, loc="left")
            self.banda = ax.axhspan(ref - 0.02 * abs(ref), ref + 0.02 * abs(ref),
                                    color=COR_REF, alpha=0.12, lw=0)
            self.l_ma.set_label("sem controle (F = K·r)")
        else:
            ax.set_title("Deslocamento no tempo — condição inicial (r = 0)", fontsize=10, loc="left")
            self.l_ma.set_label("sem controle (livre)")
        if self.leg_t is not None:
            self.leg_t.remove()
        self.leg_t = ax.legend(loc="lower right", fontsize=8, frameon=False)
        ax.set_xlim(t[0], t[-1])
        series = [x, [0, ref]] + ([] if x_ma is None else [x_ma])
        _limites(ax.set_ylim, *series)

    def _atualizar_frequencia(self, d):
        fator = 1 / (2 * np.pi) if d["hz"] else 1.0
        f = d["w"] * fator
        self.l_mag_mf.set_data(f, d["mag_mf"])
        self.l_mag_p.set_data(f, d["mag_p"])
        self.l_fase_mf.set_data(f, d["fase_mf"])
        self.l_fase_p.set_data(f, d["fase_p"])
        self.ax_mag.set_xlim(f[0], f[-1])
        self.ax_fase.set_xlabel("f [Hz]" if d["hz"] else "ω [rad/s]", fontsize=9)
        _limites(self.ax_mag.set_ylim, d["mag_mf"], d["mag_p"])
        _limites(self.ax_fase.set_ylim, d["fase_mf"], d["fase_p"])

        for l in self.linhas_wn:
            l.remove()
        self.linhas_wn = []
        if d["wn"] is not None:
            fn = d["wn"] * fator
            for ax in (self.ax_mag, self.ax_fase):
                self.linhas_wn.append(ax.axvline(fn, color=COR_REF, lw=0.8, ls=":"))
            rot = f" fn={fn:.2f} Hz" if d["hz"] else f" ωn={fn:.2f} rad/s"
            self.linhas_wn.append(self.ax_mag.text(
                fn, 1.0, rot, transform=self.ax_mag.get_xaxis_transform(),
                fontsize=8, color=COR_TEXTO, va="bottom"))

    def _atualizar_polos(self, d):
        ax = self.ax_polos
        pp, pm, zm = d["polos_p"], d["polos_mf"], d["zeros_mf"]
        self.p_planta.set_data(pp.real, pp.imag)
        self.p_mf.set_data(pm.real, pm.imag)
        self.z_mf.set_data(zm.real, zm.imag)

        todos = np.concatenate([pp, pm, zm, [0]])
        todos = todos[np.isfinite(todos)]
        r = max(np.abs(todos.real).max(), np.abs(todos.imag).max(), 1e-3) * 1.15
        re_min = min(todos.real.min(), 0)
        re_max = max(todos.real.max(), 0)
        larg = max(re_max - re_min, 1e-3)
        ax.set_xlim(re_min - 0.15 * larg, re_max + 0.15 * larg + 0.05 * r)
        ax.set_ylim(-r, r)

        if self.regiao_instavel is not None:
            self.regiao_instavel.remove()
        self.regiao_instavel = ax.axvspan(0, ax.get_xlim()[1] + 1e9, color=COR_INSTAVEL,
                                          alpha=0.08, lw=0)

    def mover_cursor(self, t):
        self.cursor.set_xdata([t, t])
