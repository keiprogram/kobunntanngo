import streamlit as st
import pandas as pd
import numpy as np
import os

# --------------------------------
# アプリ設定
# --------------------------------
st.set_page_config(page_title="古文単語315テスト", layout="centered")

# --------------------------------
# シンプルCSS
# --------------------------------
st.markdown(
    """
    <style>
    body {
        font-family: 'Arial', sans-serif;
        background-color: #ffffff;
        color: #222;
    }
    .choices-container button {
        background-color: #f2f2f2;
        color: #222;
        border: 1px solid #ccc;
        margin: 5px;
        padding: 8px 12px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 15px;
    }
    .choices-container button:hover {
        background-color: #e0e0e0;
    }
    .results-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }
    .results-table th {
        background-color: #f2f2f2;
        color: #333;
        padding: 8px;
        border-bottom: 1px solid #ccc;
    }
    .results-table td {
        border-bottom: 1px solid #ddd;
        padding: 6px;
        text-align: center;
    }
    .stProgress > div > div > div > div {
        background-color: #888;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------
# データ読み込み
# --------------------------------
@st.cache_data
def load_data():
    file_path = "古文単語315_整形版_2.xlsx"
    if not os.path.exists(file_path):
        st.error("❌ Excelファイルが見つかりません。同じフォルダに置いてください。")
        return pd.DataFrame()

    df = pd.read_excel(file_path).fillna("")
    expected_cols = ["問題番号", "古文単語", "意味"]
    if not all(col in df.columns for col in expected_cols):
        st.error("❌ Excelの列名が正しくありません。「問題番号」「古文単語」「意味」の3列にしてください。")
        return pd.DataFrame()

    df = df[(df["古文単語"].str.strip() != "") & (df["意味"].str.strip() != "")]
    df["問題番号"] = df["問題番号"].astype(int)
    return df

words_df = load_data()
if words_df.empty:
    st.stop()

# --------------------------------
# サイドバー設定
# --------------------------------
st.sidebar.title("テスト設定")

test_type = st.sidebar.radio("出題形式", ["古文単語 → 意味", "意味 → 古文単語"])

# 出題範囲設定
range_mode = st.sidebar.radio("出題範囲", ["100語ごと", "自由指定"])

if range_mode == "100語ごと":
    total = len(words_df)
    ranges = [(i + 1, min(i + 100, total)) for i in range(0, total, 100)]
    labels = [f"No.{start}〜No.{end}" for start, end in ranges]
    selected_label = st.sidebar.selectbox("範囲を選択", labels)
    selected_range = ranges[labels.index(selected_label)]
else:
    min_no, max_no = int(words_df["問題番号"].min()), int(words_df["問題番号"].max())
    start_no = st.sidebar.number_input("開始No.", min_value=min_no, max_value=max_no, value=min_no)
    end_no = st.sidebar.number_input("終了No.", min_value=min_no, max_value=max_no, value=min_no + 49)
    if start_no > end_no:
        st.sidebar.error("開始No.は終了No.以下にしてください")
    selected_range = (start_no, end_no)

filtered_df = words_df[(words_df["問題番号"] >= selected_range[0]) & (words_df["問題番号"] <= selected_range[1])]
if filtered_df.empty:
    st.warning("指定した範囲に単語がありません。")
    st.stop()

num_questions = st.sidebar.slider("出題数", 1, min(50, len(filtered_df)), 10)

# --------------------------------
# タイトル
# --------------------------------
st.title("古文単語315テスト")
st.caption("古文単語315の中からランダムに出題されます。")

# --------------------------------
# テスト開始
# --------------------------------
if st.button("テストを開始"):
    st.session_state.update({
        "test_started": True,
        "correct": 0,
        "current_q": 0,
        "finished": False,
        "wrong": [],
    })

    selected = filtered_df.sample(num_questions).reset_index(drop=True)
    st.session_state.update({
        "selected": selected,
        "total": len(selected),
        "current_data": selected.iloc[0],
    })

    # 選択肢生成
    if test_type == "古文単語 → 意味":
        opts = selected[selected["意味"] != selected.iloc[0]["意味"]]["意味"].sample(min(3, len(selected) - 1)).tolist()
    else:
        opts = selected[selected["古文単語"] != selected.iloc[0]["古文単語"]]["古文単語"].sample(min(3, len(selected) - 1)).tolist()

    correct_opt = selected.iloc[0]["意味"] if test_type == "古文単語 → 意味" else selected.iloc[0]["古文単語"]
    options = opts + [correct_opt]
    np.random.shuffle(options)
    st.session_state.options = options

# --------------------------------
# セッション初期化（エラー防止用）
# --------------------------------
if "test_started" not in st.session_state:
    st.session_state.test_started = False
if "current_data" not in st.session_state:
    st.session_state.current_data = None
if "finished" not in st.session_state:
    st.session_state.finished = False

# --------------------------------
# 問題更新関数
# --------------------------------
def update_question(ans):
    q_data = st.session_state.current_data
    if test_type == "古文単語 → 意味":
        correct = q_data["意味"]
        q_text = q_data["古文単語"]
    else:
        correct = q_data["古文単語"]
        q_text = q_data["意味"]

    if ans == correct:
        st.session_state.correct += 1
    else:
        st.session_state.wrong.append((q_data["問題番号"], q_text, correct))

    st.session_state.current_q += 1

    if st.session_state.current_q < st.session_state.total:
        st.session_state.current_data = st.session_state.selected.iloc[st.session_state.current_q]
        if test_type == "古文単語 → 意味":
            opts = st.session_state.selected[
                st.session_state.selected["意味"] != st.session_state.current_data["意味"]
            ]["意味"].sample(min(3, len(st.session_state.selected) - 1)).tolist()
        else:
            opts = st.session_state.selected[
                st.session_state.selected["古文単語"] != st.session_state.current_data["古文単語"]
            ]["古文単語"].sample(min(3, len(st.session_state.selected) - 1)).tolist()
        correct_opt = (
            st.session_state.current_data["意味"]
            if test_type == "古文単語 → 意味"
            else st.session_state.current_data["古文単語"]
        )
        options = opts + [correct_opt]
        np.random.shuffle(options)
        st.session_state.options = options
    else:
        st.session_state.finished = True

# --------------------------------
# 結果表示
# --------------------------------
def show_results():
    correct = st.session_state.correct
    total = st.session_state.total
    st.subheader("テスト結果")
    st.write(f"正解数：{correct}/{total}")
    st.progress(correct / total)
    st.metric("正答率", f"{(correct / total) * 100:.1f}%")

    if st.session_state.wrong:
        df_wrong = pd.DataFrame(st.session_state.wrong, columns=["問題番号", "出題内容", "正答"])
        st.markdown(df_wrong.to_html(classes="results-table"), unsafe_allow_html=True)
    else:
        st.success("全問正解です！")

# --------------------------------
# 出題画面
# --------------------------------
if st.session_state.test_started and not st.session_state.finished and st.session_state.current_data is not None:
    q = st.session_state.current_data
    st.subheader(f"第 {st.session_state.current_q + 1} 問 / {st.session_state.total}")
    st.write(f"問題番号：{q['問題番号']}")
    st.write(q["古文単語"] if test_type == "古文単語 → 意味" else q["意味"])
    st.progress((st.session_state.current_q + 1) / st.session_state.total)

    st.markdown('<div class="choices-container">', unsafe_allow_html=True)
    for i, option in enumerate(st.session_state.options):
        st.button(
            str(option),
            key=f"btn_{i}_{st.session_state.current_q}",
            on_click=update_question,
            args=(option,),
        )
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.test_started and st.session_state.finished:
    show_results()
