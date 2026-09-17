import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from token_classifier import cli  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestFailOn(unittest.TestCase):
    def test_security_fails(self):
        path = os.path.join(ROOT, "demo", "demo_security_token.md")
        self.assertEqual(
            cli.main(["-f", path, "-n", "X", "--fail-on", "possibly_security"]), 1)

    def test_utility_passes(self):
        path = os.path.join(ROOT, "demo", "demo_utility_token.md")
        self.assertEqual(
            cli.main(["-f", path, "-n", "X", "--fail-on", "possibly_security"]), 0)

    def test_ambiguous_not_fails_on_likely(self):
        path = os.path.join(ROOT, "demo", "demo_ambiguous_token.md")
        self.assertEqual(
            cli.main(["-f", path, "-n", "X", "--fail-on", "likely_security"]), 0)


if __name__ == "__main__":
    unittest.main()
