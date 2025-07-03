import pytest

pytest.importorskip("pygame")
pytest.importorskip("pygame_gui")

from tien_len_full import Game, Card


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

    move = game._minimax_decision(ai)
    assert set(move) == {Card('Spades', '3'), Card('Hearts', '3')}

