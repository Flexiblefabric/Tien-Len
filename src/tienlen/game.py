from __future__ import annotations
# tien_len_full.py
"""Tiến Lên full game implementation.

This module contains a minimal command line version of the Vietnamese card game
**Tiến Lên** along with a very small AI.  The implementation is intentionally
compact so that it can be easily read and used in tests.  A few key design
decisions:

* The module logs actions to ``tien_len_game.log`` for easier debugging.
  Log rotation prevents this file from growing without bound.
* Only the human player is forbidden from passing on the very first turn when
  they hold the ``3♠`` (or ``3♥`` when suit ranking is flipped).  This mirrors
  the behaviour of the original proof of
  concept from which this repository was created.
* The :class:`Game` class encapsulates all state and can be reused by the GUI
  implemented in ``tienlen_gui``.
"""

import random
import sys
import argparse
import logging
from logging.handlers import RotatingFileHandler
from . import sound
from collections import Counter
from itertools import combinations, product
from typing import Optional
from . import rules

# ---------------------------------------------------------------------------
# Logging utilities
# ---------------------------------------------------------------------------

# All game actions are appended to this file.  Keeping the log simple avoids any
# extra dependencies while still providing insight when running tests or the
# GUI.
LOG_FILE = 'tien_len_game.log'

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log_action(action: str) -> None:
    """Log a game action."""

    logger.info(action)


# Card constants are defined in :mod:`tienlen.rules` along with helper
# functions used throughout the game logic.
SUIT_SYMBOLS = rules.SUIT_SYMBOLS
SUITS = rules.SUITS
RANKS = rules.RANKS
TYPE_PRIORITY = rules.TYPE_PRIORITY
AI_NAMES = rules.AI_NAMES
suit_index = rules.suit_index
opening_suit = rules.opening_suit
opening_card_str = rules.opening_card_str


class Card:
    """Simple container for a playing card."""

    def __init__(self, suit: str, rank: str):
        """Initialise a card from ``(suit, rank)``.

        Arguments are provided in this order so they mirror the short
        notation used throughout the codebase.
        """

        self.suit = suit
        self.rank = rank

    def __repr__(self) -> str:
        """Return the short form ``<rank><symbol>`` used throughout the game."""

        symbol = next((s for s, r in SUIT_SYMBOLS.items() if r == self.suit), '?')
        return f"{self.rank}{symbol}"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.suit == other.suit and self.rank == other.rank

    def __hash__(self) -> int:
        return hash((self.suit, self.rank))

    def to_dict(self) -> dict:
        """Return a ``dict`` representation of this card."""

        return {"suit": self.suit, "rank": self.rank}

    @staticmethod
    def from_dict(d: dict) -> "Card":
        """Create a :class:`Card` from ``d``."""

        return Card(d["suit"], d["rank"])


class Deck:
    """A standard 52-card deck."""

    def __init__(self, flip_suit_rank: bool = False) -> None:
        # Generate cards in canonical order so tests can seed ``random`` and
        # reproduce games deterministically.  Suit ordering respects the
        # ``flip_suit_rank`` rule.
        ordered = sorted(SUITS, key=lambda s: suit_index(s, flip_suit_rank))
        self.cards = [Card(s, r) for s in ordered for r in RANKS]

    def shuffle(self) -> None:
        """Shuffle the deck in place."""

        random.shuffle(self.cards)

    def deal(self, n: int):
        """Deal ``n`` hands as evenly as possible."""

        size = len(self.cards) // n
        return [self.cards[i * size:(i + 1) * size] for i in range(n)]

# ---------------------------------------------------------------------------
# Combination detection helpers
# ---------------------------------------------------------------------------

# The following functions recognise the basic valid combinations used in the
# game.  Each function accepts a list of :class:`Card` objects and returns a
# boolean indicating whether the list forms that combination.


