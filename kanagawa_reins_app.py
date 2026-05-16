import streamlit as st
import pandas as pd
import numpy as np
import re
import os
import json
import time
import urllib.parse
import urllib.request
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="神奈川 REINS成約データ", layout="wide", page_icon="🏠")

# ── フォルダマッピング ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AREA_MAP = {
    '横浜市港北区': '横浜市港北区',
    '横浜市神奈川区': '横浜市神奈川区',
    '横浜市都筑区': '横浜市都筑区',
    '横浜市鶴見区': '横浜市鶴見区',
    '川崎市中原区': '川崎市中原区',
    '川崎市川崎区': '川崎市川崎区',
    '川崎市幸区': '川崎市幸区',
    '川崎市高津区': '川崎市高津区',
}

BUKKEN_MAP = {
    'マンション': 'マンション',
    '戸建': '一戸建',
    '土地': '土地',
}

EXCEL_NAME_MAP = {
    ('横浜市港北区', 'マンション'): '港北区マンション成約データ.xlsx',
    ('横浜市港北区', '戸建'):       '港北区戸建成約データ.xlsx',
    ('横浜市港北区', '土地'):       '港北区土地成約データ.xlsx',
    ('横浜市神奈川区', 'マンション'): '神奈川区マンション成約データ.xlsx',
    ('横浜市神奈川区', '戸建'):       '神奈川区戸建成約データ.xlsx',
    ('横浜市神奈川区', '土地'):       '神奈川区土地成約データ.xlsx',
    ('横浜市都筑区', 'マンション'): '都筑区マンション成約データ.xlsx',
    ('横浜市都筑区', '戸建'):       '都筑区戸建成約データ.xlsx',
    ('横浜市都筑区', '土地'):       '都筑区土地成約データ.xlsx',
    ('横浜市鶴見区', 'マンション'): '鶴見区マンション成約データ.xlsx',
    ('横浜市鶴見区', '戸建'):       '鶴見区戸建成約データ.xlsx',
    ('横浜市鶴見区', '土地'):       '鶴見区土地成約データ.xlsx',
    ('川崎市中原区', 'マンション'): '中原区マンション成約データ.xlsx',
    ('川崎市中原区', '戸建'):       '中原区戸建成約データ.xlsx',
    ('川崎市中原区', '土地'):       '中原区土地成約データ.xlsx',
    ('川崎市川崎区', 'マンション'): '川崎区マンション成約データ.xlsx',
    ('川崎市川崎区', '戸建'):       '川崎区戸建成約データ.xlsx',
    ('川崎市川崎区', '土地'):       '川崎区土地成約データ.xlsx',
    ('川崎市幸区', 'マンション'): '幸区マンション成約データ.xlsx',
    ('川崎市幸区', '戸建'):       '幸区戸建成約データ.xlsx',
    ('川崎市幸区', '土地'):       '幸区土地成約データ.xlsx',
    ('川崎市高津区', 'マンション'): '高津区マンション成約データ.xlsx',
    ('川崎市高津区', '戸建'):       '高津区戸建成約データ.xlsx',
    ('川崎市高津区', '土地'):       '高津区土地成約データ.xlsx',
}

# ── 各区のバウンディングボックス（海・山の誤ジオコーディング除外用）──
AREA_BBOX = {
    '横浜市港北区':  dict(lat_min=35.50, lat_max=35.60, lon_min=139.58, lon_max=139.68),
    '横浜市神奈川区':dict(lat_min=35.46, lat_max=35.53, lon_min=139.60, lon_max=139.68),
    '横浜市都筑区':  dict(lat_min=35.52, lat_max=35.59, lon_min=139.52, lon_max=139.61),
    '横浜市鶴見区':  dict(lat_min=35.48, lat_max=35.55, lon_min=139.65, lon_max=139.73),
    '川崎市中原区':  dict(lat_min=35.55, lat_max=35.60, lon_min=139.63, lon_max=139.70),
    '川崎市川崎区':  dict(lat_min=35.51, lat_max=35.56, lon_min=139.68, lon_max=139.76),
    '川崎市幸区':    dict(lat_min=35.53, lat_max=35.58, lon_min=139.67, lon_max=139.73),
    '川崎市高津区':  dict(lat_min=35.57, lat_max=35.63, lon_min=139.62, lon_max=139.70),
}

