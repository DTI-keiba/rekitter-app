import streamlit as st
from openai import OpenAI
import json
import time

# --- 1. OpenAI APIキーの設定 (Secretsを使用) ---
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception:
    st.error("APIキーが未設定です。StreamlitのSecrets設定を確認してください。")
    st.stop()

# --- 2. データ読み込み ---
def load_characters():
    with open('characters.json', 'r', encoding='utf-8') as f:
        return json.load(f)

characters_data = load_characters()

# --- 3. 画面表示の設定 (モバイル対応) ---
st.set_page_config(page_title="歴ッター (Rekitter)", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 20px; font-weight: bold; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; border: 1px solid #f0f2f6; }
    .sidebar-content { padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📜 歴ッター (Rekitter)")
st.caption("歴史上の人物たちがSNSで対話します")

# --- 4. セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_running" not in st.session_state:
    st.session_state.is_running = False

# --- 5. サイドバー (操作パネル) ---
with st.sidebar:
    st.header("🎮 操作パネル")
    
    # 自動論争モード
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 論争開始"):
            st.session_state.is_running = True
    with col2:
        if st.button("⏹️ 停止"):
            st.session_state.is_running = False
    
    if st.button("🗑️ 履歴をリセット"):
        st.session_state.messages = []
        st.session_state.is_running = False
        st.rerun()

    st.divider()

    # --- 個別投稿機能 (復活！) ---
    st.header("✍️ 個別投稿")
    selected_id = st.selectbox("投稿者を選択", options=list(characters_data.keys()), 
                               format_func=lambda x: characters_data[x]['name'])
    user_text = st.text_area("投稿内容を入力", placeholder="免罪符について一言...")
    
    if st.button("📤 投稿する"):
        if user_text:
            char = characters_data[selected_id]
            st.session_state.messages.append({
                "role": selected_id,
                "name": char["name"],
                "content": user_text,
                "avatar": f"static/{char['image']}"
            })
            st.rerun()

# --- 6. メッセージ表示関数 ---
def display_messages():
    # 最新の投稿が上にくるように表示
    for msg in reversed(st.session_state.messages):
        with st.chat_message(msg["role"], avatar=msg["avatar"]):
            st.write(f"**{msg['name']}** @{msg['role']}")
            st.write(msg["content"])

# --- 7. 自動論争ロジック ---
if st.session_state.is_running:
    # 交互に投稿させるための判定
    last_role = st.session_state.messages[-1]["role"] if st.session_state.messages else "leo"
    current_char_id = "luther" if last_role == "leo" else "leo"
    char = characters_data[current_char_id]

    # AIへの指示作成
    context = [{"role": "system", "content": f"あなたは{char['name']}です。{char['description']} 140文字以内で、相手に反論するか、自分の主張をSNS投稿風に述べてください。"}]
    # 直近の会話の流れを教える
    for m in st.session_state.messages[-5:]:
        context.append({"role": "user", "content": m["content"]})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=context,
            max_tokens=200
        )
        answer = response.choices[0].message.content

        # 履歴に追加
        st.session_state.messages.append({
            "role": current_char_id,
            "name": char["name"],
            "content": answer,
            "avatar": f"static/{char['image']}"
        })
        
        # 画面更新
        st.rerun()
        time.sleep(2) # 投稿間隔

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        st.session_state.is_running = False

# --- 8. メイン表示エリア ---
if not st.session_state.messages:
    st.info("左側のパネルから『論争開始』を押すか、個別投稿を行ってください。")
else:
    display_messages()
