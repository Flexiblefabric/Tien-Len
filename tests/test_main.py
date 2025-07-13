import unittest
from unittest.mock import patch

import main


class TestMain(unittest.TestCase):
    def test_main_invokes_gameview(self):
        with patch("main.tienlen_gui.GameView") as gv:
            main.main()
            gv.return_value.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
