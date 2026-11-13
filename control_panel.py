#!/usr/bin/env python3
'''Local control panel for Bitmap Lyrics Player (Windows-friendly, stdlib UI/API).'''
from __future__ import annotations
import json, os, socket, subprocess, sys, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
LYRICS_FILE = ROOT / "lyrics.json"
GENERATOR = ROOT / "generate_bitmaps_harfbuzz_ui.py"
CONTROL_FILE = WEB / "control.json"
SERVER_PORT = 8000
UI_PORT = 8080
MAX_BODY = 1_000_000
DEFAULT_LYRICS = [
    {"time_ms": 32000, "text": "তুমি"}, {"time_ms": 35000, "text": "সামনে নেই"},
    {"time_ms": 39000, "text": "তাও তুমি"}, {"time_ms": 43000, "text": "ভাসো"},
    {"time_ms": 46000, "text": "মনের"}, {"time_ms": 50000, "text": "মাঝে"},
    {"time_ms": 53000, "text": "লুকিয়ে"}, {"time_ms": 56000, "text": "একটুখানি হাসো"},
    {"time_ms": 61000, "text": "স্বপ্নে আমার তোমার ছবি"}, {"time_ms": 66000, "text": "চুপটি করে আসে"},
    {"time_ms": 69000, "text": "সকাল থেকে"}, {"time_ms": 71000, "text": "রাতের শেষে"},
    {"time_ms": 73000, "text": "থাকো আমার পাশে"}, {"time_ms": 78000, "text": "তাতা তা"},
    {"time_ms": 81000, "text": "তারারা"}, {"time_ms": 85000, "text": "তারারা"},
    {"time_ms": 86000, "text": "রারা রারা"}, {"time_ms": 87000, "text": "রারা রারা"},
]

