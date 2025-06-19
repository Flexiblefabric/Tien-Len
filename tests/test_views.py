import pytest
from unittest.mock import MagicMock, patch
from tien_len_full import Game, Card
import views


def setup_hand_view(root, game, callback=None):
    with patch('views.tk.Frame'), patch('views.tk.Label'), \
         patch('views.tk.StringVar'), patch('views.ToolTip'), \
         patch('views.ImageTk.PhotoImage'):
        hv = views.HandView(root, game, {}, {}, select_callback=callback)
    return hv


def test_toggle_card_select_deselect():
    game = Game()
    root = MagicMock()
    cb = MagicMock()
    hv = setup_hand_view(root, game, cb)
    hv.refresh = MagicMock()
    card = Card('Spades', '3')

    hv.toggle_card(card)
    assert card in hv.selected
    cb.assert_called_with(hv.selected)
    hv.refresh.assert_called_once()

    cb.reset_mock()
    hv.refresh.reset_mock()

    hv.toggle_card(card)
    assert card not in hv.selected
    cb.assert_called_with(hv.selected)
    hv.refresh.assert_called_once()


def test_drag_select_adds_cards():
    game = Game()
    root = MagicMock()
    hv = setup_hand_view(root, game)
    hv.refresh = MagicMock()
    c1, c2 = Card('Spades', '3'), Card('Hearts', '4')
    s1, s2 = MagicMock(), MagicMock()
    s1.winfo_rootx.return_value = 0
    s1.winfo_rooty.return_value = 0
    s1.winfo_width.return_value = 10
    s1.winfo_height.return_value = 10
    s2.winfo_rootx.return_value = 15
    s2.winfo_rooty.return_value = 0
    s2.winfo_width.return_value = 10
    s2.winfo_height.return_value = 10
    hv.widgets = {c1: s1, c2: s2}
    hv.selected = set()

    press = MagicMock(x_root=0, y_root=0)
    hv._on_press(press, c1, 0)
    move = MagicMock(x_root=20, y_root=10)
    hv._on_motion(move)
    release = MagicMock(state=0)
    hv._on_release(release, c1, 0)

    assert hv.selected == {c1, c2}
    hv.refresh.assert_called_once()


def test_tableview_refresh_creates_sprites():
    game = Game()
    player = game.players[0]
    cards = [Card('Spades', '3'), Card('Hearts', '4')]
    game.pile.append((player, cards))
    root = MagicMock()
    info = MagicMock()
    with patch('views.tk.StringVar', return_value=info), \
         patch('views.tk.Label'), \
         patch('views.CardSprite') as mock_sprite, \
         patch('views.detect_combo', return_value='pair'):
        table = views.TableView(root, game, {}, {})
        w = MagicMock(); table.pack_slaves = MagicMock(return_value=[MagicMock(), w])
        table.refresh()
    info.set.assert_called_with(f"Pile: {player.name} -> {cards} (pair)")
    w.destroy.assert_called_once()
    assert mock_sprite.call_count == 2


def test_opponentview_refresh_updates_display():
    game = Game()
    opponent = game.players[1]
    opponent.hand = [Card('Clubs', '5')]
    root = MagicMock()
    count = MagicMock()
    avatar = MagicMock()
    card_label = MagicMock()
    with patch('views.tk.Label', side_effect=[avatar, card_label, MagicMock()]), \
         patch('views.tk.StringVar', return_value=count), \
         patch('views.ImageTk.PhotoImage') as mock_photo:
        img = MagicMock(width=2, height=4)
        view = views.OpponentView(root, game, 1, {'card_back': img}, {})
        view.refresh()
    count.set.assert_called_with('1')
    card_label.config.assert_called_with(image=mock_photo.return_value)
    assert view.card_label.image is mock_photo.return_value
