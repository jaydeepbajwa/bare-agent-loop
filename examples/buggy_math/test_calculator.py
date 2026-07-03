import unittest

from calculator import average


class AverageTests(unittest.TestCase):
    def test_average_uses_all_values(self) -> None:
        self.assertEqual(average([2, 4, 6]), 4)

    def test_average_rejects_empty_input(self) -> None:
        with self.assertRaises(ValueError):
            average([])


if __name__ == "__main__":
    unittest.main()

