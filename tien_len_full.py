# tien_len_full.py
"""
Tiến Lên full game with refactored AI, modular play loop, and full CLI utilities.
Fixed first-turn pass rule: player cannot pass on first turn if holding 3♠.
"""
import random
import datetime
import sys
from collections import Counter
from itertools import combinations

# Logging setup
LOG_FILE = 'tien_len_game.log'

def log_action(action: str):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{ts}] {action}\n")

# Card constants
SUIT_SYMBOLS = {'♠':'Spades', '♥':'Hearts', '♦':'Diamonds', '♣':'Clubs'}
SUITS = list(SUIT_SYMBOLS.values())
RANKS = ['3','4','5','6','7','8','9','10','J','Q','K','A','2']
TYPE_PRIORITY = {'bomb':5, 'sequence':4, 'triple':3, 'pair':2, 'single':1}

class Card:
    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank
    def __repr__(self) -> str:
        symbol = next((s for s,r in SUIT_SYMBOLS.items() if r == self.suit), '?')
        return f"{self.rank}{symbol}"

class Deck:
    def __init__(self):
        self.cards = [Card(s, r) for s in SUITS for r in RANKS]
    def shuffle(self): random.shuffle(self.cards)
    def deal(self, n):
        size = len(self.cards)//n
        return [self.cards[i*size:(i+1)*size] for i in range(n)]

# Combo logic

def is_single(cards): return len(cards)==1

def is_pair(cards): return len(cards)==2 and cards[0].rank==cards[1].rank

def is_triple(cards): return len(cards)==3 and len({c.rank for c in cards})==1

def is_bomb(cards): return len(cards)==4 and len({c.rank for c in cards})==1

def is_sequence(cards):
    if len(cards)<3: return False
    if any(c.rank=='2' for c in cards): return False
    if len({c.suit for c in cards})!=1: return False
    idx = sorted(RANKS.index(c.rank) for c in cards)
    return all(idx[i]+1==idx[i+1] for i in range(len(idx)-1))

def detect_combo(cards):
    if is_bomb(cards): return 'bomb'
    if is_sequence(cards): return 'sequence'
    if is_triple(cards): return 'triple'
    if is_pair(cards): return 'pair'
    if is_single(cards): return 'single'
    return None

class Player:
    def __init__(self, name, is_human=False):
        self.name = name
        self.hand = []
        self.is_human = is_human
    def sort_hand(self):
        self.hand.sort(key=lambda c:(RANKS.index(c.rank), SUITS.index(c.suit)))
    def find_bombs(self):
        cnt = Counter(c.rank for c in self.hand)
        return [[c for c in self.hand if c.rank==r] for r,v in cnt.items() if v==4]

