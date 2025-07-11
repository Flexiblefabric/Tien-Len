from tien_len_full import Game, SUITS, RANKS


def test_clone_preserves_rule_settings():
    game = Game(allow_2_in_sequence=True, flip_suit_rank=True)
    clone = game._clone()
    assert clone.allow_2_in_sequence is True
    assert clone.flip_suit_rank is True
    block = len(RANKS)
    suits = [clone.deck.cards[i * block].suit for i in range(len(SUITS))]
    assert suits == list(reversed(SUITS))
