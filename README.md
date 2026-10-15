# Massa-mola-amortecedor com controle PID

Simulador interativo para estudar controle PID num sistema de segunda ordem. Você mexe nos parâmetros da planta (M, K, C) e nos ganhos do controlador (Kp, Ki, Kd) e vê na hora a resposta no tempo, a resposta em frequência e os polos do sistema. Uma animação mostra a massa se movendo.

## Como rodar

Requer Python 3.10+ com:

```
pip install numpy scipy matplotlib
```

Tkinter já vem com o Python no Windows. Depois:

```
python main.py
```

## A janela

**Lado esquerdo**
- Desenho do modelo físico: parede, mola K, amortecedor C e massa M. A linha laranja tracejada marca a referência; a seta embaixo mostra o deslocamento x.
- Botões **Animar / Pausar**, **Reiniciar animação** e **Valores padrão**.
- Controles (slider + caixa de texto; a caixa aceita valores fora da faixa do slider):

| Grupo | Parâmetro | Faixa do slider | Padrão |
|---|---|---|---|
| Planta | Massa M [kg] | 0.1 a 20 | 1 |
| | Rigidez K [N/m] | 0 a 200 | 20 |
| | Amortecimento C [N·s/m] | 0 a 50 | 2 |
| Controlador PID | Kp | 0 a 500 | 50 |
| | Ki | 0 a 500 | 20 |
| | Kd | 0 a 100 | 5 |
| Entrada | Referência r [m] (modo degrau) | −2 a 2 | 1 |
| | Posição inicial x0 [m] (modo condição inicial) | −2 a 2 | 0.5 |
| | Velocidade inicial v0 [m/s] (modo condição inicial) | −10 a 10 | 0 |
| Simulação | Tempo final [s] | 1 a 60 | 10 |
| | Velocidade da animação [x] | 0.1 a 4 | 1 |

- **Resultados:** ωn e ζ da planta, estabilidade com PID, valor final, erro em regime permanente, sobressinal, tempo de subida (10–90%), tempo de acomodação (±2%) e polos de malha fechada.

**Lado direito**
- **Deslocamento no tempo:** resposta com PID (azul) e sem controle (laranja), referência e faixa de ±2%. Um cursor vertical acompanha a animação.
- **Amplitude e fase por frequência:** malha fechada X/R e planta sozinha X/F. A caixa **Frequência em Hz** na barra de ferramentas alterna entre rad/s e Hz.
- **Mapa de polos e zeros:** polos da planta, polos e zeros com PID. A região instável (Re > 0) aparece sombreada.

A barra de ferramentas do matplotlib permite dar zoom e salvar os gráficos.

## Modos de entrada

- **Degrau na referência:** r vai de 0 ao valor escolhido em t = 0, com a massa parada em x = 0. A curva "sem controle" aplica uma força constante F = K·r, que levaria a massa até r no regime (não aparece se K = 0).
- **Condição inicial (r = 0):** a massa parte de x0 com velocidade v0 e o controlador tenta trazê-la para zero. A curva "sem controle" é a oscilação livre da planta.

## Modelo

Planta:

$$M\ddot{x} + C\dot{x} + Kx = u \quad\Rightarrow\quad G(s) = \frac{1}{Ms^2 + Cs + K}$$

Controlador (derivativo ideal sobre o erro e = r − x):

$$u = K_p e + K_i \int e\,dt + K_d \dot{e} \quad\Rightarrow\quad G_c(s) = \frac{K_d s^2 + K_p s + K_i}{s}$$

Malha fechada:

$$T(s) = \frac{X(s)}{R(s)} = \frac{K_d s^2 + K_p s + K_i}{M s^3 + (C + K_d)s^2 + (K + K_p)s + K_i}$$

Com Ki = 0 o polo e o zero em s = 0 se cancelam, e o sistema vira de segunda ordem.

## Estrutura

```
Model_massa_mola/
├── main.py              # abre a janela
├── .gitignore
└── funcoes/
    ├── modelo.py        # funções de transferência, simulação, polos, métricas
    ├── desenho.py       # desenho animado do modelo físico
    ├── graficos.py      # gráficos do lado direito
    └── interface.py     # janela Tkinter, controles e animação
```

## Sugestões para estudar

- Zere Ki e Kd e aumente Kp: o erro em regime cai mas não zera, e o sobressinal cresce.
- Ligue Ki: o erro em regime vai a zero, mas aparece um polo lento perto da origem.
- Aumente Kd: os polos complexos se afastam do eixo imaginário (mais amortecimento).
- Zere C e use só Ki: o sistema fica instável. Veja os polos cruzarem para o lado direito.
- No modo condição inicial, compare a oscilação livre da planta com a resposta controlada.
