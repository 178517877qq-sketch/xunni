#!/usr/bin/env python3
"""
Cloudflare IP 优选工具 (TCP筛选 + IP可用性二次筛选 + curl带宽测速 + WxPusher通知)
依赖：requests, curl (系统自带)
配置文件：同目录下的 config.json（请根据需要修改参数）
结果保存到 ip.txt，并自动推送到 GitHub，同时批量更新到 Cloudflare DNS
支持 Windows / Linux
优化：国家过滤前置，减少无效 TCP 测试；重试参数可配置；所有网络请求连接超时分离
"""

import requests
import socket
import time
import sys
import re
import os
import subprocess
import shutil
import json
import ipaddress
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 预编译正则 ====================
NODE_PATTERN = re.compile(r"^(\d+\.\d+\.\d+\.\d+):(\d+)#(.+)$")
IP_PORT_PATTERN = re.compile(r"^(\d+\.\d+\.\d+\.\d+):(\d+)#")

# ==================== 国家代码映射表（全球覆盖）====================
CN_TO_CODE = {
    "阿富汗": "AF", "奥兰群岛": "AX", "阿尔巴尼亚": "AL", "阿尔及利亚": "DZ",
    "美属萨摩亚": "AS", "安道尔": "AD", "安哥拉": "AO", "安圭拉": "AI",
    "南极洲": "AQ", "安提瓜和巴布达": "AG", "阿根廷": "AR", "亚美尼亚": "AM",
    "阿鲁巴": "AW", "澳大利亚": "AU", "奥地利": "AT", "阿塞拜疆": "AZ",
    "巴哈马": "BS", "巴林": "BH", "孟加拉国": "BD", "孟加拉": "BD",
    "巴巴多斯": "BB", "白俄罗斯": "BY", "比利时": "BE", "伯利兹": "BZ",
    "贝宁": "BJ", "百慕大": "BM", "不丹": "BT", "玻利维亚": "BO",
    "波黑": "BA", "波斯尼亚和黑塞哥维那": "BA", "博茨瓦纳": "BW",
    "布维岛": "BV", "巴西": "BR", "英属印度洋领地": "IO",
    "文莱": "BN", "保加利亚": "BG", "布基纳法索": "BF", "布隆迪": "BI",
    "柬埔寨": "KH", "喀麦隆": "CM", "加拿大": "CA", "佛得角": "CV",
    "开曼群岛": "KY", "中非": "CF", "乍得": "TD", "智利": "CL",
    "中国": "CN", "圣诞岛": "CX", "科科斯(基林)群岛": "CC",
    "哥伦比亚": "CO", "科摩罗": "KM", "刚果(布)": "CG", "刚果（布）": "CG",
    "刚果(金)": "CD", "刚果（金）": "CD", "库克群岛": "CK",
    "哥斯达黎加": "CR", "科特迪瓦": "CI", "克罗地亚": "HR", "古巴": "CU",
    "塞浦路斯": "CY", "捷克": "CZ", "丹麦": "DK", "吉布提": "DJ",
    "多米尼克": "DM", "多米尼加": "DO", "厄瓜多尔": "EC", "埃及": "EG",
    "萨尔瓦多": "SV", "赤道几内亚": "GQ", "厄立特里亚": "ER",
    "爱沙尼亚": "EE", "埃塞俄比亚": "ET", "福克兰群岛(马尔维纳斯)": "FK",
    "法罗群岛": "FO", "斐济": "FJ", "芬兰": "FI", "法国": "FR",
    "法属圭亚那": "GF", "法属波利尼西亚": "PF", "法属南部领地": "TF",
    "加蓬": "GA", "冈比亚": "GM", "格鲁吉亚": "GE", "德国": "DE",
    "加纳": "GH", "直布罗陀": "GI", "希腊": "GR", "格陵兰": "GL",
    "格林纳达": "GD", "瓜德罗普": "GP", "关岛": "GU", "危地马拉": "GT",
    "根西岛": "GG", "几内亚": "GN", "几内亚比绍": "GW", "圭亚那": "GY",
    "海地": "HT", "赫德岛和麦克唐纳群岛": "HM", "梵蒂冈": "VA",
    "洪都拉斯": "HN", "香港": "HK", "匈牙利": "HU", "冰岛": "IS",
    "印度": "IN", "印度尼西亚": "ID", "伊朗": "IR", "伊拉克": "IQ",
    "爱尔兰": "IE", "马恩岛": "IM", "以色列": "IL", "意大利": "IT",
    "牙买加": "JM", "日本": "JP", "泽西岛": "JE", "约旦": "JO",
    "哈萨克斯坦": "KZ", "肯尼亚": "KE", "基里巴斯": "KI", "朝鲜": "KP",
    "韩国": "KR", "科威特": "KW", "吉尔吉斯斯坦": "KG", "老挝": "LA",
    "拉脱维亚": "LV", "黎巴嫩": "LB", "莱索托": "LS", "利比里亚": "LR",
    "利比亚": "LY", "列支敦士登": "LI", "立陶宛": "LT", "卢森堡": "LU",
    "澳门": "MO", "北马其顿": "MK", "马其顿": "MK", "马达加斯加": "MG",
    "马拉维": "MW", "马来西亚": "MY", "马尔代夫": "MV", "马里": "ML",
    "马耳他": "MT", "马绍尔群岛": "MH", "马提尼克": "MQ",
    "毛里塔尼亚": "MR", "毛里求斯": "MU", "马约特": "YT", "墨西哥": "MX",
    "密克罗尼西亚": "FM", "摩尔多瓦": "MD", "摩纳哥": "MC", "蒙古": "MN",
    "黑山": "ME", "蒙特塞拉特": "MS", "摩洛哥": "MA", "莫桑比克": "MZ",
    "缅甸": "MM", "纳米比亚": "NA", "瑙鲁": "NR", "尼泊尔": "NP",
    "荷兰": "NL", "新喀里多尼亚": "NC", "新西兰": "NZ", "尼加拉瓜": "NI",
    "尼日尔": "NE", "尼日利亚": "NG", "纽埃": "NU", "诺福克岛": "NF",
    "北马里亚纳群岛": "MP", "挪威": "NO", "阿曼": "OM", "巴基斯坦": "PK",
    "帕劳": "PW", "巴勒斯坦": "PS", "巴拿马": "PA", "巴布亚新几内亚": "PG",
    "巴拉圭": "PY", "秘鲁": "PE", "菲律宾": "PH", "皮特凯恩": "PN",
    "波兰": "PL", "葡萄牙": "PT", "波多黎各": "PR", "卡塔尔": "QA",
    "留尼汪": "RE", "罗马尼亚": "RO", "俄罗斯": "RU", "卢旺达": "RW",
    "圣巴泰勒米": "BL", "圣赫勒拿": "SH", "圣基茨和尼维斯": "KN",
    "圣卢西亚": "LC", "圣马丁": "MF", "圣皮埃尔和密克隆": "PM",
    "圣文森特和格林纳丁斯": "VC", "萨摩亚": "WS", "圣马力诺": "SM",
    "圣多美和普林西比": "ST", "沙特阿拉伯": "SA", "沙特": "SA",
    "塞内加尔": "SN", "塞尔维亚": "RS", "塞舌尔": "SC", "塞拉利昂": "SL",
    "新加坡": "SG", "圣马丁(荷兰)": "SX", "斯洛伐克": "SK",
    "斯洛文尼亚": "SI", "所罗门群岛": "SB", "索马里": "SO", "南非": "ZA",
    "南乔治亚和南桑威奇群岛": "GS", "南苏丹": "SS", "西班牙": "ES",
    "斯里兰卡": "LK", "苏丹": "SD", "苏里南": "SR", "斯瓦尔巴和扬马延": "SJ",
    "斯威士兰": "SZ", "瑞典": "SE", "瑞士": "CH", "叙利亚": "SY",
    "台湾": "TW", "塔吉克斯坦": "TJ", "坦桑尼亚": "TZ", "泰国": "TH",
    "东帝汶": "TL", "多哥": "TG", "托克劳": "TK", "汤加": "TO",
    "特立尼达和多巴哥": "TT", "突尼斯": "TN", "土耳其": "TR",
    "土库曼斯坦": "TM", "特克斯和凯科斯群岛": "TC", "图瓦卢": "TV",
    "乌干达": "UG", "乌克兰": "UA", "阿联酋": "AE", "英国": "GB",
    "美国": "US", "美国本土外小岛屿": "UM", "乌拉圭": "UY",
    "乌兹别克斯坦": "UZ", "瓦努阿图": "VU", "委内瑞拉": "VE",
    "越南": "VN", "英属维尔京群岛": "VG", "美属维尔京群岛": "VI",
    "瓦利斯和富图纳": "WF", "西撒哈拉": "EH", "也门": "YE",
    "赞比亚": "ZM", "津巴布韦": "ZW",
}

