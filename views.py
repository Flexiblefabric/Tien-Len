"""GUI helper classes for displaying cards and the table."""

from __future__ import annotations

from typing import Callable
import tkinter as tk
from PIL import Image, ImageTk

from tooltip import ToolTip

from tien_len_full import Game, Card, detect_combo


class CardSprite(tk.Label):
    """Widget representing a single card image or text."""

    def __init__(self, master: tk.Widget, card: Card,
                 base_images: dict[str, Image.Image],
                 cache: dict[tuple[str, int], ImageTk.PhotoImage],
                 width: int = 80,
                 **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.card = card
        self.base_images = base_images
        self.cache = cache
        self.width = width
        self.selected = False
        self._update_image()

    # ------------------------------------------------------------------
    def _image_key(self) -> str:
        rank_map = {"J": "jack", "Q": "queen", "K": "king", "A": "ace"}
        rank = rank_map.get(self.card.rank, self.card.rank.lower())
        suit = self.card.suit.lower()
        return f"{rank}_of_{suit}"

    def _update_image(self) -> None:
        key = self._image_key()
        base = self.base_images.get(key)
        if base is None:
            self.config(text=str(self.card))
            return
        cache_key = (key, self.width)
        if cache_key not in self.cache:
            ratio = self.width / base.width
            img = base.resize((self.width, int(base.height * ratio)), Image.LANCZOS)
            self.cache[cache_key] = ImageTk.PhotoImage(img)
        img = self.cache[cache_key]
        self.config(image=img)
        self.image = img

    def set_selected(self, value: bool) -> None:
        self.selected = value
        if value:
            self.config(relief=tk.SUNKEN, bd=3,
                        highlightthickness=2,
                        highlightbackground="gold",
                        highlightcolor="gold")
        else:
            self.config(relief=tk.RAISED, bd=2, highlightthickness=0)


class TableView(tk.Frame):
    """Simple view for the pile of cards on the table."""

    def __init__(self, master: tk.Widget, game: Game,
                 base_images: dict[str, Image.Image],
                 cache: dict[tuple[str, int], ImageTk.PhotoImage],
                 card_width: int = 80) -> None:
        super().__init__(master, bd=2, relief=tk.SUNKEN)
        self.game = game
        self.base_images = base_images
        self.cache = cache
        self.card_width = card_width
        self.info_var = tk.StringVar()
        tk.Label(self, textvariable=self.info_var).pack()

    def refresh(self) -> None:
        for w in self.pack_slaves()[1:]:
            w.destroy()
        if not self.game.pile:
            self.info_var.set("Pile: empty")
            return
        player, cards = self.game.pile[-1]
        self.info_var.set(f"Pile: {player.name} -> {cards} ({detect_combo(cards)})")
        for c in cards:
            sprite = CardSprite(self, c, self.base_images, self.cache,
                                self.card_width)
            sprite.pack(side=tk.LEFT, padx=2)


class HandView(tk.Frame):
    """Display for the player's hand allowing card selection."""

    def __init__(self, master: tk.Widget, game: Game,
                 base_images: dict[str, Image.Image],
                 cache: dict[tuple[str, int], ImageTk.PhotoImage],
                 select_callback: Callable[[set[Card]], None] | None = None,
                 card_width: int = 80) -> None:
        super().__init__(master)
        self.game = game
        self.base_images = base_images
        self.cache = cache
        self.card_width = card_width
        self.selected: set[Card] = set()
        self.select_callback = select_callback
        self.widgets: dict[Card, CardSprite] = {}
        self.order: list[Card] = []
        self.last_idx: int | None = None
        self.dragging = False
        self.drag_sel: set[Card] = set()
        self.start_x = 0
        self.start_y = 0

    # ------------------------------------------------------------------
    def toggle_card(self, card: Card) -> None:
        if card in self.selected:
            self.selected.remove(card)
        else:
            self.selected.add(card)
        if self.select_callback:
            self.select_callback(self.selected)
        self.refresh()

    def _on_press(self, event: tk.Event, card: Card, idx: int) -> None:
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.dragging = False
        self.drag_sel.clear()
        self.press_card = card
        self.press_idx = idx

    def _on_motion(self, event: tk.Event) -> None:
        if not hasattr(self, "press_card"):
            return
        if abs(event.x_root - self.start_x) > 5 or abs(event.y_root - self.start_y) > 5:
            self.dragging = True
        if not self.dragging:
            return
        x1 = min(self.start_x, event.x_root)
        y1 = min(self.start_y, event.y_root)
        x2 = max(self.start_x, event.x_root)
        y2 = max(self.start_y, event.y_root)
        self.drag_sel = set()
        for card, spr in self.widgets.items():
            cx1 = spr.winfo_rootx()
            cy1 = spr.winfo_rooty()
            cx2 = cx1 + spr.winfo_width()
            cy2 = cy1 + spr.winfo_height()
            if x2 >= cx1 and x1 <= cx2 and y2 >= cy1 and y1 <= cy2:
                self.drag_sel.add(card)
        for card, spr in self.widgets.items():
            spr.set_selected(card in self.selected or card in self.drag_sel)

    def _on_release(self, event: tk.Event, card: Card, idx: int) -> None:
        shift = event.state & 0x0001
        if self.dragging:
            self.selected.update(self.drag_sel)
            self.drag_sel.clear()
            self.dragging = False
        elif shift and self.last_idx is not None:
            start = min(self.last_idx, idx)
            end = max(self.last_idx, idx)
            for c in self.order[start : end + 1]:
                self.selected.add(c)
        else:
            if card in self.selected:
                self.selected.remove(card)
            else:
                self.selected.add(card)
        self.last_idx = idx
        if self.select_callback:
            self.select_callback(self.selected)
        self.refresh()

    def refresh(self) -> None:
        for w in self.pack_slaves():
            w.destroy()
        self.widgets.clear()
        player = self.game.players[0]
        self.order = list(player.hand)
        count = len(player.hand)
        if count:
            width = min(self.card_width, max(40, self.winfo_width() // count))
        else:
            width = self.card_width
        for idx, c in enumerate(player.hand):
            spr = CardSprite(self, c, self.base_images, self.cache, width)
            spr.set_selected(c in self.selected)
            spr.bind("<ButtonPress-1>", lambda e, card=c, i=idx: self._on_press(e, card, i))
            spr.bind("<B1-Motion>", self._on_motion)
            spr.bind("<ButtonRelease-1>", lambda e, card=c, i=idx: self._on_release(e, card, i))
            ToolTip(spr, "Click to select")
            spr.pack(side=tk.LEFT, padx=2)
            self.widgets[c] = spr
        self.update_idletasks()
class OpponentView(tk.Frame):
    """Display an AI player's remaining cards."""

    def __init__(self, master: tk.Widget, game: Game, idx: int,
                 base_images: dict[str, Image.Image],
                 cache: dict[tuple[str, int], ImageTk.PhotoImage],
                 card_width: int = 80, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.game = game
        self.idx = idx
        self.base_images = base_images
        self.cache = cache
        self.card_width = card_width
        self.count_var = tk.StringVar()
        self.avatar = tk.Label(self, text=self.game.players[idx].name)
        self.avatar.pack()
        self.card_label = tk.Label(self)
        self.card_label.pack()
        tk.Label(self, textvariable=self.count_var).pack()
        self.refresh()

    def refresh(self) -> None:
        player = self.game.players[self.idx]
        self.count_var.set(str(len(player.hand)))
        base = self.base_images.get("card_back")
        if base is None:
            self.card_label.config(text="[]")
            return
        key = ("card_back", self.card_width)
        if key not in self.cache:
            ratio = self.card_width / base.width
            img = base.resize((self.card_width, int(base.height * ratio)), Image.LANCZOS)
            self.cache[key] = ImageTk.PhotoImage(img)
        img = self.cache[key]
        self.card_label.config(image=img)
        self.card_label.image = img

