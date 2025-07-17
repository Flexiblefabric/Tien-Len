from tienlen import Game, Card


def setup_hand():
    return [
        Card('Spades', '3'),
        Card('Hearts', '4'),
        Card('Diamonds', '5'),
    ]


def test_parse_by_index():
    game = Game()
    hand = setup_hand()
    cmd, cards = game.parse_input('1 2', hand)
    assert cmd == 'play'
    assert cards == [hand[0], hand[1]]


def test_parse_by_notation():
    game = Game()
    hand = setup_hand()
    cmd, cards = game.parse_input('3\u2660 4\u2665', hand)
    assert cmd == 'play'
    assert cards == [hand[0], hand[1]]


def test_negative_index():
    game = Game()
    hand = setup_hand()
    cmd, msg = game.parse_input('-1', hand)
    assert (cmd, msg) == ('error', 'Invalid index')


def test_index_out_of_range():
    game = Game()
    hand = setup_hand()
    cmd, msg = game.parse_input('10', hand)
    assert (cmd, msg) == ('error', 'Invalid index')
