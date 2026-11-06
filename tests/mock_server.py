"""Arayüzün Claude akışlarını sahte yanıtlarla denemek için sunucu (anahtar gerekmez, ağa çıkmaz)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "app"))
sys.path.insert(0, HERE)

import ops_ai  # noqa: E402
import test_ai  # noqa: E402  (fake_call burada)

ops_ai.call = test_ai.fake_call
ops_ai.get_key = lambda: "sk-ant-test"

import main  # noqa: E402

if __name__ == "__main__":
    sys.argv.append("--no-window")
    main.main()