# ── 区ごとの地図センター座標 ──────────────────────────────────
AREA_CENTER = {
    '横浜市港北区':  [35.548, 139.628],
    '横浜市神奈川区':[35.485, 139.632],
    '横浜市都筑区':  [35.548, 139.554],
    '横浜市鶴見区':  [35.509, 139.680],
    '川崎市中原区':  [35.573, 139.659],
    '川崎市川崎区':  [35.531, 139.703],
    '川崎市幸区':    [35.555, 139.694],
    '川崎市高津区':  [35.593, 139.643],
}

# ── 駅名フォールバック座標（ジオコーディング失敗時の代替用）──────
STATION_FALLBACK_COORDS = {
    # 横浜市港北区
    '仲町台':   (35.5234, 139.5891),
    '新羽':     (35.5312, 139.6123),
    '高田':     (35.5189, 139.5967),
    '東山田':   (35.5156, 139.5834),
    '白楽':     (35.4789, 139.6234),
    '妙蓮寺':   (35.4823, 139.6198),
    '大倉山':   (35.5046, 139.6284),
    '菊名':     (35.5003, 139.6303),
    '綱島':     (35.5338, 139.6430),
    '日吉':     (35.5574, 139.6328),
    '元住吉':   (35.5703, 139.6528),
    '小机':     (35.5216, 139.5995),
    '鴨居':     (35.5100, 139.5761),
    # 横浜市神奈川区
    '横浜':     (35.4660, 139.6223),
    '東神奈川': (35.4797, 139.6310),
    '反町':     (35.4828, 139.6265),
    '三ツ沢下町': (35.4767, 139.6131),
    '三ツ沢上町': (35.4839, 139.6131),
    '岸根公園': (35.4928, 139.6101),
    # 横浜市都筑区
    '中川':     (35.5541, 139.5596),
    'センター北': (35.5601, 139.5543),
    'センター南': (35.5514, 139.5481),
    '都筑ふれあいの丘': (35.5667, 139.5459),
    '牛込':     (35.5454, 139.5355),
    '葛が谷':   (35.5559, 139.5451),
    # 横浜市鶴見区
    '鶴見':     (35.5082, 139.6795),
    '鶴見小野': (35.5001, 139.6862),
    '国道':     (35.5045, 139.6849),
    '弁天橋':   (35.5012, 139.6924),
    '浅野':     (35.5012, 139.6977),
    '新芝浦':   (35.4974, 139.7012),
    # 川崎市中原区
    '武蔵小杉': (35.5759, 139.6593),
    '向河原':   (35.5783, 139.6711),
    '平間':     (35.5719, 139.6788),
    '鹿島田':   (35.5728, 139.6866),
    '武蔵中原': (35.5786, 139.6517),
    '武蔵新城': (35.5905, 139.6394),
    # 川崎市幸区
    '川崎':     (35.5308, 139.7027),
    '矢向':     (35.5407, 139.6901),
    '尻手':     (35.5498, 139.6945),
    '八丁畷':   (35.5333, 139.7010),
    '鹿島田':   (35.5728, 139.6866),
    # 川崎市高津区
    '溝の口':   (35.5999, 139.6165),
    '武蔵溝ノ口': (35.6003, 139.6144),
    '津田山':   (35.5958, 139.6048),
    '久地':     (35.5929, 139.5986),
    '宿河原':   (35.5863, 139.5938),
    '登戸':     (35.5871, 139.5764),
    # 川崎市川崎区
    '川崎':     (35.5308, 139.7027),
    '港町':     (35.5254, 139.7085),
    '小田栄':   (35.5361, 139.7068),
    '川崎新町': (35.5244, 139.7125),
    # 港北区追加分
    '日吉本町': (35.5491, 139.6285),
    '新横浜':   (35.5100, 139.6061),
    '新綱島':   (35.5404, 139.6350),
}

# ── 町名フォールバック座標（駅名も空欄の場合）───────────────
TOWN_FALLBACK_COORDS = {
    '鳥山町':   (35.5180, 139.5990),
    '新吉田東': (35.5280, 139.6050),
    '篠原台町': (35.4950, 139.6150),
}

# ── ジオコーディングキャッシュ（JSONファイル）────────────────
GEOCODE_CACHE_PATH = os.path.join(BASE_DIR, 'geocode_cache.json')

