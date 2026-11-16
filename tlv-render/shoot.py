#!/usr/bin/env python3
"""Multi-view render captures of the TLV mirror via CDP chrome."""
import asyncio
import base64
import json
import urllib.request

import websockets

msg_id = 0
OUT = "/Users/wangyaomin/Desktop/策展/文物建模/renders"


def http(method, path):
    req = urllib.request.Request(f"http://127.0.0.1:9333{path}", method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


async def send(ws, method, params=None):
    global msg_id
    msg_id += 1
    await ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        data = json.loads(await ws.recv())
        if data.get("id") == msg_id:
            return data


async def evaluate(ws, expr):
    result = await send(ws, "Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
    return result.get("result", {}).get("result", {}).get("value")


async def main():
    import os
    os.makedirs(OUT, exist_ok=True)
    tab = http("PUT", "/json/new?about:blank")
    ws_url = tab["webSocketDebuggerUrl"]
    async with websockets.connect(ws_url, max_size=100 * 1024 * 1024) as ws:
        await send(ws, "Page.enable")
        await send(ws, "Runtime.enable")
        await send(ws, "Emulation.setDeviceMetricsOverride", {"width": 1000, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
        for view in ("back", "front", "side", "iso", "knob", "tlv", "band"):
            await send(ws, "Page.navigate", {"url": f"http://localhost:7200/?cam={view}"})
            for _ in range(120):
                await asyncio.sleep(0.5)
                state = await evaluate(ws, "window.__SCENE_READY__ ? 'ready' : (window.__SCENE_ERROR__ ? 'error' : 'wait')")
                if state in ("ready", "error"):
                    break
            print(view, "->", state)
            if state != "ready":
                err = await evaluate(ws, "window.__SCENE_ERROR__ || ''")
                print("  error:", err)
                continue
            await asyncio.sleep(0.5)
            data = await send(ws, "Page.captureScreenshot", {"format": "png"})
            with open(f"{OUT}/view-{view}.png", "wb") as f:
                f.write(base64.b64decode(data["result"]["data"]))
            print("  saved", f"view-{view}.png")


asyncio.run(main())
