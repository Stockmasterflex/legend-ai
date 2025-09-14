#!/usr/bin/env python3
import os
import signal
import subprocess
import sys

def kill_port(port: str):
    try:
        res = subprocess.run(['lsof', '-tiTCP:%s' % port, '-sTCP:LISTEN'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL,
                              text=True,
                              check=False)
        pids = [int(x) for x in res.stdout.strip().split() if x.strip()]
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
        if pids:
            try:
                subprocess.run(['sleep','0.2'])
            except Exception:
                pass
            for pid in pids:
                try:
                    os.kill(pid, 0)
                    os.kill(pid, signal.SIGKILL)
                except Exception:
                    pass
    except Exception:
        pass

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: kill_port.py <port>')
        sys.exit(0)
    kill_port(sys.argv[1])

