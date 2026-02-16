import streamlit as st
from openai import OpenAI
import json
import time
import re

# --- 1. OpenAI APIキーの設定 (Secrets) ---
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception:
    st.error("APIキーが設定されていません。")
    st.stop()

# --- 2. データ読み込み (リスト/辞書両対応ロジックを完全維持) ---
def load_characters():
    with open('characters.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        return {item.get('id', item.get('image', f'char_{i}').split('.')[0]): item for i, item in enumerate(data)}
    return data

characters_data = load_characters()

# --- 3. 画面設定 & ハッシュタグ青色化CSS ---
st.set_page_config(page_title="歴ッター (Rekitter)", layout="wide")
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 20px; font-weight: bold; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; border: 1px solid #f0f2f6; }
    .hashtag { color: #1DA1F2; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# ハッシュタグを青くするための処理
def format_content(text):
    # #で始まる単語を探して、htmlタグで囲む
    formatted_text = re.sub(r'(#\w+)', r'<span class="hashtag">\1</span>', text)
    return formatted_text.replace('\n', '<br>')

st.title("📜 歴ッター (Rekitter)")

# --- 4. セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "current_round" not in st.session_state:
    st.session_state.current_round = 0

# --- 5. サイドバー (全機能維持 + 往復回数設定) ---
with st.sidebar:
    st.header("🎮 操作パネル")
    
    # 往復回数の設定 (新機能)
    st.subheader("🔁 論争の長さ")
    max_rounds = st.number_input("往復回数（AIが喋る総数）", min_value=1, max_value=50, value=6)
    
    st.divider()
    
    # テーマ選択 (維持)
    st.subheader("📢 論争テーマ")
    theme_options = [
        "宗教改革 (免罪符や教皇の権威について)", 
        "聖書の解釈 (ラテン語か民衆の言葉か)", 
        "現代のSNSについて (もしルターがXを使っていたら)",
        "自由テーマ (下の入力欄を使用)"
    ]
    selected_theme = st.selectbox("テーマ選択", theme_options)
    custom_theme = st.text_input("自由テーマ入力", "")
    current_theme = custom_theme if selected_theme == "自由テーマ (下の入力欄を使用)" else selected_theme

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 論争開始"):
            st.session_state.is_running = True
            st.session_state.current_round = 0 # カウントリセット
    with col2:
        if st.button("⏹️ 停止"):
            st.session_state.is_running = False
    
    if st.button("🗑️ 履歴をリセット"):
        st.session_state.messages = []
        st.session_state.is_running = False
        st.session_state.current_round = 0
        st.rerun()

    st.divider()
    
    # 個別投稿機能 (維持)
    st.header("✍️ 個別投稿")
    char_ids = list(characters_data.keys())
    selected_id = st.selectbox("投稿者を選択", options=char_ids, format_func=lambda x: characters_data[x].get('name', x))
    user_text = st.text_area("内容を入力")
    if st.button("📤 投稿する"):
        if user_text:
            char = characters_data[selected_id]
            st.session_state.messages.append({
                "role": selected_id, 
                "name": char.get('name'), 
                "content": user_text, 
                "avatar": f"static/{char.get('image')}"
            })
            st.rerun()

# --- 6. メイン表示エリア (最新が上) ---
st.info(f"現在のテーマ: {current_theme} (進行状況: {st.session_state.current_round}/{max_rounds})")

message_container = st.container()

def display_messages():
    with message_container:
        for msg in reversed(st.session_state.messages):
            with st.chat_message(msg["role"], avatar=msg["avatar"]):
                st.write(f"**{msg['name']}** @{msg['role']}")
                # ハッシュタグを青くして表示
                st.markdown(format_content(msg["content"]), unsafe_allow_html=True)

# --- 7. 自動論争ロジック (回数制限を追加) ---
if st.session_state.is_running:
    # 指定回数に達したら停止
    if st.session_state.current_round >= max_rounds:
        st.session_state.is_running = False
        st.success("指定された往復回数に達しました。")
        st.rerun()
    
    char_ids = list(characters_data.keys())
    last_role = st.session_state.messages[-1]["role"] if st.session_state.messages else char_ids[1]
    current_char_id = char_ids[0] if last_role == char_ids[1] else char_ids[1]
    char = characters_data[current_char_id]

    with st.spinner(f"{char.get('name')}が投稿を準備中..."):
        system_prompt = (
            f"あなたは{char.get('name')}です。{char.get('description')} "
            f"テーマ『{current_theme}』について140文字以内で主張してください。 "
            "SNS風に、適宜ハッシュタグ（#）も混ぜてください。"
        )
        context = [{"role": "system", "content": system_prompt}]
        for m in st.session_state.messages[-5:]:
            context.append({"role": "user", "content": m["content"]})

        try:
            response = client.chat.completions.create(model="gpt-3.5-turbo", messages=context, max_tokens=200)
            answer = response.choices[0].message.content
            
            st.session_state.messages.append({
                "role": current_char_id, "name": char.get('name'),
                "content": answer, "avatar": f"static/{char.get('image')}"
            })
            
            # 往復カウントを増やす
            st.session_state.current_round += 1
            
            display_messages()
            time.sleep(3) 
            st.rerun()

        except Exception as e:
            st.error(f"AI通信エラー: {e}")
            st.session_state.is_running = False

# 停止中、または最初の表示
if not st.session_state.is_running:
    display_messages()
