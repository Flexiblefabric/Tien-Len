import pytest
from tien_len_full import Game, Card


def test_undo_play_restores_state():
    game = Game()
    p = game.players[0]
    p.hand = [Card('Spades', '3'), Card('Hearts', '4')]
    game.current_idx = 0
    game.start_idx = 0
    game.first_turn = True
    game.snapshots = [game.to_json()]

    game.process_play(p, [p.hand[0]])
    assert len(game.snapshots) == 2
    assert len(game.players[0].hand) == 1
    assert game.pile

    assert game.undo_last() is True
    assert len(game.snapshots) == 1
    assert not game.pile
    assert len(game.players[0].hand) == 2
    assert game.first_turn is True


def test_undo_pass_restores_state():
    game = Game()
    game.players[0].hand = [Card('Spades', '3')]
    game.current_idx = 0
    game.start_idx = 1  # allow pass on first turn
    game.first_turn = False
    game.snapshots = [game.to_json()]

    game.process_pass(game.players[0])
    assert len(game.snapshots) == 2
    assert game.pass_count == 1

    assert game.undo_last() is True
    assert len(game.snapshots) == 1
    assert game.pass_count == 0


def test_process_play_invalid_card_raises():
    game = Game()
    player = game.players[0]
    player.hand = [Card('Spades', '3')]
    invalid = Card('Hearts', '4')
    with pytest.raises(ValueError, match='not in hand'):
        game.process_play(player, [invalid])
