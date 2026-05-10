#!/usr/bin/env python3
"""DeepSeek Token Monitor v5.0 — Windows Desktop Widget"""

import json, os, sys, time, threading, ctypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from pathlib import Path
import requests, webview
import win32gui, win32con, win32api

BASE = Path(__file__).parent
CFG = BASE / "deepseek_config.json"
PORT = 9876
TTL = 60

def lc():
    if CFG.exists():
        try: return json.loads(CFG.read_text(encoding="utf-8"))
        except: pass
    return {}
def sc(c): CFG.write_text(json.dumps(c, indent=2, ensure_ascii=False), encoding="utf-8")
def ak(): return lc().get("api_key","") or os.environ.get("DEEPSEEK_API_KEY","")
def ut(): return lc().get("user_token","")

def fb(k):
    r = requests.get("https://api.deepseek.com/user/balance",
        headers={"Authorization":f"Bearer {k}","Accept":"application/json"}, timeout=15)
    if r.status_code!=200: return {"error":True,"status":r.status_code,"msg":f"Err {r.status_code}"}
    d = r.json(); inf = d.get("balance_infos",[])
    if not inf: return {"error":True,"msg":"No data"}
    i = inf[0]
    return {"error":False,"total_balance":round(float(i.get("total_balance",0)),2),
        "granted_balance":round(float(i.get("granted_balance",0)),2),
        "topped_up_balance":round(float(i.get("topped_up_balance",0)),2),
        "currency":i.get("currency","CNY")}

def fu(tk, y, m):
    t = tk
    try:
        p = json.loads(tk)
        if isinstance(p,dict) and "value" in p: t = p["value"]
    except: pass
    r = requests.get(f"https://platform.deepseek.com/api/v0/usage/cost?month={m:02d}&year={y}",
        headers={"Authorization":f"Bearer {t}","User-Agent":"Mozilla/5.0",
            "Referer":"https://platform.deepseek.com/usage","Accept":"application/json"}, timeout=20)
    if r.status_code!=200: return {"error":True,"status":r.status_code,"msg":f"API err {r.status_code}"}
    d = r.json()
    if d.get("code") and d["code"]!=0: return {"error":True,"msg":str(d.get("msg",d["code"]))}
    return {"error":False,"raw":d}

def parse(raw):
    bd = raw.get("data",{}).get("biz_data",[])
    if not bd: return {"error":True,"msg":"No data"}
    b = bd[0]; days_raw = b.get("days",[]); total_models = b.get("total",[])
    dl, mt, tc = [], {}, 0.0
    for day in days_raw:
        date = day.get("date",""); dt = 0.0; dm = {}
        for mi in day.get("data",[]):
            model = mi.get("model","unknown")
            amt = sum(float(u.get("amount",0)) for u in mi.get("usage",[]))
            dt += amt; dm[model] = {"cost":round(amt,4)}
            if model not in mt: mt[model] = {"cost":0.0}
            mt[model]["cost"] += amt
        tc += dt; dl.append({"date":date,"total_cost":round(dt,4),"models":dm})
    pt = sum(sum(float(u.get("amount",0)) for u in m.get("usage",[])) for m in total_models)
    for m,i in mt.items(): i["cost"] = round(i["cost"],2)
    return {"error":False,"currency":b.get("currency","CNY"),
        "total_cost":round(pt or tc,2),"daily":dl,
        "model_summary":[{"model":m,"cost":i["cost"]} for m,i in mt.items()]}

_cache = {}; _cl = threading.Lock()
def cfetch(k, fetcher):
    with _cl:
        e = _cache.get(k)
        if e and time.time()-e["ts"]<TTL: return e["data"]
    d = fetcher()
    with _cl: _cache[k] = {"ts":time.time(),"data":d}
    return d

