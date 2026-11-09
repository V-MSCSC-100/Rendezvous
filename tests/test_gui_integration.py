"""
GUI Integration tests for HF Deluxe Pro Manager.
Verifies window creation, styling, and page navigation across all 9 pages.
"""

import unittest
import tkinter as tk
from main import HFDeluxeManagerApp


class TestGUIIntegration(unittest.TestCase):
    def setUp(self):
        try:
            self.app = HFDeluxeManagerApp()
            # Withdraw window so it doesn't pop up visibly during test
            self.app.withdraw()
            self.app.update_idletasks()
        except tk.TclError:
            self.skipTest("No display available for GUI tests")

    def tearDown(self):
        if hasattr(self, "app") and self.app:
            self.app.destroy()

    def test_navigation_across_all_pages(self):
        pages = [
            "dashboard",
            "vehicle",
            "fuel",
            "maintenance",
            "upgrades",
            "analytics",
            "trip_planner",
            "trip_history",
            "settings",
        ]
        for p in pages:
            self.app.navigate_to(p)
            self.app.update_idletasks()
            self.assertEqual(self.app.current_page_key, p)
            page_widget = self.app.pages[p]
            self.assertTrue(page_widget.winfo_exists())


if __name__ == "__main__":
    unittest.main()