is_single = rules.is_single
is_pair = rules.is_pair
is_triple = rules.is_triple
is_bomb = rules.is_bomb
is_sequence = rules.is_sequence
detect_combo = rules.detect_combo


class Player:
    """Represents a human or AI participant."""

    def __init__(self, name: str, is_human: bool = False) -> None:
        self.name = name
        self.hand: list[Card] = []
        self.is_human = is_human
        # Optional AI customisations that override global settings when set
        self.ai_level: Optional[str] = None
        self.ai_personality: Optional[str] = None

    def sort_hand(self, mode: str = "rank", flip_suit_rank: bool = False) -> None:
        """Sort the player's hand.

        Parameters
        ----------
        mode:
            ``"rank"`` to sort by rank then suit (default) or ``"suit"``
            to sort by suit then rank.
        """

        if mode == "suit":
            self.hand.sort(
                key=lambda c: (suit_index(c.suit, flip_suit_rank), RANKS.index(c.rank))
            )
        else:
            self.hand.sort(
                key=lambda c: (RANKS.index(c.rank), suit_index(c.suit, flip_suit_rank))
            )

    def find_bombs(self):
        """Return all four-of-a-kind sets in the player's hand."""

        cnt = Counter(c.rank for c in self.hand)
        return [[c for c in self.hand if c.rank == r] for r, v in cnt.items() if v == 4]


