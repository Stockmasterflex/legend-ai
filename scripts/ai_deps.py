#!/usr/bin/env python3
import sys
import subprocess


def ensure(pkg: str, optional: bool = False):
    name = pkg.split("==")[0]
    try:
        __import__(name)
        print(f"✅ {pkg} ok")
    except Exception as e:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])
            print(f"📦 installed {pkg}")
        except Exception as e2:
            msg = f"⚠️ failed to install {pkg}: {e2}"
            if optional:
                print(msg)
            else:
                raise

# Core deps
for p in ["pandas", "numpy", "yfinance", "ta"]:
    ensure(p)

# Optional heavy deps
for opt in ["transformers", "torch"]:
    ensure(opt, optional=True)
