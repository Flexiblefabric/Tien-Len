from tien_len_full import Game, Card


def test_cli_input_retries_on_invalid(monkeypatch):
    game = Game()
    player = game.players[0]
    game.current_idx = 0
    game.start_idx = 0
    game.first_turn = False
    player.hand = [Card('Spades', '3'), Card('Spades', '4')]

    inputs = iter(['foo', 'bar'])
    monkeypatch.setattr('builtins.input', lambda *args: next(inputs))

    parse_results = iter([
        ('play', [player.hand[0]]),
        ('play', [player.hand[1]]),
    ])
    monkeypatch.setattr(Game, 'parse_input', lambda self, s, h: next(parse_results))

    valid_results = iter([(False, 'bad'), (True, '')])
    monkeypatch.setattr(Game, 'is_valid', lambda self, p, c, cur: next(valid_results))

    move = game.cli_input(None)
    assert move == [player.hand[1]]
