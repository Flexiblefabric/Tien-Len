from unittest.mock import patch

from tien_len_full import Game, Card


def setup_hand():
    return [
        Card('Spades', '3'),
        Card('Hearts', '4'),
        Card('Diamonds', '5'),
    ]


def test_parse_notation_not_in_hand():
    game = Game()
    hand = setup_hand()
    cmd, msg = game.parse_input('6\u2665', hand)
    assert (cmd, msg) == ('error', 'Card 6\u2665 not in hand')


def test_parse_invalid_notation():
    game = Game()
    hand = setup_hand()
    cmd, msg = game.parse_input('foo', hand)
    assert (cmd, msg) == ('error', 'Invalid index')


def test_parse_duplicate_card():
    game = Game()
    hand = setup_hand()
    cmd, msg = game.parse_input('1 1', hand)
    assert (cmd, msg) == ('error', 'Duplicate card')


def test_ai_plays_bomb_when_only_bomb_left():
    game = Game()
    ai = game.players[1]
    ai.hand = [
        Card('Spades', '7'),
        Card('Hearts', '7'),
        Card('Diamonds', '7'),
        Card('Clubs', '7'),
    ]
    game.current_idx = 1
    move = game.ai_play(None)
    assert set(move) == set(ai.hand)


def test_reset_pile_after_consecutive_passes():
    game = Game()
    # Only three players have one card each
    game.players[0].hand = [Card('Spades', '3')]
    game.players[1].hand = [Card('Hearts', '4')]
    game.players[2].hand = [Card('Clubs', '5')]
    game.players[3].hand = []

    game.current_combo = [Card('Diamonds', '6')]
    game.pile = [(game.players[3], [Card('Diamonds', '6')])]
    game.first_turn = False
    game.current_idx = 0

    # Player 0 passes
    with patch('builtins.input', lambda *args: 'pass'):
        game.handle_turn()

    assert game.pass_count == 1
    assert game.current_combo is not None

    # Player 1 also passes
    with patch.object(Game, 'ai_play', return_value=[]):
        game.handle_turn()

    assert game.current_combo is None
    assert game.pass_count == 0
    assert game.pile == []


def test_ai_plays_long_sequence():
    game = Game()
    ai = game.players[1]
    ai.hand = [
        Card('Spades', '7'),
        Card('Spades', '8'),
        Card('Spades', '9'),
        Card('Spades', '10'),
        Card('Spades', 'J'),
    ]
    game.current_idx = 1
    move = game.ai_play(None)
    assert set(move) == set(ai.hand)


def test_generate_moves_calls_is_valid_for_long_sequence():
    game = Game()
    ai = game.players[1]
    ai.hand = [
        Card('Hearts', '4'),
        Card('Hearts', '5'),
        Card('Hearts', '6'),
        Card('Hearts', '7'),
        Card('Hearts', '8'),
    ]
    game.current_idx = 1
    with patch.object(Game, 'is_valid', wraps=game.is_valid) as mock_valid:
        moves = game.generate_valid_moves(ai, None)
        assert any(len(m) == 5 for m in moves)
        assert any(len(args[1]) == 5 for args, _ in mock_valid.call_args_list)


def test_generate_valid_moves_matches_naive():
    game = Game()
    ai = game.players[1]
    ai.hand = [
        Card('Spades', '7'),
        Card('Hearts', '7'),
        Card('Diamonds', '7'),
        Card('Clubs', '7'),
        Card('Spades', '8'),
        Card('Spades', '9'),
    ]
    game.current_idx = 1

    def naive(player, current):
        from itertools import combinations

        all_moves = []
        for n in range(1, len(player.hand) + 1):
            for combo in combinations(player.hand, n):
                move = list(combo)
                ok, _ = game.is_valid(player, move, current)
                if ok:
                    all_moves.append(move)
        return all_moves

    expected = {frozenset(m) for m in naive(ai, None)}
    result = {frozenset(m) for m in game.generate_valid_moves(ai, None)}
    assert expected == result
