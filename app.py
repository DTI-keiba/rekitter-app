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

# --- 2. データ読み込み (リスト/辞書両対応の頑丈なロジックを維持) ---
def load_characters():
    with open('characters.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        return {item.get('id', item.get('image', f'char_{i}').split('.')[0]): item for i, item in enumerate(data)}
    return data

characters_data = load_characters()

# --- 3. 画面表示の設定 (モバイル最適化CSSを維持) ---
st.set_page_config(page_title="歴ッター (Rekitter)", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 20px; font-weight: bold; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; border: 1px solid #f0f2f6; }
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
    
    # 【新機能】論争テーマの選択
    st.subheader("📢 論争テーマの選択")
    theme_options = [
        "宗教改革 (免罪符や教皇の権威について)", 
        "聖書の解釈 (ラテン語か民衆の言葉か)", 
        "現代のSNSについて (もしルターがXを使っていたら)",
        "自由テーマ (下のテキスト入力を使用)"
    ]
    selected_theme = st.selectbox("テーマを選んでください", theme_options)
    custom_theme = st.text_input("自由テーマ（上の選択肢で自由テーマを選んだ場合）", "")
    
    # 最終的なテーマの決定
    current_theme = custom_theme if selected_theme == "自由テーマ (下のテキスト入力を使用)" else selected_theme

    st.divider()

    # 自動論争コントロール
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

    # 個別投稿機能 (完全に維持)
    st.header("✍️ 個別投稿")
    char_ids = list(characters_data.keys())
    selected_id = st.selectbox(
        "投稿者を選択", 
        options=char_ids, 
        format_func=lambda x: characters_data[x].get('name', x)
    )
    user_text = st.text_area("投稿内容を入力", placeholder="ここにメッセージを入力...")
    
    if st.button("📤 投稿する"):
        if user_text:
            char = characters_data[selected_id]
            st.session_state.messages.append({
                "role": selected_id,
                "name": char.get('name', '不明'),
                "content": user_text,
                "avatar": f"static/{char.get('image', 'default.jpg')}"
            })
            st.rerun()

# --- 6. メッセージ表示 (最新を上にする表示順を維持) ---
def display_messages():
    for msg in reversed(st.session_state.messages):
        with st.chat_message(msg["role"], avatar=msg["avatar"]):
            st.write(f"**{msg['name']}** @{msg['role']}")
            st.write(msg["content"])

# --- 7. 自動論争ロジック (テーマをAIに伝えるように強化) ---
if st.session_state.is_running:
    char_ids = list(characters_data.keys())
    last_role = st.session_state.messages[-1]["role"] if st.session_state.messages else char_ids[1]
    current_char_id = char_ids[0] if last_role == char_ids[1] else char_ids[1]
    char = characters_data[current_char_id]

    # AIへの指示に「現在のテーマ」を組み込む
    system_prompt = (
        f"あなたは{char.get('name')}です。{char.get('description')} "
        f"現在の論争テーマは『{current_theme}』です。"
        "140文字以内で、このテーマに沿って相手に反論するか、自分の主張をSNS投稿風に述べてください。"
    )

    context = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.messages[-5:]:
        context.append({"role": "user", "content": m["content"]})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=context,
            max_tokens=200
        )
        answer = response.choices[0].message.content

        st.session_state.messages.append({
            "role": current_char_id,
            "name": char.get('name', '不明'),
            "content": answer,
            "avatar": f"static/{char.get('image', 'default.jpg')}"
        })
        st.rerun()
        time.sleep(2)

    except Exception as e:
        st.error(f"エラー: {e}")
        st.session_state.is_running = False

# --- 8. メイン表示エリア ---
if not st.session_state.messages:
    st.info(f"現在のテーマ: {current_theme}\n左側のパネルから開始してください。")
else:
    display_messages()
