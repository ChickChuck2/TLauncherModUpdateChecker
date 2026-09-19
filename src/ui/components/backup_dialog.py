"""
Modal para Gerenciamento, Criação, Exportação e Restauração de Backups do Modpack.
"""

import os
import tkinter.messagebox as messagebox
from tkinter import filedialog
import customtkinter as ctk
from typing import Optional, Callable

from src.core.models import ModpackInfo
from src.services.backup_service import BackupService


class BackupManagerDialog(ctk.CTkToplevel):

    def __init__(
        self,
        master,
        modpack: ModpackInfo,
        on_restored: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self.modpack = modpack
        self.on_restored = on_restored

        self.title(f"🛡️ Gerenciador de Backups — {modpack.name}")
        self.geometry("680x540")
        self.minsize(580, 420)

        # Configura como janela modal
        self.transient(master)
        self.after(10, self.grab_set)

        self._create_widgets()
        self._load_backup_list()

    def _create_widgets(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ---- Topo: Informações do Diretório de Backups ----
        top_frame = ctk.CTkFrame(self, corner_radius=8, fg_color="#161b22")
        top_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        top_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_frame,
            text=f"📁 Pasta de Backups de: {self.modpack.name}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#58a6ff",
            anchor="w"
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 2), sticky="w")

        backup_dir = str(BackupService.get_backup_dir(self.modpack.json_path))
        self.lbl_path = ctk.CTkLabel(
            top_frame,
            text=backup_dir,
            font=ctk.CTkFont(size=11),
            text_color="#8b949e",
            anchor="w"
        )
        self.lbl_path.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="ew")

        ctk.CTkButton(
            top_frame,
            text="📂 Abrir no Explorer",
            width=140,
            height=28,
            fg_color="#21262d",
            hover_color="#30363d",
            command=self._on_open_folder
        ).grid(row=1, column=1, padx=(0, 12), pady=(0, 10), sticky="e")

        # ---- Barra de Ações Rápidas ----
        actions_bar = ctk.CTkFrame(self, fg_color="transparent")
        actions_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        actions_bar.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            actions_bar,
            text="➕ Criar Backup Agora",
            width=160,
            height=32,
            fg_color="#1f618d",
            hover_color="#154360",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_create_backup
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")

        ctk.CTkButton(
            actions_bar,
            text="📤 Exportar Cópias para Pasta...",
            width=210,
            height=32,
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_export_backups
        ).grid(row=0, column=1, padx=(0, 8), sticky="w")

        self.lbl_status = ctk.CTkLabel(
            actions_bar,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#3fb950",
            anchor="e"
        )
        self.lbl_status.grid(row=0, column=2, sticky="e")

        # ---- Lista de Backups Salvos ----
        self.scroll = ctk.CTkScrollableFrame(self, corner_radius=8, fg_color="#0d1117")
        self.scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.scroll.grid_columnconfigure(0, weight=1)

    def _load_backup_list(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        backups = BackupService.list_backups(self.modpack.json_path)
        if not backups:
            ctk.CTkLabel(
                self.scroll,
                text="Nenhum backup encontrado ainda para este modpack.\nClique em 'Criar Backup Agora' acima para criar o primeiro!",
                text_color="#8b949e",
                font=ctk.CTkFont(size=12)
            ).pack(pady=40)
            return

        for b in backups:
            card = ctk.CTkFrame(self.scroll, corner_radius=6, fg_color="#161b22", height=44)
            card.pack(fill="x", padx=4, pady=3)
            card.grid_columnconfigure(1, weight=1)

            # Ícone
            icon_text = "⚡" if b["is_quick_bak"] else "📄"
            ctk.CTkLabel(card, text=icon_text, font=ctk.CTkFont(size=16), width=30).grid(
                row=0, column=0, rowspan=2, padx=(8, 4), pady=4
            )

            # Nome e Data
            lbl_name = ctk.CTkLabel(
                card,
                text=b["name"],
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
                text_color="#e6edf3"
            )
            lbl_name.grid(row=0, column=1, padx=4, pady=(4, 0), sticky="w")

            info_text = f"🕒 {b['date_str']}  •  Tamanho: {b['size_kb']} KB"
            lbl_info = ctk.CTkLabel(
                card,
                text=info_text,
                font=ctk.CTkFont(size=10),
                text_color="#8b949e",
                anchor="w"
            )
            lbl_info.grid(row=1, column=1, padx=4, pady=(0, 4), sticky="w")

            # Botão Restaurar
            btn_restore = ctk.CTkButton(
                card,
                text="Restaurar",
                width=80,
                height=26,
                fg_color="#b9770e",
                hover_color="#935116",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda path=b["path"], name=b["name"]: self._on_restore(path, name)
            )
            btn_restore.grid(row=0, column=2, rowspan=2, padx=8, pady=4, sticky="e")

    def _on_open_folder(self):
        opened = BackupService.open_backup_folder(self.modpack.json_path)
        if not opened:
            messagebox.showerror("Erro", "Não foi possível abrir o diretório no Explorer.", parent=self)

    def _on_create_backup(self):
        try:
            created_path = BackupService.create_manual_backup(self.modpack.json_path)
            fname = os.path.basename(created_path)
            self.lbl_status.configure(text=f"✓ Backup criado: {fname}", text_color="#3fb950")
            self._load_backup_list()
        except Exception as e:
            messagebox.showerror("Erro ao Criar Backup", str(e), parent=self)

    def _on_export_backups(self):
        target_dir = filedialog.askdirectory(
            parent=self,
            title="Selecione a pasta para onde deseja exportar as cópias de backup"
        )
        if not target_dir:
            return

        try:
            count, export_path = BackupService.export_backups(
                self.modpack.json_path,
                target_dir,
                pack_name=self.modpack.name
            )
            self.lbl_status.configure(text=f"✓ {count} cópias exportadas com sucesso!", text_color="#3fb950")
            messagebox.showinfo(
                "Exportação Concluída",
                f"Foram exportadas {count} cópias de segurança com sucesso para:\n\n{export_path}",
                parent=self
            )
        except Exception as e:
            messagebox.showerror("Erro ao Exportar", str(e), parent=self)

    def _on_restore(self, backup_path: str, backup_name: str):
        confirm = messagebox.askyesno(
            "Confirmar Restauração",
            f"Deseja restaurar as configurações do modpack a partir de:\n\n{backup_name}?\n\n"
            "Um backup do estado atual será criado automaticamente antes de restaurar.",
            parent=self
        )
        if not confirm:
            return

        try:
            BackupService.restore_backup(self.modpack.json_path, backup_path)
            messagebox.showinfo("Sucesso", f"Backup restaurado com sucesso:\n{backup_name}", parent=self)
            self.lbl_status.configure(text=f"✓ Restaurado: {backup_name}", text_color="#3fb950")
            self._load_backup_list()
            if self.on_restored:
                self.on_restored()
        except Exception as e:
            messagebox.showerror("Erro na Restauração", f"Falha ao restaurar backup:\n{e}", parent=self)
