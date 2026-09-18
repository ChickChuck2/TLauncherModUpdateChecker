"""
Painel de Progresso com status em tempo real de cada mod verificado.
"""

import customtkinter as ctk
from src.core.models import UpdateStatus


class ProgressPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)
        self._pulse_job = None
        self._pulse_step = 0
        self._create_widgets()

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)

        # Barra de progresso
        self.progress_bar = ctk.CTkProgressBar(self, height=10, corner_radius=5)
        self.progress_bar.grid(row=0, column=0, padx=16, pady=(10, 4), sticky="ew")
        self.progress_bar.set(0)

        # Linha de status
        sf = ctk.CTkFrame(self, fg_color="transparent")
        sf.grid(row=1, column=0, padx=16, pady=(0, 4), sticky="ew")
        sf.grid_columnconfigure(0, weight=1)

        # Indicador "Verificando: <nome do mod>" — fica à esquerda
        self.lbl_current = ctk.CTkLabel(
            sf, text="", font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#58a6ff", anchor="w"
        )
        self.lbl_current.grid(row=0, column=0, sticky="w")

        # Contador à direita
        self.lbl_counter = ctk.CTkLabel(
            sf, text="", font=ctk.CTkFont(size=11),
            text_color="#6e7681", anchor="e"
        )
        self.lbl_counter.grid(row=0, column=1, sticky="e")

        # Linha de status geral
        self.lbl_status = ctk.CTkLabel(
            self, text="Pronto para verificar.",
            font=ctk.CTkFont(size=11), text_color="#cccccc", anchor="w"
        )
        self.lbl_status.grid(row=2, column=0, padx=16, pady=(0, 4), sticky="w")

        # Badges de estatísticas
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")

        self.badge_total      = self._badge(bf, "Total: 0",         "#34495e")
        self.badge_up_to_date = self._badge(bf, "Em dia: 0",        "#1e8449")
        self.badge_updates    = self._badge(bf, "Updates: 0",       "#d35400")
        self.badge_tlauncher  = self._badge(bf, "No TLauncher: 0",  "#1f618d")

    def _badge(self, parent, text: str, color: str) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(
            parent, text=text, fg_color=color,
            corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ffffff"
        )
        lbl.pack(side="left", padx=(0, 6), pady=2)
        return lbl

    # ------------------------------------------------------------------ #
    #  API pública                                                         #
    # ------------------------------------------------------------------ #

    def start_checking(self, total: int):
        """Chamado antes de iniciar a verificação em lote."""
        self.progress_bar.set(0)
        self.lbl_counter.configure(text=f"0 / {total}")
        self.lbl_status.configure(text="🔍 Iniciando verificação...")
        self.lbl_current.configure(text="")

    def tick(self, current: int, total: int, mod_name: str, status_label: str, status_color: str):
        """
        Chamado a cada mod concluído.
        Atualiza barra, nome do mod e resultado individual.
        """
        ratio = current / total if total > 0 else 0
        self.progress_bar.set(ratio)
        pct = int(ratio * 100)
        self.lbl_counter.configure(text=f"{current} / {total}  ({pct}%)")

        # Ícone por resultado
        icon_map = {
            "#1e8449": "✅",   # up to date
            "#d68910": "⚠️",  # update available
            "#117a65": "✅",   # tlauncher confirmed
            "#2980b9": "🔍",  # checking
            "#566573": "❓",  # not found
            "#922b21": "❌",  # error
        }
        icon = icon_map.get(status_color, "•")
        self.lbl_current.configure(
            text=f"{icon}  {mod_name}  ·  {status_label}",
            text_color=status_color
        )

    def done(self, message: str):
        """Chamado ao concluir toda a verificação."""
        self.progress_bar.set(1.0)
        self.lbl_current.configure(text="", text_color="#58a6ff")
        self.lbl_status.configure(text=message)
        self.lbl_counter.configure(text="")

    def set_progress(self, current: int, total: int, status_text: str = ""):
        """Compatibilidade com código legado."""
        ratio = (current / total) if total > 0 else 0
        self.progress_bar.set(ratio)
        pct = int(ratio * 100)
        self.lbl_status.configure(text=f"{status_text} ({current}/{total} - {pct}%)")

    def update_stats(self, total: int, up_to_date: int, updates: int, tlauncher_avail: int):
        self.badge_total.configure(text=f"Total: {total}")
        self.badge_up_to_date.configure(text=f"Em dia: {up_to_date}")
        self.badge_updates.configure(text=f"Updates: {updates}")
        self.badge_tlauncher.configure(text=f"TLauncher: {tlauncher_avail}")

    def reset(self):
        self.progress_bar.set(0)
        self.lbl_status.configure(text="Pronto para verificar.")
        self.lbl_current.configure(text="", text_color="#58a6ff")
        self.lbl_counter.configure(text="")
