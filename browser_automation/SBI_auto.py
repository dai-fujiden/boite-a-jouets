from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import re
import pandas as pd

timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

PROFILE_DIR = r"C:\playwright_sbi_profile"

#! 以下、ユーザー管理項目
USER_ID = #TODO ユーザーIDを入力 (環境変数などで管理推奨)
PASSWORD = #TODO パスワードを入力 (環境変数などで管理推奨)
DATA_FOLDER = r"C:\finance_data"
OUTPUT_DETAIL = r"C:\finance_data\detail_{}.csv".format(timestamp)
OUTPUT_SUMMARY = r"C:\finance_data\summary_{}.csv".format(timestamp)
OUTPUT_FOREIGN = r"C:\finance_data\foreign_{}.csv".format(timestamp)
# True = 試験（ログイン省略・保存セッション利用）
# False = 本番（ログイン処理あり）
TEST_MODE = False


# =========================
# セッション保存
# =========================


import pandas as pd
import datetime




# =========================================================
# 外国株（韓国・米国）
# =========================================================
def parse_foreign(page, timestamp):

    results = []

    # セクション取得（韓国株・米国株）
    sections = page.locator("div.security-table-title")

    for i in range(sections.count()):
        section = sections.nth(i)
        kind = safe_text(section)

        # このセクションの直後の ul を取得
        ul = section.locator("xpath=following-sibling::ul[1]")
        if ul.count() == 0:
            continue

        rows = ul.locator("li.table-primary-row")

        for j in range(rows.count()):
            row = rows.nth(j)

            # ----------------------------
            # 銘柄情報（上段）
            # ----------------------------
            name_block = row.locator("div.security-title-item").first
            if name_block.count() == 0:
                continue

            raw_name = safe_text(name_block)

            # ティッカー＋名称を整形
            # 例: "069500Samsung KODEX200 ETF"
            # → 分割
            ticker = ""
            name = raw_name

            # 数値ブロック
            values = row.locator("label.security-amount-item")

            if values.count() < 4:
                continue

            results.append({
                "timestamp": timestamp,
                "種類": kind,

                "銘柄名": name,

                "保有数量": safe_text(values.nth(0)),
                "取得単価": safe_text(values.nth(1)),
                "現在値": safe_text(values.nth(2)),
                "外貨建評価損益": safe_text(values.nth(3)),
            })

    return results


# =========================================================
# メイン
# =========================================================
def read_foreign(page, OUTPUT_FILE):

    page.wait_for_timeout(2000)

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    data = parse_foreign(page, timestamp)

    df = pd.DataFrame(data)

    # 重複除去（再描画対策）
    if not df.empty:
        df = df.drop_duplicates()

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(df)
    print("保存完了")
    
def save_session(context, path="sbi_state.json"):
    context.storage_state(path=path)
    print("セッション保存完了")


# =========================
# 再開（試験モード用）
# =========================
def load_context(p):
    try:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            slow_mo=300,
            storage_state="sbi_state.json"
        )
        print("保存セッションで起動")
        return context

    except Exception:
        print("セッションなし → 通常起動")
        return p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            slow_mo=300,
        )


# =========================
# 資産読み取り
# =========================
import pandas as pd

