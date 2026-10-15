"""Desenho animado do modelo fisico (parede - mola/amortecedor - massa)."""

import numpy as np
from matplotlib.patches import FancyArrowPatch, Rectangle

COR_MASSA = "#2a78d6"
COR_LINHA = "#3a3936"
COR_REF = "#eb6834"

X_REPOUSO = 3.0      # posicao da face esquerda da massa em repouso
LARG_MASSA = 1.2
ALT_MASSA = 1.2
Y_MOLA = 0.9
Y_AMORT = 0.3
CURSO = 1.6          # deslocamento maximo desenhado (unidades do desenho)


def _pontos_mola(x0, x1, y, n_espiras=7, amp=0.15):
    """Zigue-zague entre x0 e x1, com pequenos trechos retos nas pontas."""
    comp = x1 - x0
    ponta = 0.12 * comp
    xs = np.linspace(x0 + ponta, x1 - ponta, 2 * n_espiras + 1)
    ys = np.full_like(xs, y)
    ys[1:-1:2] += amp
    ys[2:-1:2] -= amp
    return np.r_[x0, xs, x1], np.r_[y, ys, y]


class DesenhoModelo:
    def __init__(self, ax):
        self.ax = ax
        ax.set_xlim(-0.4, X_REPOUSO + LARG_MASSA + CURSO + 0.6)
        ax.set_ylim(-0.6, 1.9)
        ax.set_aspect("equal")
        ax.axis("off")

        # Parede e chao
        ax.add_patch(Rectangle((-0.3, -0.1), 0.3, 1.6, hatch="////",
                               facecolor="none", edgecolor=COR_LINHA, lw=0))
        ax.plot([0, 0], [-0.1, 1.5], color=COR_LINHA, lw=2)
        ax.plot([-0.3, ax.get_xlim()[1]], [-0.1, -0.1], color=COR_LINHA, lw=2)

        # Mola, amortecedor e massa (atualizados a cada quadro)
        self.mola, = ax.plot([], [], color=COR_LINHA, lw=1.8)
        self.haste, = ax.plot([], [], color=COR_LINHA, lw=1.8)
        self.pistao, = ax.plot([], [], color=COR_LINHA, lw=3)
        self.cilindro, = ax.plot([], [], color=COR_LINHA, lw=1.8)
        self.massa = Rectangle((X_REPOUSO, 0), LARG_MASSA, ALT_MASSA,
                               facecolor=COR_MASSA, edgecolor=COR_LINHA, lw=1.5)
        ax.add_patch(self.massa)
        self.txt_massa = ax.text(0, ALT_MASSA / 2, "M", color="white",
                                 ha="center", va="center", fontsize=14, weight="bold")

        ax.text(1.4, Y_MOLA + 0.3, "K", ha="center", fontsize=11, color=COR_LINHA)
        ax.text(1.4, Y_AMORT - 0.42, "C", ha="center", fontsize=11, color=COR_LINHA)

        # Referencia (onde o controlador quer levar a massa)
        self.ref, = ax.plot([], [], color=COR_REF, lw=1.5, ls="--")
        self.txt_ref = ax.text(0, 1.55, "ref", color=COR_REF, ha="center", fontsize=9)

        # Seta de deslocamento x(t)
        self.seta = FancyArrowPatch((0, 0), (0, 0), arrowstyle="-|>", mutation_scale=12,
                                    color=COR_LINHA, lw=1.2)
        ax.add_patch(self.seta)
        ax.plot([X_REPOUSO, X_REPOUSO], [-0.5, -0.15], color=COR_LINHA, lw=1, ls=":")
        self.txt_x = ax.text(X_REPOUSO, -0.55, "", ha="left", va="top", fontsize=9,
                             color=COR_LINHA, family="monospace")
        self.txt_t = ax.text(-0.3, 1.85, "", ha="left", va="top", fontsize=9,
                             color=COR_LINHA, family="monospace")
        self.escala = 1.0

    def definir_escala(self, x_max):
        """x_max (m) e mapeado para CURSO unidades do desenho."""
        self.escala = CURSO / x_max if x_max > 1e-12 else 1.0

    def atualizar(self, x, t, ref):
        e = self.escala
        xm = X_REPOUSO + np.clip(x * e, -X_REPOUSO + 0.8, CURSO + 0.5)

        self.massa.set_x(xm)
        self.txt_massa.set_x(xm + LARG_MASSA / 2)

        self.mola.set_data(*_pontos_mola(0, xm, Y_MOLA))

        # Amortecedor: haste presa na parede, cilindro preso na massa
        cil_dir = xm
        cil_esq = xm - 0.9
        pist = np.clip(X_REPOUSO - 0.45, cil_esq + 0.08, cil_dir - 0.08)
        self.haste.set_data([0, pist], [Y_AMORT, Y_AMORT])
        self.pistao.set_data([pist, pist], [Y_AMORT - 0.12, Y_AMORT + 0.12])
        self.cilindro.set_data(
            [cil_esq, cil_dir, cil_dir, cil_dir, cil_esq],
            [Y_AMORT + 0.2, Y_AMORT + 0.2, Y_AMORT, Y_AMORT - 0.2, Y_AMORT - 0.2],
        )

        xr = X_REPOUSO + ref * e
        self.ref.set_data([xr, xr], [-0.1, 1.5])
        self.txt_ref.set_x(xr)

        self.seta.set_positions((X_REPOUSO, -0.3), (xm, -0.3))
        self.txt_x.set_text(f"x = {x:+.4f} m")
        self.txt_t.set_text(f"t = {t:6.2f} s")
