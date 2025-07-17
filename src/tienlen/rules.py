from __future__ import annotations

# Card constants
SUIT_SYMBOLS = {'♠': 'Spades', '♥': 'Hearts', '♦': 'Diamonds', '♣': 'Clubs'}
SUITS = list(SUIT_SYMBOLS.values())
RANKS = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']

# Rough ranking used by the simple AI
TYPE_PRIORITY = {'bomb': 5, 'sequence': 4, 'triple': 3, 'pair': 2, 'single': 1}

AI_NAMES = ["Linh", "Phong", "Bao", "Trang", "My", "Tuan", "Nam", "Duy", "Ha", "Minh"]


def suit_index(suit: str, flip_suit_rank: bool = False) -> int:
    idx = SUITS.index(suit)
    if flip_suit_rank:
        idx = len(SUITS) - idx - 1
    return idx


def opening_suit(flip_suit_rank: bool = False) -> str:
    return "Hearts" if flip_suit_rank else "Spades"


def opening_card_str(flip_suit_rank: bool = False) -> str:
    symbol = next(sym for sym, name in SUIT_SYMBOLS.items() if name == opening_suit(flip_suit_rank))
    return f"3{symbol}"


def is_single(cards) -> bool:
    return len(cards) == 1


def is_pair(cards) -> bool:
    return len(cards) == 2 and cards[0].rank == cards[1].rank


def is_triple(cards) -> bool:
    return len(cards) == 3 and len({c.rank for c in cards}) == 1


def is_bomb(cards) -> bool:
    return len(cards) == 4 and len({c.rank for c in cards}) == 1


def is_sequence(cards, allow_2_in_sequence: bool = False) -> bool:
    if len(cards) < 3:
        return False
    if not allow_2_in_sequence and any(c.rank == '2' for c in cards):
        return False
    idx = sorted(RANKS.index(c.rank) for c in cards)
    if len(set(idx)) != len(idx):
        return False
    return all(idx[i] + 1 == idx[i + 1] for i in range(len(idx) - 1))


def detect_combo(cards, allow_2_in_sequence: bool = False):
    if is_bomb(cards):
        return 'bomb'
    if is_sequence(cards, allow_2_in_sequence):
        return 'sequence'
    if is_triple(cards):
        return 'triple'
    if is_pair(cards):
        return 'pair'
    if is_single(cards):
        return 'single'
    return None