def load_geocode_cache():
    if os.path.exists(GEOCODE_CACHE_PATH):
        with open(GEOCODE_CACHE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_geocode_cache(cache):
    with open(GEOCODE_CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def geocode_gsi(address: str, area: str, cache: dict) -> tuple:
    """
    国土地理院ジオコーディングAPIで住所→(lat, lon)を取得。
    - キャッシュがあればそれを返す
    - バウンディングボックスで妥当性チェック（海・山対策）
    - 失敗時は (None, None) を返す
    """
    if address in cache:
        v = cache[address]
        return (v['lat'], v['lon']) if v else (None, None)

    bbox = AREA_BBOX.get(area, {})
    url = 'https://msearch.gsi.go.jp/address-search/AddressSearch?q=' + \
          urllib.parse.quote(address)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'kanagawa-reins-app/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        time.sleep(0.3)  # 過負荷防止

        if not data:
            # 丁目以降を削ってリトライ
            addr_short = re.sub(r'\d+丁目.*$', '', address).strip()
            addr_short = re.sub(r'[一二三四五六七八九十]+丁目.*$', '', addr_short).strip()
            if addr_short != address:
                url2 = 'https://msearch.gsi.go.jp/address-search/AddressSearch?q=' + \
                       urllib.parse.quote(addr_short)
                req2 = urllib.request.Request(url2, headers={'User-Agent': 'kanagawa-reins-app/1.0'})
                with urllib.request.urlopen(req2, timeout=10) as resp2:
                    data = json.loads(resp2.read().decode('utf-8'))
                time.sleep(0.3)
            if not data:
                cache[address] = None
                return (None, None)

        # 最初の候補を取得
        coords = data[0]['geometry']['coordinates']  # [lon, lat]
        lon, lat = float(coords[0]), float(coords[1])

        # バウンディングボックスチェック
        if bbox:
            if not (bbox['lat_min'] <= lat <= bbox['lat_max'] and
                    bbox['lon_min'] <= lon <= bbox['lon_max']):
                # 範囲外 → 次の候補を試す
                for candidate in data[1:]:
                    c = candidate['geometry']['coordinates']
                    lo, la = float(c[0]), float(c[1])
                    if (bbox['lat_min'] <= la <= bbox['lat_max'] and
                            bbox['lon_min'] <= lo <= bbox['lon_max']):
                        lat, lon = la, lo
                        break
                else:
                    # 全候補が範囲外
                    cache[address] = None
                    return (None, None)

        cache[address] = {'lat': lat, 'lon': lon}
        return (lat, lon)

    except Exception:
        cache[address] = None
        return (None, None)


def build_geocode_address(row, area):
    """所在地から町名レベルのジオコーディング用住所を組み立て"""
    addr = str(row.get('所在地', ''))
    if not addr or addr == 'nan':
        return None

    # CID修正
    addr = addr.replace('(cid:7738)', '樽')
    addr = addr.replace('(cid:7738)町', '樽町')
    # 「樽」だけになっている場合も補正
    addr = re.sub(r'(?<![\u4e00-\u9fff])樽(?!町)', '樽町', addr)

    # 全角数字→半角に変換
    addr = addr.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

    # 丁目・番地以降をすべて削除して町名レベルに統一
    # 「港北区町○丁目」は樽町に補正
    addr = re.sub(r'^港北区町\d+丁目', '港北区樽町', addr)
    addr = re.sub(r'\d+丁目.*$', '', addr).strip()
    addr = re.sub(r'[一二三四五六七八九十]+丁目.*$', '', addr).strip()
    addr = re.sub(r'\d+番地.*$', '', addr).strip()
    addr = re.sub(r'\d+-\d+.*$', '', addr).strip()
    addr = re.sub(r'\d+番.*$', '', addr).strip()

    # 例: addr = "港北区大曽根" → "神奈川県横浜市港北区大曽根"
    # 先頭に「神奈川県」＋市名を付与
    if '横浜市' in area:
        prefix = '神奈川県横浜市'
    elif '川崎市' in area:
        prefix = '神奈川県川崎市'
    else:
        prefix = '神奈川県'

    if not addr.startswith('神奈川県'):
        addr = prefix + addr

    return addr if addr else None


# ── データ読み込み（キャッシュ付き）──────────────────────────
@st.cache_data
def load_data(area: str, bukken: str) -> pd.DataFrame:
    folder = BUKKEN_MAP[bukken]
    excel_name = EXCEL_NAME_MAP.get((area, bukken))
    if not excel_name:
        return pd.DataFrame()

    path = os.path.join(BASE_DIR, area, folder, excel_name)
    if not os.path.exists(path):
        return pd.DataFrame()

    raw = pd.read_excel(path, sheet_name='成約データ一覧', header=None)
    data = raw.iloc[2:].copy()

    if bukken == 'マンション':
        data.columns = ['No','物件番号','所在地','建物名','間取','専有面積',
                        '価格','㎡単価','坪単価','管理費','取引態様',
                        '沿線','駅','交通','成約年月日','築年月']
        data['面積'] = pd.to_numeric(data['専有面積'], errors='coerce')
        data['単価'] = pd.to_numeric(data['㎡単価'], errors='coerce')
        data['単価ラベル'] = '㎡単価（万円）'
    elif bukken == '戸建':
        data.columns = ['No','物件番号','種目','所在地','取引態様','土地面積',
                        '建物面積','間取','用途地域','価格','坪単価',
                        '沿線','駅','交通','成約年月日','築年月']
        data['面積'] = pd.to_numeric(data['土地面積'], errors='coerce')
        data['単価'] = pd.to_numeric(data['坪単価'], errors='coerce')
        data['単価ラベル'] = '坪単価（万円）'
    else:  # 土地
        data.columns = ['No','物件番号','種目','所在地','取引態様','土地面積',
                        '用途地域','建ぺい率','容積率','接道','価格',
                        '㎡単価','坪単価','沿線','駅','交通','成約年月日']
        data['面積'] = pd.to_numeric(data['土地面積'], errors='coerce')
        data['単価'] = pd.to_numeric(data['坪単価'], errors='coerce')
        data['単価ラベル'] = '坪単価（万円）'

    data['価格'] = pd.to_numeric(data['価格'], errors='coerce')
    data['成約年月日'] = pd.to_datetime(data['成約年月日'], errors='coerce')
    data['month'] = data['成約年月日'].dt.to_period('M').astype(str)

    def get_walk(t):
        if pd.isna(t): return None
        m = re.search(r'徒歩(\d+)分', str(t))
        return int(m.group(1)) if m else None
    data['徒歩分'] = data['交通'].apply(get_walk)

    data = data.reset_index(drop=True)
    return data


# ── ジオコーディング実行（進捗バー付き）─────────────────────
def geocode_dataframe(df, area, cache):
    """DataFrameの所在地列をジオコーディングしてlat/lon列を追加"""
    lats, lons = [], []
    # 住所文字列を組み立て（ユニーク住所でAPIを叩く）
    addresses = [build_geocode_address(row, area) for _, row in df.iterrows()]

    # ユニークな未キャッシュ住所だけAPIコール
    unique_addrs = list(set(a for a in addresses if a and a not in cache))
    if unique_addrs:
        prog = st.progress(0, text=f"ジオコーディング中… 0/{len(unique_addrs)}")
        for i, addr in enumerate(unique_addrs):
            geocode_gsi(addr, area, cache)
            prog.progress((i + 1) / len(unique_addrs),
                          text=f"ジオコーディング中… {i+1}/{len(unique_addrs)}")
        prog.empty()
        save_geocode_cache(cache)

    for addr, (_, row) in zip(addresses, df.iterrows()):
        if addr and addr in cache and cache[addr]:
            lats.append(cache[addr]['lat'])
            lons.append(cache[addr]['lon'])
        else:
            # フォールバック①：駅名から座標を取得
            eki = str(row.get('駅', '') or '').strip()
            fallback = STATION_FALLBACK_COORDS.get(eki)
            # フォールバック②：駅名も空なら町名で取得
            if not fallback:
                raw_addr = str(row.get('所在地', '') or '')
                town_m = re.search(r'区(.+?)(?:\d|[一二三四五六七八九十]|$)', raw_addr)
                town = town_m.group(1).strip() if town_m else ''
                fallback = TOWN_FALLBACK_COORDS.get(town)
            if fallback:
                # 駅座標に小さなランダムオフセットを加えて重複を避ける
                import random
                lat_offset = random.uniform(-0.002, 0.002)
                lon_offset = random.uniform(-0.002, 0.002)
                lats.append(fallback[0] + lat_offset)
                lons.append(fallback[1] + lon_offset)
            else:
                lats.append(None)
                lons.append(None)

    result = df.copy()
    result['lat'] = lats
    result['lon'] = lons
    result['_geo_fallback'] = [
        (a is None or a not in cache or not cache.get(a))
        and STATION_FALLBACK_COORDS.get(str(row.get('駅', '') or '').strip()) is not None
        for a, (_, row) in zip(addresses, df.iterrows())
    ]
    return result


# ── 価格→マーカー色（4段階）──────────────────────────────────
def price_to_color(price, p25, p50, p75):
    if pd.isna(price): return 'gray'
    if price < p25:   return '#3B82F6'  # 青：安い
    if price < p50:   return '#22C55E'  # 緑：中安
    if price < p75:   return '#F59E0B'  # 黄：中高
    return '#EF4444'                    # 赤：高い


# ── 地図を生成 ────────────────────────────────────────────────
def make_map(df_geo, area, bukken):
    center = AREA_CENTER.get(area, [35.54, 139.64])
    m = folium.Map(location=center, zoom_start=14, tiles='CartoDB positron')

    valid = df_geo.dropna(subset=['lat', 'lon'])
    if valid.empty:
        return m, 0, 0, 0

    p25 = valid['価格'].quantile(0.25)
    p50 = valid['価格'].quantile(0.50)
    p75 = valid['価格'].quantile(0.75)

    unit_label = valid['単価ラベル'].iloc[0] if len(valid) else '単価'

    # 町名を抽出（geocode用住所から）
    import re as _re
    def extract_town_from_geo(addr_key):
        if not addr_key:
            return 'その他'
        # 「神奈川県横浜市港北区大倉山」→「大倉山」
        s = _re.sub(r'^神奈川県(横浜市|川崎市)[^区]+区', '', addr_key)
        return s if s else 'その他'

    valid2 = valid.copy()
    valid2['_geo_addr'] = [build_geocode_address(row, area) for _, row in valid2.iterrows()]
    valid2['_town'] = valid2['_geo_addr'].apply(extract_town_from_geo)

    # 町名ごとにグループ化
    has_fallback = '_geo_fallback' in valid2.columns
    for town, grp in valid2.groupby('_town'):
        lat = grp['lat'].iloc[0]
        lon = grp['lon'].iloc[0]
        cnt = len(grp)
        avg_price = int(grp['価格'].mean())
        med_price = int(grp['価格'].median())
        avg_tan = grp['単価'].mean()
        radius = max(8, min(30, cnt * 1.5))  # 件数で円の大きさを変える
        color = price_to_color(med_price, p25, p50, p75)

        # 物件リスト（最大10件）
        if bukken == 'マンション':
            rows_html = ''.join([
                f"<tr><td style='padding:2px 6px'>{str(r.get('建物名','－') or '－')[:12]}</td>"
                f"<td style='padding:2px 6px;text-align:right'><b>{int(r['価格']):,}万</b></td>"
                f"<td style='padding:2px 6px'>{r.get('間取','－')}</td>"
                f"<td style='padding:2px 6px'>{r.get('専有面積','－')}㎡</td></tr>"
                for _, r in grp.iterrows()
            ])
            list_html = f"<table style='font-size:11px;width:100%'>{rows_html}</table>"

        elif bukken == '戸建':
            rows_html = ''.join([
                f"<tr><td style='padding:2px 6px'>{r.get('所在地','－')[:10]}</td>"
                f"<td style='padding:2px 6px;text-align:right'><b>{int(r['価格']):,}万</b></td>"
                f"<td style='padding:2px 6px'>土地{r.get('土地面積','－')}㎡</td></tr>"
                for _, r in grp.iterrows()
            ])
            list_html = f"<table style='font-size:11px;width:100%'>{rows_html}</table>"
        else:
            rows_html = ''.join([
                f"<tr><td style='padding:2px 6px'>{r.get('所在地','－')[:10]}</td>"
                f"<td style='padding:2px 6px;text-align:right'><b>{int(r['価格']):,}万</b></td>"
                f"<td style='padding:2px 6px'>{r.get('土地面積','－')}㎡</td></tr>"
                for _, r in grp.iterrows()
            ])
            list_html = f"<table style='font-size:11px;width:100%'>{rows_html}</table>"

        popup_html = f"""
        <div style="font-family:sans-serif;font-size:13px;min-width:260px;max-width:340px;max-height:400px;overflow-y:auto">
        <b>📍 {town}</b>　<span style="color:#888">{cnt}件</span><br>
        <hr style="margin:4px 0">
        💰 中央値 <b>{med_price:,}万円</b>　平均 {avg_price:,}万円<br>
        📊 平均{unit_label} {avg_tan:.1f}<br>
        <hr style="margin:4px 0">
        {list_html}
        </div>"""

        color = price_to_color(med_price, p25, p50, p75)

        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            weight=2,
            popup=folium.Popup(popup_html, max_width=340),
            tooltip=f"📍{town}　{cnt}件　中央値{med_price:,}万円"
        ).add_to(m)

    return m, p25, p50, p75


# ── サイドバー ────────────────────────────────────────────────
st.sidebar.header("🔍 エリア・種別選択")
sel_area   = st.sidebar.selectbox("エリア", list(AREA_MAP.keys()))
sel_bukken = st.sidebar.selectbox("種別", list(BUKKEN_MAP.keys()))

df = load_data(sel_area, sel_bukken)

if df.empty:
    st.error(f"データが見つかりません：{sel_area} / {sel_bukken}")
    st.stop()

st.sidebar.divider()
st.sidebar.header("📊 フィルター")

stations = ['全駅'] + sorted(df['駅'].dropna().unique().tolist())
sel_station = st.sidebar.selectbox("最寄駅", stations)

price_min, price_max = int(df['価格'].min()), int(df['価格'].max())
price_range = st.sidebar.slider("価格範囲（万円）", price_min, price_max,
                                 (price_min, price_max), step=100)

area_min = float(df['面積'].min()) if df['面積'].notna().any() else 0.0
area_max = float(df['面積'].max()) if df['面積'].notna().any() else 500.0
area_range = st.sidebar.slider("面積（㎡）", area_min, area_max,
                                (area_min, area_max), step=5.0)

fdf = df.copy()
if sel_station != '全駅':
    fdf = fdf[fdf['駅'] == sel_station]
fdf = fdf[(fdf['価格'] >= price_range[0]) & (fdf['価格'] <= price_range[1])]
fdf = fdf[(fdf['面積'] >= area_range[0]) & (fdf['面積'] <= area_range[1])]

# ── タイトル ──────────────────────────────────────────────────
st.title(f"🏠 {sel_area}　{sel_bukken}　成約データ")
st.caption(f"REINSデータ 2025年5月〜2026年5月 / 全{len(df)}件")

# ── KPI ──────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("対象件数", f"{len(fdf)}件")
c2.metric("平均価格", f"{int(fdf['価格'].mean()):,}万円" if len(fdf) else "-")
c3.metric("中央値価格", f"{int(fdf['価格'].median()):,}万円" if len(fdf) else "-")
unit_label = fdf['単価ラベル'].iloc[0] if len(fdf) else '単価'
c4.metric(f"平均{unit_label}", f"{fdf['単価'].mean():.1f}" if len(fdf) else "-")
c5.metric("平均面積", f"{fdf['面積'].mean():.1f}㎡" if len(fdf) else "-")

st.divider()

# ── タブ構成 ─────────────────────────────────────────────────
tab_chart, tab_map, tab_table = st.tabs(["📊 グラフ分析", "🗺️ 地図表示", "📋 データ一覧"])

# ═══════════════════════════════════════════════
# TAB 1: グラフ分析（既存コードそのまま）
# ═══════════════════════════════════════════════
with tab_chart:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 駅別 中央値単価・件数")
        s_grp = fdf.groupby('駅').agg(
            件数=('価格', 'count'),
            中央値単価=('単価', 'median'),
            中央値価格=('価格', 'median'),
        ).reset_index().sort_values('中央値単価', ascending=True)
        fig = go.Figure()
        fig.add_bar(
            y=s_grp['駅'], x=s_grp['中央値単価'],
            name='中央値単価', marker_color='#F5A623', orientation='h',
            text=s_grp['件数'].astype(str) + '件', textposition='outside'
        )
        fig.update_layout(
            xaxis=dict(title=unit_label),
            height=max(350, len(s_grp) * 30),
            margin=dict(l=10, r=60, t=10, b=10),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📈 月別 成約件数推移")
        m_grp = fdf.groupby('month').size().reset_index(name='件数').sort_values('month')
        fig2 = px.bar(m_grp, x='month', y='件数', color_discrete_sequence=['#E8721C'])
        fig2.update_layout(height=350, xaxis_title='成約月', yaxis_title='件数')
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("💰 価格分布")
        fig3 = px.histogram(fdf, x='価格', nbins=30,
                            color_discrete_sequence=['#F5A623'],
                            labels={'価格': '価格（万円）', 'count': '件数'})
        fig3.update_layout(height=320)
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader(f"📐 面積 vs {unit_label}")
        upper = fdf['単価'].quantile(0.98)
        plot_df = fdf[fdf['単価'] <= upper].copy()
        fig4 = px.scatter(
            plot_df, x='面積', y='単価',
            color='駅', size='価格', size_max=18,
            hover_data={'面積': True, '単価': True, '価格': True, '駅': False},
            labels={'面積': '面積（㎡）', '単価': unit_label, '駅': '最寄駅'},
            color_discrete_sequence=px.colors.qualitative.Vivid,
            opacity=0.75
        )
        fig4.update_layout(height=320, legend=dict(font=dict(size=10)))
        st.plotly_chart(fig4, use_container_width=True)

    # 町名抽出
    def extract_town(address):
        if pd.isna(address): return 'その他'
        s = str(address)
        s = s.replace('(cid:7738)', '樽')
        for prefix in ['神奈川県川崎市', '神奈川県横浜市', '川崎市', '横浜市']:
            s = s.replace(prefix, '')
        s = re.sub(r'^[^区]+区', '', s)
        s = re.sub(r'[０-９0-9]+丁目.*$', '', s)
        s = re.sub(r'[一二三四五六七八九十]+丁目.*$', '', s)
        s = re.sub(r'\d+番地.*$', '', s)
        s = s.strip()
        if s == '町': s = '樽町'
        return s if s else 'その他'

    fdf2 = fdf.copy()
    fdf2['町名'] = fdf2['所在地'].apply(extract_town)

    st.subheader("🚉 駅別集計")
    eki_grp = fdf2.groupby('駅').agg(
        件数=('価格', 'count'),
        平均価格=('価格', lambda x: round(x.mean())),
        中央値価格=('価格', lambda x: round(x.median())),
        平均面積=('面積', lambda x: round(x.mean(), 1)),
        平均単価=('単価', lambda x: round(x.mean(), 1)),
        中央値単価=('単価', lambda x: round(x.median(), 1)),
    ).reset_index().sort_values('件数', ascending=False)
    eki_grp = eki_grp.rename(columns={'平均単価': f'平均{unit_label}', '中央値単価': f'中央値{unit_label}'})
    st.dataframe(eki_grp, use_container_width=True, height=300)

    st.subheader("🗺️ 町名別集計")
    town_grp = fdf2.groupby('町名').agg(
        件数=('価格', 'count'),
        平均価格=('価格', lambda x: round(x.mean())),
        中央値価格=('価格', lambda x: round(x.median())),
        平均面積=('面積', lambda x: round(x.mean(), 1)),
        平均単価=('単価', lambda x: round(x.mean(), 1)),
        中央値単価=('単価', lambda x: round(x.median(), 1)),
    ).reset_index().sort_values('件数', ascending=False)
    town_grp = town_grp.rename(columns={
        '平均単価': f'平均{unit_label}',
        '中央値単価': f'中央値{unit_label}'
    })
    st.dataframe(town_grp, use_container_width=True, height=300)


# ═══════════════════════════════════════════════
# TAB 2: 地図表示（新規）
# ═══════════════════════════════════════════════
with tab_map:
    st.subheader(f"🗺️ 成約事例マップ　{sel_area}　{sel_bukken}")

    col_info, col_btn, col_reset = st.columns([3, 1, 1])
    with col_info:
        st.caption(
            "マーカーをクリックすると物件詳細が表示されます。"
            "色は価格帯（青＝安い〜赤＝高い）を示します。"
        )
    with col_btn:
        run_geocode = st.button("📍 地図を表示する", type="primary", use_container_width=True)
    with col_reset:
        if st.button("🗑️ キャッシュ削除", use_container_width=True):
            if os.path.exists(GEOCODE_CACHE_PATH):
                os.remove(GEOCODE_CACHE_PATH)
            for k in list(st.session_state.keys()):
                if k.startswith("geo_"):
                    del st.session_state[k]
            st.success("キャッシュ削除完了。再度地図を表示するを押してください。")
            st.stop()

    # ジオコーディング済みデータをsession_stateに保持
    cache_key = f"geo_{sel_area}_{sel_bukken}"
    if run_geocode or cache_key in st.session_state:
        if run_geocode or cache_key not in st.session_state:
            geocode_cache = load_geocode_cache()
            fdf_geo = geocode_dataframe(fdf, sel_area, geocode_cache)
            st.session_state[cache_key] = fdf_geo
        else:
            fdf_geo = st.session_state[cache_key]

        # フィルター後のデータに座標を再マージ（フィルター変更対応）
        if not run_geocode and cache_key in st.session_state:
            base_geo = st.session_state[cache_key][['物件番号', 'lat', 'lon']]
            fdf_geo = fdf.merge(base_geo, on='物件番号', how='left')

        total = len(fdf_geo)
        mapped = fdf_geo.dropna(subset=['lat', 'lon']).shape[0]
        failed = total - mapped
        fallback_cnt = int(fdf_geo.get('_geo_fallback', pd.Series([False]*total)).sum()) if '_geo_fallback' in fdf_geo.columns else 0
        exact_cnt = mapped - fallback_cnt

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("表示件数", f"{mapped}件")
        col_m2.metric("住所で確定", f"{exact_cnt}件")
        col_m3.metric("駅名で代替", f"{fallback_cnt}件",
                      help="住所ジオコーディング失敗のため最寄駅付近に表示")
        col_m4.metric("座標取得失敗", f"{failed}件",
                      delta=f"-{failed}" if failed > 0 else None,
                      delta_color="inverse")

        m, p25, p50, p75 = make_map(fdf_geo, sel_area, sel_bukken)
        # 凡例（Streamlit側で表示）
        st.markdown(
            f"""<div style="display:flex;gap:20px;align-items:center;
                font-size:13px;padding:6px 0">
            <b>価格帯：</b>
            <span><span style="color:#3B82F6;font-size:18px">●</span> ～{int(p25):,}万</span>
            <span><span style="color:#22C55E;font-size:18px">●</span> {int(p25):,}～{int(p50):,}万</span>
            <span><span style="color:#F59E0B;font-size:18px">●</span> {int(p50):,}～{int(p75):,}万</span>
            <span><span style="color:#EF4444;font-size:18px">●</span> {int(p75):,}万～</span>
            </div>""",
            unsafe_allow_html=True
        )
        st_folium(m, width=None, height=600, returned_objects=[])

        if failed > 0:
            with st.expander(f"⚠️ 座標取得失敗 {failed}件の住所"):
                failed_df = fdf_geo[fdf_geo['lat'].isna()][['所在地','価格','駅']].copy()
                st.dataframe(failed_df, use_container_width=True)
    else:
        st.info("「📍 地図を表示する」ボタンを押すと、住所から座標を取得してマップを表示します。\n\n"
                "初回は国土地理院APIへの問い合わせが発生しますが、次回からはキャッシュを使用します。")


# ═══════════════════════════════════════════════
# TAB 3: データ一覧
# ═══════════════════════════════════════════════
with tab_table:
    st.subheader("📋 取引データ一覧")
    if sel_bukken == 'マンション':
        disp_cols = ['所在地','建物名','駅','交通','価格','専有面積','㎡単価','間取','成約年月日']
    elif sel_bukken == '戸建':
        disp_cols = ['所在地','駅','交通','価格','土地面積','建物面積','坪単価','間取','成約年月日']
    else:
        disp_cols = ['所在地','駅','交通','価格','土地面積','㎡単価','坪単価','用途地域','成約年月日']

    disp = fdf[[c for c in disp_cols if c in fdf.columns]].copy()
    if '成約年月日' in disp.columns:
        disp['成約年月日'] = disp['成約年月日'].dt.strftime('%Y/%m/%d')
    st.dataframe(disp, use_container_width=True, height=600)

st.caption("出典：REINS（不動産流通標準情報システム）成約データ / （有）まるみや")
