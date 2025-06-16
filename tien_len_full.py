# tien_len_full.py
"""Tiến Lên full game implementation.

This module contains a minimal command line version of the Vietnamese card game
**Tiến Lên** along with a very small AI.  The implementation is intentionally
compact so that it can be easily read and used in tests.  A few key design
decisions:

* The module logs actions to ``tien_len_game.log`` for easier debugging.
* Only the human player is forbidden from passing on the very first turn when
  they hold the ``3♠``.  This mirrors the behaviour of the original proof of
  concept from which this repository was created.
* The :class:`Game` class encapsulates all state and can be reused by the GUI
  prototype found in ``gui.py``.
"""
import random
import datetime
import sys
import sound
from collections import Counter
from itertools import combinations

# ---------------------------------------------------------------------------
# Logging utilities
# ---------------------------------------------------------------------------

# All game actions are appended to this file.  Keeping the log simple avoids any
# extra dependencies while still providing insight when running tests or the
# GUI.
LOG_FILE = 'tien_len_game.log'

def log_action(action: str) -> None:
    """Append a timestamped entry to the log file."""

    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{ts}] {action}\n")

# Card constants
# Mapping from suit symbol to its full name.  The order of ``SUITS`` and
# ``RANKS`` defines the sorting used when displaying hands.
SUIT_SYMBOLS = {'♠': 'Spades', '♥': 'Hearts', '♦': 'Diamonds', '♣': 'Clubs'}
SUITS = list(SUIT_SYMBOLS.values())
RANKS = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']

# Global rule toggles
# ``ALLOW_2_IN_SEQUENCE`` controls whether suited sequences may contain a 2.
# The default preserves the house rule used by the tests which forbids 2s
# in sequences.
ALLOW_2_IN_SEQUENCE = False

# Rough ranking used by the very simple AI to choose which move to play.  Higher
# values are better.
TYPE_PRIORITY = {'bomb': 5, 'sequence': 4, 'triple': 3, 'pair': 2, 'single': 1}

class Card:
    """Simple container for a playing card."""

    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank

    def __repr__(self) -> str:
        """Return the short form ``<rank><symbol>`` used throughout the game."""

        symbol = next((s for s, r in SUIT_SYMBOLS.items() if r == self.suit), '?')
        return f"{self.rank}{symbol}"

class Deck:
    """A standard 52-card deck."""

    def __init__(self) -> None:
        # Generate cards in canonical order so tests can seed ``random`` and
        # reproduce games deterministically.
        self.cards = [Card(s, r) for s in SUITS for r in RANKS]

    def shuffle(self) -> None:
        """Shuffle the deck in place."""

        random.shuffle(self.cards)

    def deal(self, n: int):
        """Deal ``n`` hands as evenly as possible."""

        size = len(self.cards) // n
        return [self.cards[i * size : (i + 1) * size] for i in range(n)]

# ---------------------------------------------------------------------------
# Combination detection helpers
# ---------------------------------------------------------------------------

# The following functions recognise the basic valid combinations used in the
# game.  Each function accepts a list of :class:`Card` objects and returns a
# boolean indicating whether the list forms that combination.

def is_single(cards) -> bool:
    """Return ``True`` if the list contains exactly one card."""

    return len(cards) == 1

def is_pair(cards) -> bool:
    """Return ``True`` if the list is two cards of the same rank."""

    return len(cards) == 2 and cards[0].rank == cards[1].rank

def is_triple(cards) -> bool:
    """Return ``True`` if the list is three cards of the same rank."""

    return len(cards) == 3 and len({c.rank for c in cards}) == 1

def is_bomb(cards) -> bool:
    """Return ``True`` if the list is four cards of the same rank."""

    return len(cards) == 4 and len({c.rank for c in cards}) == 1

def is_sequence(cards) -> bool:
    """Return ``True`` if the cards form a suited consecutive sequence."""

    if len(cards) < 3:
        return False
    # Optionally disallow sequences containing a 2
    if not ALLOW_2_IN_SEQUENCE and any(c.rank == '2' for c in cards):
        return False
    # All cards must share the same suit
    if len({c.suit for c in cards}) != 1:
        return False
    idx = sorted(RANKS.index(c.rank) for c in cards)
    return all(idx[i] + 1 == idx[i + 1] for i in range(len(idx) - 1))

def detect_combo(cards):
    """Return the combo type for ``cards`` or ``None`` if invalid."""

    if is_bomb(cards):
        return 'bomb'
    if is_sequence(cards):
        return 'sequence'
    if is_triple(cards):
        return 'triple'
    if is_pair(cards):
        return 'pair'
    if is_single(cards):
        return 'single'
    return None