# ==================== 加载配置文件 ====================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config():
    """加载 config.json 配置文件，缺失必填字段时抛出异常"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ 错误：未找到配置文件 {CONFIG_FILE}")
        print("请在同目录下创建 config.json 文件，内容参考示例。")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ 错误：配置文件格式不正确 - {e}")
        sys.exit(1)

    defaults = {
        "USE_GLOBAL_MODE": True,
        "GLOBAL_TOP_N": 15,
        "PER_COUNTRY_TOP_N": 1,
        "BANDWIDTH_CANDIDATES": 90,
        "TCP_PROBES": 3,
        "MIN_SUCCESS_RATE": 1.0,
        "TIMEOUT": 2.0,
        "SOCKET_DEFAULT_TIMEOUT": 3,
        "PROGRESS_PRINT_INTERVAL": 1,
        "FILTER_COUNTRIES_ENABLED": False,
        "ALLOWED_COUNTRIES": ["US"],
        "ENABLE_WXPUSHER": True,
        "WXPUSHER_APP_TOKEN": "your_app_token_here",
        "WXPUSHER_UIDS": ["your_uid_here"],
        "WXPUSHER_API_URL": "http://wxpusher.zjiecode.com/api/send/message",
        "NOTIFY_TIMEOUT": 3,
        "NOTIFY_CONNECT_TIMEOUT": 3,
        "CF_ENABLED": True,
        "CF_API_TOKEN": "your_CF_API_TOKEN",
        "CF_ZONE_ID": "your_CF_ZONE_ID",
        "CF_DNS_RECORD_NAME": "your_CF_DNS_RECORD_NAME",
        "CF_TTL": 60,
        "CF_PROXIED": False,
        "CF_DNS_CONNECT_TIMEOUT": 3,
        "CF_DNS_READ_TIMEOUT": 3,
        "ADDITIONAL_SOURCES": [],
        "FETCH_MAX_RETRIES": 3,
        "FETCH_RETRY_DELAY": 3,
        "FETCH_TIMEOUT": 3,
        "FETCH_CONNECT_TIMEOUT": 3,
        "LOCAL_SEED_FILES": ["重要ip.txt", "全量ip.txt"],
        "ENABLE_CF_OFFICIAL_IP_SAMPLING": False,
        "CF_OFFICIAL_IPV4_URL": "https://www.cloudflare.com/ips-v4",
        "CF_OFFICIAL_SAMPLE_PER_24": 3,
        "CF_OFFICIAL_SAMPLE_PORTS": [443],
        "CF_OFFICIAL_COUNTRY_CODE": "CF",
        "OUTPUT_FILE": "ip.txt",
        "OUTPUT_NODE_LIMIT": 24,
        "STABILITY_SCORING_ENABLED": True,
        "STABILITY_STATS_FILE": "ip_stats.json",
        "STABILITY_HISTORY_WEIGHT": 1.0,
        "STABILITY_MAX_BONUS": 35,
        "ENABLE_LOGGING": False,
        "LOG_FILE": "cfnb.log",
        "TEST_AVAILABILITY": True,
        "AVAILABILITY_CHECK_API": "https://api.090227.xyz/check",
        "AVAILABILITY_TIMEOUT": 3,
        "AVAILABILITY_CONNECT_TIMEOUT": 3,
        "AVAILABILITY_RETRY_MAX": 2,
        "AVAILABILITY_RETRY_DELAY": 3,
        "FILTER_IPV6_AVAILABILITY": True,
        "FILTER_BLOCKED_COUNTRIES_ENABLED": True,
        "BLOCKED_COUNTRIES": [
            "BD", "BI", "BY", "CD", "CF", "CN", "CU", "DE", "ET", "HK",
            "IR", "KP", "LY", "MO", "NG", "NL", "PK", "RU", "SD", "SO",
            "SY", "TH", "TW", "UA", "VE", "VN", "YE", "ZW"
        ],
        "DNS_UPDATE_TARGET_COUNT": 15,
        "BANDWIDTH_SIZE_MB": 0.5,
        "BANDWIDTH_TIMEOUT": 3,
        "BANDWIDTH_RETRY_MAX": 2,
        "BANDWIDTH_RETRY_DELAY": 3,
        "BANDWIDTH_URL_TEMPLATE": "https://speed.cloudflare.com/__down?bytes={bytes}",
        "BANDWIDTH_PROCESS_BUFFER": 2,
        "BANDWIDTH_CONNECT_TIMEOUT": 3,
        "MAX_WORKERS": 200,
        "AVAILABILITY_WORKERS": 10,
        "FALLBACK_WORKERS": 10,
        "BANDWIDTH_WORKERS": 10,
        "DNS_UPDATE_MAX_RETRIES": 3,
        "DNS_UPDATE_RETRY_DELAY": 3,
        "GITHUB_SYNC_ENABLED": True,
        "GITHUB_SYNC_PROXY_URL": "",
        "GITHUB_SYNC_MAX_RETRIES": 3,
        "GITHUB_SYNC_RETRY_DELAY": 3,
        "GIT_SYNC_PROCESS_TIMEOUT": 180,
    }

    for key, value in defaults.items():
        if key not in config:
            config[key] = value
            print(f"[WARN] config key {key} missing, using default: {value}")

    return config

cfg = load_config()

USE_GLOBAL_MODE = cfg["USE_GLOBAL_MODE"]
GLOBAL_TOP_N = cfg["GLOBAL_TOP_N"]
PER_COUNTRY_TOP_N = cfg["PER_COUNTRY_TOP_N"]
BANDWIDTH_CANDIDATES = cfg["BANDWIDTH_CANDIDATES"]
TCP_PROBES = cfg["TCP_PROBES"]
MIN_SUCCESS_RATE = cfg["MIN_SUCCESS_RATE"]
TIMEOUT = cfg["TIMEOUT"]
SOCKET_DEFAULT_TIMEOUT = cfg["SOCKET_DEFAULT_TIMEOUT"]
PROGRESS_PRINT_INTERVAL = cfg["PROGRESS_PRINT_INTERVAL"]
FILTER_COUNTRIES_ENABLED = cfg["FILTER_COUNTRIES_ENABLED"]
ALLOWED_COUNTRIES = cfg["ALLOWED_COUNTRIES"]
ENABLE_WXPUSHER = cfg["ENABLE_WXPUSHER"]
WXPUSHER_APP_TOKEN = cfg["WXPUSHER_APP_TOKEN"]
WXPUSHER_UIDS = cfg["WXPUSHER_UIDS"]
WXPUSHER_API_URL = cfg["WXPUSHER_API_URL"]
NOTIFY_TIMEOUT = cfg["NOTIFY_TIMEOUT"]
NOTIFY_CONNECT_TIMEOUT = cfg["NOTIFY_CONNECT_TIMEOUT"]
CF_ENABLED = cfg["CF_ENABLED"]
CF_API_TOKEN = cfg["CF_API_TOKEN"]
CF_ZONE_ID = cfg["CF_ZONE_ID"]
CF_DNS_RECORD_NAME = cfg["CF_DNS_RECORD_NAME"]
CF_TTL = cfg["CF_TTL"]
CF_PROXIED = cfg["CF_PROXIED"]
CF_DNS_CONNECT_TIMEOUT = cfg["CF_DNS_CONNECT_TIMEOUT"]
CF_DNS_READ_TIMEOUT = cfg["CF_DNS_READ_TIMEOUT"]
# ADDITIONAL_SOURCES 不在顶层声明，在 main() 中直接使用 cfg.get("ADDITIONAL_SOURCES", [])
FETCH_MAX_RETRIES = cfg["FETCH_MAX_RETRIES"]
FETCH_RETRY_DELAY = cfg["FETCH_RETRY_DELAY"]
FETCH_TIMEOUT = cfg["FETCH_TIMEOUT"]
FETCH_CONNECT_TIMEOUT = cfg["FETCH_CONNECT_TIMEOUT"]
LOCAL_SEED_FILES = cfg["LOCAL_SEED_FILES"]
ENABLE_CF_OFFICIAL_IP_SAMPLING = cfg["ENABLE_CF_OFFICIAL_IP_SAMPLING"]
CF_OFFICIAL_IPV4_URL = cfg["CF_OFFICIAL_IPV4_URL"]
CF_OFFICIAL_SAMPLE_PER_24 = cfg["CF_OFFICIAL_SAMPLE_PER_24"]
CF_OFFICIAL_SAMPLE_PORTS = cfg["CF_OFFICIAL_SAMPLE_PORTS"]
CF_OFFICIAL_COUNTRY_CODE = cfg["CF_OFFICIAL_COUNTRY_CODE"]
OUTPUT_FILE = cfg["OUTPUT_FILE"]
OUTPUT_NODE_LIMIT = cfg["OUTPUT_NODE_LIMIT"]
STABILITY_SCORING_ENABLED = cfg["STABILITY_SCORING_ENABLED"]
STABILITY_STATS_FILE = cfg["STABILITY_STATS_FILE"]
STABILITY_HISTORY_WEIGHT = cfg["STABILITY_HISTORY_WEIGHT"]
STABILITY_MAX_BONUS = cfg["STABILITY_MAX_BONUS"]
ENABLE_LOGGING = cfg["ENABLE_LOGGING"]
LOG_FILE = cfg["LOG_FILE"]
TEST_AVAILABILITY = cfg["TEST_AVAILABILITY"]
AVAILABILITY_CHECK_API = cfg["AVAILABILITY_CHECK_API"]
AVAILABILITY_TIMEOUT = cfg["AVAILABILITY_TIMEOUT"]
AVAILABILITY_CONNECT_TIMEOUT = cfg["AVAILABILITY_CONNECT_TIMEOUT"]
AVAILABILITY_RETRY_MAX = cfg["AVAILABILITY_RETRY_MAX"]
AVAILABILITY_RETRY_DELAY = cfg["AVAILABILITY_RETRY_DELAY"]
FILTER_IPV6_AVAILABILITY = cfg["FILTER_IPV6_AVAILABILITY"]
FILTER_BLOCKED_COUNTRIES_ENABLED = cfg["FILTER_BLOCKED_COUNTRIES_ENABLED"]
BLOCKED_COUNTRIES = cfg["BLOCKED_COUNTRIES"]
DNS_UPDATE_TARGET_COUNT = cfg["DNS_UPDATE_TARGET_COUNT"]
BANDWIDTH_SIZE_MB = cfg["BANDWIDTH_SIZE_MB"]
BANDWIDTH_TIMEOUT = cfg["BANDWIDTH_TIMEOUT"]
BANDWIDTH_RETRY_MAX = cfg["BANDWIDTH_RETRY_MAX"]
BANDWIDTH_RETRY_DELAY = cfg["BANDWIDTH_RETRY_DELAY"]
BANDWIDTH_URL_TEMPLATE = cfg["BANDWIDTH_URL_TEMPLATE"]
BANDWIDTH_PROCESS_BUFFER = cfg["BANDWIDTH_PROCESS_BUFFER"]
BANDWIDTH_CONNECT_TIMEOUT = cfg["BANDWIDTH_CONNECT_TIMEOUT"]
MAX_WORKERS = cfg["MAX_WORKERS"]
AVAILABILITY_WORKERS = cfg["AVAILABILITY_WORKERS"]
FALLBACK_WORKERS = cfg["FALLBACK_WORKERS"]
BANDWIDTH_WORKERS = cfg["BANDWIDTH_WORKERS"]
DNS_UPDATE_MAX_RETRIES = cfg["DNS_UPDATE_MAX_RETRIES"]
DNS_UPDATE_RETRY_DELAY = cfg["DNS_UPDATE_RETRY_DELAY"]
GITHUB_SYNC_MAX_RETRIES = cfg["GITHUB_SYNC_MAX_RETRIES"]
GITHUB_SYNC_RETRY_DELAY = cfg["GITHUB_SYNC_RETRY_DELAY"]
GITHUB_SYNC_ENABLED = cfg["GITHUB_SYNC_ENABLED"]
GITHUB_SYNC_PROXY_URL = cfg["GITHUB_SYNC_PROXY_URL"]
GIT_SYNC_PROCESS_TIMEOUT = cfg["GIT_SYNC_PROCESS_TIMEOUT"]

socket.setdefaulttimeout(SOCKET_DEFAULT_TIMEOUT)
BANDWIDTH_URL = BANDWIDTH_URL_TEMPLATE.format(bytes=int(BANDWIDTH_SIZE_MB * 1024 * 1024))

# ====================================================

def send_wxpusher_notification(content, summary):
    if not ENABLE_WXPUSHER:
        return
    try:
        payload = {
            "appToken": WXPUSHER_APP_TOKEN,
            "content": content,
            "summary": summary,
            "uids": WXPUSHER_UIDS
        }
        headers = {"Content-Type": "application/json; charset=utf-8"}
        resp = requests.post(
            WXPUSHER_API_URL,
            data=json.dumps(payload),
            headers=headers,
            timeout=(NOTIFY_CONNECT_TIMEOUT, NOTIFY_TIMEOUT)
        )
        if resp.status_code == 200:
            print("✅ 微信通知已发送")
        else:
            print(f"⚠️ 微信通知发送失败: {resp.status_code}")
    except Exception as e:
        print(f"⚠️ 微信通知异常: {e}")

# ==================== 自适应多数据源解析引擎 ====================
def extract_country_code(label):
    """从任意标签中提取标准两位国家代码（支持纯代码、中文名、emoji国旗、混合无关文字）"""
    label = label.strip()
    if not label:
        return None

    tokens = re.split(r'[\s,;|/]+', label)

    # 1. 优先找标准两位大写字母代码
    for token in tokens:
        token = token.strip()
        if re.match(r'^[A-Z]{2}$', token):
            return token

    # 2. 对每个 token 尝试提取中文名
    for token in tokens:
        token_no_emoji = re.sub(r'[\U0001F1E6-\U0001F1FF]', '', token).strip()
        cn_match = re.match(r'^([\u4e00-\u9fff（）()]+)\d*$', token_no_emoji)
        if cn_match:
            cn_name = cn_match.group(1).strip()
            code = CN_TO_CODE.get(cn_name)
            if code:
                return code

    # 3. 解码纯 emoji 国旗
    emoji_chars = [c for c in label if '\U0001F1E6' <= c <= '\U0001F1FF']
    if len(emoji_chars) >= 2 and len(emoji_chars) % 2 == 0:
        first = ord(emoji_chars[0]) - 0x1F1E6
        second = ord(emoji_chars[1]) - 0x1F1E6
        if 0 <= first <= 25 and 0 <= second <= 25:
            return chr(first + ord('A')) + chr(second + ord('A'))

    return None


def _parse_json_nodes(data):
    """从 JSON 结构中递归提取节点"""
    nodes = []
    if isinstance(data, list):
        for item in data:
            nodes.extend(_parse_json_nodes(item))
    elif isinstance(data, dict):
        for key in ('nodes', 'data', 'result', 'list'):
            if key in data and isinstance(data[key], list):
                nodes.extend(_parse_json_nodes(data[key]))
                break
        ip = data.get('ip') or data.get('host')
        port = data.get('port')
        code = data.get('country') or data.get('cc')
        if ip and port and code:
            nodes.append(f"{ip}:{port}#{code.upper()}")
    elif isinstance(data, str):
        nodes.extend(_parse_text_nodes(data))
    return nodes


def _query_country(ip, port):
    """通过已有的可用性检测 API 查询 IP 的国家代码"""
    api_url = cfg.get("AVAILABILITY_CHECK_API", "https://api.090227.xyz/check")
    try:
        resp = requests.get(
            api_url,
            params={"proxyip": f"{ip}:{port}"},
            timeout=(AVAILABILITY_CONNECT_TIMEOUT, AVAILABILITY_TIMEOUT)
        )
        if resp.status_code == 200:
            data = resp.json()
            country = data.get("probe_results", {}).get("ipv4", {}).get("exit", {}).get("country", "")
            if country and len(country) == 2:
                return country.upper()
    except Exception:
        pass
    return None


def _resolve_countries_batch(ipports):
    """并发查询一批 IP 的国家代码"""
    results = {}
    total = len(ipports)
    completed = 0
    last_print = time.time()

    def worker(ipport):
        ip, port = ipport.rsplit(':', 1)
        return ipport, _query_country(ip, port)

    with ThreadPoolExecutor(max_workers=FALLBACK_WORKERS) as executor:
        futures = {executor.submit(worker, ipp): ipp for ipp in ipports}
        for future in as_completed(futures):
            try:
                ipport, code = future.result()
                results[ipport] = code
            except Exception:
                results[futures[future]] = None
            completed += 1
            now = time.time()
            if now - last_print >= PROGRESS_PRINT_INTERVAL or completed == total:
                print(f"\r    [备用API查询] 进度：{completed}/{total} ({(completed/total)*100:.1f}%)", end="", flush=True)
                last_print = now

    if total > 0:
        print()
    return results


def _parse_text_nodes(text):
    """从纯文本中提取标准节点（内置备用 API 查询）"""
    nodes = []
    pending = []

    tokens = text.split()
    for token in tokens:
        if '#' not in token:
            continue
        try:
            ipport, label = token.split('#', 1)
        except ValueError:
            continue
        ipport = ipport.strip()
        label = label.strip()

        if ipport.startswith('['):
            continue
        if not re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', ipport):
            continue

        code = extract_country_code(label)
        if code:
            nodes.append(f"{ipport}#{code}")
        else:
            pending.append(ipport)

    if pending:
        print(f"    {len(pending)} 个标签未能识别，通过可用性检测 API 查询国家...")
        resolved = _resolve_countries_batch(pending)
        for ipport, code in resolved.items():
            if code:
                nodes.append(f"{ipport}#{code}")

    return nodes


def parse_adaptive(text):
    """自适应解析任意格式的节点列表文本（JSON、纯文本等）"""
    text = text.strip()
    if not text:
        return []

    if text.startswith('{') or text.startswith('['):
        try:
            data = json.loads(text)
            return _parse_json_nodes(data)
        except (json.JSONDecodeError, Exception):
            pass

    return _parse_text_nodes(text)


def fetch_additional_source(url):
    """拉取单个数据源并返回标准节点列表"""
    if not url:
        return []

    max_retries = FETCH_MAX_RETRIES
    retry_delay = FETCH_RETRY_DELAY

    for attempt in range(1, max_retries + 1):
        try:
            print(f"正在请求数据源 {url} (尝试 {attempt}/{max_retries}) ...")
            resp = requests.get(url, timeout=(FETCH_CONNECT_TIMEOUT, FETCH_TIMEOUT))
            resp.raise_for_status()
            nodes = parse_adaptive(resp.text)
            print(f"从 {url} 解析出 {len(nodes)} 个节点。")
            return nodes
        except Exception as e:
            print(f"请求或解析失败 ({url}): {e}")
            if attempt < max_retries:
                print(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"已尝试 {max_retries} 次，放弃该数据源。")
                return []

def _resolve_local_path(path):
    if os.path.isabs(path):
        return path
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)

def load_local_seed_files(paths):
    """读取本地种子文件，支持全量ip.txt、重要ip.txt 等标准节点列表。"""
    nodes = []
    for path in paths or []:
        resolved_path = _resolve_local_path(path)
        if not os.path.exists(resolved_path):
            print(f"⚠️ 本地种子文件不存在，跳过: {path}")
            continue
        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                parsed = parse_adaptive(f.read())
            print(f"从本地种子 {path} 解析出 {len(parsed)} 个节点。")
            nodes.extend(parsed)
        except Exception as e:
            print(f"⚠️ 读取本地种子失败 ({path}): {e}")
    return nodes

def _sample_offsets_for_24(sample_count):
    sample_count = max(1, int(sample_count))
    if sample_count == 1:
        return [1]
    if sample_count == 2:
        return [1, 254]

    step = 253 / (sample_count - 1)
    offsets = []
    for index in range(sample_count):
        offset = round(1 + (step * index))
        offsets.append(max(1, min(254, offset)))
    return list(dict.fromkeys(offsets))

def sample_cloudflare_ipv4_cidrs(cidrs, ports, sample_per_24=3, country_code="CF"):
    """从 Cloudflare 官方 IPv4 CIDR 按 /24 分段抽样生成候选节点。"""
    nodes = []
    ports = [int(port) for port in (ports or [443])]
    offsets = _sample_offsets_for_24(sample_per_24)
    country_code = (country_code or "CF").upper()

    for cidr in cidrs or []:
        cidr = cidr.strip()
        if not cidr:
            continue
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            continue
        if network.version != 4:
            continue

        subnets = [network] if network.prefixlen >= 24 else network.subnets(new_prefix=24)
        for subnet in subnets:
            base_ip = int(subnet.network_address)
            usable_size = subnet.num_addresses
            for offset in offsets:
                if offset >= usable_size - 1:
                    continue
                ip = str(ipaddress.ip_address(base_ip + offset))
                for port in ports:
                    nodes.append(f"{ip}:{port}#{country_code}")
    return nodes

def fetch_cloudflare_official_ipv4_source(url, ports, sample_per_24, country_code):
    """拉取 Cloudflare 官方 IPv4 CIDR 列表并抽样为候选节点。"""
    if not url:
        return []

    for attempt in range(1, FETCH_MAX_RETRIES + 1):
        try:
            print(f"正在请求 Cloudflare 官方 IPv4 段 {url} (尝试 {attempt}/{FETCH_MAX_RETRIES}) ...")
            resp = requests.get(url, timeout=(FETCH_CONNECT_TIMEOUT, FETCH_TIMEOUT))
            resp.raise_for_status()
            cidrs = [line.strip() for line in resp.text.splitlines() if line.strip()]
            nodes = sample_cloudflare_ipv4_cidrs(
                cidrs=cidrs,
                ports=ports,
                sample_per_24=sample_per_24,
                country_code=country_code,
            )
            print(f"从 Cloudflare 官方 IPv4 段抽样生成 {len(nodes)} 个候选节点。")
            return nodes
        except Exception as e:
            print(f"Cloudflare 官方 IPv4 段请求或抽样失败: {e}")
            if attempt < FETCH_MAX_RETRIES:
                print(f"等待 {FETCH_RETRY_DELAY} 秒后重试...")
                time.sleep(FETCH_RETRY_DELAY)
            else:
                print(f"已尝试 {FETCH_MAX_RETRIES} 次，放弃 Cloudflare 官方 IPv4 段。")
                return []

def merge_nodes_preserve_order(node_groups):
    """按完整 IP:端口 去重，保留不同端口候选。"""
    nodes = []
    seen = set()
    for group in node_groups:
        for node in group or []:
            key = node.split("#", 1)[0]
            if key in seen:
                continue
            seen.add(key)
            nodes.append(node)
    return nodes

def is_country_allowed_for_pre_filter(node, allowed_countries, official_country_code=None, official_sampling_enabled=False):
    parts = node.split("#")
    if len(parts) != 2:
        return False
    country = parts[1].upper()
    if country in allowed_countries:
        return True
    return bool(official_sampling_enabled and official_country_code and country == official_country_code.upper())

def relabel_nodes_with_exit_country(nodes, ip_info, exit_details):
    """用可用性 API 返回的真实落地国家修正候选节点标签。"""
    relabeled_nodes = []
    relabeled_ip_info = {}
    relabeled_exit_details = {}
    aliases = {}

    for node in nodes:
        exit_info = exit_details.get(node, {}) if exit_details else {}
        country = str(exit_info.get("country", "")).upper()
        new_node = node
        if len(country) == 2 and "#" in node:
            new_node = node.rsplit("#", 1)[0] + f"#{country}"
            if new_node != node:
                aliases[node] = new_node

        relabeled_nodes.append(new_node)
        if ip_info and node in ip_info:
            relabeled_ip_info[new_node] = ip_info[node]
        if exit_details and node in exit_details:
            relabeled_exit_details[new_node] = exit_details[node]

    return relabeled_nodes, relabeled_ip_info, relabeled_exit_details, aliases

# =========================== 原有测试、测速、DNS、GitHub 等函数保持不变 ===========================

def test_tcp_latency(ip, port, timeout=TIMEOUT, probes=TCP_PROBES):
    min_latency = float("inf")
    success = 0
    for _ in range(probes):
        try:
            start = time.time()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                sock.connect((ip, int(port)))
            latency = time.time() - start
            if latency < min_latency:
                min_latency = latency
            success += 1
        except Exception:
            continue
    return min_latency, success

def test_node(node_str):
    m = NODE_PATTERN.match(node_str)
    if not m:
        return None
    ip, port, country = m.groups()
    min_lat, success = test_tcp_latency(ip, port)

    if success == 0 or (success / TCP_PROBES) < MIN_SUCCESS_RATE:
        return None

    return (node_str, min_lat, country, success)

def check_availability(node_str):
    m = IP_PORT_PATTERN.match(node_str)
    if not m:
        return (node_str, False, "unknown", {})
    ip, port = m.group(1), m.group(2)
    proxyip = f"{ip}:{port}"

    best_stack = "unknown"
    best_exit_info = {}
    success = False

    try:
        resp = requests.get(
            AVAILABILITY_CHECK_API,
            params={"proxyip": proxyip},
            timeout=(AVAILABILITY_CONNECT_TIMEOUT, AVAILABILITY_TIMEOUT)
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") is True:
                success = True
                best_stack = data.get("inferred_stack", "unknown")
                probe = data.get("probe_results", {}).get("ipv6") or data.get("probe_results", {}).get("ipv4") or {}
                best_exit_info = probe.get("exit", {})
    except Exception:
        pass

    return (node_str, success, best_stack, best_exit_info)

def availability_filter_candidates(candidates):
    if not TEST_AVAILABILITY or not candidates:
        return candidates, {}, {}

    print(f"\n对 {len(candidates)} 个候选节点进行可用性二次筛选...")
    passed = []
    ip_info = {}
    exit_details = {}
    completed = 0
    total = len(candidates)
    last_print = time.time()

    with ThreadPoolExecutor(max_workers=AVAILABILITY_WORKERS) as executor:
        futures = {executor.submit(check_availability, node): node for node in candidates}
        for future in as_completed(futures):
            completed += 1
            node_str, ok, stack, exit_info = future.result()
            if ok:
                passed.append(node_str)
                ip_info[node_str] = stack
                exit_details[node_str] = exit_info
            now = time.time()
            if now - last_print >= PROGRESS_PRINT_INTERVAL or completed == total:
                print(f"\r[可用性检测] 进度：{completed}/{total} ({(completed/total)*100:.1f}%) 通过数量：{len(passed)}", end="", flush=True)
                last_print = now
    print()
    return passed, ip_info, exit_details

def availability_filter_with_retry(candidates):
    if not TEST_AVAILABILITY or not candidates:
        return candidates, {}, {}

    passed = []
    ip_info = {}
    exit_details = {}
    for attempt in range(1, AVAILABILITY_RETRY_MAX + 1):
        print(f"\n[可用性检测] 第 {attempt} 轮检测...")
        passed, ip_info, exit_details = availability_filter_candidates(candidates)
        if passed:
            print(f"✅ 可用性检测通过 {len(passed)} 个节点")
            return passed, ip_info, exit_details
        if attempt < AVAILABILITY_RETRY_MAX:
            print(f"⚠️ 本轮可用性检测通过率为 0%，等待 {AVAILABILITY_RETRY_DELAY} 秒后重试...")
            time.sleep(AVAILABILITY_RETRY_DELAY)

    print(f"❌ 可用性检测经 {AVAILABILITY_RETRY_MAX} 轮重试后仍无节点通过。")
    send_wxpusher_notification(
        content=f"IP 可用性检测经 {AVAILABILITY_RETRY_MAX} 轮重试后仍无节点通过，已跳过过滤，使用原候选列表继续。",
        summary="可用性检测全部失败"
    )
    return candidates, {}, {}

def measure_bandwidth_curl(node_str):
    m = IP_PORT_PATTERN.match(node_str)
    if not m:
        return (node_str, 0)
    ip, port = m.group(1), m.group(2)

    null_device = "NUL" if sys.platform == "win32" else "/dev/null"
    curl_cmd = [
        "curl", "-s", "-o", null_device,
        "-w", "%{size_download} %{time_total}",
        "--resolve", f"speed.cloudflare.com:{port}:{ip}",
        "--connect-timeout", str(BANDWIDTH_CONNECT_TIMEOUT),
        "--max-time", str(BANDWIDTH_TIMEOUT),
        "--insecure",
        BANDWIDTH_URL
    ]

    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=BANDWIDTH_TIMEOUT + BANDWIDTH_PROCESS_BUFFER)
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split()
            if len(parts) >= 2:
                size_bytes = float(parts[0])
                time_total = float(parts[1])
                if time_total > 0 and size_bytes > 0:
                    speed_mbps = (size_bytes * 8) / (time_total * 1000 * 1000)
                    return (node_str, speed_mbps)
    except Exception:
        pass
    return (node_str, 0)

def bandwidth_filter(candidates):
    if not candidates:
        return []

    if not shutil.which("curl"):
        print("⚠️ 未检测到 curl 命令，带宽测速将跳过。")
        return []

    print(f"\n开始带宽测速（对前 {len(candidates)} 个节点，并发 {BANDWIDTH_WORKERS}，超时 {BANDWIDTH_TIMEOUT}s）...")
    results = []
    completed = 0
    total = len(candidates)
    last_print = time.time()

    with ThreadPoolExecutor(max_workers=BANDWIDTH_WORKERS) as executor:
        futures = {executor.submit(measure_bandwidth_curl, node): node for node in candidates}
        for future in as_completed(futures):
            completed += 1
            node, speed = future.result()
            if speed > 0:
                results.append((node, speed))
            now = time.time()
            if now - last_print >= PROGRESS_PRINT_INTERVAL or completed == total:
                print(f"\r[带宽测速] 进度：{completed}/{total} ({(completed/total)*100:.1f}%)", end="", flush=True)
                last_print = now

    print()
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def _stability_stats_path():
    if os.path.isabs(STABILITY_STATS_FILE):
        return STABILITY_STATS_FILE
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), STABILITY_STATS_FILE)

def _safe_number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def load_stability_stats():
    if not STABILITY_SCORING_ENABLED:
        return {"nodes": {}}

    path = _stability_stats_path()
    if not os.path.exists(path):
        return {"nodes": {}}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"nodes": {}}
        if not isinstance(data.get("nodes"), dict):
            data["nodes"] = {}
        return data
    except Exception as e:
        print(f"⚠️ 稳定性统计文件读取失败，将从空统计开始: {e}")
        return {"nodes": {}}

def save_stability_stats(stats):
    if not STABILITY_SCORING_ENABLED:
        return

    path = _stability_stats_path()
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp_path, path)
        print(f"稳定性统计已保存到 {os.path.basename(path)}")
    except Exception as e:
        print(f"⚠️ 稳定性统计文件保存失败: {e}")

def update_stability_stats(stats, attempted_nodes, bw_results, latency_map=None):
    if not STABILITY_SCORING_ENABLED:
        return stats

    stats.setdefault("nodes", {})
    speed_map = {node: speed for node, speed in bw_results}
    unique_attempts = list(dict.fromkeys(list(attempted_nodes) + list(speed_map.keys())))
    now = int(time.time())

    for node in unique_attempts:
        record = stats["nodes"].setdefault(
            node,
            {
                "runs": 0,
                "passes": 0,
                "failures": 0,
                "avg_speed_mbps": 0.0,
                "best_speed_mbps": 0.0,
                "avg_latency_ms": 0.0,
                "best_latency_ms": 0.0,
            },
        )

        previous_passes = int(record.get("passes", 0))
        record["runs"] = int(record.get("runs", 0)) + 1
        record["last_seen_ts"] = now

        speed = _safe_number(speed_map.get(node), 0.0)
        if speed > 0:
            record["passes"] = previous_passes + 1
            new_passes = record["passes"]
            old_avg_speed = _safe_number(record.get("avg_speed_mbps"), 0.0)
            record["avg_speed_mbps"] = round(((old_avg_speed * previous_passes) + speed) / new_passes, 3)
            record["best_speed_mbps"] = round(max(_safe_number(record.get("best_speed_mbps"), 0.0), speed), 3)

            if latency_map and node in latency_map:
                latency_ms = _safe_number(latency_map[node], 0.0) * 1000
                old_avg_latency = _safe_number(record.get("avg_latency_ms"), 0.0)
                record["avg_latency_ms"] = round(((old_avg_latency * previous_passes) + latency_ms) / new_passes, 3)
                best_latency = _safe_number(record.get("best_latency_ms"), 0.0)
                record["best_latency_ms"] = round(latency_ms if best_latency <= 0 else min(best_latency, latency_ms), 3)
        else:
            record["failures"] = int(record.get("failures", 0)) + 1

    stats["updated_at_ts"] = now
    return stats

def _latency_bonus(node, latency_map):
    if not latency_map or node not in latency_map:
        return 0.0
    latency_ms = _safe_number(latency_map[node], 9999.0) * 1000
    if latency_ms <= 0:
        return 0.0
    return max(0.0, (300.0 - min(latency_ms, 300.0)) / 300.0) * 20.0

def _history_bonus(node, stats):
    record = (stats or {}).get("nodes", {}).get(node, {})
    runs = max(0, int(record.get("runs", 0)))
    passes = max(0, int(record.get("passes", 0)))
    failures = max(0, int(record.get("failures", 0)))
    if runs <= 0 or passes <= 0:
        return 0.0

    pass_rate = passes / runs
    experience = min(passes, 10) / 10.0
    failure_drag = min(failures, 5) * 1.5
    bonus = ((pass_rate * 0.7) + (experience * 0.3)) * STABILITY_MAX_BONUS
    return max(0.0, bonus - failure_drag)

def calculate_node_score(node, speed, latency_map=None, stats=None):
    score = _safe_number(speed, 0.0)
    score += _latency_bonus(node, latency_map)
    if STABILITY_SCORING_ENABLED:
        score += _history_bonus(node, stats or {}) * STABILITY_HISTORY_WEIGHT
    return score

def rank_bandwidth_results(bw_results, latency_map=None, stats=None):
    ranked = []
    for node, speed in bw_results:
        score = calculate_node_score(node, speed, latency_map, stats)
        latency = _safe_number((latency_map or {}).get(node), 9999.0)
        ranked.append((node, speed, score, latency))

    ranked.sort(key=lambda item: (-item[2], -item[1], item[3], item[0]))
    return [(node, speed) for node, speed, _, _ in ranked]

def _node_port(node_str):
    match = IP_PORT_PATTERN.match(node_str)
    if not match:
        return ""
    return match.group(2)

def _split_port_priority(items, preferred_port="443"):
    preferred = []
    fallback = []
    for item in items:
        node = item[0]
        if _node_port(node) == preferred_port:
            preferred.append(item)
        else:
            fallback.append(item)
    return preferred, fallback

def select_final_nodes(
    ranked_results,
    tcp_results,
    use_global_mode,
    global_top_n,
    per_country_top_n,
    output_node_limit=None,
):
    limit = output_node_limit or global_top_n

    if ranked_results:
        preferred_results, fallback_results = _split_port_priority(ranked_results)
        if use_global_mode:
            target = min(global_top_n, limit)
            selected = [node for node, _ in preferred_results[:target]]
            if len(selected) < target:
                remaining = target - len(selected)
                selected.extend([node for node, _ in fallback_results[:remaining]])
        else:
            selected = []
            country_counts = defaultdict(int)
            for source in (preferred_results, fallback_results):
                for node, _ in source:
                    country = node.split("#")[-1].upper() if "#" in node else ""
                    if not country:
                        continue
                    if country_counts[country] >= per_country_top_n:
                        continue
                    selected.append(node)
                    country_counts[country] += 1
                    if len(selected) >= limit:
                        break
                if len(selected) >= limit:
                    break
        return selected[:limit]

    preferred_results, fallback_results = _split_port_priority(tcp_results)
    if use_global_mode:
        target = min(global_top_n, limit)
        selected = [node for node, _, _, _ in preferred_results[:target]]
        if len(selected) < target:
            remaining = target - len(selected)
            selected.extend([node for node, _, _, _ in fallback_results[:remaining]])
        return selected

    selected = []
    country_counts = defaultdict(int)
    for source in (preferred_results, fallback_results):
        country_nodes = defaultdict(list)
        for node_str, lat, country, succ in source:
            country_nodes[country].append((node_str, lat, succ))
        for country, nodes in country_nodes.items():
            nodes_sorted = sorted(nodes, key=lambda x: (-x[2], x[1]))
            for node_str, _, _ in nodes_sorted:
                if len(selected) >= limit:
                    return selected
                if country_counts[country] >= per_country_top_n:
                    break
                selected.append(node_str)
                country_counts[country] += 1
                if len(selected) >= limit:
                    return selected
    return selected

def batch_update_cloudflare_dns(ip_list, ip_info=None, full_bw_results=None, target_count=None, latency_map=None):
    if not cfg.get("CF_ENABLED", False):
        print("Cloudflare DNS 批量更新未启用。")
        return

    if target_count is None:
        target_count = cfg.get("DNS_UPDATE_TARGET_COUNT", 15)

    dns_ip_list = []
    dns_node_list = []
    filtered_by_port = 0
    filtered_by_ipv6 = 0
    filtered_by_country = 0

    if full_bw_results and ip_info:
        blocked_set = set()
        if cfg.get("FILTER_BLOCKED_COUNTRIES_ENABLED", False):
            blocked_set = {c.upper() for c in cfg.get("BLOCKED_COUNTRIES", [])}

        for node_str, speed in full_bw_results:
            if ':' in node_str:
                port = node_str.split(':')[1].split('#')[0]
                if port != '443':
                    filtered_by_port += 1
                    continue

            if cfg.get("FILTER_IPV6_AVAILABILITY", False):
                stack = ip_info.get(node_str, "unknown")
                if stack == "ipv6_only":
                    filtered_by_ipv6 += 1
                    continue

            if blocked_set and '#' in node_str:
                country = node_str.split('#')[-1].upper()
                if country in blocked_set:
                    filtered_by_country += 1
                    continue

            pure_ip = node_str.split(':')[0]
            dns_ip_list.append(pure_ip)
            dns_node_list.append(node_str)

            if len(dns_ip_list) >= target_count:
                break

        filter_parts = []
        if filtered_by_port > 0:
            filter_parts.append(f"非443端口过滤({filtered_by_port}个)")
        if cfg.get("FILTER_IPV6_AVAILABILITY", False):
            filter_parts.append(f"IPv6落地过滤({filtered_by_ipv6}个)")
        if cfg.get("FILTER_BLOCKED_COUNTRIES_ENABLED", False):
            filter_parts.append(f"屏蔽国家过滤({filtered_by_country}个)")
        filter_str = " + ".join(filter_parts) if filter_parts else "无过滤"
        print(f"从 {len(full_bw_results)} 个测速节点中筛选出 {len(dns_ip_list)} 个节点用于 DNS 更新（{filter_str}）。")

    if not dns_ip_list:
        if ip_list:
            print("⚠️ 未能从完整测速结果构建 DNS 列表，降级使用 ip.txt 中的 IP。")
            dns_ip_list = ip_list
            dns_node_list = ip_list
        else:
            msg = "没有可用的 IP 用于 DNS 更新，跳过。"
            print(msg)
            send_wxpusher_notification(content=msg, summary="DNS 更新跳过")
            return

    seen = set()
    unique_ips = []
    unique_nodes = []
    for ip, node in zip(dns_ip_list, dns_node_list):
        if ip not in seen:
            seen.add(ip)
            unique_ips.append(ip)
            unique_nodes.append(node)
    dns_ip_list = unique_ips
    dns_node_list = unique_nodes

    print(f"\n准备将以下 {len(dns_ip_list)} 个 IP 批量更新到 Cloudflare DNS:")
    speed_map = {}
    if full_bw_results:
        speed_map = {node: speed for node, speed in full_bw_results}
    for i, (ip, node) in enumerate(zip(dns_ip_list, dns_node_list), 1):
        speed = speed_map.get(node, 0)
        lat_ms = float('inf')
        if latency_map and node in latency_map:
            lat_ms = latency_map[node] * 1000
        if lat_ms != float('inf'):
            print(f"{i}. {node} 速度 {speed:.2f} Mbps 延迟 {lat_ms:.2f} ms")
        else:
            print(f"{i}. {ip} 速度 {speed:.2f} Mbps")

    headers = {
        "Authorization": f"Bearer {cfg['CF_API_TOKEN']}",
        "Content-Type": "application/json"
    }
    zone_id = cfg['CF_ZONE_ID']
    record_name = cfg['CF_DNS_RECORD_NAME']
    ttl = cfg.get('CF_TTL', 120)
    proxied = cfg.get('CF_PROXIED', False)

    max_retries = cfg.get('DNS_UPDATE_MAX_RETRIES', 5)
    retry_delay = cfg.get('DNS_UPDATE_RETRY_DELAY', 10)

    for attempt in range(1, max_retries + 1):
        print(f"\n[DNS 更新] 尝试 {attempt}/{max_retries}...")
        try:
            list_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name={record_name}"
            response = requests.get(list_url, headers=headers, timeout=(CF_DNS_CONNECT_TIMEOUT, CF_DNS_READ_TIMEOUT))
            response.raise_for_status()
            result = response.json()
            if not result.get('success'):
                error_detail = result.get('errors')
                raise Exception(f"查询 DNS 记录失败: {error_detail}")

            existing_records = result.get('result', [])
            deletes = [{"id": rec["id"]} for rec in existing_records]
            posts = [
                {
                    "name": record_name,
                    "type": "A",
                    "content": ip,
                    "ttl": ttl,
                    "proxied": proxied
                }
                for ip in dns_ip_list
            ]

            batch_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/batch"
            payload = {"deletes": deletes, "posts": posts}
            response = requests.post(batch_url, headers=headers, json=payload, timeout=(CF_DNS_CONNECT_TIMEOUT, CF_DNS_READ_TIMEOUT))
            response.raise_for_status()
            result = response.json()
            if not result.get('success'):
                error_detail = result.get('errors')
                raise Exception(f"批量更新失败: {error_detail}")

            success_msg = f"✅ Cloudflare DNS 批量更新成功！已将 {record_name} 指向 {len(dns_ip_list)} 个 IP。"
            print(success_msg)
            print("   注意：DNS 解析将随机返回这些 IP 中的一个，实现负载均衡。")
            return

        except Exception as e:
            error_msg = f"[尝试 {attempt}/{max_retries}] DNS 更新出错: {e}"
            print(error_msg)
            if attempt < max_retries:
                print(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                final_error = f"❌ Cloudflare DNS 更新失败，已重试 {max_retries} 次，错误：{e}"
                print(final_error)
                send_wxpusher_notification(content=final_error, summary="DNS 更新失败")

def build_github_sync_env(sync_proxy_url=None):
    env = os.environ.copy()
    proxy_url = GITHUB_SYNC_PROXY_URL if sync_proxy_url is None else sync_proxy_url
    if proxy_url:
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            env[key] = proxy_url
    return env


def sync_to_github():
    if not GITHUB_SYNC_ENABLED:
        print("GitHub sync disabled, skipped.")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))

    if sys.platform == "win32":
        script_name = "git_sync.ps1"
        interpreter = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File"]
        creationflags = subprocess.CREATE_NO_WINDOW
    else:
        script_name = "git_sync.sh"
        interpreter = ["bash"]
        creationflags = 0

    script_path = os.path.join(script_dir, script_name)
    if not os.path.exists(script_path):
        print(f"⚠️ 未找到 {script_name}，跳过 GitHub 同步。")
        return

    if sys.platform != "win32":
        try:
            os.chmod(script_path, 0o755)
        except Exception:
            pass

    max_retries = cfg.get('GITHUB_SYNC_MAX_RETRIES', 5)
    retry_delay = cfg.get('GITHUB_SYNC_RETRY_DELAY', 10)
    process_timeout = cfg.get('GIT_SYNC_PROCESS_TIMEOUT', 180)

    for attempt in range(1, max_retries + 1):
        print(f"\n正在同步到 GitHub (尝试 {attempt}/{max_retries})...")
        try:
            cmd = interpreter + [script_path]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=build_github_sync_env(),
                creationflags=creationflags
            )

            try:
                stdout, stderr = process.communicate(timeout=process_timeout)
                if process.returncode == 0:
                    print("✅ 已自动推送到 GitHub。")
                    return
                else:
                    print(f"❌ 推送失败 (退出码 {process.returncode})")
                    if stderr:
                        print(f"错误信息: {stderr.strip()}")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"❌ 推送超时（超过 {process_timeout} 秒）")
        except Exception as e:
            print(f"❌ 推送过程异常: {e}")

        if attempt < max_retries:
            print(f"等待 {retry_delay} 秒后重试...")
            time.sleep(retry_delay)

    send_wxpusher_notification(
        content=f"GitHub 推送失败，已重试 {max_retries} 次，请检查网络或仓库状态。",
        summary="GitHub 推送失败"
    )
    print(f"⚠️ 已尝试 {max_retries} 次推送，均失败，请检查网络或 GitHub 仓库状态。")

def main():
    mode_str = f"全局最优{GLOBAL_TOP_N}个" if USE_GLOBAL_MODE else f"每个国家最优{PER_COUNTRY_TOP_N}个"
    print(f"当前模式：{mode_str}，每个节点测试 {TCP_PROBES} 次 TCP 连接")
    print(f"最低成功率要求：{MIN_SUCCESS_RATE*100:.0f}%")
    print(f"IP 可用性二次筛选：{'启用' if TEST_AVAILABILITY else '禁用'}（仅对候选节点）")
    print(f"IPv6 客户端 IP 过滤（仅作用于DNS更新环节）：{'启用' if FILTER_IPV6_AVAILABILITY else '禁用'}")
    print(f"屏蔽国家过滤（仅作用于DNS更新环节）：{'启用' if FILTER_BLOCKED_COUNTRIES_ENABLED else '禁用'}，屏蔽国家：{', '.join(BLOCKED_COUNTRIES)}")
    print(f"带宽测速候选数：{BANDWIDTH_CANDIDATES}，测速文件大小：{BANDWIDTH_SIZE_MB} MB，超时：{BANDWIDTH_TIMEOUT}s")
    print(f"最终输出上限：{OUTPUT_NODE_LIMIT} 个节点，稳定性评分：{'启用' if STABILITY_SCORING_ENABLED else '禁用'}")
    if FILTER_COUNTRIES_ENABLED:
        print(f"国家过滤：启用，允许国家：{', '.join(ALLOWED_COUNTRIES)}")

    # 统一从远程源、本地种子和可选官方 CIDR 抽样加载候选节点
    node_groups = []
    additional_sources = cfg.get("ADDITIONAL_SOURCES", [])
    for source in additional_sources:
        if not source.get("enabled", True):
            continue
        url = source.get("url")
        if not url:
            continue
        v2_nodes = fetch_additional_source(url)
        if v2_nodes:
            node_groups.append(v2_nodes)

    local_seed_nodes = load_local_seed_files(LOCAL_SEED_FILES)
    if local_seed_nodes:
        node_groups.append(local_seed_nodes)

    if ENABLE_CF_OFFICIAL_IP_SAMPLING:
        official_nodes = fetch_cloudflare_official_ipv4_source(
            url=CF_OFFICIAL_IPV4_URL,
            ports=CF_OFFICIAL_SAMPLE_PORTS,
            sample_per_24=CF_OFFICIAL_SAMPLE_PER_24,
            country_code=CF_OFFICIAL_COUNTRY_CODE,
        )
        if official_nodes:
            node_groups.append(official_nodes)

    nodes = merge_nodes_preserve_order(node_groups)
    print(f"合并后总计 {len(nodes)} 个节点。")

    if not nodes:
        print("没有获取到任何有效节点，退出。")
        sys.exit(1)

    if FILTER_COUNTRIES_ENABLED and ALLOWED_COUNTRIES:
        before = len(nodes)
        allowed_set = {c.upper() for c in ALLOWED_COUNTRIES}
        filtered_nodes = []
        for node in nodes:
            if is_country_allowed_for_pre_filter(
                node,
                allowed_countries=allowed_set,
                official_country_code=CF_OFFICIAL_COUNTRY_CODE,
                official_sampling_enabled=ENABLE_CF_OFFICIAL_IP_SAMPLING,
            ):
                filtered_nodes.append(node)
        nodes = filtered_nodes
        after = len(nodes)
        print(f"\n国家过滤（测试前）：{before} -> {after} 个节点（允许国家：{', '.join(allowed_set)}）")
        if not nodes:
            print("⚠️ 过滤后无任何节点，退出程序。")
            sys.exit(0)

    total = len(nodes)
    print(f"开始 TCP 连接测试（超时 {TIMEOUT}s，并发 {MAX_WORKERS}）...")

    results = []
    completed = 0
    last_print = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(test_node, node): node for node in nodes}
        for future in as_completed(futures):
            completed += 1
            res = future.result()
            if res:
                results.append(res)
            now = time.time()
            if now - last_print >= PROGRESS_PRINT_INTERVAL or completed == total:
                print(f"\r进度：{completed}/{total} ({(completed/total)*100:.1f}%)", end="", flush=True)
                last_print = now

    print("\nTCP 测试完成！")
    if not results:
        print("没有通过成功率筛选的节点，请检查网络或降低 MIN_SUCCESS_RATE。")
        sys.exit(0)

    results.sort(key=lambda x: (-x[3], x[1]))
    latency_map = {node: lat for node, lat, _, _ in results}

    if USE_GLOBAL_MODE:
        candidates = [node for node, _, _, _ in results[:BANDWIDTH_CANDIDATES]]
        print(f"\nTCP 最优前 {len(candidates)} 个节点进入候选池。")
    else:
        country_nodes = defaultdict(list)
        for node_str, lat, country, succ in results:
            country_nodes[country].append((node_str, lat, succ))

        total_countries = len(country_nodes)
        base_limit = max(1, BANDWIDTH_CANDIDATES // total_countries)
        candidates = []
        for country, nodes in country_nodes.items():
            nodes_sorted = sorted(nodes, key=lambda x: (-x[2], x[1]))
            limit = min(len(nodes_sorted), base_limit)
            for node_str, lat, succ in nodes_sorted[:limit]:
                candidates.append(node_str)
        print(f"\n各国家候选池分配：共 {total_countries} 个国家，每国最多 {base_limit} 个候选，总计 {len(candidates)} 个节点进入候选池。")

    if not candidates:
        print("没有候选节点，退出。")
        sys.exit(0)

    candidates_after_availability, avail_ip_info, avail_exit_details = availability_filter_with_retry(candidates)
    candidates_after_availability, avail_ip_info, avail_exit_details, relabeled_aliases = relabel_nodes_with_exit_country(
        candidates_after_availability,
        avail_ip_info,
        avail_exit_details,
    )
    for old_node, new_node in relabeled_aliases.items():
        if old_node in latency_map:
            latency_map[new_node] = latency_map[old_node]
    if relabeled_aliases:
        print(f"已根据可用性 API 修正 {len(relabeled_aliases)} 个节点的国家标签。")
    stability_stats = load_stability_stats()

    bw_results = []
    for attempt in range(1, BANDWIDTH_RETRY_MAX + 1):
        print(f"\n[带宽测速] 第 {attempt} 轮测试...")
        bw_results = bandwidth_filter(candidates_after_availability)
        if bw_results:
            break
        if attempt < BANDWIDTH_RETRY_MAX:
            print(f"⚠️ 本轮测速无有效结果，等待 {BANDWIDTH_RETRY_DELAY} 秒后重试...")
            time.sleep(BANDWIDTH_RETRY_DELAY)

    ranked_bw_results = []
    if bw_results:
        stability_stats = update_stability_stats(
            stability_stats,
            candidates_after_availability,
            bw_results,
            latency_map=latency_map,
        )
        ranked_bw_results = rank_bandwidth_results(bw_results, latency_map=latency_map, stats=stability_stats)
        save_stability_stats(stability_stats)
    if not bw_results:
        print("\n⚠️ 带宽测速多次重试仍无有效结果，将使用 TCP 筛选结果作为最终节点。")
        send_wxpusher_notification(
            content=f"带宽测速经 {BANDWIDTH_RETRY_MAX} 轮尝试后仍无有效结果，已降级使用 TCP 排序节点。",
            summary="带宽测速全部失败"
        )
        final_selected = select_final_nodes(
            ranked_results=[],
            tcp_results=results,
            use_global_mode=USE_GLOBAL_MODE,
            global_top_n=GLOBAL_TOP_N,
            per_country_top_n=PER_COUNTRY_TOP_N,
            output_node_limit=OUTPUT_NODE_LIMIT,
        )
    else:
        final_selected = select_final_nodes(
            ranked_results=ranked_bw_results,
            tcp_results=results,
            use_global_mode=USE_GLOBAL_MODE,
            global_top_n=GLOBAL_TOP_N,
            per_country_top_n=PER_COUNTRY_TOP_N,
            output_node_limit=OUTPUT_NODE_LIMIT,
        )

        print("\n================ 最终优选节点 ================")
        speed_map = {node: speed for node, speed in bw_results}
        for i, node in enumerate(final_selected, 1):
            speed = speed_map.get(node, 0)
            lat_sec = latency_map.get(node, float('inf'))
            score = calculate_node_score(node, speed, latency_map=latency_map, stats=stability_stats)
            if lat_sec != float('inf'):
                print(f"{i}. {node} 速度 {speed:.2f} Mbps 延迟 {lat_sec*1000:.2f} ms 综合分 {score:.2f}")
            else:
                print(f"{i}. {node} 速度 {speed:.2f} Mbps 综合分 {score:.2f}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for node_str in final_selected:
            f.write(node_str + "\n")
    print(f"\n结果已保存到 {OUTPUT_FILE}（共 {len(final_selected)} 个节点）")

    ip_list = []
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            ip_list = [line.split(':')[0].strip() for line in f if line.strip()]
    except Exception as e:
        print(f"读取 {OUTPUT_FILE} 时发生错误: {e}")

    target_dns_count = min(DNS_UPDATE_TARGET_COUNT, OUTPUT_NODE_LIMIT)
    batch_update_cloudflare_dns(
        ip_list,
        ip_info=avail_ip_info,
        full_bw_results=ranked_bw_results or bw_results,
        target_count=target_dns_count,
        latency_map=latency_map
    )

    sync_to_github()

if __name__ == "__main__":
    import atexit

    # 读取配置
    enable_log = cfg.get("ENABLE_LOGGING", False)
    log_filename = cfg.get("LOG_FILE", "cfnb.log")

    if enable_log:
        try:
            # 使用绝对路径，确保写入脚本所在目录
            script_dir = os.path.dirname(os.path.abspath(__file__))
            log_path = os.path.join(script_dir, log_filename)
            log_f = open(log_path, "w", encoding="utf-8")
            print("✅ 日志已启用，输出将保存到 " + log_path)
        except Exception as e:
            print(f"❌ 无法打开日志文件 {log_path}: {e}")
            log_f = None
        else:
            class _Tee:
                def __init__(self, *files):
                    self.files = files
                def write(self, obj):
                    for f in self.files:
                        f.write(obj)
                        f.flush()
                def flush(self):
                    for f in self.files:
                        f.flush()
            sys.stdout = _Tee(sys.stdout, log_f)

            # 确保退出时关闭日志文件
            def _close_log():
                try:
                    sys.stdout = sys.__stdout__
                    log_f.close()
                except Exception:
                    pass
            atexit.register(_close_log)

    main()
