from __future__ import annotations

import unittest

from fuzzing.config_fuzzer import fuzz_one_input


class FuzzTargetTests(unittest.TestCase):
    def test_config_fuzzer_accepts_arbitrary_bytes_without_crashing(self) -> None:
        samples = [
            b"",
            b"not-json",
            b"{}",
            b'{"expected_ports":[1,65535]}',
            b'{"expected_ports":[0,70000]}',
            b'{"ignore_paths":["foo\\\\bar","  baz  "]}',
            b'[{"not":"an object"}]',
            bytes(range(256)),
        ]
        for sample in samples:
            with self.subTest(sample=sample[:32]):
                fuzz_one_input(sample)


if __name__ == "__main__":
    unittest.main()