class Player:
    """Represents a human or AI participant."""

    def __init__(self, name: str, is_human: bool = False) -> None:
        self.name = name
        self.hand: list[Card] = []
        self.is_human = is_human

    def sort_hand(self) -> None:
        """Sort the player's hand by rank then suit."""

        self.hand.sort(key=lambda c: (RANKS.index(c.rank), SUITS.index(c.suit)))

    def find_bombs(self):
        """Return all four-of-a-kind sets in the player's hand."""

        cnt = Counter(c.rank for c in self.hand)
        return [[c for c in self.hand if c.rank == r] for r, v in cnt.items() if v == 4]

class Game:
    """Encapsulates the rules and state of a single game."""

    def __init__(self) -> None:
        """Initialise a new game instance."""

        # Create one human player followed by three AI opponents.
        self.players = [Player('Player', True)] + [Player(f'AI {i+1}') for i in range(3)]
        self.deck = Deck()
        self.pile: list[tuple[Player, list[Card]]] = []
        self.current_idx = 0
        self.first_turn = True
        self.start_idx = 0
        self.pass_count = 0
        self.current_combo: list[Card] | None = None
        self.history: list[tuple[int, str]] = []
        self.move_log: dict[int, list[tuple[str, int, list[Card]]]] = {}
        self.round_states: dict[int, str] = {}
        self.current_round = 1
        self.scores: dict[str, int] = {p.name: 0 for p in self.players}
        # AI difficulty tier and numeric multiplier
        self.ai_level = "Normal"
        self.ai_difficulty = 1.0

    def set_ai_level(self, level: str) -> None:
        """Set difficulty tier and adjust internal multiplier."""

        mapping = {"Easy": 0.5, "Normal": 1.0, "Hard": 2.0}
        self.ai_level = level
        self.ai_difficulty = mapping.get(level, 1.0)

    def setup(self):
        """Shuffle, deal and determine the starting player."""

        self.history.clear()
        self.move_log.clear()
        self.round_states.clear()
        self.current_round = 1

        self.deck.shuffle()
        sound.play("shuffle")
        hands = self.deck.deal(len(self.players))
        for p, h in zip(self.players, hands):
            # Assign and sort each player's hand
            p.hand = h
            p.sort_hand()
            # Log any four-of-a-kind sets for debugging
            b = p.find_bombs()
            if b:
                print(f"{p.name} bombs: {b}")
                log_action(f"{p.name} bombs: {b}")

        # The player holding the 3♠ must start the game
        for i, p in enumerate(self.players):
            if any(c.rank == '3' and c.suit == 'Spades' for c in p.hand):
                self.current_idx = i
                self.start_idx = i
                print(f"{p.name} starts (holds 3♠)")
                log_action(f"Start: {p.name}")
                break

        # Save state for replay of round 1
        self.round_states[self.current_round] = self.to_json()

    def is_valid(self, player, cards, current):
        """Validate ``cards`` against the current pile.

        Parameters
        ----------
        player : Player
            The player attempting the move.
        cards : list[Card]
            The cards they wish to play.  An empty list represents a pass.
        current : list[Card] | None
            The combination currently on the pile.
        """

        # Prevent passing on the opening turn if you started the game
        if not cards:
            if self.first_turn and self.current_idx == self.start_idx:
                return False, 'Must include 3♠ first'
            return True, ''

        combo = detect_combo(cards)
        if not combo:
            return False, 'Invalid combo'

        # The starting player must include the 3♠ in their very first play
        if self.first_turn and self.current_idx == self.start_idx:
            if not any(c.rank == '3' and c.suit == 'Spades' for c in cards):
                return False, 'Must include 3♠ first'

        # If the pile is empty any combo is valid at this point
        if not current:
            return True, ''

        prev = detect_combo(current)

        # Bombs beat everything except a higher bomb
        if combo == 'bomb' and prev != 'bomb':
            return True, ''

        # Otherwise combos must match type and length and be higher in rank
        if combo == prev and len(cards) == len(current):
            if max(RANKS.index(c.rank) for c in cards) > max(RANKS.index(c.rank) for c in current):
                return True, ''

        return False, 'Does not beat current'

    def parse_input(self, inp, hand):
        """Parse user input from the CLI into game commands."""

        s = inp.strip().lower()
        if s in ['pass', 'help', 'quit', 'hint']:
            # These commands do not reference any cards
            return s, []

        parts = inp.strip().split()
        cards = []
        for p in parts:
            if any(sym in p for sym in SUIT_SYMBOLS):
                # Card specified in ``<rank><symbol>`` form, e.g. ``3♠``
                rank, sym = p[:-1], p[-1]
                suit = SUIT_SYMBOLS.get(sym)
                found = [c for c in hand if c.rank == rank and c.suit == suit]
                if not found:
                    return 'error', f"Card {p} not in hand"
                card = found[0]
            else:
                # Card specified by 1-based index into the hand listing
                try:
                    idx = int(p) - 1
                    if idx < 0 or idx >= len(hand):
                        return 'error', 'Invalid index'
                    card = hand[idx]
                except ValueError:
                    return 'error', 'Invalid index'

            if card in cards:
                return 'error', 'Duplicate card'
            cards.append(card)

        return 'play', cards

    def hint(self, current):
        """Return a simple hint for the human player."""

        for c in self.players[0].hand:
            ok, _ = self.is_valid(self.players[0], [c], current)
            if ok:
                return [c]
        return []

    def cli_input(self, current):
        """Prompt the human player for a move on the command line."""

        player = self.players[self.current_idx]
        while True:
            try:
                inp = input("Enter cards or 'pass','hint','help','quit': ")
            except OSError:
                print('Input unsupported; defaulting to pass')
                return []
            cmd, res = self.parse_input(inp, player.hand)
            if cmd == 'quit':
                print('Exiting.')
                log_action('Game quit')
                sys.exit()
            if cmd == 'help':
                print("Commands: pass, hint, quit, or list card numbers/notation")
                continue
            if cmd == 'hint':
                print(f"Hint: {self.hint(current)}")
                continue
            if cmd == 'pass':
                if player.is_human and self.first_turn and self.current_idx == self.start_idx:
                    print('You must play a combo including 3♠ on your first turn; cannot pass.')
                    continue
                return []
            if cmd == 'error':
                print(res)
                continue
            if cmd == 'play':
                cards = res
                ok, msg = self.is_valid(player, cards, current)
                if ok:
                    return cards
                print(f"Invalid: {msg}")

    # AI helper functions
    def generate_valid_moves(self, player, current):
        """Return every playable move for ``player`` given ``current``."""

        moves = []
        for n in range(1, len(player.hand) + 1):
            for combo_cards in combinations(player.hand, n):
                lst = list(combo_cards)
                ok, _ = self.is_valid(player, lst, current)
                if ok:
                    moves.append(lst)
        return moves

    def score_move(self, player, move, current):
        """Heuristic scoring used by the AI when comparing moves."""

        t = detect_combo(move)
        base = TYPE_PRIORITY.get(t, 0)
        rank_val = max(RANKS.index(c.rank) for c in move)
        remaining = [c for c in player.hand if c not in move]
        finish = 1 if not remaining else 0
        diff = getattr(self, "ai_difficulty", 1.0)
        if self.ai_level == "Hard":
            low_cards = -sum(RANKS.index(c.rank) for c in remaining)
            return (base, finish * diff, rank_val * diff, low_cards)
        return (base, finish * diff, rank_val * diff)

    def ai_play(self, current):
        """Choose a move for the current AI player."""

        p = self.players[self.current_idx]
        moves = self.generate_valid_moves(p, current)
        if not moves:
            return []
        if self.ai_level == "Easy":
            return random.choice(moves)
        return max(moves, key=lambda m: self.score_move(p, m, current))

    # Display functions
    def display_pile(self):
        """Print the current pile to stdout."""

        if not self.pile:
            print('Pile: empty')
        else:
            p, c = self.pile[-1]
            print(f"Pile: {p.name} -> {c} ({detect_combo(c)})")

    def display_hand(self, player):
        """Print ``player``'s hand with 1-based indices."""

        print(f"\n{player.name}'s hand:")
        for i, c in enumerate(player.hand, 1):
            print(f" {i}:{c}")

    def display_overview(self):
        """Show how many cards each opponent has left."""

        print("Opponents' cards:")
        for p in self.players[1:]:
            print(f" {p.name}: {len(p.hand)}")

    # Round and turn processing
    def reset_pile(self):
        """Clear the pile after everyone has passed."""

        print('All passed. Resetting pile.')
        self.summary_round()
        self.pile.clear()
        self.current_combo = None
        self.pass_count = 0
        self.current_round += 1
        # Save state for the new round so it can be replayed later
        self.round_states[self.current_round] = self.to_json()
        self.move_log.setdefault(self.current_round, [])

    def summary_round(self):
        """Print a short summary of the round that just ended."""

        print('\n-- Round Summary --')
        for p, c in self.pile:
            print(f" {p.name}: {c}")
        self.display_overview()
        print('--')
        log_action(f"Round summary: {self.pile}")

    def get_rankings(self) -> list[tuple[str, int]]:
        """Return players sorted by fewest cards remaining."""

        return sorted(
            [(p.name, len(p.hand)) for p in self.players], key=lambda x: x[1]
        )

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def _card_to_dict(self, c: Card) -> dict:
        return {"suit": c.suit, "rank": c.rank}

    def _card_from_dict(self, d: dict) -> Card:
        return Card(d["suit"], d["rank"])

    def to_json(self) -> str:
        """Return a JSON string representing the current game state."""

        import json

        data = {
            "players": [
                {
                    "name": p.name,
                    "is_human": p.is_human,
                    "hand": [self._card_to_dict(c) for c in p.hand],
                }
                for p in self.players
            ],
            "pile": [
                {
                    "player": self.players.index(pl),
                    "cards": [self._card_to_dict(c) for c in cards],
                }
                for pl, cards in self.pile
            ],
            "current_idx": self.current_idx,
            "start_idx": self.start_idx,
            "first_turn": self.first_turn,
            "pass_count": self.pass_count,
            "current_combo": [
                self._card_to_dict(c) for c in self.current_combo
            ]
            if self.current_combo
            else None,
            "history": self.history,
            "current_round": self.current_round,
            "scores": self.scores,
        }
        return json.dumps(data)

    def from_json(self, s: str) -> None:
        """Restore game state from ``s`` (a JSON string)."""

        import json

        data = json.loads(s)
        self.players = [
            Player(d["name"], d.get("is_human", False)) for d in data["players"]
        ]
        for p, d in zip(self.players, data["players"]):
            p.hand = [self._card_from_dict(c) for c in d.get("hand", [])]
        self.pile = []
        for item in data.get("pile", []):
            idx = item.get("player")
            player = (
                self.players[idx]
                if isinstance(idx, int)
                else next(p for p in self.players if p.name == idx)
            )
            cards = [self._card_from_dict(c) for c in item.get("cards", [])]
            self.pile.append((player, cards))
        self.current_idx = data.get("current_idx", 0)
        self.start_idx = data.get("start_idx", 0)
        self.first_turn = data.get("first_turn", True)
        self.pass_count = data.get("pass_count", 0)
        combo = data.get("current_combo")
        self.current_combo = [self._card_from_dict(c) for c in combo] if combo else None
        self.history = [tuple(h) for h in data.get("history", [])]
        self.current_round = data.get("current_round", 1)
        self.scores = data.get("scores", {p.name: 0 for p in self.players})
        self.move_log.clear()
        self.round_states.clear()

    # New helper methods -------------------------------------------------
    def process_play(self, player: Player, cards: list[Card]) -> bool:
        """Apply ``cards`` as ``player``'s move.

        Parameters
        ----------
        player : Player
            The player making the move. ``cards`` must already be validated.
        cards : list[Card]
            The cards being played.

        Returns
        -------
        bool
            ``True`` if the player has emptied their hand and therefore won.
        """

        if self.first_turn and self.current_idx == self.start_idx:
            # Opening player has now made their initial move
            self.first_turn = False

        self.pass_count = 0
        self.history.append((self.current_round, f"{player.name} plays {cards}"))
        self.move_log.setdefault(self.current_round, []).append(
            ("play", self.current_idx, list(cards))
        )
        for c in cards:
            player.hand.remove(c)
        self.pile.append((player, cards))
        self.current_combo = cards
        print(f"{player.name} plays {cards}\n")

        if not player.hand:
            print(f"{player.name} wins!")
            log_action(f"Winner: {player.name}")
            return True
        return False

    def process_pass(self, player: Player) -> None:
        """Handle ``player`` passing their turn."""

        self.pass_count += 1
        self.history.append((self.current_round, f"{player.name} passes"))
        self.move_log.setdefault(self.current_round, []).append(
            ("pass", self.current_idx, [])
        )
        print(f"{player.name} passes\n")
        active = sum(1 for x in self.players if x.hand)
        if self.current_combo and self.pass_count >= active - 1:
            self.reset_pile()

    def handle_pass(self) -> bool:
        """Validate and process a pass for the current player."""

        player = self.players[self.current_idx]
        ok, msg = self.is_valid(player, [], self.current_combo)
        if not ok:
            print(f"Invalid pass: {msg}")
            return False

        self.process_pass(player)
        self.next_turn()
        return False

    def handle_turn(self):
        """Process the current player's turn.

        Returns ``True`` when the game has been won, otherwise ``False``.
        """

        p = self.players[self.current_idx]
        if not p.hand:
            # Skip eliminated players
            self.next_turn()
            return False

        print(f"\n-- {p.name}'s turn --")
        self.display_pile()
        self.display_overview()

        if p.is_human:
            cards = self.cli_input(self.current_combo)
        else:
            cards = self.ai_play(self.current_combo)

        ok, _ = self.is_valid(p, cards, self.current_combo)
        if not ok:
            cards = []
            if not p.is_human:
                print('Invalid AI move, passing')

        if cards:
            if self.process_play(p, cards):
                return True
        else:
            self.process_pass(p)

        self.next_turn()
        return False

    def play(self):
        """Run the game loop until a player wins."""

        self.setup()
        while not self.handle_turn():
            pass

    def next_turn(self):
        """Advance ``current_idx`` to the next active player."""

        self.current_idx = (self.current_idx + 1) % len(self.players)

if __name__ == '__main__':
    Game().play()
