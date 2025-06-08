import pytest
from tien_len_full import Game, Card


def test_parse_input_valid_index():
    g = Game()
    hand = [Card('Spades', '3'), Card('Hearts', '4')]
    cmd, cards = g.parse_input('1', hand)
    assert cmd == 'play'
    assert cards == [hand[0]]


def test_parse_input_invalid_high_index():
    g = Game()
    hand = [Card('Spades', '3'), Card('Hearts', '4')]
    cmd, msg = g.parse_input('3', hand)
    assert cmd == 'error'
    assert msg == 'Invalid index'


def test_parse_input_invalid_negative_index():
    g = Game()
    hand = [Card('Spades', '3'), Card('Hearts', '4')]
    cmd, msg = g.parse_input('0', hand)
    assert cmd == 'error'
    assert msg == 'Invalid index'
