from unittest.mock import MagicMock

import sound
from tien_len_full import Game, Card


def test_set_personality_mapping_and_default():
    game = Game()
    game.set_personality('aggressive')
    assert game.ai_personality == 'aggressive'
    assert game.bluff_chance == 0.05

    game.set_personality('DEFENSIVE')
    assert game.ai_personality == 'defensive'
    assert game.bluff_chance == 0.3

    game.set_personality('unknown')
    assert game.ai_personality == 'balanced'
    assert game.bluff_chance == 0.0


def test_score_move_respects_personality_weighting():
    game = Game()
    ai = game.players[1]
    ai.hand = [Card('Spades', '3'), Card('Hearts', '4')]
    move = [ai.hand[1]]
    game.set_personality('aggressive')
    aggr = game.score_move(ai, move, None)
    game.set_personality('defensive')
    defn = game.score_move(ai, move, None)
    assert aggr[2] > defn[2]


def test_set_volume_clamps_and_updates_loaded_sounds():
    snd1 = MagicMock()
    snd2 = MagicMock()
    sound._SOUNDS.clear()
    sound._SOUNDS['a'] = snd1
    sound._SOUNDS['b'] = snd2
    sound.set_enabled(True)
    sound.set_volume(2.0)
    assert sound._VOLUME == 1.0
    snd1.set_volume.assert_called_with(1.0)
    snd2.set_volume.assert_called_with(1.0)

    snd1.set_volume.reset_mock()
    snd2.set_volume.reset_mock()
    sound.set_enabled(False)
    sound.set_volume(-5.0)
    assert sound._VOLUME == 0.0
    snd1.set_volume.assert_not_called()
    snd2.set_volume.assert_not_called()
