import tienlen_gui


def test_calc_fan_layout_returns_arc():
    width = 400
    card_w = 50
    count = 5
    base_y = 100
    layout = tienlen_gui.calc_fan_layout(width, card_w, count, base_y, amplitude=20, angle_range=40)
    assert len(layout) == count
    mid = count // 2
    # center card should sit highest (lowest y value)
    ys = [y for _, y, _ in layout]
    assert ys[mid] == min(ys)
    # angles should span negative to positive
    assert layout[0][2] < 0 < layout[-1][2]
    assert abs(layout[0][2]) == abs(layout[-1][2])
