import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as mcolors

# ----------------------------
# 1. Streamlit 画面基本設定
# ----------------------------
st.set_page_config(
    page_title="漢字音韻圖譜",
    layout="wide"
)

st.title("🀄 漢字音韻旭日圖分析平台")

# ----------------------------
# 2. データ読み込み＆エラーハンドリング
# ----------------------------
@st.cache_data
def load_data():
    return pd.read_csv("chinese_data_classified.csv")

try:
    df = load_data()
except FileNotFoundError:
    st.error("chinese_data_classified.csv が見つかりません。パスを確認してください。")
    st.stop()

# ----------------------------
# 3. データ前処理
# ----------------------------
df = df[df["tone"].isin([1, 2, 3, 4])].copy()
df["tone"] = df["tone"].astype(str)

# 各言語の検索用・比較用にデータを標準化（完全一致や部分一致のヒット率を上げるため）
if "ピンイン_数字" not in df.columns:
    # ピンイン列から ba1 や bian3 のような文字列を想定。なければ元のピンイン等を使用
    df["ピンイン_検索用"] = df["ピンイン"].astype(str).str.strip().str.lower()
else:
    df["ピンイン_検索用"] = df["ピンイン_数字"].astype(str).str.strip().str.lower()

if "音読み" in df.columns:
    df["音読み_検索用"] = df["音読み"].astype(str).str.strip()
elif "consonant_jp" in df.columns: # 代替
    df["音読み_検索用"] = df["consonant_jp"].astype(str) + df["vowel_jp"].astype(str)
else:
    df["音読み_検索用"] = ""

if "korean" in df.columns:
    df["韓国音_検索用"] = df["korean"].astype(str).str.strip()
elif "korean_pron" in df.columns:
    df["韓国音_検索用"] = df["korean_pron"].astype(str).str.strip()
else:
    df["韓国音_検索用"] = ""

# ----------------------------
# 4. サイドバー設定コントロール
# ----------------------------
st.sidebar.header("📊 グラフ設定")

exclude_cols = ["Unnamed: 0", "频率", "累计频率(%)"]
available_columns = [c for c in df.columns if c not in exclude_cols]

default_path = ["tone", "日本語_五音", "日本語_清濁"]
selected_path = st.sidebar.multiselect(
    "サンバースト階層の選択",
    available_columns,
    default=[c for c in default_path if c in available_columns]
)

height = st.sidebar.slider("サンバーストの高さ (px)", 500, 1200, 800, 50)

# --- 🎨 カラーマップ設定セクション ---
st.sidebar.markdown("---")
st.sidebar.header("🎨 カラーマップ設定")

sunburst_color_options = {
    "標準（Plotlyデフォルト）": None,
    "パステル (Pastel)": px.colors.qualitative.Pastel,
    "鮮やか (Vivid)": px.colors.qualitative.Vivid,
    "深み (Dark24)": px.colors.qualitative.Dark24,
    "アイス・ファイア (Icefire)": px.colors.cyclical.IceFire, 
    "レインボー (Rainbow)": px.colors.sequential.Rainbow,
    "藍グラデーション (Blues)": px.colors.sequential.Blues,
}

selected_sunburst_cmap_label = st.sidebar.selectbox("サンバーストの配色", list(sunburst_color_options.keys()))
selected_sunburst_cmap = sunburst_color_options[selected_sunburst_cmap_label]

matrix_color_options = {
    "黄・緑・青 (YlGnBu)": "YlGnBu",
    "青のグラデーション (Blues)": "Blues",
    "緑のグラデーション (Greens)": "Greens",
    "マグマ (magma)": "magma",
    "プラズマ (plasma)": "plasma",
    "クール・ウォーム (coolwarm)": "coolwarm",
    "灰・黒 (Greys)": "Greys"
}

selected_matrix_cmap = st.sidebar.selectbox("マトリックスの配色", list(matrix_color_options.keys()), index=0)
matrix_cmap_code = matrix_color_options[selected_matrix_cmap]

# --- 📋 データテーブル表示列の設定 ---
st.sidebar.markdown("---")
st.sidebar.header("📋 データテーブル設定")

all_df_columns = list(df.columns)
init_df_cols = ["漢字", "ピンイン", "tone", "middle_tone"]
default_df_cols = [c for c in init_df_cols if c in all_df_columns]

selected_df_cols = st.sidebar.multiselect(
    "表示するコラムを指定",
    options=all_df_columns,
    default=default_df_cols
)

