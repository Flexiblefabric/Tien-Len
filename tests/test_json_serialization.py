import json
import pytest
from unittest.mock import patch
from tien_len_full import Game, Card, AI_NAMES


def setup_game_state():
    with patch('random.sample', return_value=AI_NAMES[:3]):
        game = Game()
    # Simple deterministic state
    game.players[0].hand = [Card('Spades', '3')]
    game.players[1].hand = [Card('Hearts', '4')]
    game.players[2].hand = []
    game.players[3].hand = []
    game.pile = [(game.players[1], [Card('Diamonds', '5')])]
    game.current_combo = [Card('Diamonds', '5')]
    game.current_idx = 1
    game.start_idx = 0
    game.first_turn = False
    game.pass_count = 1
    game.history = [(1, f'{AI_NAMES[0]} plays 5♦')]
    game.current_round = 2
    game.scores = {p.name: i for i, p in enumerate(game.players)}
    return game


def test_to_json_from_json_round_trip():
    game = setup_game_state()

    json_data = game.to_json()
    data = json.loads(json_data)
    # quick sanity checks on JSON structure
    assert data['current_idx'] == 1
    assert data['players'][0]['hand'][0] == {'suit': 'Spades', 'rank': '3'}

    with patch('random.sample', return_value=AI_NAMES[:3]):
        restored = Game()
    restored.from_json(json_data)

    assert json.loads(restored.to_json()) == data


def test_process_play_round_trip_via_undo():
    with patch('random.sample', return_value=AI_NAMES[:3]):
        game = Game()
    player = game.players[0]
    player.hand = [Card('Spades', '3')]
    game.current_idx = 0
    game.start_idx = 0
    game.first_turn = True

    snapshot = game.to_json()
    game.snapshots = [snapshot]

    game.process_play(player, [player.hand[0]])
    assert not player.hand
    assert game.pile

    assert game.undo_last() is True
    assert game.to_json() == snapshot


def test_handle_pass_and_undo_restores_state():
    with patch('random.sample', return_value=AI_NAMES[:3]):
        game = Game()
    game.players[0].hand = [Card('Spades', '3')]
    game.players[1].hand = [Card('Hearts', '4')]
    game.current_idx = 0
    game.start_idx = 0
    game.first_turn = False
    snapshot = game.to_json()
    game.snapshots = [snapshot]

    assert game.handle_pass() is False
    assert game.pass_count == 1
    assert game.current_idx == 1
    assert len(game.snapshots) == 2

    assert game.undo_last() is True
    assert game.pass_count == 0
    assert game.current_idx == 0
    assert game.to_json() == snapshot
