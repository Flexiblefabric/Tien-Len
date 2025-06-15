import tkinter as tk
from tkinter import messagebox
from tkinter import font as tkfont

from tien_len_full import Game, detect_combo


class GameGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Tiến Lên GUI Prototype")
        self.fullscreen = False
        self.card_font = tkfont.Font(size=12)
        self.game = Game()
        self.game.setup()
        self.selected = []
        self.hand_buttons = []
        self.pile_var = tk.StringVar()
        self.info_var = tk.StringVar()

        tk.Label(root, textvariable=self.pile_var, font=("Arial", 14)).pack(pady=5)
        tk.Label(root, textvariable=self.info_var).pack(pady=5)

        self.hand_frame = tk.Frame(root)
        self.hand_frame.pack(pady=10)

        action_frame = tk.Frame(root)
        action_frame.pack(pady=5)
        tk.Button(action_frame, text="Play Selected", command=self.play_selected).pack(side=tk.LEFT)
        tk.Button(action_frame, text="Pass", command=self.pass_turn).pack(side=tk.LEFT)

        # Keyboard shortcuts
        self.root.bind('<Return>', lambda e: self.play_selected())
        self.root.bind('<space>', lambda e: self.pass_turn())
        self.root.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.root.bind('<Escape>', lambda e: self.end_fullscreen())
        self.root.bind('<Configure>', self.on_resize)

        self.update_display()
        self.root.after(100, self.game_loop)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.root.attributes('-fullscreen', self.fullscreen)

    def end_fullscreen(self):
        if self.fullscreen:
            self.fullscreen = False
            self.root.attributes('-fullscreen', False)

    def on_resize(self, event):
        size = max(8, int(event.width / 50))
        if size != self.card_font['size']:
            self.card_font.configure(size=size)

    # GUI helpers -------------------------------------------------
    def update_display(self):
        if not self.game.pile:
            self.pile_var.set("Pile: empty")
        else:
            p, c = self.game.pile[-1]
            self.pile_var.set(f"Pile: {p.name} -> {c} ({detect_combo(c)})")

        for b in self.hand_buttons:
            b.destroy()
        self.hand_buttons.clear()
        player = self.game.players[0]
        if player.hand:
            card_width = max(4, int(self.root.winfo_width() / (len(player.hand) * 15)))
        else:
            card_width = 4
        for card in player.hand:
            btn = tk.Button(
                self.hand_frame,
                text=str(card),
                width=card_width,
                font=self.card_font,
                command=lambda c=card: self.toggle_card(c),
            )
            if card in self.selected:
                btn.config(relief=tk.SUNKEN)
            btn.pack(side=tk.LEFT, padx=2)
            self.hand_buttons.append(btn)

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

    # Action handlers ---------------------------------------------
    def play_selected(self):
        if not self.game.players[self.game.current_idx].is_human:
            return
        cards = list(self.selected)
        ok, msg = self.game.is_valid(self.game.players[0], cards, self.game.current_combo)
        if not ok:
            messagebox.showinfo("Invalid move", msg)
            return
        if self.game.first_turn and self.game.current_idx == self.game.start_idx:
            self.game.first_turn = False
        self.game.pass_count = 0
        for c in cards:
            self.game.players[0].hand.remove(c)
        self.game.pile.append((self.game.players[0], cards))
        self.game.current_combo = cards
        self.selected.clear()
        if not self.game.players[0].hand:
            messagebox.showinfo("Game Over", "You win!")
            self.root.destroy()
            return
        self.game.next_turn()
        self.update_display()

    def pass_turn(self):
        if not self.game.players[self.game.current_idx].is_human:
            return
        ok, msg = self.game.is_valid(self.game.players[0], [], self.game.current_combo)
        if not ok:
            messagebox.showinfo("Invalid move", msg)
            return
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
                if self.game.first_turn and self.game.current_idx == self.game.start_idx:
                    self.game.first_turn = False
                self.game.pass_count = 0
                for c in cards:
                    p.hand.remove(c)
                self.game.pile.append((p, cards))
                self.game.current_combo = cards
                if not p.hand:
                    messagebox.showinfo("Game Over", f"{p.name} wins!")
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
