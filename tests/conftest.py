"""Suite-wide defaults: the test suite always exercises the local account
backend so results are deterministic with no network or key files.
Firebase-mode behavior is covered separately with monkeypatched state."""
import os

os.environ.setdefault("AUTH_BACKEND", "local")
