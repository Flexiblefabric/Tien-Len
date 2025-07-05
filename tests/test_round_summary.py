import logging
from tien_len_full import Game, Card, logger


def test_summary_round_logs_winner_and_next_starter(caplog):
    game = Game()
    winner = game.players[1]
    loser = game.players[0]

    game.pile = [
        (loser, [Card('Spades', '3')]),
        (winner, [Card('Hearts', '4')]),
    ]
    # Give players some hands for display_overview
    loser.hand = [Card('Clubs', '5')]
    winner.hand = []
    game.players[2].hand = [Card('Diamonds', '6')]
    game.players[3].hand = [Card('Clubs', '7')]

    with caplog.at_level(logging.INFO):
        logger.addHandler(caplog.handler)
        game.summary_round()
        logger.removeHandler(caplog.handler)

    messages = [rec.message for rec in caplog.records]
    assert any(f"{winner.name} won the round" in m for m in messages)
    assert any(f"{winner.name} will start the next round" in m for m in messages)