# ═════════ HTML v6.0 ═════════
HTML = r'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>DeepSeek Monitor</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
:root{--r:20px;--gap:10px;--glass:rgba(255,255,255,0.10);--glass2:rgba(255,255,255,0.17);--border:rgba(255,255,255,0.10);--border2:rgba(255,255,255,0.18);--text:#f1f5f9;--dim:#a0aec0;--faint:#718096;--accent:#818cf8;--cyan:#22d3ee;--amber:#fbbf24;--purple:#a78bfa;--green:#34d399;--red:#f87171}
*{margin:0;padding:0;box-sizing:border-box}
html{background:transparent;border-radius:20px;overflow:hidden}
body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:transparent;color:var(--text);font-size:14px;line-height:1.45;overflow:hidden;border-radius:20px;position:relative}
.orb{position:fixed;border-radius:50%;filter:blur(100px);pointer-events:none;z-index:0}
.orb-a{width:260px;height:260px;background:rgba(99,102,241,0.12);top:-100px;right:-50px}
.orb-b{width:220px;height:220px;background:rgba(34,211,238,0.08);bottom:-80px;left:-60px}
.orb-c{width:180px;height:180px;background:rgba(167,139,250,0.08);top:40%;left:50%;transform:translate(-50%,-50%)}
.app{position:relative;z-index:1;display:flex;flex-direction:column;height:100vh}
.hd{display:flex;align-items:center;justify-content:space-between;height:36px;padding:0 14px;background:rgba(255,255,255,0.05);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-bottom:1px solid var(--border);flex-shrink:0}
.hd-l{display:flex;align-items:center;gap:7px;font-size:14px;font-weight:600}
.hd-l .logo{font-size:17px;line-height:1}
.hd-r{display:flex;gap:2px;align-items:center}
.hd-r button{width:30px;height:30px;border-radius:8px;border:none;background:none;color:var(--dim);cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;transition:all .2s}
.hd-r button:hover{background:rgba(255,255,255,0.10);color:var(--text)}
.hd-r button:focus-visible{outline:2px solid var(--accent);outline-offset:-2px;border-radius:8px}
.hd-r .btn-x:hover{background:var(--red);color:#fff}
.main{flex:1;display:flex;flex-direction:column;gap:var(--gap);padding:10px 12px 12px;overflow-y:auto;overflow-x:hidden}
.row{display:flex;gap:var(--gap);flex-shrink:0}
.row:last-child{flex:1;min-height:0}
.glass{background:var(--glass);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);border:1px solid var(--border);border-radius:var(--r);transition:all .3s ease}
.glass:hover{background:var(--glass2);border-color:var(--border2)}
.metric{padding:16px 18px;flex:1;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;gap:4px;position:relative;overflow:hidden}
.metric .m-lbl{font-size:13px;color:var(--dim);font-weight:500;letter-spacing:.3px}
.metric .m-val{font-size:30px;font-weight:700;line-height:1.1;color:var(--text)}
.metric .m-val.cost{color:var(--amber)}
.metric .m-val.calls{color:var(--cyan)}
.metric .m-sub{font-size:12px;color:var(--faint);margin-top:2px;display:flex;align-items:center;gap:5px}
.metric .m-sub .dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.metric .m-sub .dot.live{background:var(--green);box-shadow:0 0 8px rgba(52,211,153,0.5)}
.model-card{padding:16px 18px;flex:1;display:flex;align-items:center;gap:14px}
.model-card .m-ic{width:42px;height:42px;border-radius:12px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:19px}
.model-card .m-ic.flash{background:rgba(251,191,36,0.18);color:var(--amber)}
.model-card .m-ic.pro{background:rgba(167,139,250,0.18);color:var(--purple)}
.model-card .m-mid{flex:1;min-width:0}
.model-card .m-name{font-size:15px;font-weight:600;color:var(--text);margin-bottom:3px}
.model-card .m-tok{font-size:12px;color:var(--dim)}
.model-card .m-pb{height:4px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden;margin-top:6px;width:80%}
.model-card .m-pb .m-pf{height:100%;border-radius:2px;transition:width .6s ease}
.model-card .m-pb .m-pf.flash-bar{background:var(--amber)}
.model-card .m-pb .m-pf.pro-bar{background:var(--purple)}
.model-card .m-r{text-align:right;flex-shrink:0}
.model-card .m-cost{font-size:18px;font-weight:600;color:var(--text)}
.model-card .m-rate{font-size:12px;color:var(--faint)}
.chart-card{padding:14px 18px;flex:1;display:flex;flex-direction:column;min-height:0}
.chart-hd{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;flex-shrink:0}
.chart-hd .ch-l{font-size:13px;font-weight:500;color:var(--text)}
.chart-hd .ch-r{font-size:12px;color:var(--dim)}
.chart-sub{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;flex-shrink:0}
.chart-sub span{font-size:12px;color:var(--dim)}
.cw{position:relative;flex:1;min-height:0}
.cw canvas{width:100%!important;height:100%!important}
.mo{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);z-index:100;align-items:center;justify-content:center}
.mo.on{display:flex}
.mm{background:rgba(20,16,50,0.92);backdrop-filter:blur(30px);-webkit-backdrop-filter:blur(30px);border:1px solid var(--border2);border-radius:24px;padding:24px;width:380px;max-width:92vw;max-height:82vh;overflow-y:auto}
.mm h3{font-size:16px;font-weight:600;margin-bottom:16px;color:var(--text)}
.mm .fg{margin-bottom:14px}
.mm .fg label{font-size:12px;color:var(--dim);display:block;margin-bottom:5px;font-weight:500}
.mm .fg input{width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:rgba(255,255,255,0.05);color:var(--text);font-size:13px;outline:none;transition:border-color .2s}
.mm .fg input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(129,140,248,0.15)}
.mm .hint{font-size:11px;color:var(--faint);margin-top:4px;line-height:1.4}
.mm .hint a{color:var(--cyan);text-decoration:none}
.btn{padding:8px 18px;border-radius:10px;border:1px solid var(--border);background:rgba(255,255,255,0.05);color:var(--text);font-size:13px;cursor:pointer;transition:all .2s;font-weight:500}
.btn:hover{background:rgba(255,255,255,0.10);border-color:var(--border2)}
.btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.btn-p{background:var(--accent);border-color:var(--accent);color:#fff}
.btn-p:hover{background:#6d76e0}
.mm .bt{display:flex;gap:10px;justify-content:flex-end;margin-top:18px}
.rg{display:flex;align-items:center;gap:10px}.rg span{font-size:11px;color:var(--dim);flex-shrink:0}
.rg input[type=range]{flex:1;-webkit-appearance:none;height:5px;border-radius:3px;background:rgba(255,255,255,0.08);outline:none;cursor:pointer}
.rg input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;border-radius:50%;background:var(--accent);cursor:pointer;box-shadow:0 0 10px rgba(129,140,248,0.5)}
.toast{position:fixed;top:42px;left:50%;transform:translateX(-50%) translateY(-12px);background:rgba(20,16,50,0.92);backdrop-filter:blur(30px);-webkit-backdrop-filter:blur(30px);border:1px solid var(--border2);color:var(--text);padding:8px 20px;border-radius:22px;font-size:13px;font-weight:500;opacity:0;transition:all .3s ease;pointer-events:none;z-index:200;box-shadow:0 8px 32px rgba(0,0,0,0.6)}
.toast.on{opacity:1;transform:translateX(-50%) translateY(0)}
.toast.err{border-color:rgba(248,113,113,0.35);color:var(--red)}
.emp{text-align:center;padding:18px 10px;color:var(--dim);font-size:13px}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.05);border-radius:2px}::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,0.10)}
</style></head><body>

