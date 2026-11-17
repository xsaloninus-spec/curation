#!/usr/bin/env python3
"""Screenshot bay B3 of the entrance wall via CDP chrome."""
import asyncio, base64, json, urllib.request, sys

import websockets

msg_id = 0
OUT = "/Users/wangyaomin/Desktop/策展/entrance-wall/shots/verify-bay3-han-new.png"
URL = "http://localhost:7100/?tour=1&t=44"


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
    tab = http("PUT", "/json/new?about:blank")
    ws_url = tab["webSocketDebuggerUrl"]
    async with websockets.connect(ws_url, max_size=100 * 1024 * 1024) as ws:
        await send(ws, "Page.enable")
        await send(ws, "Runtime.enable")
        await send(ws, "Emulation.setDeviceMetricsOverride", {"width": 1280, "height": 800, "deviceScaleFactor": 1, "mobile": False})
        await send(ws, "Page.navigate", {"url": URL})
        await asyncio.sleep(2)
        # press Space to pause the tour inside the B3 dwell window
        await evaluate(ws, "window.dispatchEvent(new KeyboardEvent('keydown', {code:'Space', key:' '})); 'ok'")
        # wait for the 46 MB GLB + scene warm-up
        await asyncio.sleep(10)
        # check for load errors reported by the app
        errs = await evaluate(ws, "JSON.stringify([...document.querySelectorAll('[role=alert],.toast, [data-sonner-toast]')].map(e=>e.textContent).slice(0,5))")
        print("toasts:", errs)
        data = await send(ws, "Page.captureScreenshot", {"format": "png"})
        with open(OUT, "wb") as f:
            f.write(base64.b64decode(data["result"]["data"]))
        print("saved", OUT)


asyncio.run(main())
