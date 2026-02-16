import streamlit as st
from openai import OpenAI
import json
import time
import os

# --- 1. OpenAI APIキーの設定 (Streamlit Secretsを使用) ---
# 重要: GitHubには直接キーを書かず、Streamlit CloudのSettings > Secrets に設定してください
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception:
    st.error("APIキーが設定されていません。StreamlitのSecrets設定を確認してください。")
    st.stop()

# --- 2. データ読み込み ---
def load_characters():
    with open('characters.json', 'r', encoding='utf-8') as f:
        return json.load(f)

characters_data = load_characters()

# --- 3. 画面表示の設定 ---
st.set_page_config(page_title="歴ッター (Rekitter)", layout="wide")

# スマホ向けにCSSで見た目を調整
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📜 歴ッター (Rekitter)")
st.caption("歴史上の人物たちがSNSで論争を繰り広げます")

# --- 4. セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_running" not in st.session_state:
    st.session_state.is_running = False

# --- 5. サイドバー (操作パネル) ---
with st.sidebar:
    st.header("設定")
    if st.button("🚀 論争スタート"):
        st.session_state.is_running = True
    if st.button("⏹️ 停止 / リセット"):
        st.session_state.messages = []
        st.session_state.is_running = False
        st.rerun()

# --- 6. 投稿表示エリア ---
chat_container = st.container()

def display_messages():
    with chat_container:
        for msg in reversed(st.session_state.messages):
            with st.chat_message(msg["role"], avatar=msg["avatar"]):
                st.write(f"**{msg['name']}** @{msg['role']}")
                st.write(msg["content"])

# --- 7. 論争ロジック ---
if st.session_state.is_running:
    # 交互に投稿させるロジック (簡易版)
    last_role = st.session_state.messages[-1]["role"] if st.session_state.messages else "leo"
    current_char_id = "luther" if last_role == "leo" else "leo"
    char = characters_data[current_char_id]

    # コンテキスト（これまでの会話の流れ）の作成
    context = [{"role": "system", "content": f"あなたは{char['name']}です。{char['description']} 140文字以内で、相手に反論するか、自分の主張をSNS投稿風に述べてください。"}]
    for m in st.session_state.messages[-5:]: # 直近5件を参考にする
        context.append({"role": "user", "content": m["content"]})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # コストを抑えるため3.5推奨
            messages=context,
            max_tokens=200
        )
        answer = response.choices[0].message.content

        # メッセージを追加
        new_msg = {
            "role": current_char_id,
            "name": char["name"],
            "content": answer,
            "avatar": f"static/{char['image']}"
        }
        st.session_state.messages.append(new_msg)
        
        # 画面を更新
        display_messages()
        
        # 次の投稿まで待機（演出）
        time.sleep(3) 
        st.rerun()

    except Exception as e:
        st.error(f"通信エラー: {e}")
        st.session_state.is_running = False

# --- 8. 投稿がない時の初期表示 ---
if not st.session_state.messages:
    st.info("左側の「論争スタート」を押して、宗教改革の火蓋を切りましょう。")
else:
    display_messages()