<div class="orb orb-a"></div>
<div class="orb orb-b"></div>
<div class="orb orb-c"></div>

<div class="app">
  <header class="hd">
    <div class="hd-l"><span class="logo">&#x1f40b;</span>DeepSeek Monitor</div>
    <div class="hd-r">
      <button onclick="doRefresh()" title="Refresh" aria-label="Refresh">&#x21bb;</button>
      <button onclick="openSettings()" title="Settings" aria-label="Settings">&#x2699;</button>
      <button class="btn-x" onclick="doClose()" title="Close" aria-label="Close">&times;</button>
    </div>
  </header>

  <main class="main">
    <div class="row">
      <div class="glass metric">
        <div class="m-lbl">账户余额 Balance</div>
        <div class="m-val" id="balance">--</div>
        <div class="m-sub"><span class="dot live"></span> 账户可用</div>
      </div>
      <div class="glass metric">
        <div class="m-lbl">本月消费 Cost</div>
        <div class="m-val cost" id="monthCost">--</div>
        <div class="m-sub" id="tokenSub">-- Tokens</div>
      </div>
      <div class="glass metric">
        <div class="m-lbl">API 请求次数</div>
        <div class="m-val calls" id="apiCalls">--</div>
        <div class="m-sub">本月统计</div>
      </div>
    </div>

    <div class="row">
      <div class="glass model-card" id="flashCard">
        <div class="emp">请在设置中填写 Platform Token</div>
      </div>
      <div class="glass model-card" id="proCard">
        <div class="emp">请在设置中填写 Platform Token</div>
      </div>
    </div>

    <div class="row">
      <div class="glass chart-card">
        <div class="chart-hd"><span class="ch-l">&#x1f4ca; 消耗趋势 Trend</span><span class="ch-r" id="trendTotal"></span></div>
        <div class="cw"><canvas id="trendChart"></canvas></div>
      </div>
      <div class="glass chart-card">
        <div class="chart-hd"><span class="ch-l">按日 Token 消耗</span></div>
        <div class="chart-sub"><span id="dailyRange"></span><span id="dailyMax"></span></div>
        <div class="cw"><canvas id="dailyChart"></canvas></div>
      </div>
    </div>
  </main>
