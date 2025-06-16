import tkinter as tk
from tkinter import messagebox
from tkinter import font as tkfont
import time
from pathlib import Path
from PIL import Image, ImageTk
import random

from tien_len_full import Game, detect_combo, SUITS, RANKS
from views import TableView, HandView
from tooltip import ToolTip
import sound
try:
    import pygame
except ImportError:  # pragma: no cover - pygame optional
    pygame = None


class GameGUI:
    CARD_WIDTH = 80
    HISTORY_LIMIT = 8

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Tiến Lên GUI Prototype")
        # Capture the window's default background color so we can restore it
        self._default_bg = self.root.cget("background")
        # Setup menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Game", command=self.restart_game)
        file_menu.add_command(label="Save Game", command=self.save_game)
        file_menu.add_command(label="Load Game", command=self.load_game)
        file_menu.add_command(label="Quit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        opt_menu = tk.Menu(menubar, tearoff=0)
        opt_menu.add_command(label="Settings...", command=self.open_settings)
        menubar.add_cascade(label="Options", menu=opt_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Rules...", command=self.show_rules)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.fullscreen = False
        # Base font for text fallback buttons when images are missing
        self.card_font = tkfont.Font(size=12)
        self.game = Game()
        self.game.setup()
        # AI difficulty tier
        self.set_ai_level("Normal")
        self.high_contrast = False

        # Load sound effects and background music
        sdir = Path(__file__).with_name("assets") / "sound"
        sound.load("click", sdir / "card-play.wav")
        sound.load("pass", sdir / "pass.wav")
        sound.load("bomb", sdir / "bomb.wav")
        sound.load("shuffle", sdir / "shuffle.wav")
        sound.load("win", sdir / "win.wav")
        sound.set_volume(1.0)
        music = sdir / "Ambush in Rattlesnake Gulch.mp3"
        if pygame:
            try:
                pygame.mixer.music.load(str(music))
                pygame.mixer.music.play(-1)
            except Exception:
                pass
        self.base_images = {}
        self.scaled_images = {}
        self.card_images = {}
        self.card_back = None
        self.card_width = self.CARD_WIDTH
        self.load_images()
        if self.card_back is not None:
            try:
                self.root.iconphoto(False, self.card_back)
            except Exception:
                pass
        self.selected: set = set()
        self.pile_var = tk.StringVar()
        self.info_var = tk.StringVar()
        self.turn_var = tk.StringVar()
        self.history_var = tk.StringVar()
        self.ranking_var = tk.StringVar()
        self.score_var = tk.StringVar()
        self.overlay_active = False
        self.table_cloth_color = "darkgreen"

        self.main_area = tk.Frame(root)
        self.main_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Optional table cloth background image
        bg_path = Path(__file__).with_name("assets") / "table_bg.png"
        self._bg_base = None
        if bg_path.exists():
            try:
                self._bg_base = Image.open(bg_path)
                self._bg_img = ImageTk.PhotoImage(self._bg_base)
                self._bg_label = tk.Label(self.main_area, image=self._bg_img)
                self._bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
                self._bg_label.lower()
                self.main_area.bind("<Configure>", self._resize_bg)
            except Exception:
                self._bg_base = None
        self.sidebar = tk.Frame(root, bd=1, relief=tk.SUNKEN)
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        self.table_view = TableView(
            self.main_area, self.game, self.base_images, self.scaled_images, self.CARD_WIDTH
        )
        self.table_view.config(bg=self.table_cloth_color)
        self.table_view.pack(pady=5)
        tk.Label(self.main_area, textvariable=self.info_var).pack(pady=5)
        self.turn_label = tk.Label(self.main_area, textvariable=self.turn_var, font=("Arial", 12, "bold"))
        self.turn_label.pack(pady=2)

        self.hand_view = HandView(
            self.main_area,
            self.game,
            self.base_images,
            self.scaled_images,
            lambda sel: self.on_selection(sel),
            self.CARD_WIDTH,
        )
        self.hand_view.pack(pady=10)

        action_frame = tk.Frame(self.main_area)
        action_frame.pack(pady=5)
        self.play_btn = tk.Button(action_frame, text="Play", command=self.play_selected)
        self.play_btn.pack(side=tk.LEFT)
        self.pass_btn = tk.Button(action_frame, text="Pass", command=self.pass_turn)
        self.pass_btn.pack(side=tk.LEFT)
        self.sort_btn = tk.Button(action_frame, text="Sort Hand", command=self.sort_hand)
        self.sort_btn.pack(side=tk.LEFT)
        self.hint_btn = tk.Button(action_frame, text="Hint", command=self.show_hint)
        self.hint_btn.pack(side=tk.LEFT)
        ToolTip(self.play_btn, "Drag to play")
        ToolTip(self.pass_btn, "Drag to play")
        ToolTip(self.sort_btn, "Drag to play")
        ToolTip(self.hint_btn, "Suggest a move")

        # Indicator shown when AI players are thinking
        self.thinking = tk.Label(
            self.main_area, text="Thinking...", font=("Arial", 12, "italic")
        )
        self.thinking.pack(pady=5)
        self.thinking.pack_forget()

        tk.Label(self.sidebar, text="History", font=("Arial", 12, "bold")).pack(anchor="w")
        tk.Label(self.sidebar, textvariable=self.history_var, justify=tk.LEFT, anchor="nw").pack(anchor="w")
        tk.Label(self.sidebar, text="Rankings", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10, 0))
        tk.Label(self.sidebar, textvariable=self.ranking_var, justify=tk.LEFT, anchor="nw").pack(anchor="w")
        tk.Label(self.sidebar, text="Scores", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10, 0))
        tk.Label(self.sidebar, textvariable=self.score_var, justify=tk.LEFT, anchor="nw").pack(anchor="w")

        ctrl = tk.Frame(self.sidebar)
        ctrl.pack(anchor="w", pady=(10, 0))
        self.music_btn = tk.Button(ctrl, text="Pause Music", command=self.toggle_music)
        self.music_btn.pack(anchor="w")
        tk.Label(ctrl, text="Music Vol").pack(anchor="w")
        self.music_volume = tk.DoubleVar(value=pygame.mixer.music.get_volume() if pygame else 1.0)
        tk.Scale(ctrl, from_=0, to=1, orient=tk.HORIZONTAL, resolution=0.1,
                 variable=self.music_volume,
                 command=lambda v: pygame.mixer.music.set_volume(float(v)) if pygame else None).pack(anchor="w")
        tk.Label(ctrl, text="SFX Vol").pack(anchor="w")
        self.sfx_volume = tk.DoubleVar(value=1.0)
        tk.Scale(ctrl, from_=0, to=1, orient=tk.HORIZONTAL, resolution=0.1,
                 variable=self.sfx_volume,
                 command=lambda v: sound.set_volume(float(v))).pack(anchor="w")
        tk.Button(ctrl, text="Replay Last Round", command=self.replay_last_round).pack(anchor="w", pady=(5, 0))

        # Keyboard shortcuts
        self.root.bind("<Return>", lambda e: self.play_selected())
        self.root.bind("<space>", lambda e: self.pass_turn())
        self.root.bind("<h>", lambda e: self.show_hint())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Escape>", lambda e: self.end_fullscreen())
        self.root.bind("<Configure>", self.on_resize)

        self.set_high_contrast(False)
        self.update_display()
        self.show_menu()
        self.root.after(100, self.game_loop)

    def set_ai_level(self, level: str) -> None:
        """Set difficulty tier for the AI opponents."""

        mapping = {"Easy": 0.5, "Normal": 1.0, "Hard": 2.0}
        self.ai_level = level
        self.ai_difficulty = mapping.get(level, 1.0)
        self.game.set_ai_level(level)

    def on_selection(self, selection: set) -> None:
        """Callback from :class:`HandView` when the selection changes."""
        self.selected = set(selection)
        self.update_display()

    # Image loading -------------------------------------------------
    def load_images(self):
        """Load card face and back images if available."""
        assets = Path(__file__).with_name("assets")
        if not assets.exists():
            return

        # Map face card ranks to the full filename prefix used by the assets.
        rank_map = {
            "J": "jack",
            "Q": "queen",
            "K": "king",
            "A": "ace",
        }

        missing = []

        for suit in SUITS:
            for rank in RANKS:
                rank_name = rank_map.get(rank, rank.lower())
                suit_name = suit.lower()
                stem = f"{rank_name}_of_{suit_name}"
                img_path = assets / f"{stem}.png"
                if img_path.exists():
                    try:
                        img = Image.open(img_path)
                        self.base_images[stem] = img
                        w = self.CARD_WIDTH
                        h = int(img.height * w / img.width)
                        self.card_images[stem] = ImageTk.PhotoImage(
                            img.resize((w, h), Image.LANCZOS)
                        )
                    except Exception:
                        continue
                else:
                    missing.append(img_path.name)

        # Load joker and card back images if present.
        for extra in ("card_back.png", "red_joker.png", "black_joker.png"):
            img_path = assets / extra
            if img_path.exists():
                try:
                    img = Image.open(img_path)
                    self.base_images[img_path.stem] = img
                    w = self.CARD_WIDTH
                    h = int(img.height * w / img.width)
                    self.card_images[img_path.stem] = ImageTk.PhotoImage(
                        img.resize((w, h), Image.LANCZOS)
                    )
                except Exception:
                    continue
            else:
                missing.append(img_path.name)

        self.card_back = self.card_images.get("card_back")

        if missing:
            print("Missing card images:", ", ".join(sorted(missing)))

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def end_fullscreen(self):
        if self.fullscreen:
            self.fullscreen = False
            self.root.attributes("-fullscreen", False)

    def set_high_contrast(self, enable: bool):
        """Toggle high contrast mode for better visibility."""
        self.high_contrast = enable
        default_font = tkfont.nametofont("TkDefaultFont")
        size = 12 if enable else 10
        default_font.configure(size=size)
        self.card_font.configure(size=16 if enable else 12)
        if enable:
            self.root.tk_setPalette(background="black", foreground="white",
                                   activeBackground="#333",
                                   activeForeground="white")
        else:
            # Restore the palette to the window's original background color
            self.root.tk_setPalette(background=self._default_bg)
        self.update_display()

    def on_resize(self, event):
        size = max(8, int(event.width / 50))
        if size != self.card_font["size"]:
            self.card_font.configure(size=size)
        self.update_display()
        
    def _ease_out_quad(self, t: float) -> float:
        """Quadratic easing for smoother animations."""
        return 1 - (1 - t) ** 2

    def _sparkle(self, x: int, y: int, count: int = 8) -> None:
        """Create a simple sparkle effect at (x, y)."""
        for _ in range(count):
            dx = random.randint(-30, 30)
            dy = random.randint(-30, 30)
            lbl = tk.Label(self.root, text="\u2728", fg="gold", font=("Arial", 16), bd=0)
            lbl.place(x=x + dx, y=y + dy)

            def animate(step=0, lbl=lbl):
                if step >= 8:
                    lbl.destroy()
                    return
                size = 16 - step
                lbl.config(font=("Arial", size))
                self.root.after(60, lambda: animate(step + 1, lbl))

            animate()

    def _resize_bg(self, event):
        if not getattr(self, "_bg_base", None):
            return
        try:
            img = self._bg_base.resize((event.width, event.height), Image.LANCZOS)
            self._bg_img = ImageTk.PhotoImage(img)
            self._bg_label.config(image=self._bg_img)
            self._bg_label.image = self._bg_img
        except Exception:
            pass

    # GUI helpers -------------------------------------------------
    def update_display(self):
        self.table_view.refresh()
        self.hand_view.selected = set(self.selected)
        self.hand_view.refresh()

        cur = self.game.players[self.game.current_idx]
        if cur.is_human:
            self.info_var.set("Your turn")
            self.turn_label.config(bg="lightgreen")
        else:
            self.info_var.set(f"Waiting for {cur.name}...")
            self.turn_label.config(bg="lightblue")
        self.turn_var.set(f"Turn: {cur.name}")

        # Enable or disable action buttons
        is_human_turn = cur.is_human
        play_ok, _ = self.game.is_valid(
            self.game.players[0], list(self.selected), self.game.current_combo
        )
        pass_ok, _ = self.game.is_valid(
            self.game.players[0], [], self.game.current_combo
        )
        self.play_btn.config(
            state=tk.NORMAL if is_human_turn and play_ok else tk.DISABLED
        )
        self.pass_btn.config(
            state=tk.NORMAL if is_human_turn and pass_ok else tk.DISABLED
        )
        self.hint_btn.config(
            state=tk.NORMAL if is_human_turn else tk.DISABLED
        )

        self.update_sidebar()

    def update_sidebar(self):
        """Refresh the history and ranking display."""

        hist = [
            f"R{r}: {msg}" for r, msg in self.game.history[-self.HISTORY_LIMIT :]
        ]
        self.history_var.set("\n".join(hist))

        ranks = self.game.get_rankings()
        lines = [f"{i+1}. {n} ({c})" for i, (n, c) in enumerate(ranks)]
        self.ranking_var.set("\n".join(lines))
        score_lines = [f"{n}: {self.game.scores.get(n,0)}" for n in self.game.scores]
        self.score_var.set("\n".join(score_lines))

    def toggle_music(self):
        if not pygame:
            return
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.music_btn.config(text="Play Music")
        else:
            pygame.mixer.music.unpause()
            self.music_btn.config(text="Pause Music")

    def open_settings(self):
        from settings_dialog import SettingsDialog
        SettingsDialog(self.root, self)

    def save_game(self):
        """Prompt for a file and save the current game state."""
        from tkinter import filedialog

        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.game.to_json())
        except Exception as exc:
            messagebox.showerror("Save Failed", str(exc))

    def load_game(self):
        """Load game state from a JSON file."""
        from tkinter import filedialog

        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
            new_game = Game()
            new_game.from_json(data)
            new_game.set_ai_level(self.ai_level)
            self.game = new_game
            self.table_view.game = self.game
            self.hand_view.game = self.game
            self.selected.clear()
            self.update_display()
            self.update_sidebar()
        except Exception as exc:
            messagebox.showerror("Load Failed", str(exc))

    def show_rules(self):
        """Display a modal window with basic rules."""
        win = tk.Toplevel(self.root)
        win.title("Game Rules")
        win.transient(self.root)
        win.grab_set()
        text = (
            "Each player is dealt 13 cards.\n"
            "On your turn play a higher combo or pass.\n"
            "The first player to shed all cards wins.\n\n"
            "Example: play a pair of 7s over a pair of 5s."
        )
        tk.Label(win, text=text, justify=tk.LEFT, wraplength=400).pack(padx=20, pady=20)
        tk.Button(win, text="Close", command=win.destroy).pack(pady=(0, 10))

    def replay_last_round(self):
        """Replay the most recently completed round using animations."""
        round_no = self.game.current_round - 1
        actions = self.game.move_log.get(round_no)
        state = self.game.round_states.get(round_no)
        if not actions or not state:
            messagebox.showinfo("Replay", "No round to replay yet")
            return

        orig_game = self.game
        replay_game = Game()
        replay_game.from_json(state)
        replay_game.set_ai_level(self.ai_level)
        self.game = replay_game
        self.table_view.game = self.game
        self.hand_view.game = self.game
        self.selected.clear()
        self.update_display()

        def step(i=0):
            if i >= len(actions):
                self.game = orig_game
                self.table_view.game = self.game
                self.hand_view.game = self.game
                self.update_display()
                self.update_sidebar()
                return
            typ, idx, cards = actions[i]
            self.game.current_idx = idx
            p = self.game.players[idx]
            if typ == "play":
                self.animate_play(cards)
                self.game.process_play(p, list(cards))
            else:
                self.animate_pass(p)
                self.game.process_pass(p)
            self.update_sidebar()
            self.game.next_turn()
            self.update_display()
            self.root.after(600, lambda: step(i + 1))

        self.root.after(100, step)

    def toggle_card(self, card):
        if card in self.selected:
            self.selected.remove(card)
        else:
            self.selected.add(card)
        self.update_display()

    # Drag and drop helpers --------------------------------------
    def start_drag(self, event, card):
        if not self.game.players[self.game.current_idx].is_human:
            return
        # Save the pile frame's original style the first time we start a drag
        if not hasattr(self, "_pile_style"):
            self._pile_style = {
                "highlightthickness": self.table_view.cget("highlightthickness"),
                "highlightbackground": self.table_view.cget("highlightbackground"),
            }
        self.table_view.config(highlightthickness=2, highlightbackground="gold")

        drag_cards = list(self.selected) if self.selected and card in self.selected else [card]
        self.drag_data = {
            "cards": drag_cards,
            "card": card,
            "widget": event.widget,
            "start_x": event.x_root,
            "start_y": event.y_root,
            "dragged": False,
        }
        img = event.widget.image if hasattr(event.widget, "image") else None
        if img:
            self.drag_label = tk.Label(self.root, image=img)
            self.drag_label.image = img
            self.drag_label.place(x=event.x_root, y=event.y_root)

    def drag_motion(self, event):
        if not getattr(self, "drag_data", None):
            return
        self.drag_data["dragged"] = True
        # Keep the drop target highlighted during drag motion
        self.table_view.config(highlightthickness=2, highlightbackground="gold")
        if hasattr(self, "drag_label"):
            self.drag_label.place(x=event.x_root, y=event.y_root)

    def end_drag(self, event):
        data = getattr(self, "drag_data", None)
        if not data:
            return
        if hasattr(self, "drag_label"):
            self.drag_label.destroy()
        x, y = event.x_root, event.y_root
        self.drag_data = None
        px1 = self.table_view.winfo_rootx()
        py1 = self.table_view.winfo_rooty()
        px2 = px1 + self.table_view.winfo_width()
        py2 = py1 + self.table_view.winfo_height()
        if px1 <= x <= px2 and py1 <= y <= py2 and data["dragged"]:
            self.selected = set(data.get("cards", [data["card"]]))
            self.play_selected()
        else:
            self.toggle_card(data["card"])
        # Restore the pile frame's original style after dropping
        if hasattr(self, "_pile_style"):
            self.table_view.config(**self._pile_style)
            delattr(self, "_pile_style")


    def animate_play(self, cards):
        self.root.bell()
        sound.play("click")
        labels = []
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        target_x = (
            self.table_view.winfo_rootx() - root_x + self.table_view.winfo_width() // 2
        )
        target_y = (
            self.table_view.winfo_rooty() - root_y + self.table_view.winfo_height() // 2
        )
        for c in cards:
            btn = self.hand_view.widgets.get(c)
            if not btn:
                continue
            x = btn.winfo_rootx() - root_x
            y = btn.winfo_rooty() - root_y
            img = btn.image if hasattr(btn, "image") else None
            if img:
                lbl = tk.Label(self.root, image=img)
                lbl.image = img
                lbl.place(x=x, y=y)
                labels.append((lbl, x, y))
        steps = 10
        for step in range(steps + 1):
            t = self._ease_out_quad(step / steps)
            for lbl, sx, sy in labels:
                nx = sx + (target_x - sx) * t
                ny = sy + (target_y - sy) * t
                lbl.place(x=nx, y=ny)
            self.root.update_idletasks()
            self.root.after(20)
        for lbl, _, _ in labels:
            lbl.destroy()
        if detect_combo(cards) == "bomb":
            sound.play("bomb")
            bomb = tk.Label(
                self.root, text="\U0001f4a5 Bomb!", font=("Arial", 20), fg="red"
            )
            bomb.place(relx=0.5, rely=0.1, anchor="n")
            self.root.after(1000, bomb.destroy)
            self._sparkle(target_x, target_y)

    def animate_pass(self, player):
        """Show a short sliding label indicating a pass."""
        sound.play("pass")
        lbl = tk.Label(self.root, text=f"{player.name} passes", bg="yellow")
        lbl.place(relx=0.5, rely=0.4, anchor="center")
        steps = 10
        for step in range(steps + 1):
            t = self._ease_out_quad(step / steps)
            lbl.place_configure(rely=0.4 - 0.3 * t)
            self.root.update_idletasks()
            self.root.after(20)
        lbl.destroy()

    def show_game_over(self, winner: str):
        """Display a semi-transparent overlay with winner message."""
        sound.play("win")
        self.overlay_active = True
        overlay = tk.Frame(self.root, bg="#00000080")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        box = tk.Frame(overlay, bg="white", bd=2, relief=tk.RIDGE)
        box.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(box, text=f"\U0001f389 {winner} wins!", font=("Arial", 16)).pack(padx=20, pady=(10, 5))
        btn_frame = tk.Frame(box, bg="white")
        btn_frame.pack(pady=(0, 10))
        tk.Button(btn_frame, text="Play Again", command=lambda: self.play_again(overlay)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Quit", command=self.root.destroy).pack(side=tk.LEFT, padx=5)
        self._sparkle(self.root.winfo_width() // 2, self.root.winfo_height() // 2)

    def show_menu(self):
        """Display the start menu with basic actions."""
        self.overlay_active = True
        self.menu_overlay = tk.Frame(self.root, bg="#00000080")
        self.menu_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        box = tk.Frame(self.menu_overlay, bg="white", bd=2, relief=tk.RIDGE)
        box.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(box, text="Tiến Lên", font=("Arial", 16, "bold")).pack(padx=20, pady=(10, 5))
        tk.Button(box, text="New Game", command=self.menu_new_game).pack(fill="x", padx=20, pady=5)
        tk.Button(box, text="Load Game", command=self.menu_load_game).pack(fill="x", padx=20, pady=5)
        tk.Button(box, text="Options", command=self.open_settings).pack(fill="x", padx=20, pady=5)
        tk.Button(box, text="Quit", command=self.root.destroy).pack(fill="x", padx=20, pady=(5, 10))

    def hide_menu(self):
        if hasattr(self, 'menu_overlay') and self.menu_overlay:
            self.menu_overlay.destroy()
            self.menu_overlay = None
        self.overlay_active = False

    def menu_new_game(self):
        self.hide_menu()
        self.restart_game()

    def menu_load_game(self):
        self.hide_menu()
        self.load_game()

    def play_again(self, overlay):
        overlay.destroy()
        self.overlay_active = False
        self.restart_game()

    def restart_game(self):
        scores = self.game.scores if hasattr(self, "game") else None
        self.game = Game()
        if scores:
            self.game.scores = scores
        self.game.setup()
        self.selected.clear()
        self.update_display()
        self.update_sidebar()

    # Action handlers ---------------------------------------------
    def play_selected(self):
        if not self.game.players[self.game.current_idx].is_human:
            return
        cards = list(self.selected)
        ok, msg = self.game.is_valid(
            self.game.players[0], cards, self.game.current_combo
        )
        if ok:
            self.animate_play(cards)
            winner = self.game.process_play(self.game.players[0], cards)
            self.update_sidebar()
            self.game.next_turn()
            if winner:
                self.game.scores[self.game.players[0].name] += 1
                self.update_sidebar()
                self.show_game_over(self.game.players[0].name)
                return
        else:
            messagebox.showwarning("Invalid", msg)
        self.selected.clear()
        self.update_display()

    def pass_turn(self):
        if not self.game.players[self.game.current_idx].is_human:
            return
        ok, msg = self.game.is_valid(self.game.players[0], [], self.game.current_combo)
        if not ok:
            messagebox.showinfo("Invalid move", msg)
            return
        self.root.bell()
        self.animate_pass(self.game.players[0])
        self.game.process_pass(self.game.players[0])
        self.update_sidebar()
        self.game.next_turn()
        self.selected.clear()
        self.update_display()

    def sort_hand(self):
        self.game.players[0].sort_hand()
        self.selected.clear()
        self.update_display()

    def show_hint(self):
        """Display a suggested move for the player."""
        hint = self.game.hint(self.game.current_combo)
        if hint:
            msg = "Suggested move: " + ", ".join(map(str, hint))
        else:
            msg = "No valid moves available"
        messagebox.showinfo("Hint", msg)

    # Main game loop ---------------------------------------------
    def game_loop(self):
        if self.overlay_active:
            self.root.after(100, self.game_loop)
            return
        p = self.game.players[self.game.current_idx]
        if not p.is_human:
            # Show thinking indicator for AI
            self.thinking.pack()
            self.root.update_idletasks()
            time.sleep(0.3)
            cards = self.game.ai_play(self.game.current_combo)
            self.thinking.pack_forget()
            ok, _ = self.game.is_valid(p, cards, self.game.current_combo)
            if not ok:
                cards = []
            if cards:
                self.animate_play(cards)
                winner = self.game.process_play(p, cards)
                self.update_sidebar()
                if winner:
                    self.game.scores[p.name] += 1
                    self.update_sidebar()
                    self.show_game_over(p.name)
                    return
            else:
                self.animate_pass(p)
                self.game.process_pass(p)
                self.update_sidebar()
            self.game.next_turn()
            self.update_display()
        self.root.after(100, self.game_loop)


def main():
    root = tk.Tk()
    GameGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
