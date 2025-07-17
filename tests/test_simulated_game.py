import itertools
import random
from unittest.mock import patch

from tienlen import Game, AI_NAMES


def test_simulated_game():
    # Seed random module so deck shuffling is deterministic
    random.seed(1)
    with patch('random.sample', return_value=AI_NAMES[:3]):
        game = Game()
    # Provide endless 'pass' inputs for the human player
    inputs = itertools.repeat('pass')
    with patch('builtins.input', lambda *args: next(inputs)):
        game.play()
    winners = [p.name for p in game.players if not p.hand]
    assert winners == [AI_NAMES[0]]
