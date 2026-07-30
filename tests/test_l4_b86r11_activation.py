from __future__ import annotations
import importlib
import json
import unittest


class B86R11ActivationTests(unittest.TestCase):
    def test_canonical_accepted_activation_passes(self):
        validator = importlib.import_module("scripts.validate_l_4_breadth_b86r11_provisioning_activation_v13")
        self.assertEqual("pass", validator.validate()["status"])

    def test_unknown_or_noncanonical_activation_blocks(self):
        validator = importlib.import_module("scripts.validate_l_4_breadth_b86r11_provisioning_activation_v13")
        root = validator.ROOT
        raw = (root / validator.ACTIVATION).read_bytes()
        gate = (root / validator.GATE).read_bytes()
        accepted = __import__("subprocess").run(["git", "show", f"{validator.ACCEPTED}:{validator.GATE}"], cwd=root, capture_output=True, check=False).stdout
        value = json.loads(raw.decode("ascii")); value["unknown"] = True
        self.assertFalse(validator.activation_ok(validator.canonical(value), value, gate, accepted))
        self.assertFalse(validator.activation_ok(raw + b" ", json.loads(raw.decode("ascii")), gate, accepted))


if __name__ == "__main__":
    unittest.main()
