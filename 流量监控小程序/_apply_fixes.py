"""Apply all fixes to deepseek_monitor.py"""
import os

BASE = r'C:\Users\寻逆啊\Claude'

# 1. Read new UI
with open(os.path.join(BASE, 'new_ui_v3.html'), 'r', encoding='utf-8') as f:
    new_html = f.read()

# 2. Read target
target = os.path.join(BASE, 'deepseek_monitor.py')
with open(target, 'r', encoding='utf-8') as f:
    content = f.read()

# 3. Replace HTML block
start = content.find("HTML = r'''")
end = content.find("</script></body></html>'''", start) + len("</script></body></html>'''")
if start == -1 or end == -1:
    print('ERROR: HTML block not found')
    exit(1)
content = content[:start] + "HTML = r'''" + new_html + "'''" + content[end:]

# 4. Update window size: 660,540 -> 720,580
content = content.replace('ww,wh=660,540', 'ww,wh=720,580')
# 5. Update min_size: 500,420 -> 540,460
content = content.replace('min_size=(500,420)', 'min_size=(540,460)')

# 6. Update do_POST to add /api/close and /api/brightness routes
old_post = '''    def do_POST(self):
        if urlparse(self.path).path == "/api/config": self._cfg_post()
        else: self._json({"error":True,"msg":"404"},404)'''
new_post = '''    def do_POST(self):
        p = urlparse(self.path).path
        if p == "/api/config": self._cfg_post()
        elif p == "/api/close": self._close()
        elif p == "/api/brightness": self._brightness()
        else: self._json({"error":True,"msg":"404"},404)'''
content = content.replace(old_post, new_post)

# 7. Add _close method (after _cfg_post method)
old_cfg_post_end = '''        if chg: sc(c); global _cache; _cl.acquire(); _cache.clear(); _cl.release()
        self._json({"ok":True})'''
old_cfg_post_end_v2 = '''        if chg: sc(c); global _cache; _cl.acquire(); _cache.clear(); _cl.release()
        self._json({"ok":True})


# ═════════ Pin ═════════'''

new_cfg_post_end = '''        if "opacity" in body:
            try:
                op = int(body["opacity"])
                if 10 <= op <= 100:
                    c["opacity"] = op
                    chg = True
            except: pass
        if chg: sc(c); global _cache; _cl.acquire(); _cache.clear(); _cl.release()
        self._json({"ok":True})

    def _close(self):
        self._json({"ok":True})
        def s():
            import time as _t
            _t.sleep(0.3)
            os._exit(0)
        threading.Thread(target=s, daemon=True).start()

    def _brightness(self):
        try:
            body = json.loads(self._rb())
        except:
            self._json({"error":True,"msg":"Bad JSON"},400); return
        op = int(body.get("opacity", 100))
        if op < 10: op = 10
        if op > 100: op = 100
        c = lc(); c["opacity"] = op; sc(c)
        ok = set_window_opacity(op)
        self._json({"ok":True, "opacity":op, "win32":ok})


# ═════════ Window Opacity ═════════
def set_window_opacity(opacity_pct):
    try:
        import ctypes
        h = win32gui.FindWindow(None, "DeepSeek Monitor")
        if not h: return False
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x80000
        LWA_ALPHA = 0x2
        ex = ctypes.windll.user32.GetWindowLongW(h, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(h, GWL_EXSTYLE, ex | WS_EX_LAYERED)
        alpha = int(opacity_pct * 255 / 100)
        ctypes.windll.user32.SetLayeredWindowAttributes(h, 0, alpha, LWA_ALPHA)
        return True
    except Exception as e:
        print(f"  [opacity] Win32 failed: {e}")
        return False


# ═════════ Pin ═════════'''

content = content.replace(old_cfg_post_end + '\n\n\n# ═════════ Pin ═════════', new_cfg_post_end)

# 8. Update _cfg_get to include saved opacity
old_cfg_get = '''    def _cfg_get(self):
        c = lc(); a = c.get("api_key",""); u = c.get("user_token","")
        self._json({"api_key_display":a[:8]+"***" if a else "","has_api_key":bool(a),
            "user_token_masked":bool(u),"has_user_token":bool(u),"opacity":float(c.get("opacity",1.0))})'''
new_cfg_get = '''    def _cfg_get(self):
        c = lc(); a = c.get("api_key",""); u = c.get("user_token","")
        self._json({"api_key_display":a[:8]+"***" if a else "","has_api_key":bool(a),
            "user_token_masked":bool(u),"has_user_token":bool(u),"opacity":int(c.get("opacity",100))})'''
content = content.replace(old_cfg_get, new_cfg_get)

# 9. Update _cfg_post to handle opacity
old_cfg_post_body = '''        c = lc(); chg = False
        if "api_key" in body and body["api_key"] and body["api_key"].strip() and "***" not in body["api_key"]:
            c["api_key"] = body["api_key"].strip(); chg = True
        if "user_token" in body and body["user_token"] and body["user_token"].strip() and body["user_token"].strip()!="••••••••":
            c["user_token"] = body["user_token"].strip(); chg = True
        if chg: sc(c); global _cache; _cl.acquire(); _cache.clear(); _cl.release()
        self._json({"ok":True})'''
# This is the OLD version before my prev edit, which now has opacity handling
# Let me check what the current version looks like after my edit above
# Actually, the replacement above already handles this. Let me just make sure.
# The _cfg_post change is already included in step 7 above.

# 10. Update af() in main() to apply saved opacity after pin
old_af = '''    def af():
        for _ in range(40):
            time.sleep(.1);h=win32gui.FindWindow(None,"DeepSeek Monitor")
            if h: pin(h);threading.Thread(target=kb,args=(h,),daemon=True).start();break'''
new_af = '''    def af():
        for _ in range(40):
            time.sleep(.1);h=win32gui.FindWindow(None,"DeepSeek Monitor")
            if h:
                pin(h)
                threading.Thread(target=kb,args=(h,),daemon=True).start()
                # Apply saved opacity
                try:
                    saved_op = lc().get("opacity", 100)
                    if saved_op != 100:
                        set_window_opacity(saved_op)
                except: pass
                break'''
content = content.replace(old_af, new_af)

# Write back
with open(target, 'w', encoding='utf-8') as f:
    f.write(content)

print('SUCCESS: All fixes applied')
print('  - HTML block replaced (glassmorphism v3)')
print('  - Window size: 720x580')
print('  - Min size: 540x460')
print('  - /api/close + /api/brightness endpoints added')
print('  - Window opacity (WS_EX_LAYERED) support added')
print('  - _cfg_get/_cfg_post updated for opacity')
print('  - af() applies saved opacity on startup')