def read_assets(page):

    # 画面が完全に描画されるのを待つ
    page.wait_for_selector("li.table-row", timeout=20000)

    rows = page.locator("li.table-row")

    count = rows.count()
    print("行数:", count)

    records = []

    for i in range(count):
        row = rows.nth(i)

        # 合計行などスキップ
        if row.locator("text=合計").count() > 0:
            continue

        # ★重要：待ち付き取得（timeout回避）
        def safe_text(locator):
            try:
                return locator.inner_text(timeout=5000).strip()
            except:
                return None

        name = safe_text(row.locator("a.link").first)

        eval_amount = safe_text(row.locator('[data-label="評価額"] p'))

        profit = row.locator('[data-label="評価損益"] p')
        profit_yen = safe_text(profit.nth(0))
        profit_pct = safe_text(profit.nth(1))

        day = row.locator('[data-label="前日比"] p')
        day_yen = safe_text(day.nth(0))
        day_pct = safe_text(day.nth(1))

        month = row.locator('[data-label="前月比"] p')
        month_yen = safe_text(month.nth(0))
        month_pct = safe_text(month.nth(1))

        # 空行スキップ
        if not name or not eval_amount:
            continue

        records.append({
            "timestamp": timestamp,
            "資産": name,
            "評価額": eval_amount,
            "評価損益(円)": profit_yen,
            "評価損益(%)": profit_pct,
            "前日比(円)": day_yen,
            "前日比(%)": day_pct,
            "前月比(円)": month_yen,
            "前月比(%)": month_pct,
        })

    df = pd.DataFrame(records)

    df.to_csv(
        OUTPUT_SUMMARY,
        index=False,
        encoding="utf-8-sig"
    )

    print(df)
    print("保存完了")

    return df


def safe_text(el):
    try:
        v = el.text_content(timeout=3000)
        return v.strip() if v else ""
    except:
        return ""


def clean_stock_name(raw_text):
    """「285A キオクシアＨＤ 現買...」からコードと銘柄名を分離"""
    # 4桁のコードを探す
    code_match = re.search(r"\b(\d{4}[A-Z]?|\d{4})\b", raw_text)
    code = code_match.group(1) if code_match else ""

    # コード部分をカット
    text_without_code = raw_text.replace(code, "").strip()

    # 注文ボタン等のゴミキーワード
    garbage = [
        "現買",
        "現売",
        "信買",
        "信売",
        "積立",
        "買付",
        "売却",
        "株オプション",
    ]

    # 改行で分割して最初の1行（銘柄名が含まれる行）を取得
    lines = [line.strip() for line in text_without_code.split("\n") if line.strip()]
    if not lines:
        return code, ""

    name = lines[0]
    for word in garbage:
        if word in name:
            name = name.split(word)[0].strip()

    # 全角スペースや特殊空白を通常の半角スペース1つに統一
    name = re.sub(r"[\s\xa0]+", " ", name).strip()
    return code, name


def parse_target_table(page, h3_text, kind, account):
    """指定された見出し文字列（例: '株式（現物/特定預り）'）を持つテーブルだけを解析する"""
    results = []

    # 見出しテキストが含まれるボールド要素(b)を特定
    target_b = page.locator(f"b:has-text('{h3_text}')").first
    if not target_b.count():
        return results

    # その要素の親(あるいは先祖)にある直近の table を取得
    table = target_b.locator("xpath=ancestor::table[1]").first
    rows = table.locator("tr")
    row_count = rows.count()

    # ヘッダー（タイトル行と項目名行など）を飛ばし、データ行から処理
    # 3行目（インデックス2）から2行ずつのペア（銘柄行、数値行）で回す
    i = 2
    while i < row_count:
        name_row = rows.nth(i)
        name_raw = safe_text(name_row)

        # 全く関係のない行や、空行、フッターはスキップ
        if not name_raw or "保有株数" in name_raw or "保有口数" in name_raw:
            i += 1
            continue

        # 1行目: 銘柄名とコード
        tds_name = name_row.locator("td")
        code, name = clean_stock_name(safe_text(tds_name.first))

        # 2行目: 数値データ（保有数、取得単価、現在値、評価損益）
        if i + 1 < row_count:
            data_row = rows.nth(i + 1)
            tds_data = data_row.locator("td")

            if tds_data.count() >= 4:
                results.append(
                    {
                        "timestamp": timestamp,
                        "種別": kind,
                        "口座": account,
                        "コード": code,
                        "銘柄": name,
                        "保有数": safe_text(tds_data.nth(0)),
                        "取得単価": safe_text(tds_data.nth(1)),
                        "現在値": safe_text(tds_data.nth(2)),
                        "評価損益": safe_text(tds_data.nth(3)),
                    }
                )
            i += 2  # ペアなので2行進める
        else:
            i += 1

    return results


