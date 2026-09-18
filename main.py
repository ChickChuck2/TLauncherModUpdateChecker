"""
Ponto de Entrada Principal da Aplicação TLauncher Mod Update Checker.
"""

import sys
import os

# Garante que o diretório raiz esteja no sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.app import run_app

if __name__ == "__main__":
    run_app()
