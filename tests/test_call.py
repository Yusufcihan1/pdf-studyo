"""ops_ai.call: akış, JSON çıktısı, iptal ve 'fallback reddedildi' durumunda yedeksiz yeniden deneme."""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "app"))

import anthropic  # noqa: E402

import ops_ai  # noqa: E402
from core import Job  # noqa: E402

try:
    import httpx2 as httpx
except ImportError:
    import httpx

SEEN = []


class FakeStream:
    def __init__(self, text):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        yield NS(type="content_block_delta", delta=NS(type="text_delta", text=self.text))

    def get_final_message(self):
        return NS(stop_reason="end_turn", content=[NS(type="text", text=self.text)],
                  usage=NS(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0))


def bad(msg):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.BadRequestError(msg, response=httpx.Response(400, request=req), body=None)


class Beta:
    def __init__(self, fail):
        self.fail = fail

    def stream(self, **kw):
        SEEN.append(("beta", sorted(kw)))
        if self.fail:
            raise bad("fallbacks: unexpected parameter")
        return FakeStream('{"text": "beta"}')


class Std:
    def stream(self, **kw):
        SEEN.append(("std", sorted(kw)))
        assert "fallbacks" not in kw and "betas" not in kw
        return FakeStream('{"text": "std"}')


def make(fail):
    return NS(beta=NS(messages=Beta(fail)), messages=Std())


schema = ops_ai.S({"text": ops_ai.STR})
ops_ai.client = lambda: make(False)
print("normal:", ops_ai.call([{"type": "text", "text": "x"}], schema=schema, job=Job("t")))
ops_ai.client = lambda: make(True)
print("yedeksiz:", ops_ai.call([{"type": "text", "text": "x"}], schema=schema, job=Job("t")))
for s in SEEN:
    print(s)
print("kullanım:", ops_ai.usage_summary())
