import unittest
from unittest.mock import patch, MagicMock
from heidi_cli.cli import open_url
import sys

class TestOpenUrl(unittest.TestCase):
    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('webbrowser.open')
    @patch('heidi_cli.cli.console.print')
    def test_open_url_success_subprocess(self, mock_print, mock_webbrowser_open, mock_run, mock_which):
        # Setup: shutil.which returns a path for 'xdg-open'
        def which_side_effect(cmd):
            return '/usr/bin/' + cmd if cmd == 'xdg-open' else None
        mock_which.side_effect = which_side_effect

        # Setup: subprocess.run returns success
        mock_run.return_value = MagicMock(returncode=0)

        url = "http://example.com"
        open_url(url)

        # Verify: xdg-open was called
        mock_run.assert_called()
        args = mock_run.call_args[0][0]
        self.assertIn('xdg-open', args)
        self.assertIn(url, args)

        # Verify: webbrowser.open was NOT called
        mock_webbrowser_open.assert_not_called()

        # Verify: failure message was NOT printed
        mock_print.assert_not_called()

    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('webbrowser.open')
    @patch('heidi_cli.cli.console.print')
    def test_open_url_success_webbrowser(self, mock_print, mock_webbrowser_open, mock_run, mock_which):
        # Setup: shutil.which returns None for everything (or simulate failures)
        mock_which.return_value = None

        # Setup: webbrowser.open returns True
        mock_webbrowser_open.return_value = True

        url = "http://example.com"
        open_url(url)

        # Verify: webbrowser.open was called
        mock_webbrowser_open.assert_called_with(url)

        # Verify: failure message was NOT printed
        mock_print.assert_not_called()

    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('webbrowser.open')
    @patch('heidi_cli.cli.console.print')
    def test_open_url_failure(self, mock_print, mock_webbrowser_open, mock_run, mock_which):
        # Setup: all external commands fail
        mock_which.return_value = None

        # Setup: webbrowser.open fails (returns False or raises)
        mock_webbrowser_open.return_value = False # or .side_effect = Exception

        url = "http://example.com"
        open_url(url)

        # Verify: failure message WAS printed
        mock_print.assert_called()

        # Verify Panel content includes the expected instructions
        from rich.panel import Panel
        panel = mock_print.call_args[0][0]
        self.assertIsInstance(panel, Panel)

        # To check the content of a Panel, we access panel.renderable
        content = str(panel.renderable)
        self.assertIn("Couldn't find a suitable web browser!", content)
        self.assertIn("Open this URL manually", content)
        self.assertIn("export BROWSER", content)
        self.assertIn("pbcopy", content)

if __name__ == '__main__':
    unittest.main()
