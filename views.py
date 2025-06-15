"""GUI helper classes for displaying cards and the table."""

from __future__ import annotations

from pathlib import Path
from typing import Callable
import tkinter as tk
from PIL import Image, ImageTk

from tien_len_full import Game, Card, detect_combo, SUITS, RANKS


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

    # ------------------------------------------------------------------
    def toggle_card(self, card: Card) -> None:
        if card in self.selected:
            self.selected.remove(card)
        else:
            self.selected.add(card)
        if self.select_callback:
            self.select_callback(self.selected)
        self.refresh()

    def refresh(self) -> None:
        for w in self.pack_slaves():
            w.destroy()
        self.widgets.clear()
        player = self.game.players[0]
        count = len(player.hand)
        if count:
            width = min(self.card_width, max(40, self.winfo_width() // count))
        else:
            width = self.card_width
        for c in player.hand:
            spr = CardSprite(self, c, self.base_images, self.cache, width)
            spr.set_selected(c in self.selected)
            spr.bind("<Button-1>", lambda e, card=c: self.toggle_card(card))
            spr.pack(side=tk.LEFT, padx=2)
            self.widgets[c] = spr
        self.update_idletasks()
