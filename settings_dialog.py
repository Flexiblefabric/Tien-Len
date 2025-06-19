import tkinter as tk
from tkinter import colorchooser
from tkinter import ttk
import sound
import tien_len_full as rules
try:
    import pygame
except ImportError:  # pragma: no cover - pygame optional
    pygame = None


def _mixer_ready() -> bool:
    """Return True if pygame and the mixer are initialized."""
    return bool(pygame and pygame.mixer.get_init())

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
        busy = pygame.mixer.music.get_busy() if _mixer_ready() else False
        self.music_var = tk.BooleanVar(value=busy)
        tk.Checkbutton(frame, text="Enable music", variable=self.music_var).pack(anchor="w")

        tk.Label(frame, text="Volume").pack(anchor="w")
        self.vol_var = tk.DoubleVar(value=self.gui.sfx_volume.get())
        tk.Scale(frame, from_=0, to=1, orient=tk.HORIZONTAL, resolution=0.1, variable=self.vol_var).pack(anchor="w")

        # Card theme selector
        backs = [k for k in self.gui.card_images if k.startswith("card_back")]
        if not backs:
            backs = ["card_back"]
        self.back_var = tk.StringVar(value=self.gui.card_back_name)
        tk.Label(frame, text="Card theme").pack(anchor="w")
        ttk.OptionMenu(frame, self.back_var, self.gui.card_back_name, *backs).pack(anchor="w")

        # Table theme
        themes = ["darkgreen", "saddlebrown", "navy", "darkred"]
        self.theme_var = tk.StringVar(value=self.gui.table_cloth_color)
        tk.Label(frame, text="Table theme").pack(anchor="w")
        ttk.OptionMenu(frame, self.theme_var, self.gui.table_cloth_color, *themes).pack(anchor="w")

        # Table cloth colour
        tk.Label(frame, text="Table colour").pack(anchor="w")
        self.colour = self.gui.table_cloth_color
        self.colour_lbl = tk.Label(frame, width=10, bg=self.colour)
        self.colour_lbl.pack(anchor="w")
        tk.Button(frame, text="Choose...", command=self.choose_colour).pack(anchor="w")

        # Rule variant
        self.no2_var = tk.BooleanVar(value=not rules.ALLOW_2_IN_SEQUENCE)
        tk.Checkbutton(frame, text="Disallow 2 in sequences", variable=self.no2_var).pack(anchor="w")

        # AI difficulty tier
        tk.Label(frame, text="AI difficulty").pack(anchor="w")
        levels = ["Easy", "Normal", "Hard"]
        self.diff_var = tk.StringVar(value=self.gui.ai_level)
        ttk.OptionMenu(frame, self.diff_var, self.gui.ai_level, *levels).pack(anchor="w")

        # AI personality preset
        tk.Label(frame, text="AI personality").pack(anchor="w")
        personalities = ["Aggressive", "Defensive", "Random"]
        cur_pers = getattr(self.gui, "ai_personality", "balanced").title()
        self.pers_var = tk.StringVar(value=cur_pers)
        ttk.OptionMenu(frame, self.pers_var, cur_pers, *personalities).pack(anchor="w")
        self.lookahead_var = tk.BooleanVar(value=getattr(self.gui, "ai_lookahead", False))
        tk.Checkbutton(frame, text="Enable lookahead (Hard)", variable=self.lookahead_var).pack(anchor="w")

        # Animation speed
        tk.Label(frame, text="Animation speed").pack(anchor="w")
        speeds = ["Slow", "Normal", "Fast"]
        speed_map = {0.5: "Slow", 1.0: "Normal", 2.0: "Fast"}
        cur_speed = speed_map.get(self.gui.animation_speed, "Normal")
        self.anim_var = tk.StringVar(value=cur_speed)
        ttk.OptionMenu(frame, self.anim_var, cur_speed, *speeds).pack(anchor="w")

        # Sort preference
        tk.Label(frame, text="Sort hand by").pack(anchor="w")
        sort_labels = ["Rank then Suit", "Suit then Rank"]
        cur_sort = "Suit then Rank" if self.gui.sort_mode == "suit" else "Rank then Suit"
        self.sort_var = tk.StringVar(value=cur_sort)
        ttk.OptionMenu(frame, self.sort_var, cur_sort, *sort_labels).pack(anchor="w")

        # Player name
        tk.Label(frame, text="Player name").pack(anchor="w")
        self.name_var = tk.Entry(frame)
        self.name_var.insert(0, self.gui.player_name)
        self.name_var.pack(anchor="w")

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
            self.theme_var.set(col)

    def on_ok(self) -> None:
        sound._ENABLED = self.sound_var.get()
        rules.ALLOW_2_IN_SEQUENCE = not self.no2_var.get()
        val = float(self.vol_var.get())
        self.gui.sfx_volume.set(val)
        sound.set_volume(val)
        if _mixer_ready():
            pygame.mixer.music.set_volume(val)
            if self.music_var.get():
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.pause()
        self.colour = self.theme_var.get()
        self.gui.table_cloth_color = self.colour
        back = self.back_var.get()
        self.gui.card_back_name = back
        speed_map = {"Slow": 0.5, "Normal": 1.0, "Fast": 2.0}
        self.gui.animation_speed = speed_map.get(self.anim_var.get(), 1.0)
        self.gui.sort_mode = "suit" if self.sort_var.get() == "Suit then Rank" else "rank"
        self.gui.player_name = self.name_var.get() or "Player"
        level = self.diff_var.get()
        self.gui.set_ai_level(level)
        self.gui.ai_lookahead = self.lookahead_var.get()
        self.gui.set_personality(self.pers_var.get().lower())
        self.gui.set_high_contrast(self.hc_var.get())
        self.gui.apply_options()
        self.gui.save_options()
        self.destroy()
