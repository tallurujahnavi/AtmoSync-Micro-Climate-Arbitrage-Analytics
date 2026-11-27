"""
test_role_views.py – Unit tests verifying strict RBAC separation across all three personas.
"""

import ast
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "views"))


VIEW_FILES = {
    "Commodities Trader": os.path.join(os.path.dirname(__file__), "..", "src", "views", "cold_chain_view.py"),
    "Agronomist": os.path.join(os.path.dirname(__file__), "..", "src", "views", "agro_view.py"),
    "Supply Chain Analyst": os.path.join(os.path.dirname(__file__), "..", "src", "views", "supply_chain_view.py"),
}


class TestRoleViewSeparation(unittest.TestCase):

    def test_all_view_modules_importable(self):
        import auth_view
        import cold_chain_view
        import agro_view
        import supply_chain_view
        self.assertTrue(callable(auth_view.render_auth_page))
        self.assertTrue(callable(cold_chain_view.render_cold_chain_view))
        self.assertTrue(callable(agro_view.render_agro_suitability_view))
        self.assertTrue(callable(supply_chain_view.render_supply_chain_view))

    def test_views_have_distinct_non_overlapping_tabs(self):
        tab_sets = {}
        for role, path in VIEW_FILES.items():
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
            tabs_found = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "tabs":
                    if node.args and isinstance(node.args[0], ast.List):
                        for elt in node.args[0].elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                tabs_found.add(elt.value)
            self.assertGreaterEqual(len(tabs_found), 5, f"{role} must define >= 5 exclusive tabs")
            tab_sets[role] = tabs_found

        # Verify zero overlap across all pairs of role workspaces
        self.assertEqual(tab_sets["Commodities Trader"] & tab_sets["Agronomist"], set())
        self.assertEqual(tab_sets["Commodities Trader"] & tab_sets["Supply Chain Analyst"], set())
        self.assertEqual(tab_sets["Agronomist"] & tab_sets["Supply Chain Analyst"], set())

    def test_app_py_strict_rbac_routing(self):
        app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
        with open(app_path, "r", encoding="utf-8") as f:
            src = f.read()
        self.assertIn("ROLE_WORKSPACE_MAP", src)
        self.assertIn("render_cold_chain_view", src)
        self.assertIn("render_agro_suitability_view", src)
        self.assertIn("render_supply_chain_view", src)
        # Ensure shared analytical switcher radio was removed
        self.assertNotIn("st.sidebar.radio", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
