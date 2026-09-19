"""
Componente Visual Interativo: Arrastar para Enviar / Exportar Modpack (ZIP).
Permite ao usuário segurar e arrastar o pacote diretamente para o Windows Explorer,
Desktop ou Discord, ou clicar para copiar para a Área de Transferência.
"""

import os
import subprocess
import threading
import customtkinter as ctk
from typing import Optional

from src.core.models import ModpackInfo
from src.services.pack_export_service import PackExportService


class DragExportCard(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            corner_radius=10,
            fg_color="#161b22",
            border_width=1,
            border_color="#30363d",
            **kwargs
        )

        self.current_pack: Optional[ModpackInfo] = None
        self.zip_path: Optional[str] = None
        self.is_packing: bool = False
        self._drag_started: bool = False
        self._press_x = 0
        self._press_y = 0

        self._create_widgets()
        self._bind_events()

    def _create_widgets(self):
        self.grid_columnconfigure(1, weight=1)

        # Ícone de exportação
        self.lbl_icon = ctk.CTkLabel(
            self,
            text="📦",
            font=ctk.CTkFont(size=26)
        )
        self.lbl_icon.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=10)

        # Título principal
        self.lbl_title = ctk.CTkLabel(
            self,
            text="Arrastar para Enviar / Compartilhar Modpack (ZIP)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#e6edf3",
            anchor="w"
        )
        self.lbl_title.grid(row=0, column=1, padx=4, pady=(8, 0), sticky="w")

        # Subtítulo descritivo / Status
        self.lbl_desc = ctk.CTkLabel(
            self,
            text="Segure e arraste este card para fora (Discord, pasta) ou clique em Copiar.",
            font=ctk.CTkFont(size=12),
            text_color="#8b949e",
            anchor="w"
        )
        self.lbl_desc.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="w")

        # Painel de botões de ação à direita
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.grid(row=0, column=2, rowspan=2, padx=14, pady=8, sticky="e")

        # Badge com tamanho do arquivo
        self.lbl_badge = ctk.CTkLabel(
            self.actions_frame,
            text="Carregando...",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#58a6ff",
            fg_color="#0d1117",
            corner_radius=6,
            padx=8,
            pady=3
        )
        self.lbl_badge.pack(side="left", padx=6)

        # Botão Copiar para Clipboard
        self.btn_copy = ctk.CTkButton(
            self.actions_frame,
            text="📋 Copiar ZIP (Ctrl+V)",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=140,
            height=30,
            command=self._on_copy_clicked,
            fg_color="#238636",
            hover_color="#2ea043"
        )
        self.btn_copy.pack(side="left", padx=4)

        # Botão Abrir Pasta
        self.btn_open = ctk.CTkButton(
            self.actions_frame,
            text="📂 Abrir Local",
            font=ctk.CTkFont(size=12),
            width=90,
            height=30,
            command=self._on_open_clicked,
            fg_color="#21262d",
            hover_color="#30363d"
        )
        self.btn_open.pack(side="left", padx=4)

    def _bind_events(self):
        widgets_to_bind = [self, self.lbl_icon, self.lbl_title, self.lbl_desc]
        for w in widgets_to_bind:
            w.bind("<Button-1>", self._on_mouse_down)
            w.bind("<B1-Motion>", self._on_mouse_drag)
            w.bind("<ButtonRelease-1>", self._on_mouse_up)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _get_pack_dir(self) -> Optional[str]:
        if not self.current_pack or not self.current_pack.json_path:
            return None
        return os.path.dirname(self.current_pack.json_path)

    def set_modpack(self, modpack: Optional[ModpackInfo]):
        self.current_pack = modpack
        if not modpack:
            self.lbl_badge.configure(text="Nenhum modpack selecionado")
            self.btn_copy.configure(state="disabled")
            self.btn_open.configure(state="disabled")
            return

        self.btn_copy.configure(state="normal")
        self.btn_open.configure(state="normal")
        self.lbl_badge.configure(text="⚡ Preparando ZIP...")

        pack_dir = self._get_pack_dir()
        if pack_dir and os.path.exists(pack_dir):
            # Gera o ZIP em thread rápida de segundo plano para deixar pré-carregado
            threading.Thread(target=self._prebuild_zip, args=(pack_dir,), daemon=True).start()

    def _prebuild_zip(self, pack_dir: str):
        if self.is_packing:
            return
        self.is_packing = True
        try:
            zip_p, files, size_kb, elapsed = PackExportService.build_sync_zip(pack_dir)
            self.zip_path = zip_p

            def update_ui():
                try:
                    if not self.winfo_exists():
                        return
                    size_str = f"{size_kb / 1024:.1f} MB" if size_kb >= 1024 else f"{size_kb:.0f} KB"
                    self.lbl_badge.configure(text=f"📦 {size_str} ({files} arqs)")
                    self.lbl_desc.configure(
                        text=f"Pronto para envio! Arraste ou clique em Copiar ZIP ({files} arqs de config, json e opções)."
                    )
                except Exception:
                    pass

            try:
                if self.winfo_exists():
                    self.after(0, update_ui)
            except Exception:
                pass
        except Exception as e:
            def update_err():
                try:
                    if not self.winfo_exists():
                        return
                    self.lbl_badge.configure(text="Erro ao gerar ZIP")
                except Exception:
                    pass

            try:
                if self.winfo_exists():
                    self.after(0, update_err)
            except Exception:
                pass
        finally:
            self.is_packing = False

    def _on_enter(self, event=None):
        self.configure(border_color="#58a6ff")

    def _on_leave(self, event=None):
        if not self._drag_started:
            self.configure(border_color="#30363d")

    def _on_mouse_down(self, event):
        self._press_x = event.x_root
        self._press_y = event.y_root
        self._drag_started = False
        self.configure(border_color="#2ea043", fg_color="#1b222d")

        # Garante que o ZIP existe e coloca na área de transferência imediatamente
        pack_dir = self._get_pack_dir()
        if pack_dir and os.path.exists(pack_dir):
            if not self.zip_path or not os.path.exists(self.zip_path):
                self.zip_path, _, _, _ = PackExportService.build_sync_zip(pack_dir)
            if self.zip_path:
                PackExportService.copy_file_to_clipboard(self.zip_path)

    def _on_mouse_drag(self, event):
        dx = abs(event.x_root - self._press_x)
        dy = abs(event.y_root - self._press_y)
        if (dx > 8 or dy > 8) and not self._drag_started:
            self._drag_started = True
            self.lbl_desc.configure(
                text="🚀 Arrastando modpack... Solte em qualquer pasta, Área de Trabalho ou Discord!",
                text_color="#3fb950"
            )
            # Inicia Drag-and-Drop nativo do Windows em thread para não travar a GUI
            if self.zip_path and os.path.exists(self.zip_path):
                threading.Thread(target=self._run_native_drag, args=(self.zip_path,), daemon=True).start()

    def _run_native_drag(self, zip_path: str):
        PackExportService.start_native_drag(zip_path)
        def reset():
            try:
                if not self.winfo_exists():
                    return
                self._drag_started = False
                self.configure(border_color="#30363d", fg_color="#161b22")
                self.lbl_desc.configure(
                    text="Segure e arraste este card para fora (Discord, pasta) ou clique em Copiar.",
                    text_color="#8b949e"
                )
            except Exception:
                pass

        try:
            if self.winfo_exists():
                self.after(500, reset)
        except Exception:
            pass

    def _on_mouse_up(self, event):
        self.configure(border_color="#30363d", fg_color="#161b22")
        if not self._drag_started and self.zip_path:
            self._on_copy_clicked()

    def _on_copy_clicked(self):
        pack_dir = self._get_pack_dir()
        if not pack_dir:
            return

        if not self.zip_path or not os.path.exists(self.zip_path):
            self.zip_path, _, _, _ = PackExportService.build_sync_zip(pack_dir)

        if self.zip_path and PackExportService.copy_file_to_clipboard(self.zip_path):
            original_text = self.btn_copy.cget("text")
            self.btn_copy.configure(text="✅ Copiado! (Ctrl+V)", fg_color="#1f6feb")
            self.lbl_desc.configure(
                text="✅ Arquivo .zip copiado para a Área de Transferência! Dê Ctrl+V no Discord ou pasta.",
                text_color="#58a6ff"
            )

            def restore():
                try:
                    if not self.winfo_exists():
                        return
                    self.btn_copy.configure(text=original_text, fg_color="#238636")
                    self.lbl_desc.configure(
                        text="Segure e arraste este card para fora (Discord, pasta) ou clique em Copiar.",
                        text_color="#8b949e"
                    )
                except Exception:
                    pass

            try:
                if self.winfo_exists():
                    self.after(3000, restore)
            except Exception:
                pass

    def _on_open_clicked(self):
        pack_dir = self._get_pack_dir()
        if not pack_dir:
            return

        if not self.zip_path or not os.path.exists(self.zip_path):
            self.zip_path, _, _, _ = PackExportService.build_sync_zip(pack_dir)

        if self.zip_path and os.path.exists(self.zip_path):
            try:
                subprocess.Popen(f'explorer /select,"{os.path.abspath(self.zip_path)}"')
            except Exception:
                os.startfile(os.path.dirname(self.zip_path))
