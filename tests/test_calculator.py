import unittest
import sys
import os

# Adjust path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import calculator

class TestCalculator(unittest.TestCase):
    def test_calculate_active_transport(self):
        res = calculator.calculate_footprint(10, 'active', 0, 'vegan')
        # transport = 10 * 0 = 0
        # electricity = 0 * 0.390 = 0
        # diet = vegan = 2.9
        # total = 2.9
        self.assertEqual(res['transport'], 0.0)
        self.assertEqual(res['electricity'], 0.0)
        self.assertEqual(res['diet'], 2.9)
        self.assertEqual(res['total'], 2.9)

    def test_calculate_gasoline_car(self):
        res = calculator.calculate_footprint(20, 'gasoline_car', 10, 'meat_heavy')
        # transport = 20 * 0.411 = 8.22
        # electricity = 10 * 0.390 = 3.90
        # diet = meat_heavy = 7.2
        # total = 8.22 + 3.9 + 7.2 = 19.32
        self.assertEqual(res['transport'], 8.22)
        self.assertEqual(res['electricity'], 3.90)
        self.assertEqual(res['diet'], 7.2)
        self.assertEqual(res['total'], 19.32)

if __name__ == '__main__':
    unittest.main()
