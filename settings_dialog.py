import tkinter as tk
from tkinter import colorchooser
from tkinter import ttk
import sound
import pygame
import tien_len_full as rules

class SettingsDialog(tk.Toplevel):
    """Modal dialog for adjusting game options."""

    def __init__(self, master: tk.Tk, gui) -> None:
        super().__init__(master)
        self.gui = gui
        self.title("Settings")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)

        # Sound and music toggles
        self.sound_var = tk.BooleanVar(value=sound._ENABLED)
        tk.Checkbutton(frame, text="Enable sound effects", variable=self.sound_var).pack(anchor="w")
        self.music_var = tk.BooleanVar(value=pygame.mixer.music.get_busy() if pygame else False)
        tk.Checkbutton(frame, text="Enable music", variable=self.music_var).pack(anchor="w")

        tk.Label(frame, text="Volume").pack(anchor="w")
        self.vol_var = tk.DoubleVar(value=self.gui.sfx_volume.get())
        tk.Scale(frame, from_=0, to=1, orient=tk.HORIZONTAL, resolution=0.1, variable=self.vol_var).pack(anchor="w")

        # Card back selector (placeholder options)
        backs = [k for k in self.gui.card_images if k.startswith("card_back")]
        if not backs:
            backs = ["card_back"]
        self.back_var = tk.StringVar(value=backs[0])
        tk.Label(frame, text="Card back").pack(anchor="w")
        ttk.OptionMenu(frame, self.back_var, backs[0], *backs).pack(anchor="w")

        # Table cloth colour
        tk.Label(frame, text="Table colour").pack(anchor="w")
        self.colour = self.gui.table_cloth_color
        self.colour_lbl = tk.Label(frame, width=10, bg=self.colour)
        self.colour_lbl.pack(anchor="w")
        tk.Button(frame, text="Choose...", command=self.choose_colour).pack(anchor="w")

        # Rule variant
        self.no2_var = tk.BooleanVar(value=not rules.ALLOW_2_IN_SEQUENCE)
        tk.Checkbutton(frame, text="Disallow 2 in sequences", variable=self.no2_var).pack(anchor="w")

        # AI difficulty slider
        tk.Label(frame, text="AI difficulty").pack(anchor="w")
        self.diff_var = tk.DoubleVar(value=self.gui.ai_difficulty)
        tk.Scale(frame, from_=0.5, to=3.0, resolution=0.1, orient=tk.HORIZONTAL,
                 variable=self.diff_var).pack(anchor="w")

        # Accessibility
        self.hc_var = tk.BooleanVar(value=self.gui.high_contrast)
        tk.Checkbutton(frame, text="High contrast mode",
                       variable=self.hc_var).pack(anchor="w", pady=(5, 0))

        tk.Button(frame, text="OK", command=self.on_ok).pack(pady=(5,0))

    def choose_colour(self) -> None:
        col = colorchooser.askcolor(self.colour, parent=self)[1]
        if col:
            self.colour = col
            self.colour_lbl.config(bg=col)

    def on_ok(self) -> None:
        sound._ENABLED = self.sound_var.get()
        rules.ALLOW_2_IN_SEQUENCE = not self.no2_var.get()
        val = float(self.vol_var.get())
        self.gui.sfx_volume.set(val)
        sound.set_volume(val)
        if pygame:
            pygame.mixer.music.set_volume(val)
            if self.music_var.get():
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.pause()
        self.gui.table_cloth_color = self.colour
        self.gui.table_view.config(bg=self.colour)
        back = self.back_var.get()
        img = self.gui.card_images.get(back)
        if img:
            self.gui.card_back = img
            try:
                self.gui.root.iconphoto(False, img)
            except Exception:
                pass
        diff = float(self.diff_var.get())
        self.gui.ai_difficulty = diff
        self.gui.game.ai_difficulty = diff
        self.gui.set_high_contrast(self.hc_var.get())
        self.destroy()
