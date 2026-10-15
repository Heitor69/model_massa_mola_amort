"""Modelo matematico do sistema massa-mola-amortecedor com PID.

Planta:      M x'' + C x' + K x = u          ->  G(s) = 1 / (M s^2 + C s + K)
Controlador: u = Kp e + Ki int(e) + Kd de/dt  ->  Gc(s) = (Kd s^2 + Kp s + Ki) / s
Malha fechada (r -> x):
    T(s) = (Kd s^2 + Kp s + Ki) / (M s^3 + (C + Kd) s^2 + (K + Kp) s + Ki)
"""

import numpy as np
from scipy import signal


def _limpar(num):
    """Remove zeros a esquerda do numerador (evita avisos do scipy)."""
    num = np.trim_zeros(np.asarray(num, dtype=float), "f")
    return num if num.size else np.array([0.0])


def funcao_planta(M, C, K):
    """Numerador e denominador de G(s) = X(s)/F(s)."""
    return np.array([1.0]), np.array([M, C, K], dtype=float)


def funcao_malha_fechada(M, C, K, Kp, Ki, Kd):
    """Numerador e denominador de T(s) = X(s)/R(s)."""
    if Ki == 0:
        # Sem integrador o polo/zero em s=0 se cancelam: reduz a ordem.
        num = [Kd, Kp]
        den = [M, C + Kd, K + Kp]
    else:
        num = [Kd, Kp, Ki]
        den = [M, C + Kd, K + Kp, Ki]
    return _limpar(num), np.array(den, dtype=float)


def polos(den):
    return np.roots(den)


def estavel(den, tol=1e-9):
    p = polos(den)
    return bool(np.all(p.real < -tol))


def zeros(num):
    return np.roots(num) if len(num) > 1 else np.array([])


def resposta_degrau(num, den, t, amplitude):
    """Resposta x(t) a um degrau de referencia com a amplitude dada."""
    if not np.any(num) or amplitude == 0:
        return np.zeros_like(t)
    _, y = signal.step((num, den), T=t)
    return y * amplitude


def _resposta_livre(A, t, x0, v0):
    """Resposta livre (entrada nula) de x' = A x, saida = 1o estado."""
    if x0 == 0 and v0 == 0:
        return np.zeros_like(t)
    n = A.shape[0]
    X0 = np.zeros(n)
    X0[:2] = [x0, v0]
    Cs = np.zeros((1, n))
    Cs[0, 0] = 1
    _, y, _ = signal.lsim((A, np.zeros((n, 1)), Cs, [[0]]), U=np.zeros_like(t), T=t, X0=X0)
    return y


def resposta_livre_malha_fechada(M, C, K, Kp, Ki, Kd, t, x0, v0):
    """x(t) com r = 0 partindo de x(0)=x0, x'(0)=v0.

    Estados [x, v, z] com z = int(x):  M v' = -(K+Kp) x - (C+Kd) v - Ki z
    """
    A = np.array([
        [0, 1, 0],
        [-(K + Kp) / M, -(C + Kd) / M, -Ki / M],
        [1, 0, 0],
    ])
    return _resposta_livre(A, t, x0, v0)


def resposta_livre_planta(M, C, K, t, x0, v0):
    """x(t) sem controle (u = 0) partindo de x0, v0."""
    A = np.array([[0, 1], [-K / M, -C / M]])
    return _resposta_livre(A, t, x0, v0)


def resposta_degrau_planta(M, C, K, t, ref):
    """Sem controle: forca constante F = K*r, que levaria a massa a r no regime."""
    if K == 0:
        return None
    return resposta_degrau(np.array([K]), np.array([M, C, K]), t, ref)


def resposta_frequencia(num, den, w):
    """Modulo (dB) e fase (graus) de H(jw)."""
    _, H = signal.freqs(num, den, worN=w)
    mag = 20 * np.log10(np.maximum(np.abs(H), 1e-12))
    fase = np.degrees(np.unwrap(np.angle(H)))
    return mag, fase


def faixa_frequencia(*dens, n=800):
    """Faixa de w (rad/s) que cobre os polos dos sistemas com folga de 2 decadas."""
    mods = np.concatenate([np.abs(polos(d)) for d in dens])
    mods = mods[mods > 1e-6]
    if mods.size == 0:
        mods = np.array([1.0])
    wmin = mods.min() / 100
    wmax = mods.max() * 100
    return np.logspace(np.log10(wmin), np.log10(wmax), n)


def metricas(t, y, num, den, amplitude):
    """Metricas classicas da resposta ao degrau."""
    m = {
        "estavel": estavel(den),
        "polos": polos(den),
        "valor_final": np.nan,
        "erro_rp": np.nan,
        "sobressinal": np.nan,
        "t_subida": np.nan,
        "t_acomodacao": np.nan,
    }
    if not m["estavel"]:
        return m

    ganho_dc = num[-1] / den[-1] if den[-1] != 0 else np.nan
    yf = ganho_dc * amplitude
    m["valor_final"] = yf
    m["erro_rp"] = amplitude - yf
    if abs(yf) < 1e-12:
        return m

    yn = y / yf  # resposta normalizada (vai para 1)
    m["sobressinal"] = max(0.0, (yn.max() - 1) * 100)

    i10 = np.argmax(yn >= 0.1)
    i90 = np.argmax(yn >= 0.9)
    if yn[i90] >= 0.9 and yn[i10] >= 0.1:
        m["t_subida"] = t[i90] - t[i10]

    m["t_acomodacao"] = _tempo_acomodacao(t, np.abs(yn - 1), 0.02)
    return m


def metricas_condicao_inicial(t, y, den):
    """Metricas da resposta livre (r = 0): pico e acomodacao em 2% do pico."""
    m = {
        "estavel": estavel(den),
        "polos": polos(den),
        "pico": np.abs(y).max(),
        "t_acomodacao": np.nan,
    }
    if m["estavel"] and m["pico"] > 0:
        m["t_acomodacao"] = _tempo_acomodacao(t, np.abs(y), 0.02 * m["pico"])
    return m


def _tempo_acomodacao(t, desvio, banda):
    """Instante a partir do qual o desvio fica dentro da banda (nan se nunca)."""
    fora = np.where(desvio > banda)[0]
    if fora.size == 0:
        return 0.0
    if fora[-1] < len(t) - 1:
        return t[fora[-1] + 1]
    return np.nan
