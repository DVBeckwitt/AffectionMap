import unittest

import numpy as np

from affection_map.analysis import correlation


class CorrelationTests(unittest.TestCase):
    def test_identical_profiles_return_one(self) -> None:
        values = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
        self.assertEqual(correlation(values, values), 1.0)

    def test_constant_against_variable_returns_zero(self) -> None:
        constant = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
        variable = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(correlation(constant, variable), 0.0)

    def test_distinct_but_matching_trends(self) -> None:
        a = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
        b = np.array([3.0, 6.0, 9.0, 12.0, 15.0])
        self.assertAlmostEqual(correlation(a, b), 1.0)


if __name__ == "__main__":
    unittest.main()