# ----------------------------
# 5. メインロジック（3つのタブによる画面分離）
# ----------------------------
if len(selected_path) == 0:
    st.warning("サイドバーから階層を1つ以上選択してください。")
else:
    # 👈 ご要望通り、3つ目の「検索タブ」を追加拡張
    tab1, tab2, tab3 = st.tabs(["📊 サンバースト分析", "📜 韻図風クロスマトリックス", "🔍 漢字・音韻逆引き検索"])

    # ==========================================
    # タブ1: サンバースト分析画面
    # ==========================================
    with tab1:
        st.subheader("📍 現在の階層構造: " + " ➔ ".join(selected_path))

        def get_examples(x):
            chars = []
            for h, p in zip(x["漢字"], x["ピンイン"]):
                item = f"{h}({p})"
                if item not in chars:
                    chars.append(item)
                if len(chars) >= 5:
                    break
            return "、".join(chars)

        grouped = (
            df.groupby(selected_path)
            .agg(頻度=("频率", "sum"), 漢字数=("漢字", "count"), 代表例=("漢字", "count"))
            .reset_index()
        )

        examples = (
            df.groupby(selected_path)
            .apply(get_examples, include_groups=False)
            .reset_index(name="代表漢字")
        )

        grouped = grouped.merge(examples, on=selected_path)

        fig = px.sunburst(
            grouped, path=selected_path, values="頻度", color=selected_path[0],
            color_discrete_sequence=selected_sunburst_cmap if isinstance(selected_sunburst_cmap, list) else None,
            color_continuous_scale=selected_sunburst_cmap if isinstance(selected_sunburst_cmap, str) else None,
            custom_data=["漢字数", "代表漢字"]
        )

        fig.update_traces(
            hovertemplate="<b>%{label}</b><br>頻度: %{value:,}<br>漢字数: %{customdata[0]:,}<br>代表漢字:<br>%{customdata[1]}<extra></extra>"
        )

        note = """<b>五音</b><br>唇音：p b m f<br>舌音：t d n l<br>歯音：s z c j 系<br>牙音：k g 系<br>喉音：h y w 零声母<br><br><b>清濁</b><br>全清：無気清音<br>次清：有気清音<br>全濁：有声阻害音<br>次濁：鼻音・流音<br><br><b>声調</b><br>平：陰平・陽平の祖形<br>上：上昇調<br>去：下降調<br>入：閉鎖音終わり"""

        fig.add_annotation(
            x=1.15, y=0.5, xref="paper", yref="paper", showarrow=False, align="left", text=note,
            bgcolor="black", bordercolor="gray", borderwidth=1
        )

        fig.update_layout(height=height, margin=dict(t=20, l=20, r=280, b=20), font=dict(size=15))
        st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # タブ2: クロスマトリックス画面
    # ==========================================
    with tab2:
        st.subheader("🔍 音韻データの詳細・プルダウン絞り込み")
        
        if len(selected_df_cols) == 0:
            st.info("サイドバーの「データテーブル設定」から表示したいコラムを選択してください。")
        else:
            filtered_df = df[selected_df_cols].copy()
            st.markdown("##### 📥 各コラムの絞り込み項目を選択（未選択ですべて表示）")
            cols_widgets = st.columns(len(selected_df_cols))
            
            for i, col_name in enumerate(selected_df_cols):
                with cols_widgets[i]:
                    unique_values = sorted(filtered_df[col_name].dropna().unique().astype(str))
                    selected_options = st.multiselect(f"{col_name}", options=unique_values, key=f"filter_{col_name}")
                    if selected_options:
                        filtered_df = filtered_df[filtered_df[col_name].astype(str).isin(selected_options)]
            
            st.markdown("---")
            st.subheader("📜 韻図風：母音 × 子音 クロス集計マトリックス")
            st.markdown("💡 *縦軸に子音（声母）、横軸に母音（韻母）を配した体系的な分布表です。*")

            current_analysis_df = df.loc[filtered_df.index].copy()
            all_vowels = sorted(current_analysis_df["vowel"].dropna().unique())
            all_consonants = sorted(current_analysis_df["consonants"].dropna().unique())

            if len(all_vowels) == 0 or len(all_consonants) == 0:
                st.info("現在の絞り込み条件に該当する音韻データがありません。")
            else:
                matrix_data = {}
                max_count = 1  

                for consonant in all_consonants:
                    matrix_data[consonant] = {}
                    for vowel in all_vowels:
                        _df_sub = current_analysis_df[
                            (current_analysis_df["consonants"] == consonant) & 
                            (current_analysis_df["vowel"] == vowel)
                        ]
                        count = len(_df_sub)
                        if count > max_count:
                            max_count = count

                        if count > 0:
                            unique_kanji = _df_sub["漢字"].dropna().unique()
                            line1_chars = unique_kanji[0:3]
                            line2_chars = unique_kanji[3:6]
                            
                            line1_str = " ".join(line1_chars)
                            line2_str = " ".join(line2_chars)
                            
                            if len(line2_chars) > 0:
                                cell_text = f"{count}字\n{line1_str}\n{line2_str}"
                            else:
                                cell_text = f"{count}字\n{line1_str}"
                        else:
                            cell_text = "-"
                        
                        matrix_data[consonant][vowel] = {"count": count, "text": cell_text}

                display_records = []
                for consonant in all_consonants:
                    row = {"子音 (声母)": consonant}
                    for vowel in all_vowels:
                        row[vowel] = matrix_data[consonant][vowel]["text"]
                    display_records.append(row)
                
                final_matrix_df = pd.DataFrame(display_records).set_index("子音 (声母)")

                def style_yindu_cells(data):
                    styles = pd.DataFrame('', index=data.index, columns=data.columns)
                    cmap = cm.get_cmap(matrix_cmap_code)
                    
                    for consonant in data.index:
                        for vowel in data.columns:
                            cell_info = matrix_data[consonant][vowel]
                            cnt = cell_info["count"]
                            
                            if cnt > 0:
                                power = (cnt / max_count) * 0.5
                                rgba = cmap(max(0.02, min(power, 0.6)))
                                hex_color = mcolors.to_hex(rgba)
                                text_color = "#ffffff" if power > 0.25 else "#1a1a1a"
                                styles.at[consonant, vowel] = f"background-color: {hex_color}; color: {text_color};"
                            else:
                                styles.at[consonant, vowel] = "background-color: transparent; color: #a0a0a0;"
                    return styles

                styled_final = final_matrix_df.style.apply(style_yindu_cells, axis=None)

                st.markdown(
                    """
                    <style>
                    div[data-testid="stDataFrame"] td {
                        white-space: pre-wrap !important; 
                        min-width: 180px !important;     
                        height: 120px !important;        
                        font-size: 14px !important;    
                        line-height: 1.4 !important;
                        text-align: center !important;
                        vertical-align: middle !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )

                st.dataframe(
                    styled_final,
                    use_container_width=True,
                    height="content"
                )
                
            st.markdown("---")
            st.markdown(f"📊 **該当件数: {len(filtered_df)} 件 (ローデータ一覧)**")
            st.dataframe(
                filtered_df,
                use_container_width=True,
                height="content"
            )

    # ==========================================
    # 👈 タブ3: 【新機能】漢字・音韻逆引き検索画面
    # ==========================================
    with tab3:
        st.header("🔍 東亞多種語言音韻辭典")
        
        search_mode = st.radio(
            "検索モードを選択してください",
            options=["① 漢字から音韻を調べる（個国語・中古音情報）", "② 発音から該当する漢字を逆引きする"],
            horizontal=True
        )
        
        st.markdown("---")
        
        # --------------------------------------
        # モード①：漢字入力 ➔ 読み方・中古音出力
        # --------------------------------------
        if search_mode == "① 漢字から音韻を調べる（個国語・中古音情報）":
            st.subheader("📌 漢字から調べる")
            input_kanji = st.text_input("調べたい漢字を1文字または複数文字で入力してください（例: 東 水 北）", value="水").strip()
            
            if input_kanji:
                # 入力された文字列を1文字ずつのリストに分解
                kanji_list = list(input_kanji.replace(" ", "").replace("、", ""))
                
                # 該当する漢字の行をデータから全抽出
                res_df = df[df["漢字"].isin(kanji_list)].copy()
                
                if res_df.empty:
                    st.warning(f"入力された漢字 '{input_kanji}' はデータベースに見つかりませんでした。")
                else:
                    st.success(f"該当するデータが {len(res_df)} 件見つかりました。")
                    
                    # ユーザーに見やすいレイアウトの専用カード、または厳選テーブルで表示
                    # カラムの存在チェックを挟んで安全に出力
                    display_cols = ["漢字"]
                    if "音読み_検索用" in df.columns: display_cols.append("日本語_五音")
                    if "pin" in df.columns or "ピンイン" in df.columns: display_cols.append("ピンイン")
                    if "tone" in df.columns: display_cols.append("tone")
                    if "korean" in df.columns: display_cols.append("korean")
                    if "middle_tone" in df.columns: display_cols.append("middle_tone")
                    
                    # 他の分類用カラムも存在すればすべて動的に追加可能
                    additional_info = [c for c in ["日本語_清濁", "vowel", "consonants"] if c in df.columns]
                    display_cols.extend(additional_info)
                    
                    # リネーム用辞書でヘッダーを分かりやすく綺麗にする
                    rename_dict = {
                        "漢字": "🔤 漢字",
                        "日本語_五音": "🇯🇵 日本語音読み",
                        "ピンイン": "🇨🇳 現代中国語 (ピンイン)",
                        "tone": "🎵 現代声調",
                        "korean": "🇰🇷 韓国語音 (ハングル)",
                        "middle_tone": "📜 中古音声調",
                        "日本語_清濁": "⚖️ 清濁",
                        "vowel": "韻母",
                        "consonants": "声母"
                    }
                    
                    table_df = res_df[display_cols].rename(columns=rename_dict)
                    st.dataframe(table_df, use_container_width=True)
                    
        # --------------------------------------
        # モード②：発音（日・中・韓）➔ 漢字一覧の逆引き
        # --------------------------------------
        else:
            st.subheader("📌 発音から漢字を逆引きする")
            st.info("💡 調べたい言語の欄に入力してください（複数指定した場合は『かつ（AND）』で絞り込まれます）")
            
            c1, c2, c3 = st.columns(3)
            
            with c1:
                jp_query = st.text_input("🇯🇵 日本語のひらがな読み（例: とう、すい）", value="").strip()
            with c2:
                zh_query = st.text_input("🇨🇳 中国語ピンイン数字表記（例: dong1, shui3, bei3）", value="").strip().lower()
            with c3:
                ko_query = st.text_input("🇰🇷 韓国語ハングル読み（例: 동、수）", value="").strip()
                
            if jp_query or zh_query or ko_query:
                # 元のdfを汚さないようクローン
                reverse_res_df = df.copy()
                conditions_text = []
                
                # ① 日本語ひらがなでフィルタ
                if jp_query:
                    # カタカナとひらがなの表記揺れをマッピング。部分一致で対応
                    reverse_res_df = reverse_res_df[
                        reverse_res_df["日本語の読み"].str.contains(jp_query, na=False) |
                        reverse_res_df["日本語の読み"].astype(str).str.contains(jp_query, na=False)
                    ]
                    conditions_text.append(f"日本語読み: '{jp_query}'")
                    
                # ② 中国語ピンイン（数字付き等）でフィルタ
                if zh_query:
                    # ba1 や bian3 のように完全、もしくは部分一致
                    reverse_res_df = reverse_res_df[
                        reverse_res_df["ピンイン2"].str.contains(zh_query, na=False) |
                        reverse_res_df["ピンイン2"].astype(str).str.lower().str.contains(zh_query, na=False)
                    ]
                    conditions_text.append(f"中国語ピンイン: '{zh_query}'")
                    
                # ③ 韓国語ハングルでフィルタ
                if ko_query:
                    reverse_res_df = reverse_res_df[
                        reverse_res_df["韓国語の読み"].str.contains(ko_query, na=False)
                    ]
                    conditions_text.append(f"韓国語音: '{ko_query}'")
                    
                # 結果表示
                if reverse_res_df.empty:
                    st.warning("指定された発音条件に合致する漢字は登録されていません。")
                else:
                    st.success(f"🔍 {' ＋ '.join(conditions_text)} に合致する漢字が {len(reverse_res_df)} 件見つかりました。")
                    
                    # 漢字だけをズラッと並べるエリア（クリップボードにコピーしやすくする）
                    matched_kanji = reverse_res_df["漢字"].dropna().unique()
                    st.markdown("### 🎯 該当する漢字一覧")
                    st.code("  ".join(matched_kanji), language="text")
                    
                    # 詳細テーブルも一緒に提示
                    with st.expander("📄 合致したデータの音韻詳細情報を展開"):
                        st.dataframe(
                            reverse_res_df[selected_df_cols],
                            use_container_width=True,
                            height="content"
                        )
            else:
                st.info("上のいずれかの入力ボックスに発音を入力すると、即座に逆引きリストが計算されます。")