def read_goods(page):
    page.wait_for_timeout(2000)

    all_data = []

    # 1. 株式（特定口座）の抽出
    all_data.extend(
        parse_target_table(page, "株式（現物/特定預り）", "株式", "特定")
    )

    # 2. 株式（NISA成長投資枠）の抽出
    all_data.extend(
        parse_target_table(
            page, "株式（現物/NISA預り（成長投資枠））", "株式", "NISA成長"
        )
    )

    # 3. 投資信託（NISA成長投資枠）の抽出
    all_data.extend(
        parse_target_table(
            page,
            "投資信託（金額/NISA預り（成長投資枠））",
            "投資信託",
            "NISA成長",
        )
    )

    # DataFrameに変換
    df_portfolio = pd.DataFrame(all_data)

    df_portfolio.to_csv(OUTPUT_DETAIL, index=False, encoding="utf-8-sig")

    print("=== 分類完了データ ===")
    print(df_portfolio.to_string())
    print(f"\nCSVファイル '{OUTPUT_DETAIL}' に保存しました。")




# =========================
# 口座管理→資産画面
# =========================
def goto_asset(page):

    print("口座管理へ移動")

    page.locator('a:has-text("口座管理")').first.click()
    page.wait_for_timeout(2000)
    read_goods(page)
    
    
    
    # page.locator('a:has-text("口座(外貨建)")').first.click()
    # read_foreign(page, OUTPUT_FOREIGN)
    # page.locator('a:has-text("口座管理")').first.click()

    print("My資産クリック")

    page.locator("#my-assets-button").click(force=True)
    page.wait_for_load_state("domcontentloaded")

    return page


# =========================
# ログイン処理（本番用）
# =========================
def login(page):

    print("ログイン処理実行")

    page.wait_for_selector('input[name="username"]')

    page.fill('input[name="username"]', USER_ID)
    page.fill('input[name="password"]', PASSWORD)

    page.locator("#pw-btn").click()

    page.wait_for_timeout(5000)

    return page


# =========================
# メイン
# =========================
with sync_playwright() as p:

    context = load_context(p) if TEST_MODE else p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        slow_mo=300,
    )

    page = context.new_page()

    # =========================
    # 初期ページ
    # =========================
    page.goto( r"https://login.sbisec.co.jp/login/entry?_gl=1%2A1d4c6kd%2A_gcl_au%2AMTQ0Mzg1NDk4Mi4xNzgwMTU4NTc5%2A_ga%2AMzQxMjI4MDMzLjE3ODAxNTg1ODA.%2A_ga_2X743H1G05%2AczE3ODAxNjY2MjgkbzIkZzAkdDE3ODAxNjY2MjgkajYwJGwwJGgw&_rb_uid=2e9d372bf312f21af2e66849ad30ebd01780158578430&_rb_sid=3e5d1780158578431&hc_uus&matid#_rb_uid=2e9d372bf312f21af2e66849ad30ebd01780158578430&_rb_sid=3e5d1780158578431&hc_uus&matid", wait_until="domcontentloaded" )
    # =========================
    # ログイン（本番のみ）
    # =========================
    if not TEST_MODE:

        if "login.sbisec.co.jp" in page.url:
            login(page)

            page.locator("#home-global-nav").click()
            page.wait_for_timeout(3000)

    else:
        print("試験モード：ログインスキップ")

    # =========================
    # 資産取得
    # =========================
    page.wait_for_timeout(2000)

    page = goto_asset(page)
    df = read_assets(page)

    # =========================
    # セッション保存（任意）
    # =========================
    save_session(context)

    input("Enterで終了")
    context.close()