INDEX_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bitmap Lyrics Studio</title>
<style>
:root{color-scheme:dark;--bg:#0c0b16;--card:#151425;--card2:#1b1930;--line:#302d4c;--text:#f5f3ff;--muted:#a6a1c2;--purple:#a78bfa;--pink:#f0abfc;--green:#86efac;--red:#fda4af;--amber:#fcd34d}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 15% 0%,#251b49 0,transparent 37%),var(--bg);color:var(--text);font:15px/1.45 Inter,Segoe UI,Arial,sans-serif}
main{max-width:1220px;margin:0 auto;padding:26px 20px 48px}.top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:22px}.eyebrow{letter-spacing:.16em;text-transform:uppercase;color:var(--pink);font-size:11px;font-weight:800}.title{font-size:clamp(26px,4vw,39px);letter-spacing:-.04em;margin:4px 0}.sub{color:var(--muted);max-width:700px}.pill{border:1px solid var(--line);border-radius:999px;padding:7px 11px;display:inline-flex;align-items:center;gap:8px;color:var(--muted);font-size:12px;white-space:nowrap}.dot{width:8px;height:8px;border-radius:50%;background:#716c8a}.dot.ok{background:var(--green);box-shadow:0 0 10px #86efac55}.grid{display:grid;grid-template-columns:1.08fr .92fr;gap:16px;margin-bottom:16px}.card{background:linear-gradient(145deg,#19172aee,#11101dee);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:0 14px 40px #0002}.cardhead{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}.card h2{font-size:16px;margin:0;letter-spacing:-.01em}.muted{color:var(--muted)}.server-info{margin:12px 0;color:var(--muted);font-size:13px;overflow-wrap:anywhere}.server-info code{color:#ddd6fe}.actions{display:flex;gap:8px;flex-wrap:wrap}.btn{cursor:pointer;border:1px solid #474265;background:#24203b;color:var(--text);padding:10px 13px;border-radius:10px;font:600 13px/1.2 Segoe UI,Arial,sans-serif;transition:transform .12s,background .12s}.btn:hover{transform:translateY(-1px);background:#30294c}.btn:disabled{opacity:.45;cursor:wait;transform:none}.primary{background:linear-gradient(135deg,#8b5cf6,#c084fc);border-color:transparent;color:#140c23}.primary:hover{background:linear-gradient(135deg,#a78bfa,#e9a8ff)}.good{border-color:#397b5a;color:#bbf7d0;background:#153122}.danger{border-color:#784153;color:#fecdd3;background:#321822}.small{padding:6px 9px;font-size:12px}.playrow{display:flex;gap:8px;flex-wrap:wrap}.help{font-size:12px;color:var(--muted);margin-top:10px}.sectionhead{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}.count{color:var(--muted);font-size:12px}.tablewrap{overflow:auto;border:1px solid var(--line);border-radius:13px}table{border-collapse:collapse;width:100%;min-width:680px}th{text-align:left;text-transform:uppercase;letter-spacing:.09em;color:#aaa4ca;font-size:10px;background:#1c1930;padding:12px 10px}td{padding:9px 10px;border-top:1px solid #2a2741;vertical-align:middle}tr:hover td{background:#ffffff04}.idx{color:#726b91;font-variant-numeric:tabular-nums;font-size:12px;width:42px}.time{width:112px}.time input,.lyric-input{width:100%;border:1px solid #3b365a;background:#100f1d;border-radius:8px;padding:10px;color:var(--text);font:inherit;outline:none}.time input:focus,.lyric-input:focus{border-color:var(--purple);box-shadow:0 0 0 3px #a78bfa1b}.lyric-input{font-size:16px}.rowtools{display:flex;gap:5px}.rowtools .btn{padding:6px 8px}.bottom{display:grid;grid-template-columns:1fr 260px;gap:16px;margin-top:16px}.preview{width:100%;image-rendering:pixelated;background:#000;border:1px solid #555;border-radius:8px;aspect-ratio:2/1;object-fit:contain}.log{font-size:12px;white-space:pre-wrap;color:#c4b5fd;background:#0d0b18;padding:12px;border-radius:10px;max-height:180px;overflow:auto}.toast{position:fixed;right:20px;bottom:20px;max-width:min(520px,calc(100vw - 40px));background:#201c35;border:1px solid #5b4f8c;border-radius:12px;padding:13px 16px;box-shadow:0 20px 60px #0008;z-index:5;display:none}.toast.show{display:block}.toast.error{border-color:#a84660;color:#fecdd3}.footer{color:#77718f;font-size:11px;margin-top:18px;text-align:center}@media(max-width:850px){.grid,.bottom{grid-template-columns:1fr}.top{flex-direction:column}.pill{white-space:normal}}
</style></head><body><main>
<header class="top"><div><div class="eyebrow">Instagram: pixel_mon.47</div><h1 class="title">Lyrics Studio By Pixel Mon</h1><div class="sub">Write timestamped lyrics, generate shaped Bengali bitmaps, and control the ESP32.</div></div><div class="pill"><span id="serverDot" class="dot"></span><span id="serverLabel">Checking server…</span></div></header>
<div class="grid">
<section class="card"><div class="cardhead"><h2>01 · Web server</h2><span id="serverBadge" class="pill">Unknown</span></div><div class="server-info">ESP32 content server <code id="serverUrl">http://—:8000</code><br>PC address <code id="pcIp">Detecting…</code></div><div class="actions"><button class="btn good" onclick="serverAction('start')">Start server</button><button class="btn danger" onclick="serverAction('stop')">Stop server</button><button class="btn" onclick="serverAction('restart')">Restart server</button></div><div class="help">The content server is separate from this control panel, so the UI stays open when you stop it.</div></section>
<section class="card"><div class="cardhead"><h2>02 · ESP32 playback</h2><span id="commandBadge" class="pill">Waiting for device</span></div><div class="playrow"><button class="btn primary" onclick="sendCommand('play')">▶ Play lyrics</button><button class="btn danger" onclick="sendCommand('stop')">■ Stop lyrics</button><button class="btn" onclick="sendCommand('restart')">↻ Restart lyrics</button></div><div class="help">Restart resets the lyric timer to 00:00. Stop clears the OLED status. The ESP32 checks for button commands over Wi-Fi.</div><div class="server-info">Last command: <code id="lastCommand">—</code> · sequence <code id="lastSeq">0</code></div></section>
</div>
<section class="card"><div class="sectionhead"><div><h2>03 · Lyrics timeline</h2><div class="help">Use <b>MM:SS.mmm</b> (for example 00:32.450), MM:SS, or seconds (72). Keep rows in timestamp order.</div></div><div class="count"><span id="rowCount">0</span> / 80 lines</div></div><div class="tablewrap"><table><thead><tr><th>#</th><th>Time</th><th>Bengali lyric</th><th>Reorder / remove</th></tr></thead><tbody id="rows"></tbody></table></div><div class="actions" style="margin-top:14px"><button class="btn" onclick="addRow()">＋ Add lyric</button><button class="btn" onclick="saveDraft()">Save draft</button><button class="btn primary" id="publishBtn" onclick="publish()">Generate bitmaps + Sync ESP32</button><button class="btn" onclick="loadLyrics()">Discard local edits</button></div><div class="help">Generate + Sync rebuilds the 128×64 bitmaps and manifest, starts the content server if needed, then tells the ESP32 to reload the new playlist. Press Play Lyrics after the OLED reports the update.</div></section>
<div class="bottom"><section class="card"><div class="cardhead"><h2>Build output</h2><span id="buildBadge" class="pill">Not built yet</span></div><div id="buildLog" class="log">No build run in this session.</div></section><section class="card"><div class="cardhead"><h2>OLED preview</h2><span class="pill">128 × 64</span></div><img id="preview" class="preview" src="/api/preview.png" alt="Bitmap preview appears after generation"><div class="help">Preview is refreshed after a successful build.</div></section></div>
<div class="footer">Local control panel · UI runs on this PC · ESP32 must be on the same Wi-Fi network</div>
</main><div id="toast" class="toast"></div>
<script>
const $=id=>document.getElementById(id); let refreshBusy=false;
function toast(message,error=false){const el=$('toast');el.textContent=message;el.className='toast show'+(error?' error':'');setTimeout(()=>el.className='toast',5200)}
async function api(path,body){const opts=body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};let r=await fetch(path,opts);let data=await r.json().catch(()=>({ok:false,message:'Invalid server response'}));if(!r.ok||data.ok===false)throw new Error(data.message||('Request failed: '+r.status));return data}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fmtTime(ms){ms=Math.max(0,Math.round(Number(ms)||0));const mm=Math.floor(ms/60000),ss=Math.floor((ms%60000)/1000),mmm=ms%1000;return String(mm).padStart(2,'0')+':'+String(ss).padStart(2,'0')+'.'+String(mmm).padStart(3,'0')}
function parseTime(raw){const s=String(raw).trim();let m;if(/^\d+$/.test(s))return Number(s)*1000;m=s.match(/^(\d{1,4}):([0-5]\d)(?:\.(\d{1,3}))?$/);if(m)return Number(m[1])*60000+Number(m[2])*1000+Number((m[3]||'').padEnd(3,'0')||0);m=s.match(/^(\d+)\.(\d{1,3})$/);if(m)return Number(m[1])*1000+Number(m[2].padEnd(3,'0'));throw new Error('Use MM:SS.mmm (for example 00:32.450), MM:SS, or seconds (72).')}
function renderRows(items){$('rows').innerHTML=items.map((x,i)=>`<tr class="lyric-row" data-index="${i}"><td class="idx">${String(i+1).padStart(2,'0')}</td><td class="time"><input class="time-input" aria-label="Timestamp for row ${i+1}" value="${fmtTime(x.time_ms ?? (Number(x.time)||0)*1000)}" placeholder="00:32.450"></td><td><input class="lyric-input" aria-label="Bengali lyric for row ${i+1}" value="${esc(x.text)}" placeholder="বাংলা লিরিক্স লিখুন"></td><td><div class="rowtools"><button class="btn small" title="Move up" onclick="moveRow(${i},-1)" ${i===0?'disabled':''}>↑</button><button class="btn small" title="Move down" onclick="moveRow(${i},1)" ${i===items.length-1?'disabled':''}>↓</button><button class="btn small danger" title="Delete row" onclick="deleteRow(${i})">×</button></div></td></tr>`).join('');$('rowCount').textContent=items.length}
function readRows(){const trs=[...document.querySelectorAll('.lyric-row')];if(trs.length>80)throw new Error('Maximum 80 lyric lines are supported by the current ESP32 firmware.');const result=trs.map((tr)=>({time_ms:parseTime(tr.querySelector('.time-input').value),text:tr.querySelector('.lyric-input').value.trim()}));if(!result.length)throw new Error('Add at least one lyric line.');for(let i=0;i<result.length;i++){if(!result[i].text)throw new Error('Lyric row '+(i+1)+' is empty.');if(i&&result[i].time_ms<result[i-1].time_ms)throw new Error('Timestamps must be in ascending order. Fix row '+(i+1)+' or reorder the rows.')}return result}
function currentRowsUnsafe(){return [...document.querySelectorAll('.lyric-row')].map(tr=>{let t=0;try{t=parseTime(tr.querySelector('.time-input').value)}catch{}return {time_ms:t,text:tr.querySelector('.lyric-input').value}})}
function addRow(){const a=currentRowsUnsafe();if(a.length>=80){toast('The firmware limit is 80 lyric lines.',true);return}a.push({time_ms:a.length?(a[a.length-1].time_ms+3000):0,text:''});renderRows(a);const ins=document.querySelectorAll('.lyric-input');if(ins.length)ins[ins.length-1].focus()}
function moveRow(i,d){const a=currentRowsUnsafe(),j=i+d;if(j<0||j>=a.length)return;[a[i],a[j]]=[a[j],a[i]];renderRows(a)}
function deleteRow(i){const a=currentRowsUnsafe();a.splice(i,1);renderRows(a)}
async function loadLyrics(){try{const d=await api('/api/state');renderRows(d.lyrics);toast('Lyrics loaded.');updateState(d)}catch(e){toast(e.message,true)}}
async function saveDraft(){try{const lyrics=readRows();const d=await api('/api/save',{lyrics});renderRows(d.lyrics);toast('Draft saved to lyrics.json. Bitmaps have not been rebuilt yet.')}catch(e){toast(e.message,true)}}
async function publish(){let lyrics;try{lyrics=readRows()}catch(e){toast(e.message,true);return}const b=$('publishBtn');b.disabled=true;b.textContent='Building bitmaps…';$('buildBadge').textContent='Working';$('buildLog').textContent='Generating shaped Bengali bitmaps. This may take a little while…';try{const d=await api('/api/publish',{lyrics});renderRows(d.lyrics);$('buildLog').textContent=d.output||'Build finished.';$('buildBadge').textContent='Build successful';$('preview').src='/api/preview.png?t='+Date.now();toast(d.message||'Bitmaps generated and ESP32 reload requested.')}catch(e){$('buildBadge').textContent='Build failed';$('buildLog').textContent=e.message;toast(e.message,true)}finally{b.disabled=false;b.textContent='Generate bitmaps + Sync ESP32';refreshState()}}
async function serverAction(action){try{const d=await api('/api/server',{action});toast(d.message);updateState(d.state||d)}catch(e){toast(e.message,true)}finally{refreshState()}}
async function sendCommand(command){try{const d=await api('/api/command',{command});toast(d.message);updateState(d.state||d)}catch(e){toast(e.message,true)}finally{refreshState()}}
function updateState(d){const s=d.server||{};const running=!!s.running;$('serverDot').className='dot'+(running?' ok':'');$('serverLabel').textContent=s.managed_by_panel?'Content server online':(s.port_in_use?'External server occupies port 8000':(running?'Content server online':'Content server offline'));$('serverBadge').textContent=s.managed_by_panel?'Running':(s.port_in_use?'External process':(running?'Running':'Stopped'));$('serverUrl').textContent=s.base_url||'http://—:8000';$('pcIp').textContent=s.pc_ip||'Unknown';const c=d.control||{};$('commandBadge').textContent=c.command?('Command: '+c.command):'No command';$('lastCommand').textContent=c.command||'—';$('lastSeq').textContent=c.seq??0;if(d.build_output){$('buildLog').textContent=d.build_output}}
async function refreshState(){if(refreshBusy)return;refreshBusy=true;try{updateState(await api('/api/state'))}catch(e){$('serverLabel').textContent='Control panel API unavailable'}finally{refreshBusy=false}}
loadLyrics();refreshState();setInterval(refreshState,3000);
</script></body></html>'''

class QuietStaticHandler(SimpleHTTPRequestHandler):
    """Static-file handler for the ESP32 content server; keep the console quiet."""
    def log_message(self, fmt, *args):
        pass


class ControlManager:
    def __init__(self):
        # Run the static content server in a thread in this same Python process.
        # This avoids failures from spawning `python -m http.server` in unusual
        # Python installations where the child process cannot resolve that module.
        self.content_server = None
        self.content_thread = None
        self.last_build_output = "No build run in this session."
        self.lock = threading.RLock()
        self.ensure_files()

    def ensure_files(self):
        if not WEB.is_dir():
            WEB.mkdir(parents=True, exist_ok=True)
        if not LYRICS_FILE.exists():
            LYRICS_FILE.write_text(json.dumps({"audio":"/songs/song.mp3","lyrics":DEFAULT_LYRICS},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        if not CONTROL_FILE.exists():
            self.write_control("stop", seq=0)

    def lan_ip(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except OSError:
            try:
                return socket.gethostbyname(socket.gethostname())
            except OSError:
                return "127.0.0.1"

    def port_in_use(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.25)
            return s.connect_ex(("127.0.0.1", SERVER_PORT)) == 0

    def running(self):
        return (self.content_server is not None and
                self.content_thread is not None and self.content_thread.is_alive())

    def server_state(self):
        own_running = self.running()
        occupied = self.port_in_use()
        ip = self.lan_ip()
        external = occupied and not own_running
        return {"running": own_running or external,
                "managed_by_panel": own_running, "port_in_use": external,
                "port": SERVER_PORT, "pc_ip": ip, "base_url": f"http://{ip}:{SERVER_PORT}"}

    def start_server(self):
        with self.lock:
            if self.running():
                return {"ok": True, "message": "Content server is already running."}
            if self.port_in_use():
                return {"ok": False, "message": "Port 8000 is already occupied. Stop your old HTTP server in its original terminal first, then click Start server here."}
            if not WEB.is_dir():
                WEB.mkdir(parents=True, exist_ok=True)
            try:
                handler = partial(QuietStaticHandler, directory=str(WEB))
                self.content_server = ThreadingHTTPServer(("0.0.0.0", SERVER_PORT), handler)
                self.content_server.daemon_threads = True
                self.content_thread = threading.Thread(
                    target=self.content_server.serve_forever,
                    kwargs={"poll_interval": 0.25},
                    name="BitmapLyricsContentServer",
                    daemon=True,
                )
                self.content_thread.start()
                time.sleep(0.15)
                if not self.content_thread.is_alive():
                    self.content_server.server_close()
                    self.content_server = None
                    self.content_thread = None
                    return {"ok": False, "message": "Content server failed to start. Check whether port 8000 is available."}
            except OSError as exc:
                if self.content_server is not None:
                    try: self.content_server.server_close()
                    except OSError: pass
                self.content_server = None
                self.content_thread = None
                return {"ok": False, "message": f"Could not start content server on port 8000: {exc}"}
            return {"ok": True, "message": f"Content server started on port {SERVER_PORT}."}

    def stop_server(self):
        with self.lock:
            if self.content_server is None:
                return {"ok": True, "message": "The panel has no content server running. If port 8000 is occupied, stop the old server in its original terminal."}
            server = self.content_server
            thread = self.content_thread
            try:
                server.shutdown()
                server.server_close()
                if thread is not None and thread.is_alive():
                    thread.join(timeout=3)
            finally:
                self.content_server = None
                self.content_thread = None
            return {"ok": True, "message": "Content server stopped. The control panel is still available."}

    def write_control(self, command, seq=None):
        old = {"seq": 0, "command": "stop"}
        if CONTROL_FILE.exists():
            try:
                parsed = json.loads(CONTROL_FILE.read_text(encoding="utf-8"))
                if isinstance(parsed, dict): old = parsed
            except (OSError, json.JSONDecodeError): pass
        if seq is None:
            try: seq = int(old.get("seq", 0)) + 1
            except (TypeError, ValueError): seq = 1
        payload = {"seq": int(seq), "command": str(command)}
        CONTROL_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp = CONTROL_FILE.with_suffix(".json.tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, CONTROL_FILE)
        return payload

    def read_control(self):
        try:
            data = json.loads(CONTROL_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict): return {"seq": int(data.get("seq", 0)), "command": str(data.get("command", "stop"))}
        except (OSError, ValueError, json.JSONDecodeError): pass
        return {"seq": 0, "command": "stop"}

    def validate_lyrics(self, payload):
        if not isinstance(payload, dict) or not isinstance(payload.get("lyrics"), list):
            raise ValueError("Expected a lyrics array.")
        lyrics = payload["lyrics"]
        if not lyrics: raise ValueError("Add at least one lyric line.")
        if len(lyrics) > 80: raise ValueError("Maximum 80 lyrics are supported by the current firmware.")
        normal = []
        prev = -1
        for i, item in enumerate(lyrics, 1):
            if not isinstance(item, dict): raise ValueError(f"Row {i} is invalid.")
            t = item.get("time_ms")
            # Backward compatibility: older drafts stored integer seconds in `time`.
            if t is None and "time" in item:
                legacy = item.get("time")
                if isinstance(legacy, bool) or not isinstance(legacy, int) or legacy < 0:
                    raise ValueError(f"Row {i}: timestamp must be non-negative milliseconds or legacy whole seconds.")
                t = legacy * 1000
            text = item.get("text")
            if isinstance(t, bool) or not isinstance(t, int) or t < 0: raise ValueError(f"Row {i}: timestamp must be a non-negative integer number of milliseconds.")
            if t < prev: raise ValueError("Timestamps must be in ascending order. Reorder rows or fix their times.")
            if not isinstance(text, str) or not text.strip(): raise ValueError(f"Row {i}: lyric text cannot be empty.")
            normal.append({"time_ms": t, "text": text.strip()})
            prev = t
        old_audio = "/songs/song.mp3"
        try:
            existing = json.loads(LYRICS_FILE.read_text(encoding="utf-8"))
            if isinstance(existing, dict): old_audio = existing.get("audio", old_audio)
        except Exception: pass
        return {"audio": old_audio, "lyrics": normal}

    def read_lyrics(self):
        try:
            data = json.loads(LYRICS_FILE.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict) and isinstance(data.get("lyrics"), list):
                lyrics = data["lyrics"]
                if lyrics:
                    normalized = []
                    for item in lyrics:
                        if not isinstance(item, dict):
                            continue
                        if isinstance(item.get("time_ms"), int) and not isinstance(item.get("time_ms"), bool):
                            t_ms = item["time_ms"]
                        elif isinstance(item.get("time"), int) and not isinstance(item.get("time"), bool):
                            t_ms = item["time"] * 1000
                        else:
                            continue
                        normalized.append({"time_ms": t_ms, "text": str(item.get("text", ""))})
                    if normalized: return normalized
        except (OSError, json.JSONDecodeError): pass
        return DEFAULT_LYRICS

    def save(self, payload):
        doc = self.validate_lyrics(payload)
        LYRICS_FILE.write_text(json.dumps(doc, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        return doc["lyrics"]

    def build(self):
        if not GENERATOR.is_file():
            raise RuntimeError(f"Missing generator: {GENERATOR.name}. Extract all files from the control panel ZIP into your project folder.")
        proc = subprocess.run([sys.executable, str(GENERATOR)], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
        self.last_build_output = ((proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")).strip()
        if proc.returncode != 0:
            raise RuntimeError(self.last_build_output or f"Generator failed with exit code {proc.returncode}.")
        return self.last_build_output

manager = ControlManager()

class Handler(BaseHTTPRequestHandler):
    server_version = "BitmapLyricsStudio/1.0"
    def log_message(self, fmt, *args):
        # Keep the console quiet; content server logs go to their own file.
        pass
    def send_bytes(self, status, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, str): body = body.encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)
    def send_json(self, status, data): self.send_bytes(status, json.dumps(data, ensure_ascii=False).encode("utf-8"))
    def read_body(self):
        n = int(self.headers.get("Content-Length", "0"))
        if n <= 0 or n > MAX_BODY: raise ValueError("Request body is empty or too large.")
        try: return json.loads(self.rfile.read(n).decode("utf-8"))
        except json.JSONDecodeError as exc: raise ValueError("Invalid JSON request body.") from exc
    def state(self):
        return {"server": manager.server_state(), "lyrics": manager.read_lyrics(), "control": manager.read_control(), "build_output": manager.last_build_output}
    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/" or p == "/index.html": return self.send_bytes(200, INDEX_HTML, "text/html; charset=utf-8")
        if p == "/api/state": return self.send_json(200, self.state())
        if p == "/api/preview.png":
            preview = ROOT / "lyric_preview.png"
            if not preview.is_file(): return self.send_bytes(404, b"No preview yet. Generate the bitmaps first.", "text/plain; charset=utf-8")
            return self.send_bytes(200, preview.read_bytes(), "image/png")
        if p == "/favicon.ico": return self.send_bytes(204, b"", "image/x-icon")
        return self.send_bytes(404, {"ok":False,"message":"Not found"})
    def do_POST(self):
        p = urlparse(self.path).path
        try:
            data = self.read_body()
            if p == "/api/server":
                action = data.get("action") if isinstance(data, dict) else None
                if action == "start": result = manager.start_server()
                elif action == "stop": result = manager.stop_server()
                elif action == "restart":
                    manager.stop_server(); time.sleep(0.25); result = manager.start_server()
                    if result.get("ok"): result["message"] = "Content server restarted on port 8000."
                else: raise ValueError("Unknown server action.")
                result["state"] = {"server": manager.server_state(), "control": manager.read_control()}
                return self.send_json(200 if result.get("ok") else 409, result)
            if p == "/api/save":
                lyrics = manager.save(data)
                return self.send_json(200, {"ok":True,"message":"Draft saved.","lyrics":lyrics})
            if p == "/api/publish":
                lyrics = manager.save(data)
                output = manager.build()
                # Ensure the ESP32 can fetch the fresh manifest and bitmaps.
                start_result = manager.start_server()
                if not start_result.get("ok"):
                    return self.send_json(409, {"ok":False,"message":"Bitmaps were generated, but the content server could not start. "+start_result.get("message", ""),"output":output})
                command = manager.write_control("reload")
                state = {"server": manager.server_state(), "control": command}
                return self.send_json(200, {"ok":True,"message":"Bitmaps generated. Reload was sent to the ESP32; wait for 'Lyrics updated', then press Play lyrics.","lyrics":lyrics,"output":output,"state":state})
            if p == "/api/command":
                command = data.get("command") if isinstance(data, dict) else None
                if command not in {"play", "stop", "restart", "reload"}: raise ValueError("Unknown command.")
                if not manager.server_state()["running"]:
                    return self.send_json(409, {"ok":False,"message":"Start the content server first. The ESP32 receives playback commands from control.json over that server."})
                cmd = manager.write_control(command)
                return self.send_json(200, {"ok":True,"message":f"'{command}' command queued for the ESP32.","state":{"server":manager.server_state(),"control":cmd}})
            return self.send_json(404, {"ok":False,"message":"Not found"})
        except ValueError as exc:
            return self.send_json(400, {"ok":False,"message":str(exc)})
        except subprocess.TimeoutExpired:
            return self.send_json(500, {"ok":False,"message":"Bitmap generation timed out after 4 minutes."})
        except Exception as exc:
            return self.send_json(500, {"ok":False,"message":str(exc)})

def main():
    global UI_PORT
    httpd = None
    last_error = None
    # If the usual UI port is occupied, choose the next free local port.
    for candidate in range(8080, 8100):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            UI_PORT = candidate
            break
        except OSError as exc:
            last_error = exc
    if httpd is None:
        raise SystemExit(f"Could not find a free control panel port between 8080 and 8099: {last_error}")
    httpd.daemon_threads = True
    url = f"http://127.0.0.1:{UI_PORT}"
    print(f"Bitmap Lyrics Studio is running at {url}")
    print("Keep this window open while using the control panel.")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try: httpd.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt: print("\nControl panel closing...")
    finally:
        manager.stop_server()
        httpd.server_close()

if __name__ == "__main__": main()