class Game:
    """Encapsulates the rules and state of a single game."""

    def __init__(
        self,
        allow_2_in_sequence: bool = False,
        flip_suit_rank: bool = False,
        bomb_override: bool = True,
        chain_cutting: bool = False,
        bomb_hierarchy: bool = True,
    ) -> None:
        """Initialise a new game instance."""

        self.allow_2_in_sequence = allow_2_in_sequence
        self.flip_suit_rank = flip_suit_rank
        self.bomb_override = bomb_override
        self.chain_cutting = chain_cutting
        self.bomb_hierarchy = bomb_hierarchy

        # Create one human player followed by three AI opponents chosen from a
        # predefined pool of names.
        used = random.sample(AI_NAMES, 3)
        self.players = [Player('Player', True)] + [Player(n) for n in used]
        self.deck = Deck(self.flip_suit_rank)
        self.pile: list[tuple[Player, list[Card]]] = []
        self.current_idx = 0
        self.first_turn = True
        self.start_idx = 0
        self.pass_count = 0
        self.current_combo: Optional[list[Card]] = None
        self.history: list[tuple[int, str]] = []
        # Log of moves in each round using simple serialisable card dictionaries
        self.move_log: dict[int, list[tuple[str, int, list[dict]]]] = {}
        self.round_states: dict[int, str] = {}
        self.current_round = 1
        self.scores: dict[str, int] = {p.name: 0 for p in self.players}
        # AI difficulty tier and numeric multiplier
        self.ai_level = "Normal"
        self.ai_difficulty = 1.0
        self.ai_depth = 1
        # Optional AI behaviour tweaks
        self.ai_personality = "balanced"
        self.ai_lookahead = False
        self.bluff_chance = 0.0
        # Snapshots of the game state for undo functionality
        self.snapshots: list[str] = []

    # ------------------------------------------------------------------
    # Helper wrappers using instance rule settings
    # ------------------------------------------------------------------
    def suit_index(self, suit: str) -> int:
        return suit_index(suit, self.flip_suit_rank)

    def opening_suit(self) -> str:
        return opening_suit(self.flip_suit_rank)

    def opening_card_str(self) -> str:
        return opening_card_str(self.flip_suit_rank)

    def set_ai_level(self, level: str) -> None:
        """Set difficulty tier and adjust internal multiplier."""

        mapping = {
            "Easy": 0.5,
            "Normal": 1.0,
            "Hard": 2.0,
            "Expert": 3.0,
            "Master": 4.0,
        }
        depth_map = {"Expert": 1, "Master": 2}
        self.ai_level = level
        self.ai_difficulty = mapping.get(level, 1.0)
        self.ai_depth = depth_map.get(level, self.ai_depth)

    def set_personality(self, name: str) -> None:
        """Configure AI personality traits."""

        name = name.lower()
        if name not in {"aggressive", "defensive", "random", "balanced"}:
            name = "balanced"
        self.ai_personality = name
        mapping = {
            "aggressive": 0.05,
            "defensive": 0.3,
            "random": 0.1,
            "balanced": 0.0,
        }
        self.bluff_chance = mapping.get(self.ai_personality, 0.0)

    # ------------------------------------------------------------------
    # Per-player AI configuration helpers
    # ------------------------------------------------------------------
    def _ai_level_for(self, player: Player) -> str:
        """Return the effective AI level for ``player``."""

        return player.ai_level or self.ai_level

    def _ai_personality_for(self, player: Player) -> str:
        """Return the effective AI personality for ``player``."""

        return player.ai_personality or self.ai_personality

    def set_player_ai_level(self, player_id, level: str) -> None:
        """Set the AI level for a specific player."""

        player = self._resolve_player(player_id)
        player.ai_level = level

    def set_player_personality(self, player_id, name: str) -> None:
        """Set the AI personality for a specific player."""

        player = self._resolve_player(player_id)
        player.ai_personality = name.lower() if name else None

    def _resolve_player(self, player_id) -> Player:
        """Return the :class:`Player` indicated by ``player_id``."""

        if isinstance(player_id, Player):
            return player_id
        if isinstance(player_id, int):
            return self.players[player_id]
        return next(p for p in self.players if p.name == player_id)

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
            p.sort_hand(flip_suit_rank=self.flip_suit_rank)
            # Log any four-of-a-kind sets for debugging
            b = p.find_bombs()
            if b:
                logger.info("%s bombs: %s", p.name, b)
                log_action(f"{p.name} bombs: {b}")

        # The player holding the 3♠ (or 3♥) must start the game
        for i, p in enumerate(self.players):
            if any(c.rank == '3' and c.suit == self.opening_suit() for c in p.hand):
                self.current_idx = i
                self.start_idx = i
                logger.info("%s starts (holds %s)", p.name, self.opening_card_str())
                log_action(f"Start: {p.name}")
                break

        # Save state for replay of round 1
        self.round_states[self.current_round] = self.to_json()
        # Initialise undo history with the starting state
        self.snapshots = [self.to_json()]

    def is_valid(self, player, cards, current):
        """Validate ``cards`` against the current pile.

        Parameters
        ----------
        player : Player
            The player attempting the move.
        cards : list[Card]
            The cards they wish to play.  An empty list represents a pass.
        current : Optional[list[Card]]
            The combination currently on the pile.
        """

        # Prevent passing on the opening turn if you started the game
        if not cards:
            if self.first_turn and self.current_idx == self.start_idx:
                return False, f'Must include {self.opening_card_str()} first'
            return True, ''

        combo = detect_combo(cards, self.allow_2_in_sequence)
        if not combo:
            return False, 'Invalid combo'

        # The starting player must include the required suit in their very first play
        if self.first_turn and self.current_idx == self.start_idx:
            if not any(c.rank == '3' and c.suit == self.opening_suit() for c in cards):
                return False, f'Must include {self.opening_card_str()} first'

        # If the pile is empty any combo is valid at this point
        if not current:
            return True, ''

        prev = detect_combo(current, self.allow_2_in_sequence)

        # Bomb behaviour depends on the optional rule toggle
        if combo == 'bomb' and prev != 'bomb':
            if self.bomb_override:
                return True, ''
            return False, 'Does not beat current'

        # Bomb hierarchy rule when both plays are bombs
        if combo == prev == 'bomb':
            if not self.bomb_hierarchy:
                return False, 'Does not beat current'
            new_val = max(RANKS.index(c.rank) for c in cards)
            cur_val = max(RANKS.index(c.rank) for c in current)
            if new_val > cur_val:
                return True, ''
            return False, 'Does not beat current'

        # Otherwise combos must match type and length and be higher in rank
        if combo == prev:
            if combo == 'sequence' and self.chain_cutting:
                if len(cards) >= len(current):
                    new_val = max(
                        (RANKS.index(c.rank), self.suit_index(c.suit))
                        for c in cards
                    )
                    cur_val = max(
                        (RANKS.index(c.rank), self.suit_index(c.suit))
                        for c in current
                    )
                    if new_val > cur_val:
                        return True, ''
            elif len(cards) == len(current):
                new_val = max(
                    (RANKS.index(c.rank), self.suit_index(c.suit)) for c in cards
                )
                cur_val = max(
                    (RANKS.index(c.rank), self.suit_index(c.suit)) for c in current
                )
                if new_val > cur_val:
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
        """Return a suggested move for the human player."""

        player = self.players[0]
        moves = self.generate_valid_moves(player, current)
        if not moves:
            return []

        # Evaluate moves using ``score_move`` but without any AI difficulty
        # modifiers so the recommendation remains neutral regardless of the
        # configured AI level.
        orig_level = getattr(self, "ai_level", "Normal")
        orig_diff = getattr(self, "ai_difficulty", 1.0)
        self.ai_level = "Normal"
        self.ai_difficulty = 1.0
        try:
            return max(moves, key=lambda m: self.score_move(player, m, current))
        finally:
            self.ai_level = orig_level
            self.ai_difficulty = orig_diff

    def cli_input(self, current):
        """Prompt the human player for a move on the command line."""

        player = self.players[self.current_idx]
        failures = 0
        while True:
            try:
                inp = input("Enter cards or 'pass','hint','help','quit': ")
            except OSError:
                logger.info('Input unsupported; defaulting to pass')
                return []
            cmd, res = self.parse_input(inp, player.hand)
            if cmd == 'quit':
                logger.info('Exiting.')
                log_action('Game quit')
                sys.exit()
            if cmd == 'help':
                logger.info("Commands: pass, hint, quit, or list card numbers/notation")
                continue
            if cmd == 'hint':
                logger.info("Hint: %s", self.hint(current))
                continue
            if cmd == 'pass':
                if player.is_human and self.first_turn and self.current_idx == self.start_idx:
                    logger.info(
                        'You must play a combo including %s on your first turn; cannot pass.',
                        self.opening_card_str(),
                    )
                    failures += 1
                    if failures == 3:
                        logger.info(
                            "Reminder: your opening play must contain %s. Example: '%s'",
                            self.opening_card_str(),
                            self.opening_card_str(),
                        )
                    continue
                return []
            if cmd == 'error':
                logger.info(str(res))
                if self.first_turn and self.current_idx == self.start_idx:
                    failures += 1
                    if failures == 3:
                        logger.info(
                            "Reminder: your opening play must contain %s. Example: '%s'",
                            self.opening_card_str(),
                            self.opening_card_str(),
                        )
                continue
            if cmd == 'play':
                cards = res
                ok, msg = self.is_valid(player, cards, current)
                if ok:
                    return cards
                logger.info("Invalid: %s", msg)
                if self.first_turn and self.current_idx == self.start_idx:
                    failures += 1
                    if failures == 3:
                        logger.info(
                            "Reminder: your opening play must contain %s. Example: '%s'",
                            self.opening_card_str(),
                            self.opening_card_str(),
                        )
                continue

    # AI helper functions
    def generate_valid_moves(self, player, current):
        """Return every playable move for ``player`` given ``current``."""

        moves: list[list[Card]] = []

        # Singles ---------------------------------------------------------
        for card in player.hand:
            ok, _ = self.is_valid(player, [card], current)
            if ok:
                moves.append([card])

        # Group cards by rank for pairs/triples/bombs --------------------
        rank_map: dict[str, list[Card]] = {}
        for card in player.hand:
            rank_map.setdefault(card.rank, []).append(card)

        for cards in rank_map.values():
            if len(cards) >= 2:
                for combo_cards in combinations(cards, 2):
                    lst = list(combo_cards)
                    ok, _ = self.is_valid(player, lst, current)
                    if ok:
                        moves.append(lst)
            if len(cards) >= 3:
                for combo_cards in combinations(cards, 3):
                    lst = list(combo_cards)
                    ok, _ = self.is_valid(player, lst, current)
                    if ok:
                        moves.append(lst)
            if len(cards) == 4:
                lst = list(cards)
                ok, _ = self.is_valid(player, lst, current)
                if ok:
                    moves.append(lst)

        # Sequences ------------------------------------------------------
        index_map: dict[int, list[Card]] = {}
        for card in player.hand:
            idx = RANKS.index(card.rank)
            index_map.setdefault(idx, []).append(card)

        sorted_indices = sorted(index_map.keys())
        for i, start in enumerate(sorted_indices):
            seq = [start]
            for j in range(i + 1, len(sorted_indices)):
                if sorted_indices[j] == seq[-1] + 1:
                    seq.append(sorted_indices[j])
                    if len(seq) >= 3:
                        if not self.allow_2_in_sequence and any(
                            RANKS[idx] == "2" for idx in seq
                        ):
                            continue
                        for combo_cards in product(*(index_map[k] for k in seq)):
                            lst = list(combo_cards)
                            ok, _ = self.is_valid(player, lst, current)
                            if ok:
                                moves.append(lst)
                else:
                    break

        return moves

    def score_move(self, player, move, current, lookahead=True):
        """Heuristic scoring used by the AI when comparing moves."""

        t = detect_combo(move, self.allow_2_in_sequence)
        base = TYPE_PRIORITY.get(t, 0)
        rank_val = max(RANKS.index(c.rank) for c in move)
        remaining = [c for c in player.hand if c not in move]
        finish = 1 if not remaining else 0
        level = self._ai_level_for(player)
        mapping = {
            "Easy": 0.5,
            "Normal": 1.0,
            "Hard": 2.0,
            "Expert": 3.0,
            "Master": 4.0,
        }
        diff = mapping.get(level, 1.0)
        low_cards = 0
        if level == "Hard":
            low_cards = -sum(RANKS.index(c.rank) for c in remaining)
            if getattr(self, "ai_lookahead", False) and lookahead:
                temp = Player(player.name)
                temp.hand = remaining
                next_moves = self.generate_valid_moves(temp, move)
                if next_moves:
                    best = max(
                        next_moves,
                        key=lambda m: self.score_move(temp, m, move, False)
                    )
                    look = sum(self.score_move(temp, best, move, False)) / 10.0
                    low_cards += look

        personality = self._ai_personality_for(player)
        rank_weight = 1.0
        finish_weight = 1.0
        if personality == "aggressive":
            rank_weight = 1.5
            finish_weight = 1.2
        elif personality == "defensive":
            rank_weight = 0.7
            finish_weight = 0.8
        return (
            base,
            finish * diff * finish_weight,
            rank_val * diff * rank_weight,
            low_cards,
        )

    # ------------------------------------------------------------------
    # Minimax helper used for the Expert AI level
    # ------------------------------------------------------------------
    def _minimax(self, depth: int, max_name: str, mc_threshold: int = 3) -> float:
        """Return a minimax evaluation score."""

        if depth > mc_threshold:
            return self._monte_carlo_eval(max_name)

        if depth == 0 or all(not p.hand for p in self.players):
            player = next(p for p in self.players if p.name == max_name)
            return -float(len(player.hand))

        current_player = self.players[self.current_idx]
        moves = self.generate_valid_moves(current_player, self.current_combo)
        if not moves:
            g = self._clone()
            g.process_pass(g.players[g.current_idx])
            g.next_turn()
            return g._minimax(depth - 1, max_name, mc_threshold)

        if current_player.name == max_name:
            best = -float("inf")
            for mv in moves:
                g = self._clone()
                g.process_play(g.players[g.current_idx], mv)
                g.next_turn()
                val = g._minimax(depth - 1, max_name, mc_threshold)
                best = max(best, val)
            return best
        else:
            best = float("inf")
            for mv in moves:
                g = self._clone()
                g.process_play(g.players[g.current_idx], mv)
                g.next_turn()
                val = g._minimax(depth - 1, max_name, mc_threshold)
                best = min(best, val)
            return best

    def _minimax_decision(
        self, player, depth: int, mc_threshold: int = 3
    ) -> list[Card]:
        """Choose a move using a depth-limited minimax search."""

        moves = self.generate_valid_moves(player, self.current_combo)
        if not moves:
            return []

        best_move = moves[0]
        best_score = -float("inf")
        for mv in moves:
            g = self._clone()
            g.process_play(g.players[g.current_idx], mv)
            g.next_turn()
            score = g._minimax(depth - 1, player.name, mc_threshold)
            if score > best_score:
                best_score = score
                best_move = mv
        return best_move

    def ai_play(self, current):
        """Choose a move for the current AI player."""

        p = self.players[self.current_idx]
        moves = self.generate_valid_moves(p, current)
        if not moves:
            return []

        personality = self._ai_personality_for(p)
        # Skip bluffing when using the "random" personality so tests are
        # deterministic and the AI always makes a play.
        if personality != "random" and random.random() < getattr(self, "bluff_chance", 0.0):
            return []

        level = self._ai_level_for(p)
        if level == "Easy" or personality == "random":
            return random.choice(moves)

        if level in {"Expert", "Master"}:
            depth_map = {"Expert": 1, "Master": 2}
            depth = depth_map.get(level, self.ai_depth)
            return self._minimax_decision(p, depth)

        return max(moves, key=lambda m: self.score_move(p, m, current))

    # Display functions
    def display_pile(self):
        """Print the current pile to stdout."""

        if not self.pile:
            logger.info('Pile: empty')
        else:
            p, c = self.pile[-1]
            logger.info("Pile: %s -> %s (%s)", p.name, c, detect_combo(c, self.allow_2_in_sequence))

    def display_hand(self, player):
        """Print ``player``'s hand with 1-based indices."""

        logger.info("\n%s's hand:", player.name)
        for i, c in enumerate(player.hand, 1):
            logger.info(" %d:%s", i, c)

    def display_overview(self):
        """Show how many cards each opponent has left."""

        logger.info("Opponents' cards:")
        for p in self.players[1:]:
            logger.info(" %s: %d", p.name, len(p.hand))

    # Round and turn processing
    def reset_pile(self):
        """Clear the pile after everyone has passed."""

        logger.info('All passed. Resetting pile.')
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

        logger.info('\n-- Round Summary --')
        for p, c in self.pile:
            logger.info(" %s: %s", p.name, c)

        # Determine who played the last non-pass move
        winner = None
        combo = None
        if self.pile:
            winner, combo = self.pile[-1]
            logger.info("%s won the round with %s", winner.name, combo)
            logger.info("%s will start the next round", winner.name)

        self.display_overview()
        logger.info('--')
        log_action(f"Round summary: {self.pile}")

    def get_rankings(self) -> list[tuple[str, int]]:
        """Return players sorted by fewest cards remaining."""

        return sorted(
            [(p.name, len(p.hand)) for p in self.players], key=lambda x: x[1]
        )

    def get_last_hands(self) -> list[tuple[str, list[Card]]]:
        """Return each player's most recent played hand from ``move_log``."""

        last: dict[int, list[Card]] = {}
        for rnd in sorted(self.move_log):
            for action, idx, cards in self.move_log[rnd]:
                if action == "play":
                    last[idx] = [Card.from_dict(c) for c in cards]
        return [(p.name, last.get(i, [])) for i, p in enumerate(self.players)]

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a dictionary representing the current game state."""

        return {
            "players": [
                {
                    "name": p.name,
                    "is_human": p.is_human,
                    "hand": [c.to_dict() for c in p.hand],
                    "ai_level": p.ai_level,
                    "ai_personality": p.ai_personality,
                }
                for p in self.players
            ],
            "pile": [
                {
                    "player": self.players.index(pl),
                    "cards": [c.to_dict() for c in cards],
                }
                for pl, cards in self.pile
            ],
            "current_idx": self.current_idx,
            "start_idx": self.start_idx,
            "first_turn": self.first_turn,
            "pass_count": self.pass_count,
            "current_combo": [c.to_dict() for c in self.current_combo]
            if self.current_combo
            else None,
            "history": self.history,
            "current_round": self.current_round,
            "scores": self.scores,
            "allow_2_in_sequence": self.allow_2_in_sequence,
            "flip_suit_rank": self.flip_suit_rank,
            "bomb_override": self.bomb_override,
            "chain_cutting": self.chain_cutting,
            "bomb_hierarchy": self.bomb_hierarchy,
        }

    def from_dict(self, data: dict) -> None:
        """Restore game state from ``data`` (a dictionary)."""

        self.players = [
            Player(d["name"], d.get("is_human", False)) for d in data["players"]
        ]
        for p, dct in zip(self.players, data["players"]):
            p.hand = [Card.from_dict(c) for c in dct.get("hand", [])]
            p.ai_level = dct.get("ai_level")
            p.ai_personality = dct.get("ai_personality")
        self.pile = []
        for item in data.get("pile", []):
            idx = item.get("player")
            player = (
                self.players[idx]
                if isinstance(idx, int)
                else next(pl for pl in self.players if pl.name == idx)
            )
            cards = [Card.from_dict(c) for c in item.get("cards", [])]
            self.pile.append((player, cards))
        self.current_idx = data.get("current_idx", 0)
        self.start_idx = data.get("start_idx", 0)
        self.first_turn = data.get("first_turn", True)
        self.pass_count = data.get("pass_count", 0)
        combo = data.get("current_combo")
        self.current_combo = [Card.from_dict(c) for c in combo] if combo else None
        self.history = [tuple(h) for h in data.get("history", [])]
        self.current_round = data.get("current_round", 1)
        self.scores = data.get("scores", {p.name: 0 for p in self.players})
        self.move_log.clear()
        self.round_states.clear()
        self.allow_2_in_sequence = data.get("allow_2_in_sequence", self.allow_2_in_sequence)
        self.flip_suit_rank = data.get("flip_suit_rank", self.flip_suit_rank)
        self.bomb_override = data.get("bomb_override", self.bomb_override)
        self.chain_cutting = data.get("chain_cutting", self.chain_cutting)
        self.bomb_hierarchy = data.get("bomb_hierarchy", self.bomb_hierarchy)

    def to_json(self) -> str:
        """Return a JSON string representing the current game state."""

        import json

        return json.dumps(self.to_dict())

    def from_json(self, s: str) -> None:
        """Restore game state from ``s`` (a JSON string)."""

        import json

        self.from_dict(json.loads(s))

    def _clone(self) -> "Game":
        """Return a deep copy of the current game state."""

        g = Game(
            allow_2_in_sequence=self.allow_2_in_sequence,
            flip_suit_rank=self.flip_suit_rank,
            bomb_override=self.bomb_override,
            chain_cutting=self.chain_cutting,
            bomb_hierarchy=self.bomb_hierarchy,
        )
        g.from_dict(self.to_dict())
        g.ai_level = self.ai_level
        g.ai_difficulty = self.ai_difficulty
        g.ai_depth = self.ai_depth
        g.ai_personality = self.ai_personality
        g.ai_lookahead = self.ai_lookahead
        return g

    def _monte_carlo_eval(self, max_name: str, samples: int = 10) -> float:
        """Approximate a state evaluation via random playouts."""

        total = 0.0
        for _ in range(samples):
            g = self._clone()
            while True:
                if any(not p.hand for p in g.players):
                    break
                pl = g.players[g.current_idx]
                moves = g.generate_valid_moves(pl, g.current_combo)
                if moves:
                    mv = random.choice(moves)
                    if g.process_play(pl, mv):
                        break
                else:
                    g.process_pass(pl)
                g.next_turn()
            player = next(p for p in g.players if p.name == max_name)
            total += -float(len(player.hand))
        return total / samples

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
            ("play", self.current_idx, [c.to_dict() for c in cards])
        )
        for c in cards:
            if c not in player.hand:
                raise ValueError(f"Card {c} not in hand")
            player.hand.remove(c)
        self.pile.append((player, cards))
        self.current_combo = cards
        logger.info("%s plays %s", player.name, cards)

        winner = False
        if not player.hand:
            logger.info("%s wins!", player.name)
            log_action(f"Winner: {player.name}")
            winner = True

        # Record snapshot after the move
        self.snapshots.append(self.to_json())
        return winner

    def process_pass(self, player: Player) -> None:
        """Handle ``player`` passing their turn."""

        self.pass_count += 1
        self.history.append((self.current_round, f"{player.name} passes"))
        self.move_log.setdefault(self.current_round, []).append(
            ("pass", self.current_idx, [])
        )
        logger.info("%s passes", player.name)
        active = sum(1 for x in self.players if x.hand)
        if self.current_combo and self.pass_count >= active - 1:
            self.reset_pile()

        # Record snapshot after the pass (and any pile reset)
        self.snapshots.append(self.to_json())

    def undo_last(self) -> bool:
        """Revert the game state to the previous snapshot."""

        if len(self.snapshots) <= 1:
            return False
        # Discard current state
        self.snapshots.pop()
        prev = self.snapshots[-1]
        self.from_json(prev)
        return True

    def handle_pass(self) -> bool:
        """Validate and process a pass for the current player."""

        player = self.players[self.current_idx]
        ok, msg = self.is_valid(player, [], self.current_combo)
        if not ok:
            logger.info("Invalid pass: %s", msg)
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

        logger.info("\n-- %s's turn --", p.name)
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
                logger.info('Invalid AI move, passing')

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


def create_parser() -> argparse.ArgumentParser:
    """Return the command line argument parser used by the CLI."""

    parser = argparse.ArgumentParser(description='Play Tiến Lên in the terminal')
    parser.add_argument(
        '--ai',
        default='Normal',
        choices=['Easy', 'Normal', 'Hard', 'Expert', 'Master'],
        help='AI difficulty level',
    )
    parser.add_argument(
        '--personality',
        default='balanced',
        choices=['aggressive', 'defensive', 'balanced', 'random'],
        help='AI personality style',
    )
    parser.add_argument(
        '--lookahead',
        action='store_true',
        help='Enable AI lookahead when scoring moves',
    )
    parser.add_argument(
        '--depth',
        type=int,
        default=1,
        help='Search depth for Expert/Master AI',
    )
    return parser


def main(argv: Optional[list[str]] = None) -> Game:
    """Run the CLI game and return the :class:`Game` instance used."""

    parser = create_parser()
    args = parser.parse_args(argv)

    game = Game()
    game.set_ai_level(args.ai)
    game.set_personality(args.personality)
    game.ai_lookahead = args.lookahead
    game.ai_depth = args.depth
    game.play()
    return game


if __name__ == '__main__':
    main()
