import streamlit as st
import pandas as pd
import numpy as np
import os

# --------------------------------
# アプリ設定
# --------------------------------
st.set_page_config(page_title="古文単語315テスト", layout="centered")

# --------------------------------
# カスタムCSS（和モダン配色）
# --------------------------------
st.markdown(
    """
    <style>
    body {
        font-family: 'Hiragino Kaku Gothic ProN', sans-serif;
        background-color: #022033;
        color: #ffae4b;
    }
    .test-container {
        background-color: #033652;
        border-radius: 15px;
        padding: 20px;
        margin-top: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    }
    .choices-container button {
        background-color: #ffae4b;
        color: #022033;
        border: none;
        margin: 6px;
        padding: 10px 15px;
        border-radius: 10px;
        font-weight: bold;
        cursor: pointer;
    }
    .choices-container button:hover {
        background-color: #ffcc70;
        color: #022033;
    }
    .results-table {
        width: 100%;
        border-collapse: collapse;
        color: #fff;
    }
    .results-table th {
        background-color: #ffae4b;
        color: #022033;
        padding: 10px;
    }
    .results-table td {
        border: 1px solid #ffae4b;
        padding: 8px;
        text-align: center;
    }
    .stProgress > div > div > div > div {
        background-color: #ffae4b;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------
# Excelデータ読み込み
# --------------------------------
@st.cache_data
def load_data():
    file_path = "古文単語315_整形版_2.xlsx"
    if not os.path.exists(file_path):
        st.error("❌ Excelファイルが見つかりません。同じフォルダに置いてください。")
        return pd.DataFrame()
    
    df = pd.read_excel(file_path).fillna("")  # 欠損値を空文字に
    df.columns = ["古文単語", "意味"]
    df.reset_index(inplace=True)
    df["No."] = df.index + 1
    return df

words_df = load_data()
if words_df.empty:
    st.stop()

# --------------------------------
# サイドバー設定
# --------------------------------
st.sidebar.title("📖 テスト設定")

test_type = st.sidebar.radio("出題形式を選択", ["古文単語 → 意味", "意味 → 古文単語"])
num_questions = st.sidebar.slider("出題数を選択", 5, min(50, len(words_df)), 10)

# --------------------------------
# メインタイトル
# --------------------------------
st.title("📘 古文単語315テストアプリ")
st.write("古文単語315の中からランダムに出題されます。")

# --------------------------------
# テスト開始処理
# --------------------------------
if st.button("テストを開始"):
    st.session_state.update({
        "test_started": True,
        "correct_answers": 0,
        "current_question": 0,
        "finished": False,
        "wrong_answers": [],
    })
    
    selected_questions = words_df.sample(num_questions).reset_index(drop=True)
    st.session_state.update({
        "selected_questions": selected_questions,
        "total_questions": len(selected_questions),
        "current_question_data": selected_questions.iloc[0],
    })
    
    # 初回選択肢生成
    if test_type == "古文単語 → 意味":
        other_opts = selected_questions[
            selected_questions["意味"] != selected_questions.iloc[0]["意味"]
        ]["意味"].sample(min(3, len(selected_questions)-1)).tolist()
        options = other_opts + [selected_questions.iloc[0]["意味"]]
    else:
        other_opts = selected_questions[
            selected_questions["古文単語"] != selected_questions.iloc[0]["古文単語"]
        ]["古文単語"].sample(min(3, len(selected_questions)-1)).tolist()
        options = other_opts + [selected_questions.iloc[0]["古文単語"]]
    
    np.random.shuffle(options)
    st.session_state.options = options

# --------------------------------
# 問題更新関数
# --------------------------------
def update_question(answer):
    if test_type == "古文単語 → 意味":
        correct = st.session_state.current_question_data["意味"]
        question = st.session_state.current_question_data["古文単語"]
    else:
        correct = st.session_state.current_question_data["古文単語"]
        question = st.session_state.current_question_data["意味"]

    if answer == correct:
        st.session_state.correct_answers += 1
    else:
        st.session_state.wrong_answers.append((question, correct))

    st.session_state.current_question += 1

    if st.session_state.current_question < st.session_state.total_questions:
        st.session_state.current_question_data = st.session_state.selected_questions.iloc[st.session_state.current_question]
        if test_type == "古文単語 → 意味":
            other_opts = st.session_state.selected_questions[
                st.session_state.selected_questions["意味"] != st.session_state.current_question_data["意味"]
            ]["意味"].sample(min(3, len(st.session_state.selected_questions)-1)).tolist()
            options = other_opts + [st.session_state.current_question_data["意味"]]
        else:
            other_opts = st.session_state.selected_questions[
                st.session_state.selected_questions["古文単語"] != st.session_state.current_question_data["古文単語"]
            ]["古文単語"].sample(min(3, len(st.session_state.selected_questions)-1)).tolist()
            options = other_opts + [st.session_state.current_question_data["古文単語"]]
        np.random.shuffle(options)
        st.session_state.options = options
    else:
        st.session_state.finished = True

# --------------------------------
# 結果表示関数
# --------------------------------
def show_results():
    correct = st.session_state.correct_answers
    total = st.session_state.total_questions
    st.subheader("✅ テスト結果")
    st.write(f"正解数：{correct}/{total}")
    st.progress(correct / total)
    st.metric("正答率", f"{(correct/total)*100:.1f}%")

    if st.session_state.wrong_answers:
        df_wrong = pd.DataFrame(st.session_state.wrong_answers, columns=["問題", "正しい答え"])
        st.markdown(df_wrong.to_html(classes="results-table"), unsafe_allow_html=True)
    else:
        st.success("全問正解です！🎉")

# --------------------------------
# 出題画面
# --------------------------------
if "test_started" in st.session_state and not st.session_state.finished:
    st.markdown('<div class="test-container">', unsafe_allow_html=True)
    q = st.session_state.current_question_data
    st.subheader(f"第 {st.session_state.current_question + 1} 問 / {st.session_state.total_questions}")
    st.write(q["古文単語"] if test_type == "古文単語 → 意味" else q["意味"])
    
    progress = (st.session_state.current_question + 1) / st.session_state.total_questions
    st.progress(progress)

    st.markdown('<div class="choices-container">', unsafe_allow_html=True)
    for i, option in enumerate(st.session_state.options):
        # ✅ NaN・None・数値などを安全に文字列化
        option_str = str(option) if pd.notna(option) else ""
        st.button(option_str, key=f"opt_{i}_{st.session_state.current_question}",
                  on_click=update_question, args=(option_str,))
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif "test_started" in st.session_state and st.session_state.finished:
    show_results()
