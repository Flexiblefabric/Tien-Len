from tien_len_full import main


def run_cli(args):
    return main(args)


def test_personality_and_lookahead_flags(monkeypatch):
    captured = {}

    def fake_play(self):
        captured['ai'] = self.ai_level
        captured['personality'] = self.ai_personality
        captured['lookahead'] = self.ai_lookahead

    monkeypatch.setattr('tien_len_full.Game.play', fake_play)
    run_cli(['--ai', 'Hard', '--personality', 'aggressive', '--lookahead'])
    assert captured == {
        'ai': 'Hard',
        'personality': 'aggressive',
        'lookahead': True,
    }


def test_cli_defaults(monkeypatch):
    captured = {}

    def fake_play(self):
        captured['ai'] = self.ai_level
        captured['personality'] = self.ai_personality
        captured['lookahead'] = self.ai_lookahead

    monkeypatch.setattr('tien_len_full.Game.play', fake_play)
    run_cli([])
    assert captured == {
        'ai': 'Normal',
        'personality': 'balanced',
        'lookahead': False,
    }
