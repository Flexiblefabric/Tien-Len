import pytest

pytest.importorskip("pygame")
pytest.importorskip("pygame_gui")

from tien_len_full import Game, Card  # noqa: E402


def test_minimax_decision_selects_optimal_move():
    game = Game()
    game.set_ai_level("Expert")
    ai = game.players[1]
    ai.hand = [Card('Spades', '3'), Card('Hearts', '3'), Card('Spades', '4')]
    ai.sort_hand()
    game.players[0].hand = [Card('Diamonds', '5')]
    game.players[2].hand = []
    game.players[3].hand = []
    game.current_idx = 1

    move = game._minimax_decision(ai, 1)
    assert set(move) == {Card('Spades', '3'), Card('Hearts', '3')}


def test_master_ai_sets_depth():
    game = Game()
    game.set_ai_level("Master")
    assert game.ai_depth > 1


def test_minimax_respects_depth_param():
    game = Game()
    ai = game.players[1]
    ai.hand = [Card('Spades', '3'), Card('Hearts', '4')]
    ai.sort_hand()
    game.players[0].hand = []
    game.players[2].hand = []
    game.players[3].hand = []
    game.current_idx = 1

    move_short = game._minimax_decision(ai, 1)
    move_deep = game._minimax_decision(ai, 2)
    assert move_short == move_deep
