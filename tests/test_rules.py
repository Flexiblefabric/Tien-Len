from tien_len_full import (
    Card,
    Player,
    Game,
    is_single,
    is_pair,
    is_triple,
    is_bomb,
    is_sequence,
    detect_combo,
)


def make_cards(*args):
    """Helper to create cards from tuples of (suit, rank)."""
    return [Card(s, r) for s, r in args]


def test_combo_detection():
    spade3 = Card('Spades', '3')
    heart3 = Card('Hearts', '3')
    club3 = Card('Clubs', '3')
    diamond3 = Card('Diamonds', '3')

    assert is_single([spade3])
    assert detect_combo([spade3]) == 'single'

    pair = [spade3, heart3]
    assert is_pair(pair)
    assert detect_combo(pair) == 'pair'
    assert not is_pair([spade3, Card('Spades', '4')])

    triple = [spade3, heart3, diamond3]
    assert is_triple(triple)
    assert detect_combo(triple) == 'triple'

    bomb = [spade3, heart3, diamond3, club3]
    assert is_bomb(bomb)
    assert detect_combo(bomb) == 'bomb'

    seq = make_cards(('Spades', '3'), ('Hearts', '4'), ('Clubs', '5'))
    assert is_sequence(seq)
    assert detect_combo(seq) == 'sequence'

    suited_seq = make_cards(('Spades', '7'), ('Spades', '8'), ('Spades', '9'))
    assert is_sequence(suited_seq)

    bad_seq = make_cards(('Spades', '3'), ('Hearts', '3'), ('Clubs', '4'))
    assert not is_sequence(bad_seq)


def test_player_sort_and_bombs():
    p = Player('Tester')
    # Unsorted order
    p.hand = make_cards(
        ('Hearts', 'K'),
        ('Clubs', '3'),
        ('Spades', '5'),
        ('Diamonds', '3'),
        ('Spades', '3'),
        ('Hearts', '3'),
    )
    p.sort_hand()
    # After sorting, ranks should be grouped and ordered
    ranks = [c.rank for c in p.hand]
    assert ranks == ['3', '3', '3', '3', '5', 'K']

    bombs = p.find_bombs()
    assert len(bombs) == 1
    assert all(c.rank == '3' for c in bombs[0])


def test_is_valid_basic_rules():
    game = Game(flip_suit_rank=False)
    starter = game.players[0]
    game.current_idx = 0
    game.start_idx = 0
    game.first_turn = True

    # Passing on the opening turn is forbidden
    ok, msg = game.is_valid(starter, [], None)
    assert not ok and msg == 'Must include 3\u2660 first'

    # Playing a non-3 on the first turn is invalid
    card4s = Card('Spades', '4')
    ok, msg = game.is_valid(starter, [card4s], None)
    assert not ok and msg == 'Must include 3\u2660 first'

    # Playing the 3\u2660 is allowed
    card3s = Card('Spades', '3')
    ok, msg = game.is_valid(starter, [card3s], None)
    assert ok

    # Invalid combo
    invalid = [card3s, card4s]
    ok, msg = game.is_valid(starter, invalid, None)
    assert not ok and msg == 'Invalid combo'

    # Valid play against existing pair
    game.first_turn = False
    current = make_cards(('Hearts', '4'), ('Clubs', '4'))
    play = make_cards(('Spades', '5'), ('Diamonds', '5'))
    ok, msg = game.is_valid(starter, play, current)
    assert ok

    # Must beat the current combo
    weak = make_cards(('Spades', '4'), ('Diamonds', '4'))
    ok, msg = game.is_valid(starter, weak, current)
    assert not ok and msg == 'Does not beat current'

    # Bomb beats non-bomb
    bomb = make_cards(('Spades', '7'), ('Hearts', '7'), ('Clubs', '7'), ('Diamonds', '7'))
    ok, msg = game.is_valid(starter, bomb, current)
    assert ok


def test_is_valid_first_card_flip_suit():
    import tien_len_full as tl

    tl_game = tl.Game(flip_suit_rank=True)
    starter = tl_game.players[0]
    tl_game.current_idx = 0
    tl_game.start_idx = 0
    tl_game.first_turn = True

    ok, msg = tl_game.is_valid(starter, [], None)
    assert not ok and msg == 'Must include 3\u2665 first'

    card3h = tl.Card('Hearts', '3')
    ok, msg = tl_game.is_valid(starter, [card3h], None)
    assert ok


def test_flip_suit_rank_sorting_and_deck_order():
    import tien_len_full as tl

    p = tl.Player('Tester')
    p.hand = [tl.Card(s, '3') for s in tl.SUITS]
    p.sort_hand()
    assert [c.suit for c in p.hand] == tl.SUITS

    p2 = tl.Player('Tester2')
    p2.hand = [tl.Card(s, '3') for s in tl.SUITS]
    p2.sort_hand(flip_suit_rank=True)
    assert [c.suit for c in p2.hand] == list(reversed(tl.SUITS))

    deck = tl.Deck(flip_suit_rank=True)
    block = len(tl.RANKS)
    suits = [deck.cards[i * block].suit for i in range(len(tl.SUITS))]
    assert suits == list(reversed(tl.SUITS))


def test_is_valid_suit_tie_breaker():
    game = Game()
    player = game.players[0]
    game.first_turn = False

    current = [Card('Hearts', '8')]
    play = [Card('Diamonds', '8')]
    ok, msg = game.is_valid(player, play, current)
    assert ok


def test_is_valid_sequence_tie_breaker():
    game = Game()
    player = game.players[0]
    game.first_turn = False

    current = make_cards(('Hearts', '3'), ('Spades', '4'), ('Hearts', '5'))
    play = make_cards(('Spades', '3'), ('Hearts', '4'), ('Diamonds', '5'))
    ok, msg = game.is_valid(player, play, current)
    assert ok
