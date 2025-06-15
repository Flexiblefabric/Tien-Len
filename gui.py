import tkinter as tk
from tkinter import messagebox
from tkinter import font as tkfont
from pathlib import Path
from PIL import Image, ImageTk

from tien_len_full import Game, detect_combo, SUITS, RANKS


class GameGUI:
    CARD_WIDTH = 80

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Tiến Lên GUI Prototype")
        self.fullscreen = False
        # Base font for text fallback buttons when images are missing
        self.card_font = tkfont.Font(size=12)
        self.game = Game()
        self.game.setup()
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
        self.selected = []
        self.hand_buttons = []
        self.pile_var = tk.StringVar()
        self.info_var = tk.StringVar()

        self.pile_frame = tk.Frame(root, width=200, height=120, bd=2, relief=tk.SUNKEN)
        self.pile_frame.pack(pady=5)
        tk.Label(self.pile_frame, textvariable=self.pile_var, font=("Arial", 14)).pack()
        tk.Label(root, textvariable=self.info_var).pack(pady=5)

        self.hand_frame = tk.Frame(root)
        self.hand_frame.pack(pady=10)

        action_frame = tk.Frame(root)
        action_frame.pack(pady=5)
        tk.Button(action_frame, text="Play", command=self.play_selected).pack(
            side=tk.LEFT
        )
        tk.Button(action_frame, text="Pass", command=self.pass_turn).pack(side=tk.LEFT)

        # Keyboard shortcuts
        self.root.bind("<Return>", lambda e: self.play_selected())
        self.root.bind("<space>", lambda e: self.pass_turn())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Escape>", lambda e: self.end_fullscreen())
        self.root.bind("<Configure>", self.on_resize)

        self.update_display()
        self.root.after(100, self.game_loop)

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

    def on_resize(self, event):
        size = max(8, int(event.width / 50))
        if size != self.card_font["size"]:
            self.card_font.configure(size=size)
        self.update_display()

    # GUI helpers -------------------------------------------------
    def update_display(self):
        for w in self.pile_frame.pack_slaves()[1:]:
            w.destroy()

        if not self.game.pile:
            self.pile_var.set("Pile: empty")
        else:
            p, c = self.game.pile[-1]
            self.pile_var.set(f"Pile: {p.name} -> {c} ({detect_combo(c)})")
            for card in c:
                key = self._image_key(card)
                img = self._scaled_image(key, self.card_width)
                if img:
                    lbl = tk.Label(self.pile_frame, image=img)
                    lbl.image = img
                    lbl.pack(side=tk.LEFT, padx=2)

        for b in self.hand_buttons:
            b.destroy()
        self.hand_buttons.clear()
        self.card_buttons = {}
        player = self.game.players[0]
        if player.hand:
            card_width = min(
                self.CARD_WIDTH, self.root.winfo_width() // max(1, len(player.hand))
            )
        else:
            card_width = self.CARD_WIDTH
        self.card_width = card_width
        for card in player.hand:
            key = self._image_key(card)
            img = self._scaled_image(key, card_width)
            if img:
                btn = tk.Button(
                    self.hand_frame,
                    image=img,
                    command=lambda c=card: self.toggle_card(c),
                    borderwidth=2,
                )
                btn.image = img
            else:
                btn = tk.Button(
                    self.hand_frame,
                    text=str(card),
                    width=card_width,
                    font=self.card_font,
                    command=lambda c=card: self.toggle_card(c),
                )
            # Apply a highlight border to indicate selection rather than only
            # changing the relief. Using ``highlightthickness`` provides a
            # simple "glow" effect around the button.
            if card in self.selected:
                btn.config(
                    relief=tk.SUNKEN,
                    bd=3,
                    highlightthickness=2,
                    highlightbackground="gold",
                )
            else:
                btn.config(relief=tk.RAISED, highlightthickness=0)
            btn.pack(side=tk.LEFT, padx=2)
            self.hand_buttons.append(btn)
            self.card_buttons[card] = btn
            btn.bind("<ButtonPress-1>", lambda e, c=card: self.start_drag(e, c))
            btn.bind("<B1-Motion>", self.drag_motion)
            btn.bind("<ButtonRelease-1>", lambda e, c=card: self.end_drag(e))

        cur = self.game.players[self.game.current_idx]
        if cur.is_human:
            self.info_var.set("Your turn")
        else:
            self.info_var.set(f"Waiting for {cur.name}...")

    def toggle_card(self, card):
        if card in self.selected:
            self.selected.remove(card)
        else:
            self.selected.append(card)
        self.update_display()

    # Drag and drop helpers --------------------------------------
    def start_drag(self, event, card):
        if not self.game.players[self.game.current_idx].is_human:
            return
        # Save the pile frame's original style the first time we start a drag
        if not hasattr(self, "_pile_style"):
            self._pile_style = {
                "highlightthickness": self.pile_frame.cget("highlightthickness"),
                "highlightbackground": self.pile_frame.cget("highlightbackground"),
            }
        self.pile_frame.config(highlightthickness=2, highlightbackground="gold")

        self.drag_data = {
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
        self.pile_frame.config(highlightthickness=2, highlightbackground="gold")
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
        px1 = self.pile_frame.winfo_rootx()
        py1 = self.pile_frame.winfo_rooty()
        px2 = px1 + self.pile_frame.winfo_width()
        py2 = py1 + self.pile_frame.winfo_height()
        if px1 <= x <= px2 and py1 <= y <= py2 and data["dragged"]:
            self.selected = [data["card"]]
            self.play_selected()
        else:
            self.toggle_card(data["card"])
        # Restore the pile frame's original style after dropping
        if hasattr(self, "_pile_style"):
            self.pile_frame.config(**self._pile_style)
            delattr(self, "_pile_style")

    def _image_key(self, card):
        """Return the asset key for a card image."""
        rank_map = {
            "J": "jack",
            "Q": "queen",
            "K": "king",
            "A": "ace",
        }
        rank = rank_map.get(card.rank, card.rank.lower())
        suit = card.suit.lower()
        return f"{rank}_of_{suit}"

    def _scaled_image(self, key: str, width: int):
        """Return a ``PhotoImage`` for ``key`` scaled to ``width``."""

        base = self.base_images.get(key)
        if not base:
            return self.card_images.get(key)

        cache_key = (key, width)
        if cache_key not in self.scaled_images:
            ratio = width / base.width
            img = base.resize((width, int(base.height * ratio)), Image.LANCZOS)
            self.scaled_images[cache_key] = ImageTk.PhotoImage(img)
        return self.scaled_images[cache_key]

    def animate_play(self, cards):
        self.root.bell()
        labels = []
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        target_x = (
            self.pile_frame.winfo_rootx() - root_x + self.pile_frame.winfo_width() // 2
        )
        target_y = (
            self.pile_frame.winfo_rooty() - root_y + self.pile_frame.winfo_height() // 2
        )
        for c in cards:
            btn = self.card_buttons.get(c)
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
        for step in range(steps):
            for lbl, sx, sy in labels:
                nx = sx + (target_x - sx) * step / steps
                ny = sy + (target_y - sy) * step / steps
                lbl.place(x=nx, y=ny)
            self.root.update_idletasks()
            self.root.after(20)
        for lbl, _, _ in labels:
            lbl.destroy()
        if detect_combo(cards) == "bomb":
            bomb = tk.Label(
                self.root, text="\U0001f4a5 Bomb!", font=("Arial", 20), fg="red"
            )
            bomb.place(relx=0.5, rely=0.1, anchor="n")
            self.root.after(1000, bomb.destroy)

    def restart_game(self):
        self.game = Game()
        self.game.setup()
        self.selected.clear()
        self.update_display()

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
            self.game.next_turn()
            if winner:
                if messagebox.askyesno("Game Over", "You win! Play again?"):
                    self.restart_game()
                else:
                    self.root.destroy()
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
        self.game.pass_count += 1
        active = sum(1 for x in self.game.players if x.hand)
        if self.game.current_combo and self.game.pass_count >= active - 1:
            self.game.reset_pile()
        self.game.next_turn()
        self.selected.clear()
        self.update_display()

    # Main game loop ---------------------------------------------
    def game_loop(self):
        p = self.game.players[self.game.current_idx]
        if not p.is_human:
            cards = self.game.ai_play(self.game.current_combo)
            ok, _ = self.game.is_valid(p, cards, self.game.current_combo)
            if not ok:
                cards = []
            if cards:
                if (
                    self.game.first_turn
                    and self.game.current_idx == self.game.start_idx
                ):
                    self.game.first_turn = False
                self.game.pass_count = 0
                for c in cards:
                    p.hand.remove(c)
                self.game.pile.append((p, cards))
                self.game.current_combo = cards
                if not p.hand:
                    if messagebox.askyesno("Game Over", f"{p.name} wins! Play again?"):
                        self.restart_game()
                    else:
                        self.root.destroy()
                        return
            else:
                self.game.pass_count += 1
                active = sum(1 for x in self.game.players if x.hand)
                if self.game.current_combo and self.game.pass_count >= active - 1:
                    self.game.reset_pile()
            self.game.next_turn()
            self.update_display()
        self.root.after(100, self.game_loop)


def main():
    root = tk.Tk()
    GameGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