</div>

<div class="mo" id="mOverlay"><div class="mm"><h3>设置 Settings</h3>
  <div class="fg"><label>API Key</label><input type="password" id="apiKeyIn" placeholder="sk-..."><div class="hint"><a href="https://platform.deepseek.com/api_keys" target="_blank">获取 Key</a> 从 DeepSeek 平台</div></div>
  <div class="fg"><label>Platform Token</label><input type="password" id="userTokenIn" placeholder="从浏览器 LocalStorage 获取"><div class="hint">登录 <a href="https://platform.deepseek.com/usage" target="_blank">platform.deepseek.com</a> &gt; F12 &gt; Application &gt; Local Storage &gt; <b>userToken</b></div></div>
  <div class="fg"><label>透明度 Brightness</label><div class="rg"><span>暗</span><input type="range" id="opacityIn" min="30" max="100" value="100" oninput="previewBrightness(this.value)"><span>亮</span></div></div>
  <div class="bt"><button class="btn" onclick="closeSettings()">取消</button><button class="btn btn-p" onclick="saveSettings()">保存</button></div>
</div></div>

<div class="toast" id="toast"></div>

<script>
const $=id=>document.getElementById(id);
const fm=n=>n==null||isNaN(n)?'--':'¥'+n.toFixed(2);
const fc=n=>{if(n==null||isNaN(n))return'--';return n.toLocaleString('en-US')}
const fbl=n=>{if(n>=1e6)return(n/1e6).toFixed(1)+'M';if(n>=1e3)return(n/1e3).toFixed(1)+'K';if(n<=0)return'0';return n.toFixed(0)}
const fmtM=n=>{if(n>=1e6)return(n/1e6).toFixed(2)+'M';if(n>=1e3)return(n/1e3).toFixed(1)+'K';return n.toFixed(0)}
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}
function toast(m,e){const t=$('toast');t.textContent=m;t.className='toast'+(e?' err':'')+' on';setTimeout(()=>t.className='toast',2500)}
async function api(p,o){const r=await fetch(p,o);if(!r.ok)throw Error('HTTP '+r.status);return r.json()}

let tc=null,dc=null;

function doRefresh(){load()}
function doClose(){
  fetch('/api/close',{method:'POST'}).catch(()=>{});
  setTimeout(()=>{try{window.close()}catch(e){}},300);
}
function previewBrightness(v){
  document.body.style.filter='brightness('+(0.4+v/100*0.6)+')';
}

