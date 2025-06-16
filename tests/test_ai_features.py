import random
from tien_len_full import Game, Card


def test_set_ai_personality_adjusts_bluff_chance():
    game = Game()
    game.set_ai_personality("Defensive")
    assert game.ai_personality == "Defensive"
    assert game.bluff_chance == 0.2


def test_ai_bluffing_passes_when_playable(monkeypatch):
    game = Game()
    game.set_ai_personality("Aggressive")
    p = game.players[1]
    p.hand = [Card('Spades', '3')]
    game.current_idx = 1

    monkeypatch.setattr(random, 'random', lambda: 0)
    assert game.ai_play(None) == []


def test_ai_lookahead_influences_choice(monkeypatch):
    game = Game()
    game.set_ai_level("Hard")
    p = game.players[1]
    p.hand = [Card('Spades', '3'), Card('Hearts', '4')]
    game.current_idx = 1

    moves = [[p.hand[0]], [p.hand[1]]]

    def fake_gen_valid(player, current):
        return moves

    def fake_score(player, move, current):
        if move == moves[0]:
            return (0, 0, 0, 0)
        if move == moves[1]:
            return (1, 0, 0, 0)
        return (0, 0, 0, 0)

    monkeypatch.setattr(game, 'generate_valid_moves', fake_gen_valid)
    monkeypatch.setattr(game, 'score_move', fake_score)

    game.set_ai_lookahead(False)
    move_no = game.ai_play(None)

    def fake_score_future(player, move, current):
        if move == moves[0]:
            return (10, 0, 0, 0)
        return (0, 0, 0, 0)

    monkeypatch.setattr(game, 'score_move', fake_score_future)
    game.set_ai_lookahead(True)
    move_yes = game.ai_play(None)

    assert move_no != move_yes
