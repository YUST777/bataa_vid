#!/usr/bin/env python3
"""Tiny client for the Blender MCP add-on socket (127.0.0.1:9876).

Usage:
  python3 bx.py file.py        # run a Python file inside Blender
  python3 bx.py -c "code"      # run inline code
Inside the code, assign a dict/str to `RESULT` to get it printed back.
"""
import json
import socket
import sys


def send(cmd_type, params, timeout=600):
    s = socket.create_connection(("127.0.0.1", 9876), timeout=timeout)
    s.sendall(json.dumps({"type": cmd_type, "params": params}).encode())
    buf = b""
    while True:
        chunk = s.recv(1 << 20)
        if not chunk:
            break
        buf += chunk
        try:
            data = json.loads(buf)
            break
        except json.JSONDecodeError:
            continue
    s.close()
    return data


def run(code, timeout=600):
    wrapped = (
        "import json as _j\nRESULT=None\n" + code +
        "\nprint('<<RESULT>>'+_j.dumps(RESULT, default=str))\n"
    )
    return send("execute_code", {"code": wrapped}, timeout)


if __name__ == "__main__":
    if sys.argv[1] == "-c":
        code = sys.argv[2]
    else:
        code = open(sys.argv[1]).read()
    out = run(code)
    res = out.get("result", out)
    text = res.get("result", "") if isinstance(res, dict) else str(res)
    if isinstance(text, str) and "<<RESULT>>" in text:
        before, after = text.split("<<RESULT>>", 1)
        if before.strip():
            print(before.strip()[-3000:])
        print(after.strip())
    else:
        print(json.dumps(out, indent=1)[-4000:])
