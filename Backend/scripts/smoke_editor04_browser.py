"""Local CDP smoke test of the Vue editor using an isolated synthetic harness.

Requires Vite on 5173 and a separate headless browser debugging on 9334.
No auth, Supabase, model provider or persistent user profile is involved.
"""
import asyncio
import base64
import json
from pathlib import Path
from urllib.request import urlopen
import websockets

OUT = Path(__file__).resolve().parents[1] / 'tests/output/editor04_browser'


async def main():
    pages = json.load(urlopen('http://127.0.0.1:9334/json'))
    target = next(p for p in pages if p['type'] == 'page')
    errors, counter = [], 0
    async with websockets.connect(target['webSocketDebuggerUrl'], max_size=20_000_000) as ws:
        async def call(method, params=None):
            nonlocal counter
            counter += 1
            identifier = counter
            await ws.send(json.dumps({'id': identifier, 'method': method, 'params': params or {}}))
            while True:
                result = json.loads(await ws.recv())
                if result.get('method') == 'Runtime.exceptionThrown':
                    errors.append(result['params']['exceptionDetails'].get('exception', {}).get('description', 'Runtime exception'))
                if result.get('method') == 'Runtime.consoleAPICalled' and result['params'].get('type') == 'error':
                    errors.append(str([a.get('value') or a.get('description') for a in result['params'].get('args', [])]))
                if result.get('id') == identifier:
                    if 'error' in result:
                        raise RuntimeError(result['error'])
                    return result.get('result', {})

        async def evaluate(js):
            result = await call('Runtime.evaluate', {'expression': js, 'returnByValue': True, 'awaitPromise': True})
            if result.get('exceptionDetails'):
                raise AssertionError(result['exceptionDetails'])
            return result.get('result', {}).get('value')

        await call('Runtime.enable')
        await call('Page.enable')
        await call('Emulation.setDeviceMetricsOverride', {'width': 1600, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': False})
        await call('Page.navigate', {'url': 'http://127.0.0.1:5173/tests/manual04-harness.html'})
        await asyncio.sleep(1)  # allow the previous document's execution context to unload
        for _ in range(60):
            if await evaluate("Boolean(document.querySelector('.construction-inspector') && window.manual04FixtureStore)"):
                break
            await asyncio.sleep(.5)
        else:
            raise AssertionError(f'Editor did not mount: {errors}')
        async def mouse_at(x, y, kind, pressed=False):
            if kind == 'mousePressed':
                await evaluate("window.manual04TestStage().container().scrollIntoView({block:'center',inline:'center'});new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
            point = await evaluate(f"(() => {{const s=window.manual04TestStage(),r=s.container().getBoundingClientRect();return {{x:r.left+s.x()+{x}*s.scaleX(),y:r.top+s.y()+{y}*s.scaleY()}};}})()")
            await call('Input.dispatchMouseEvent', {'type': kind, **point, 'button': 'left' if kind != 'mouseMoved' else 'none',
                                                    'buttons': 1 if pressed else 0, 'clickCount': 1 if kind != 'mouseMoved' else 0})
        # Real pointer events: a wall hit must bubble to the active opening tool.
        await evaluate("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Portón').click();true")
        await mouse_at(4.6, 0, 'mousePressed', True)
        await mouse_at(4.6, 0, 'mouseReleased')
        await asyncio.sleep(.2)
        assert await evaluate("window.manual04FixtureStore.estructuraEspacial.puertas.length===4"), 'Garage drawing tool did not create an opening'
        assert await evaluate("window.manual04FixtureStore.estructuraEspacial.puertas.at(-1).kind==='GARAGE_DOOR'")
        await evaluate("[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Escalera').click();true")
        await mouse_at(7, 2, 'mousePressed', True)
        await mouse_at(8, 5, 'mouseMoved', True)
        await mouse_at(8, 5, 'mouseReleased')
        await asyncio.sleep(.2)
        assert await evaluate("window.manual04FixtureStore.estructuraEspacial.escaleras.length===2"), 'Stair drawing tool did not create a footprint'
        await evaluate("document.querySelector('.construction-inspector > select').value='door:G';document.querySelector('.construction-inspector > select').dispatchEvent(new Event('change',{bubbles:true}));true")
        await asyncio.sleep(.2)
        assert await evaluate("document.querySelector('.construction-inspector').innerText.includes('Portón')")
        await evaluate("const label=[...document.querySelectorAll('.construction-inspector label')].find(l=>l.textContent.startsWith('Apertura')); label.querySelector('select').value='SLIDING';label.querySelector('select').dispatchEvent(new Event('change',{bubbles:true}));true")
        await asyncio.sleep(.2)
        await evaluate("[...document.querySelectorAll('.construction-inspector button')].find(b=>b.textContent==='Confirmar propiedades').click();true")
        await asyncio.sleep(.2)
        assert await evaluate("window.manual04FixtureStore.estructuraEspacial.puertas.find(d=>d.id==='G').operation==='SLIDING'")
        assert await evaluate("window.manual04FixtureStore.estructuraEspacial.puertas.find(d=>d.id==='G').confirmed===true")
        await evaluate("document.querySelector('.construction-inspector > select').value='stair:S';document.querySelector('.construction-inspector > select').dispatchEvent(new Event('change',{bubbles:true}));true")
        await asyncio.sleep(.2)
        assert await evaluate("document.querySelector('.construction-inspector').innerText.includes('Altura a salvar: 3')")
        assert await evaluate("document.querySelectorAll('canvas').length>0")
        OUT.mkdir(parents=True, exist_ok=True)
        await evaluate("window.scrollTo(0,0);true")
        screenshot = await call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
        (OUT / 'editor04.png').write_bytes(base64.b64decode(screenshot['data']))
        summary = {'mounted': True, 'garageDrawnOnWall': True, 'stairDrawnInsideSpace': True, 'garageEditedAndConfirmed': True, 'stairRiseFromLevels': 3,
                   'canvasRendered': True, 'runtimeErrors': errors, 'fixture': 'Frontend/tests/fixtures/manual04.json'}
        (OUT / 'smoke.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(summary, ensure_ascii=True))
        assert not errors


if __name__ == '__main__':
    asyncio.run(main())
