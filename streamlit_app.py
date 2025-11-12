import streamlit as st
import pandas as pd
import numpy as np
import os
import re

# === アプリ設定 ===
st.set_page_config(page_title="古文単語テスト", layout="wide")

# === カスタムCSS ===
st.markdown("""
<style>
    body {
        font-family: 'Hiragino Mincho ProN', 'YuMincho', serif;
        background-color: #f9f5f0;
        color: #333;
    }
    .test-container {
        background-color: #fffaf0;
        border-radius: 12px;
        padding: 25px;
        margin: 20px auto;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        max-width: 800px;
    }
    .word-display {
        font-size: 2.2em;
        font-weight: bold;
        text-align: center;
        margin: 20px 0;
        color: #5d4037;
        font-family: 'Sawarabi Mincho', serif;
    }
    .choices-container {
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin: 20px 0;
    }
    .choices-container button {
        background-color: #8d6e63;
        color: white;
        border: none;
        padding: 14px;
        border-radius: 8px;
        font-size: 1.1em;
        cursor: pointer;
        transition: 0.3s;
        text-align: left;
    }
    .choices-container button:hover {
        background-color: #6d4c41;
    }
    .results-table {
        margin: 20px auto;
        border-collapse: collapse;
        width: 100%;
        background-color: white;
    }
    .results-table th {
        background-color: #8d6e63;
        color: white;
        padding: 12px;
    }
    .results-table td {
        border: 1px solid #8d6e63;
        padding: 10px;
        text-align: center;
    }
    .stProgress > div > div > div > div {
        background-color: #a1887f;
    }
    .footer {
        text-align: center;
        margin-top: 50px;
        color: #777;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# === データ読み込み ===
@st.cache_data
def load_kobun_data():
    # アップロードされたファイルを直接使う
    if 'uploaded_file' in st.session_state and st.session_state.uploaded_file is not None:
        df = pd.read_excel(st.session_state.uploaded_file, sheet_name="シート1", header=None)
    else:
        # デフォルトでローカルファイルを探す
        file_path = "無題のスプレッドシート.xlsx"
        if not os.path.exists(file_path):
            st.error(f"ファイルが見つかりません: {file_path}")
            st.info("サイドバーからExcelファイルをアップロードしてください。")
            return pd.DataFrame()
        df = pd.read_excel(file_path, sheet_name="シート1", header=None)

    # 1行目をヘッダーに
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)
    df.columns = ['単語', '意味']

    # 意味の加工：数字＋意味 を分離
    def parse_meanings(row):
        word = row['単語']
        meaning_str = str(row['意味'])
        # 「２思う ３（男女の）関係を結ぶ」のような形式をパース
        meanings = re.split(r'\d+ ?', meaning_str)
        meanings = [m.strip() for m in meanings if m.strip() and m.strip() != 'nan']
        return pd.Series({'単語': word, '意味リスト': meanings})

    parsed = df.apply(parse_meanings, axis=1)
    # 各意味を1行に展開
    rows = []
    for _, row in parsed.iterrows():
        for i, meaning in enumerate(row['意味リスト']):
            rows.append({'単語': row['単語'], '意味': meaning, '意味番号': i+1})
    return pd.DataFrame(rows)

# === サイドバー ===
st.sidebar.title("古文単語テスト設定")

# ファイルアップロード（優先）
uploaded_file = st.sidebar.file_uploader("Excelファイルをアップロード", type=['xlsx'])
if uploaded_file is not None:
    st.session_state.uploaded_file = uploaded_file

# データ読み込み
df = load_kobun_data()
if df.empty:
    st.stop()

# 出題範囲：単語のインデックスで
total_words = len(df)
start_idx = st.sidebar.number_input("開始行（1から）", min_value=1, max_value=total_words, value=1)
end_idx = st.sidebar.number_input("終了行", min_value=start_idx, max_value=total_words, value=min(50, total_words))
if start_idx > end_idx:
    st.sidebar.error("開始行は終了行以下にしてください")
    st.stop()

# 範囲内のデータ
filtered_df = df.iloc[start_idx-1:end_idx].reset_index(drop=True)
if len(filtered_df) < 4:
    st.error("選択範囲に4単語以上必要です。")
    st.stop()

# 出題数
max_questions = len(filtered_df)
num_questions = st.sidebar.slider("出題数", 1, min(50, max_questions), min(10, max_questions))

st.sidebar.markdown("---")
st.sidebar.markdown("### ヒント")
st.sidebar.info("複数意味がある単語はランダムに1つ出題")

# === メイン画面 ===
st.markdown("<h1 style='text-align:center; color:#5d4037;'>📜 古文単語テスト</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#777;'>古典の重要単語をマスターしよう</p>", unsafe_allow_html=True)

# === テスト開始 ===
if st.button("🚀 テストを開始する", use_container_width=True):
    st.session_state.update({
        'test_started': True,
        'current_question': 0,
        'correct_answers': 0,
        'total_questions': num_questions,
        'wrong_answers': [],
        'finished': False,
    })

    # 出題単語をサンプル
    selected = filtered_df.sample(num_questions, replace=False).reset_index(drop=True)
    st.session_state.selected_questions = selected

    # 最初の問題
    current = selected.iloc[0]
    meaning = current['意味']
    options = generate_options(selected, current['単語'], meaning)
    st.session_state.update({
        'current_word': current['単語'],
        'correct_meaning': meaning,
        'options': options
    })

# === 選択肢生成関数 ===
def generate_options(df_all, correct_word, correct_meaning):
    # 正解以外の意味（同じ単語の別意味は除外）
    others = df_all[
        (df_all['単語'] != correct_word) |
        (df_all['意味'] != correct_meaning)
    ]
    if len(others) < 3:
        others = df_all[df_all['単語'] != correct_word]
    candidates = others['意味'].drop_duplicates()
    if len(candidates) < 3:
        # 足りなければ重複ありで補充
        sample = candidates.sample(3, replace=True)
    else:
        sample = candidates.sample(3, replace=False)
    options = sample.tolist() + [correct_meaning]
    np.random.shuffle(options)
    return options

# === 問題更新関数 ===
def next_question(user_answer):
    correct = st.session_state.correct_meaning
    word = st.session_state.current_word

    if user_answer == correct:
        st.session_state.correct_answers += 1
    else:
        st.session_state.wrong_answers.append({
            '単語': word,
            'あなたの答え': user_answer,
            '正解': correct
        })

    st.session_state.current_question += 1

    if st.session_state.current_question >= st.session_state.total_questions:
        st.session_state.finished = True
        return

    # 次問題
    current = st.session_state.selected_questions.iloc[st.session_state.current_question]
    meaning = current['意味']
    options = generate_options(st.session_state.selected_questions, current['単語'], meaning)

    st.session_state.update({
        'current_word': current['単語'],
        'correct_meaning': meaning,
        'options': options
    })

# === 問題表示 ===
if st.session_state.get('test_started') and not st.session_state.get('finished'):

    progress = (st.session_state.current_question + 1) / st.session_state.total_questions
    st.progress(progress)

    st.markdown(f"""
    <div class="test-container">
        <div style="text-align:center; font-size:1.1em; color:#8d6e63; margin-bottom:10px;">
            問題 {st.session_state.current_question + 1} / {st.session_state.total_questions}
        </div>
        <div class="word-display">
            {st.session_state.current_word}
        </div>
        <p style="text-align:center; color:#777;">この単語の意味は？</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="choices-container">', unsafe_allow_html=True)
    for opt in st.session_state.options:
        st.button(opt, key=f"opt_{hash(opt)}", on_click=next_question, args=(opt,))
    st.markdown('</div>', unsafe_allow_html=True)

# === 結果表示 ===
elif st.session_state.get('finished', False):
    st.balloons()
    correct = st.session_state.correct_answers
    total = st.session_state.total_questions
    rate = correct / total

    st.markdown(f"""
    <div class="test-container">
        <h2 style="text-align:center; color:#5d4037;">🎉 テスト終了！</h2>
        <h3 style="text-align:center;">正解率: <span style="color:#8d6e63;">{rate:.0%}</span> ({correct}/{total})</h3>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("正解", correct, f"+{correct}")
    with col2:
        st.metric("不正解", total - correct, f"{total - correct}")

    if st.session_state.wrong_answers:
        wrong_df = pd.DataFrame(st.session_state.wrong_answers)
        st.markdown("### ❌ 間違えた問題")
        st.dataframe(
            wrong_df,
            use_container_width=True,
            column_config={
                "単語": st.column_config.TextColumn("単語"),
                "あなたの答え": st.column_config.TextColumn("選んだ答え"),
                "正解": st.column_config.TextColumn("正解")
            }
        )
    else:
        st.success("🎯 全部正解！素晴らしい！")

    if st.button("もう一度テストする"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# === 初期画面 ===
else:
    st.markdown("""
    <div class="test-container">
        <p style="text-align:center; font-size:1.2em; line-height:1.8;">
            古文の重要単語を効率的に覚えよう！<br>
            複数意味がある単語もランダム出題されるので、<br>
            本番さながらの対策ができます。
        </p>
        <p style="text-align:center; color:#8d6e63; margin-top:20px;">
            👈 サイドバーから範囲と出題数を設定して<br>
            <strong>「テストを開始する」</strong>を押してください
        </p>
    </div>
    """, unsafe_allow_html=True)

# === フッター ===
st.markdown("""
<div class="footer">
    古文単語テストアプリ v1.0 | データ形式: 単語,意味（複数可）
</div>
""", unsafe_allow_html=True)