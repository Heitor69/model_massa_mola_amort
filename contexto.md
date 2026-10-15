# Contexto do projeto (para colar no Claude online)

**Última atualização:** 14/10/2026
**Projeto:** simulador interativo de um sistema massa-mola-amortecedor com controlador PID, em Python, para estudar controle.
**Uso:** `python main.py` abre uma janela Tkinter. Dependências: numpy, scipy, matplotlib.

## Objetivo

Ferramenta didática: o usuário ajusta M, K, C, Kp, Ki e Kd e vê em tempo real a resposta no tempo, a resposta em frequência, o mapa de polos e uma animação do modelo físico. Modelo linear, sem saturação (decisão do usuário).

## Estado atual

Tudo funcionando e testado à mão (os dois modos de entrada, alternância rad/s↔Hz e casos-limite: ganhos zerados, K = C = 0, só Ki alto). Não há testes automatizados.

Layout da janela:
- **Esquerda (fixo no topo):** desenho animado (parede, mola, amortecedor, massa, linha de referência, seta de x) e botões Animar/Pausar, Reiniciar animação, Valores padrão.
- **Esquerda (rolável):** controles de Planta, Controlador PID, Entrada (seletor de modo + r, x0, v0), Simulação (tempo final, velocidade da animação) e caixa de Resultados. Ficou rolável porque a tela do usuário é 1366×768.
- **Direita:** x(t) no topo (largura toda); amplitude e fase por frequência à esquerda embaixo; mapa de polos e zeros à direita embaixo. Caixa "Frequência em Hz" na barra de ferramentas do matplotlib.

## Modelo

- Planta: `M x'' + C x' + K x = u`, `G(s) = 1/(M s² + C s + K)`.
- PID com derivativo **ideal sobre o erro** (sem filtro): `Gc(s) = (Kd s² + Kp s + Ki)/s`.
- Malha fechada: `T(s) = (Kd s² + Kp s + Ki) / (M s³ + (C+Kd) s² + (K+Kp) s + Ki)`.
- Se Ki = 0, reduz a ordem (`num = [Kd, Kp]`, `den = [M, C+Kd, K+Kp]`) para não deixar um polo em s = 0 que seria marcado como instável.
- Modo condição inicial: espaço de estados `[x, v, z]` com `z = ∫x`, `M v' = -(K+Kp) x - (C+Kd) v - Ki z`, simulado com `scipy.signal.lsim` com entrada nula.

## O que cada módulo faz

### `main.py`
Só cria `App` e chama `mainloop()`.

### `funcoes/modelo.py`
- `funcao_planta`, `funcao_malha_fechada`: numerador e denominador.
- `polos`, `zeros`, `estavel` (todos os polos com Re < 0).
- `resposta_degrau(num, den, t, amplitude)`: via `signal.step`.
- `resposta_livre_malha_fechada`, `resposta_livre_planta`: condição inicial.
- `resposta_degrau_planta`: curva "sem controle" no modo degrau, força constante F = K·r (retorna `None` se K = 0).
- `resposta_frequencia`: módulo em dB e fase em graus (com unwrap) via `signal.freqs`.
- `faixa_frequencia`: ω de (menor |polo|)/100 a (maior |polo|)·100, 800 pontos log.
- `metricas` (degrau): valor final pelo ganho DC, erro em regime, sobressinal, subida 10–90%, acomodação ±2%. Só calcula se estável.
- `metricas_condicao_inicial`: pico de |x| e acomodação em 2% do pico.

### `funcoes/desenho.py`
Classe `DesenhoModelo` sobre um eixo matplotlib. Cria os artistas uma vez e `atualizar(x, t, ref)` só move. A escala do desenho é ajustada por `definir_escala(x_max)` para o maior deslocamento caber em 1.6 unidades. O amortecedor tem a haste presa à parede e o cilindro preso à massa.

### `funcoes/graficos.py`
Classe `Graficos` com 4 eixos (gridspec 3×2). `atualizar(d)` recebe um dicionário com t, x, x_ma, ref, modo, w, mag/fase da planta e da malha fechada, wn, hz, polos e zeros. `mover_cursor(t)` move a linha vertical da animação. Cores: azul `#2a78d6` = com PID, laranja `#eb6834` = planta/sem controle, cinza = referência.

### `funcoes/interface.py`
- Constantes `PARAMETROS_PLANTA`, `PARAMETROS_PID`, `PARAMETROS_ENTRADA`, `PARAMETROS_SIM`: `nome: (rótulo, mín, máx, passo, padrão)`. Para adicionar um controle, basta incluir uma linha.
- `CONTROLES_DO_MODO`: quais controles ficam ativos em cada modo (`degrau` → r; `ci` → x0, v0).
- Classe `Controle`: slider `tk.Scale` + `ttk.Entry` sincronizados; a caixa aceita valores fora da faixa e vírgula decimal.
- Classe `App(tk.Tk)`: monta o layout, recalcula com debounce de 60 ms ao mexer num slider (`agendar_recalculo`), anima a 30 fps usando o tempo real × velocidade.
- `N_PONTOS = 2000` pontos de simulação. Valores nan/inf (sistema instável) viram 0 ou ±1e6.

## Decisões tomadas com o usuário

- Entradas: degrau na referência e condição inicial. **Não** quis senoide nem perturbação de força.
- Gráficos extras: comparação sem controle e mapa de polos. **Não** quis u(t) nem Bode de malha aberta com margens.
- Frequência: alternável entre rad/s e Hz.
- Sem saturação nem anti-windup (modelo linear).
- Organização pedida: `main.py`, `.gitignore`, pasta `funcoes/`.

## Decisões tomadas sem confirmação

- Curva "sem controle" no modo degrau = força constante F = K·r.
- Derivativo ideal sobre o erro (no degrau, isso dá um "tranco" de velocidade em t = 0).

## Perguntas em aberto para o usuário

1. Massa "fantasma" semitransparente na animação mostrando o movimento sem controle?
2. Derivativo sobre a medida (−Kd·v) em vez de sobre o erro?
3. Salvar/carregar parâmetros ou exportar CSV/PNG por botão?
4. Sintonia automática (Ziegler–Nichols, ou alocação de polos a partir de ζ e ωn desejados)?
