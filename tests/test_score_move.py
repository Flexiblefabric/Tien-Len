from tien_len_full import Game, Card, RANKS


def test_score_move_tuple_length_and_low_cards():
    game = Game()
    ai = game.players[1]
    ai.hand = [Card('Spades', '3'), Card('Hearts', '4')]
    move = [ai.hand[0]]
    normal_score = game.score_move(ai, move, None)
    assert len(normal_score) == 4
    assert normal_score[-1] == 0

    game.set_ai_level('Hard')
    hard_score = game.score_move(ai, move, None)
    assert len(hard_score) == 4
    assert hard_score[-1] == -RANKS.index('4')
