"""Simulador interativo: massa-mola-amortecedor com controlador PID.

Execute:  python main.py
"""

from funcoes.interface import App


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
