import pytest
from unittest.mock import patch
import tienlen


@pytest.mark.parametrize("ident_attr", [1, "name", "obj"])
def test_set_player_ai_level_accepts_multiple_id_forms(ident_attr):
    with patch('random.sample', return_value=tienlen.AI_NAMES[:3]):
        game = tienlen.Game()
    player = game.players[1]
    if ident_attr == 1:
        ident = 1
    elif ident_attr == "name":
        ident = player.name
    else:
        ident = player
    game.set_player_ai_level(ident, "Hard")
    assert player.ai_level == "Hard"


@pytest.mark.parametrize("ident_attr", [1, "name", "obj"])
def test_set_player_personality_accepts_multiple_id_forms(ident_attr):
    with patch('random.sample', return_value=tienlen.AI_NAMES[:3]):
        game = tienlen.Game()
    player = game.players[1]
    if ident_attr == 1:
        ident = 1
    elif ident_attr == "name":
        ident = player.name
    else:
        ident = player
    game.set_player_personality(ident, "aggressive")
    assert player.ai_personality == "aggressive"
    game.set_player_personality(ident, None)
    assert player.ai_personality is None