async function load(){
  const cfg=await api('/api/config').catch(()=>({}));
  const bal=await api('/api/balance').catch(e=>({error:true,msg:e.message}));
  if(!bal.error){
    $('balance').textContent=fm(bal.total_balance);
  }
  if(cfg.has_user_token){
    const n=new Date();
    const u=await api('/api/usage?year='+n.getFullYear()+'&month='+(n.getMonth()+1)).catch(e=>({error:true,msg:e.message}));
    if(!u.error){
      $('monthCost').textContent=fm(u.total_cost);
      const estT=Math.round(u.total_cost*3e6);
      $('tokenSub').innerHTML='<span class="dot" style="background:var(--cyan);box-shadow:0 0 6px rgba(34,211,238,0.4);width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:5px;vertical-align:middle"></span>'+fmtM(estT)+' Tokens';
      const todayStr=new Date().toISOString().slice(0,10);
      const recent=u.daily.filter(d=>d.date<=todayStr).slice(-7);
      const recentCosts=recent.map(d=>d.total_cost);
      const recentTotal=recentCosts.reduce((a,b)=>a+b,0);
      $('trendTotal').textContent='Σ '+fmtM(Math.round(recentTotal*3e6))+' T';
      const maxCost=Math.max(...recentCosts,0);
      $('dailyMax').textContent=fmtM(Math.round(maxCost*3e6))+' T';
      const firstDate=recent[0]?.date||'';
      const lastDate=recent[recent.length-1]?.date||'';
      const fd=firstDate?firstDate.slice(5).replace(/^0/,''):'';
      const ld=lastDate?lastDate.slice(5).replace(/^0/,''):'';
      $('dailyRange').textContent=fd+' - '+ld;
      $('apiCalls').textContent=u.daily.reduce((s,d)=>s+Object.keys(d.models).length,0)||'0';
      renderModels(u.model_summary.filter(m=>m.cost>0.001),u.total_cost);
      renderTrendChart(recent);
      renderDailyChart(recent);
    }else{showModelErr(u.msg)}
  }else{showModelEmpty()}
}

function showModelEmpty(){
  const h='<div class="emp">请在设置中填写 Platform Token</div>';
  $('flashCard').innerHTML=h;$('proCard').innerHTML=h;
}
function showModelErr(m){
  const h='<div class="emp" style="color:var(--red)">'+esc(m)+'</div>';
  $('flashCard').innerHTML=h;$('proCard').innerHTML=h;
}

function renderModelCard(cid,m,total,isFlash){
  const nm='DeepSeek-'+(isFlash?'Flash':'Pro');
  const estT=Math.round(m.cost*3e6);
  const pct=total>0?Math.min(100,parseFloat((m.cost/total*100).toFixed(1))):0;
  const card=$(cid);
  card.innerHTML=
    '<div class="m-ic '+(isFlash?'flash':'pro')+'">'+(isFlash?'&#x26a1;':'&#x1f9e0;')+'</div>'+
    '<div class="m-mid"><div class="m-name">'+esc(nm)+'</div>'+
    '<div class="m-tok">'+fc(estT)+' Tokens</div>'+
    '<div class="m-pb"><div class="m-pf '+(isFlash?'flash-bar':'pro-bar')+'" style="width:'+pct+'%"></div></div></div>'+
    '<div class="m-r"><div class="m-cost">'+fm(m.cost)+'</div>'+
    '<div class="m-rate">'+(estT/(m.cost||0.01)/1e6).toFixed(1)+'M T/¥</div></div>';
}

function renderModels(models,total){
  const flash=models.find(m=>(m.model||'').toLowerCase().includes('flash'));
  const pro=models.find(m=>!(m.model||'').toLowerCase().includes('flash'));
  if(flash)renderModelCard('flashCard',flash,total,true);
  else $('flashCard').innerHTML='<div class="emp">暂无 Flash 用量</div>';
  if(pro)renderModelCard('proCard',pro,total,false);
  else $('proCard').innerHTML='<div class="emp">暂无 Pro 用量</div>';
}

const barLabelPlugin={
  id:'barLabels',
  afterDatasetsDraw(chart){
    const ctx=chart.ctx;
    const meta=chart.getDatasetMeta(0);
    if(!meta||meta.hidden)return;
    meta.data.forEach((bar,i)=>{
      const raw=chart._rawData[i]||0;
      ctx.save();
      ctx.fillStyle='#f1f5f9';
      ctx.font='12px -apple-system,"PingFang SC","Microsoft YaHei",sans-serif';
      ctx.textAlign='center';
      ctx.textBaseline='bottom';
      ctx.fillText(fbl(raw*3e6),bar.x,bar.y-2);
      ctx.restore();
    });
  }
};