class Game:
    def __init__(self):
        self.players = [Player('Player', True)] + [Player(f'AI {i+1}') for i in range(3)]
        self.deck = Deck()
        self.pile = []
        self.current_idx = 0
        self.first_turn = True
        self.start_idx = 0
        self.pass_count = 0
        self.current_combo = None

    def setup(self):
        self.deck.shuffle()
        hands = self.deck.deal(len(self.players))
        for p, h in zip(self.players, hands):
            p.hand = h; p.sort_hand()
            b = p.find_bombs()
            if b: print(f"{p.name} bombs: {b}"); log_action(f"{p.name} bombs: {b}")
        for i,p in enumerate(self.players):
            if any(c.rank=='3' and c.suit=='Spades' for c in p.hand):
                self.current_idx = i; self.start_idx = i
                print(f"{p.name} starts (holds 3♠)"); log_action(f"Start: {p.name}")
                break

    def is_valid(self, player, cards, current):
        # Prevent pass on first turn for starter
        if not cards:
            if player.is_human and self.first_turn and self.current_idx==self.start_idx:
                return False, 'Must include 3♠ first'
            return True, ''
        combo = detect_combo(cards)
        if not combo:
            return False, 'Invalid combo'
        if self.first_turn and self.current_idx==self.start_idx and player.is_human:
            if not any(c.rank=='3' and c.suit=='Spades' for c in cards):
                return False, 'Must include 3♠ first'
        if not current:
            return True, ''
        prev = detect_combo(current)
        if combo=='bomb' and prev!='bomb':
            return True, ''
        if combo==prev and len(cards)==len(current):
            if max(RANKS.index(c.rank) for c in cards) > max(RANKS.index(c.rank) for c in current):
                return True, ''
        return False, 'Does not beat current'

    def parse_input(self, inp, hand):
        s = inp.strip().lower()
        if s in ['pass', 'help', 'quit', 'hint']:
            return s, []
        parts = inp.strip().split()
        cards = []
        for p in parts:
            if any(sym in p for sym in SUIT_SYMBOLS):
                rank, sym = p[:-1], p[-1]
                suit = SUIT_SYMBOLS.get(sym)
                found = [c for c in hand if c.rank == rank and c.suit == suit]
                if not found:
                    return 'error', f"Card {p} not in hand"
                cards.append(found[0])
            else:
                try:
                    idx = int(p) - 1
                except ValueError:
                    return 'error', 'Invalid index'
                if not 0 <= idx < len(hand):
                    return 'error', 'Invalid index'
                cards.append(hand[idx])
        return 'play', cards

    def hint(self, current):
        for c in self.players[0].hand:
            ok, _ = self.is_valid(self.players[0], [c], current)
            if ok:
                return [c]
        return []

    def cli_input(self, current):
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
        moves = []
        for n in range(1, 5):
            for combo_cards in combinations(player.hand, n):
                lst = list(combo_cards)
                ok, _ = self.is_valid(player, lst, current)
                if ok:
                    moves.append(lst)
        return moves

    def score_move(self, player, move, current):
        t = detect_combo(move)
        base = TYPE_PRIORITY.get(t, 0)
        rank_val = max(RANKS.index(c.rank) for c in move)
        remaining = [c for c in player.hand if c not in move]
        finish = 1 if not remaining else 0
        return (base, finish, rank_val)

    def ai_play(self, current):
        p = self.players[self.current_idx]
        moves = self.generate_valid_moves(p, current)
        if not moves:
            return []
        return max(moves, key=lambda m: self.score_move(p, m, current))

    # Display functions
    def display_pile(self):
        if not self.pile:
            print('Pile: empty')
        else:
            p, c = self.pile[-1]
            print(f"Pile: {p.name} -> {c} ({detect_combo(c)})")

    def display_hand(self, player):
        print(f"\n{player.name}'s hand:")
        for i, c in enumerate(player.hand, 1):
            print(f" {i}:{c}")

    def display_overview(self):
        print('Opponents cards:')
        for p in self.players[1:]:
            print(f" {p.name}: {len(p.hand)}")

    # Round and turn processing
    def reset_pile(self):
        print('All passed. Resetting pile.')
        self.summary_round()
        self.pile.clear()
        self.current_combo = None
        self.pass_count = 0

    def summary_round(self):
        print('\n-- Round Summary --')
        for p, c in self.pile:
            print(f" {p.name}: {c}")
        self.display_overview()
        print('--')
        log_action(f"Round summary: {self.pile}")

    def handle_turn(self):
        p = self.players[self.current_idx]
        if not p.hand:
            self.next_turn()
            return False
        print(f"\n-- {p.name}'s turn --")
        self.display_pile()
        self.display_overview()
        if p.is_human:
            cards = self.cli_input(self.current_combo)
        else:
            cards = self.ai_play(self.current_combo)
            print(f"{p.name} plays {cards}")
            log_action(f"{p.name} plays {cards}")
        ok, _ = self.is_valid(p, cards, self.current_combo)
        if not ok:
            cards = []
            if not p.is_human:
                print('Invalid AI move, passing')
        if cards:
            if p.is_human and self.first_turn and self.current_idx == self.start_idx:
                self.first_turn = False
            self.pass_count = 0
            for c in cards:
                p.hand.remove(c)
            self.pile.append((p, cards))
            self.current_combo = cards
            print(f"{p.name} plays {cards}\n")
            if not p.hand:
                print(f"{p.name} wins!")
                log_action(f"Winner: {p.name}")
                return True
        else:
            self.pass_count += 1
            print(f"{p.name} passes\n")
            active = sum(1 for x in self.players if x.hand)
            if self.current_combo and self.pass_count >= active - 1:
                self.reset_pile()
        self.next_turn()
        return False

    def play(self):
        self.setup()
        while not self.handle_turn():
            pass

    def next_turn(self):
        self.current_idx = (self.current_idx + 1) % len(self.players)

if __name__ == '__main__':
    Game().play()
