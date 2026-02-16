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

# --- 3. 画面設定 & ハッシュタグ青色化CSS (維持) ---
st.set_page_config(page_title="歴ッター (Rekitter)", layout="wide")
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 20px; font-weight: bold; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; border: 1px solid #f0f2f6; }
    .hashtag { color: #1DA1F2; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# ハッシュタグを青くする関数
def format_content(text):
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

# --- 5. サイドバー (全機能維持) ---
with st.sidebar:
    st.header("🎮 操作パネル")
    
    # 往復回数
    st.subheader("🔁 論争の長さ")
    max_rounds = st.number_input("往復回数（AIが喋る総数）", min_value=1, max_value=50, value=6)
    
    st.divider()
    
    # テーマ選択
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
            st.session_state.current_round = 0 
    with col2:
        if st.button("⏹️ 停止"):
            st.session_state.is_running = False
    
    if st.button("🗑️ 履歴をリセット"):
        st.session_state.messages = []
        st.session_state.is_running = False
        st.session_state.current_round = 0
        st.rerun()

    st.divider()
    
    # 個別投稿
    st.header("✍️ 個別投稿")
    char_ids = list(characters_data.keys())
    selected_id = st.selectbox("投稿者を選択", options=char_ids, format_func=lambda x: characters_data[x].get('name', x))
    user_text = st.text_area("内容を入力")
    if st.button("📤 投稿する"):
        if user_text:
            char = characters_data[selected_id]
            st.session_state.messages.append({
                "role": selected_id, "name": char.get('name'), 
                "content": user_text, "avatar": f"static/{char.get('image')}"
            })
            st.rerun()

# --- 6. メイン表示エリア (最新を上にする表示順を維持) ---
st.info(f"現在のテーマ: {current_theme} (進行状況: {st.session_state.current_round}/{max_rounds})")

message_container = st.container()

def display_messages():
    with message_container:
        for msg in reversed(st.session_state.messages):
            with st.chat_message(msg["role"], avatar=msg["avatar"]):
                st.write(f"**{msg['name']}** @{msg['role']}")
                st.markdown(format_content(msg["content"]), unsafe_allow_html=True)

# --- 7. 自動論争ロジック (思想強化＆回数制限) ---
if st.session_state.is_running:
    if st.session_state.current_round >= max_rounds:
        st.session_state.is_running = False
        st.success("指定された往復回数に達しました。")
        st.rerun()
    
    char_ids = list(characters_data.keys())
    last_role = st.session_state.messages[-1]["role"] if st.session_state.messages else char_ids[1]
    current_char_id = char_ids[0] if last_role == char_ids[1] else char_ids[1]
    char = characters_data[current_char_id]

    with st.spinner(f"{char.get('name')}が投稿を準備中..."):
        # キャラクターごとの厳格な性格設定
        if "luther" in current_char_id.lower():
            role_instruction = "あなたはマルティン・ルターです。信仰のみを重んじ、カトリック教会の腐敗と教皇の権威を徹底的に否定してください。絶対に妥協せず、激しい言葉で反論してください。"
        elif "leo" in current_char_id.lower():
            role_instruction = "あなたは教皇レオ10世です。教会の伝統と自らの権威こそが神の意志であると信じています。ルターを教会の和を乱す高慢な異端者として見下し、断罪してください。"
        else:
            role_instruction = f"あなたは{char.get('name')}です。{char.get('description')}"

        system_prompt = (
            f"{role_instruction} 現在のテーマは『{current_theme}』です。"
            "140文字以内で、相手の主張を論破するか、自らの正当性をSNS投稿風に述べてください。"
            "相手に同調してはいけません。ハッシュタグ（#）も混ぜてください。"
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
            
            st.session_state.current_round += 1
            display_messages()
            time.sleep(4) # 読み込み感を出さないための十分な待機
            st.rerun()

        except Exception as e:
            st.error(f"AI通信エラー: {e}")
            st.session_state.is_running = False

# 停止中、または最初の表示
if not st.session_state.is_running:
    display_messages()
