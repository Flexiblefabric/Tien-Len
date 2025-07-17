from tienlen import Game, Card, detect_combo


def test_hint_recommends_pair_over_single():
    game = Game()
    p = game.players[0]
    c1 = Card('Spades', '3')
    c2 = Card('Hearts', '3')
    c3 = Card('Diamonds', '4')
    p.hand = [c1, c2, c3]
    game.current_idx = 0
    game.start_idx = 0
    game.first_turn = True

    hint = game.hint(None)
    assert set(hint) == {c1, c2}
    assert detect_combo(hint) == 'pair'


def test_hint_ignores_ai_difficulty():
    game = Game()
    game.set_ai_level('Hard')
    p = game.players[0]
    c1 = Card('Spades', '3')
    c2 = Card('Hearts', '3')
    c3 = Card('Diamonds', '4')
    p.hand = [c1, c2, c3]
    game.current_idx = 0
    game.start_idx = 0
    game.first_turn = True

    hint = game.hint(None)
    assert set(hint) == {c1, c2}