function renderTrendChart(daily){
  if(!daily||!daily.length)return;
  const costs=daily.map(d=>d.total_cost);
  const maxC=Math.max(...costs,0.01);
  const data=costs.map(c=>c===0?maxC*0.003:c);
  const ctx=$('trendChart').getContext('2d');
  if(tc)tc.destroy();
  const nc=new Chart(ctx,{
    type:'bar',
    data:{
      labels:daily.map(d=>{const p=d.date.slice(5);const parts=p.split('-');return parseInt(parts[0])+'/'+parseInt(parts[1])}),
      datasets:[{data:data,backgroundColor:'rgba(167,139,250,0.65)',borderColor:'#a78bfa',borderWidth:0,borderRadius:{topLeft:4,topRight:4,bottomLeft:0,bottomRight:0},borderSkipped:false}]
    },
    options:{
      responsive:true,maintainAspectRatio:false,animation:{duration:400},
      plugins:{legend:{display:false},tooltip:{enabled:false}},
      scales:{
        x:{grid:{display:false},ticks:{color:'#a0aec0',font:{size:11},maxRotation:0,autoSkip:false}},
        y:{display:false,beginAtZero:true}
      }
    },
    plugins:[barLabelPlugin]
  });
  nc._rawData=costs;
  tc=nc;
}

function renderDailyChart(daily){
  if(!daily||!daily.length)return;
  const costs=daily.map(d=>d.total_cost);
  const maxC=Math.max(...costs,0.01);
  const data=costs.map(c=>c===0?maxC*0.003:c);
  const ctx=$('dailyChart').getContext('2d');
  if(dc)dc.destroy();
  const nc=new Chart(ctx,{
    type:'bar',
    data:{
      labels:daily.map(d=>{const p=d.date.slice(5);const parts=p.split('-');return parseInt(parts[0])+'/'+parseInt(parts[1])}),
      datasets:[{data:data,backgroundColor:'rgba(34,211,238,0.55)',borderColor:'#22d3ee',borderWidth:0,borderRadius:{topLeft:4,topRight:4,bottomLeft:0,bottomRight:0},borderSkipped:false}]
    },
    options:{
      responsive:true,maintainAspectRatio:false,animation:{duration:400},
      plugins:{legend:{display:false},tooltip:{enabled:false}},
      scales:{
        x:{grid:{display:false},ticks:{color:'#a0aec0',font:{size:11},maxRotation:0,autoSkip:false}},
        y:{display:false,beginAtZero:true}
      }
    },
    plugins:[barLabelPlugin]
  });
  nc._rawData=costs;
  dc=nc;
}

