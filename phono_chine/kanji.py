import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ----------------------------
# Streamlit設定
# ----------------------------
st.set_page_config(
    page_title="漢字音韻分析サンバースト",
    layout="wide"
)

st.title("🀄 漢字音韻サンバースト図")

# ----------------------------
# データ読み込み
# ----------------------------
@st.cache_data
def load_data():
    return pd.read_csv("chinese_data_classified.csv")

try:
    df = load_data()
except FileNotFoundError:
    st.error("chinese_data_classified.csv が見つかりません")
    st.stop()

# ----------------------------
# フィルタ（基本処理）
# ----------------------------
df = df[df["tone"].isin([1, 2, 3, 4])].copy()

# ----------------------------
# サイドバー
# ----------------------------
st.sidebar.header("グラフ設定")

exclude_cols = [
    "Unnamed: 0",
    "频率",
    "累计频率(%)"
]

available_columns = [
    c for c in df.columns
    if c not in exclude_cols
]

default_path = [
    "middle_tone",
    "日本語_五音",
    "日本語_清濁"
]

default_path = [
    c for c in default_path
    if c in available_columns
]

selected_path = st.sidebar.multiselect(
    "階層",
    available_columns,
    default=default_path
)

height = st.sidebar.slider(
    "高さ",
    500,
    1200,
    800,
    50
)

# --- データフレームの表示コラム設定 ---
st.sidebar.markdown("---")
st.sidebar.header("📋 データテーブル設定")

all_df_columns = list(df.columns)
init_df_cols = ["漢字", "ピンイン", "声調", "middle_tone"]
default_df_cols = [c for c in init_df_cols if c in all_df_columns]

selected_df_cols = st.sidebar.multiselect(
    "表示するコラムを指定",
    options=all_df_columns,
    default=default_df_cols
)

# ----------------------------
# Sunburst作成
# ----------------------------
if len(selected_path) == 0:
    st.warning("階層を1つ以上選択してください")
else:
    st.subheader(" → ".join(selected_path))

    # 集計
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
        .agg(
            頻度=("频率", "sum"),
            漢字数=("漢字", "count"),
            代表例=("漢字", "count")
        )
        .reset_index()
    )

    examples = (
        df.groupby(selected_path)
        .apply(get_examples, include_groups=False)
        .reset_index(name="代表漢字")
    )

    grouped = grouped.merge(examples, on=selected_path)

    # Sunburst描画
    fig = px.sunburst(
        grouped,
        path=selected_path,
        values="頻度",
        color=selected_path[0],
        custom_data=["漢字数", "代表漢字"]
    )

    fig.update_traces(
        hovertemplate=
        "<b>%{label}</b><br>"
        "頻度: %{value:,}<br>"
        "漢字数: %{customdata[0]:,}<br>"
        "代表漢字:<br>%{customdata[1]}"
        "<extra></extra>"
    )

    # 音韻説明
    note = """
<b>五音</b><br>
唇音：p b m f<br>
舌音：t d n l<br>
歯音：s z c j 系<br>
牙音：k g 系<br>
喉音：h y w 零声母<br><br>

<b>清濁</b><br>
全清：無気清音<br>
次清：有気清音<br>
全濁：有声阻害音<br>
次濁：鼻音・流音<br><br>

<b>声調</b><br>
平：陰平・陽平の祖形<br>
上：上昇調<br>
去：下降調<br>
入：閉鎖音終わり
"""

    fig.add_annotation(
        x=1.15, y=0.5, xref="paper", yref="paper",
        showarrow=False, align="left", text=note,
        bgcolor="black", bordercolor="gray", borderwidth=1
    )

    fig.update_layout(
        height=height,
        margin=dict(t=20, l=20, r=280, b=20),
        font=dict(size=15)
    )

    st.plotly_chart(fig, use_container_width=True)

    # ----------------------------
    # 現在の選択データ確認・プルダウン絞り込み（アップデート部分）
    # ----------------------------
    st.markdown("---")
    st.subheader("🔍 表示中データの詳細・プルダウン絞り込み")
    
    if len(selected_df_cols) == 0:
        st.info("サイドバーの「データテーブル設定」から表示したいコラムを選択してください。")
    else:
        # ベースとなるデータ枠のコピー
        filtered_df = df[selected_df_cols].copy()
        
        # ユーザーが直感的に操作できるよう、横並びのプルダウン（マルチセレクト）を生成
        st.markdown("##### 📥 各コラムの絞り込み項目を選択（未選択ですべて表示）")
        
        # 画面の横幅を活かして、表示されているコラム数に応じて列を自動分割
        cols_widgets = st.columns(len(selected_df_cols))
        
        for i, col_name in enumerate(selected_df_cols):
            with cols_widgets[i]:
                # そのコラムに存在するユニークな値（選択肢）を抽出（欠損値は除外、文字列化）
                unique_values = sorted(filtered_df[col_name].dropna().unique().astype(str))
                
                # プルダウンメニュー（マルチセレクト）を設置
                selected_options = st.multiselect(
                    f"{col_name}",
                    options=unique_values,
                    key=f"filter_{col_name}"
                )
                
                # ユーザーが何かチェックを入れた場合、その値のみにdfを絞り込む
                if selected_options:
                    filtered_df = filtered_df[filtered_df[col_name].astype(str).isin(selected_options)]
        
        # 絞り込まれた結果を反映してテーブルを表示
        st.markdown(f"📊 **該当件数: {len(filtered_df)} 件**")
        st.dataframe(
            filtered_df,
            use_container_width=True
        )