async function openSettings(){
  const c=await api('/api/config');
  $('apiKeyIn').value=c.api_key_display||'';
  $('userTokenIn').value='';
  $('opacityIn').value=c.opacity||100;
  $('mOverlay').classList.add('on');
}
function closeSettings(){$('mOverlay').classList.remove('on')}
async function saveSettings(){
  const b={};
  const ak=$('apiKeyIn').value.trim();
  const ut=$('userTokenIn').value.trim();
  const op=$('opacityIn').value;
  if(ak&&!ak.includes('***'))b.api_key=ak;
  if(ut)b.user_token=ut;
  if(op)b.opacity=parseInt(op);
  await api('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});
  closeSettings();toast('已保存');load();
}

$('mOverlay').addEventListener('click',function(e){if(e.target===this)closeSettings()});
(async()=>{
  try{
    const c=await api('/api/config');
    if(c.opacity)previewBrightness(c.opacity);
  }catch(e){}
  load();
  setInterval(load,60000);
})();
</script></body></html>'''


# ═════════ Handler ═════════
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, d, s=200):
        b = json.dumps(d, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(s); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",len(b)); self.end_headers(); self.wfile.write(b)
    def _html(self, s):
        b = s.encode("utf-8"); self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",len(b)); self.end_headers(); self.wfile.write(b)
    def _rb(self):
        n = int(self.headers.get("Content-Length",0))
        return self.rfile.read(n) if n else b""

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ("/","/index.html"): self._html(HTML)
        elif p == "/api/balance": self._bal()
        elif p == "/api/usage": self._usage()
        elif p == "/api/config": self._cfg_get()
        else: self._json({"error":True,"msg":"404"},404)

    def do_POST(self):
        p = urlparse(self.path).path
        if p == "/api/config": self._cfg_post()
        elif p == "/api/close": self._close()
        elif p == "/api/brightness": self._brightness()
        else: self._json({"error":True,"msg":"404"},404)

    def do_OPTIONS(self):
        self.send_response(200); self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type"); self.end_headers()

    def _bal(self):
        k = ak()
        if not k: self._json({"error":True,"msg":"No API Key"},401); return
        try: d = cfetch("balance",lambda:fb(k)); self._json(d,d.get("status",500) if d.get("error") else 200)
        except Exception as e: self._json({"error":True,"msg":str(e)},500)

    def _usage(self):
        t = ut()
        if not t: self._json({"error":True,"msg":"No Platform Token"},401); return
        qs = parse_qs(urlparse(self.path).query); nw = datetime.now()
        y = int(qs.get("year",[str(nw.year)])[0]); m = int(qs.get("month",[str(nw.month)])[0])
        def f():
            raw = fu(t,y,m)
            if raw.get("error"): return raw
            return parse(raw["raw"])
        try: d = cfetch(f"u_{y}_{m}",f); self._json(d,d.get("status",500) if d.get("error") else 200)
        except Exception as e: self._json({"error":True,"msg":str(e)},500)

    def _cfg_get(self):
        c = lc(); a = c.get("api_key",""); u = c.get("user_token","")
        self._json({"api_key_display":a[:8]+"***" if a else "","has_api_key":bool(a),
            "user_token_masked":bool(u),"has_user_token":bool(u),"opacity":int(c.get("opacity",100))})

    def _cfg_post(self):
        try: body = json.loads(self._rb())
        except: self._json({"error":True,"msg":"Bad JSON"},400); return
        c = lc(); chg = False
        if "api_key" in body and body["api_key"] and body["api_key"].strip() and "***" not in body["api_key"]:
            c["api_key"] = body["api_key"].strip(); chg = True
        if "user_token" in body and body["user_token"] and body["user_token"].strip() and body["user_token"].strip()!="••••••••":
            c["user_token"] = body["user_token"].strip(); chg = True
        if "opacity" in body:
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


# ═════════ Pin ═════════
def pin(h):
    try:
        DWMWA=33;DWMCP=2
        v=ctypes.c_uint(DWMCP)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.wintypes.HWND(h),ctypes.c_uint(DWMWA),ctypes.byref(v),ctypes.sizeof(v))
    except: pass
    try: win32gui.SetWindowPos(h,win32con.HWND_BOTTOM,0,0,0,0,win32con.SWP_NOMOVE|win32con.SWP_NOSIZE|win32con.SWP_NOACTIVATE)
    except: pass
def kb(h):
    while True:
        time.sleep(5)
        try: win32gui.SetWindowPos(h,win32con.HWND_BOTTOM,0,0,0,0,win32con.SWP_NOMOVE|win32con.SWP_NOSIZE|win32con.SWP_NOACTIVATE|win32con.SWP_SHOWWINDOW)
        except: break


# ═════════ Entry ═════════
def main():
    print(f"\n  DeepSeek Monitor v5.0\n  http://localhost:{PORT}\n")
    srv = HTTPServer(("127.0.0.1",PORT),Handler)
    threading.Thread(target=srv.serve_forever,daemon=True).start()
    sw=win32api.GetSystemMetrics(0);sh=win32api.GetSystemMetrics(1)
    ww,wh=720,580;x=sw-ww-20;y=20
    def af():
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
                break
    threading.Thread(target=af,daemon=True).start()
    webview.create_window(title="DeepSeek Monitor",url=f"http://localhost:{PORT}",
        width=ww,height=wh,x=x,y=y,min_size=(540,460),resizable=True,frameless=True)
    webview.start();srv.shutdown();print("  Bye.")
if __name__=="__main__":main()
