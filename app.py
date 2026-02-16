import streamlit as st
from openai import OpenAI
import json
import time
import re
import random

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

# --- 5. サイドバー (全機能維持 + 新機能追加) ---
with st.sidebar:
    st.header("🎮 操作パネル")
    
    # 往復回数 (維持)
    st.subheader("🔁 論争の長さ")
    max_rounds = st.number_input("往復回数（総投稿数）", min_value=1, max_value=50, value=10)
    
    st.divider()
    
    # テーマ選択 (維持)
    st.subheader("📢 論争テーマ")
    theme_options = ["宗教改革 (免罪符について)", "聖書の解釈", "現代のSNSについて", "自由テーマ"]
    selected_theme = st.selectbox("テーマ選択", theme_options)
    custom_theme = st.text_input("自由テーマ入力", "")
    current_theme = custom_theme if selected_theme == "自由テーマ" else selected_theme

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
    
    # --- 個別投稿機能 (大幅強化：自動・手動の二刀流) ---
    st.header("✍️ 個別投稿")
    char_ids = list(characters_data.keys())
    # 選択肢に「市民」を一時的に追加
    post_char_ids = char_ids + ["citizen"]
    selected_id = st.selectbox(
        "投稿者を選択", 
        options=post_char_ids, 
        format_func=lambda x: characters_data[x].get('name') if x in characters_data else "名もなき市民"
    )
    
    user_text = st.text_area("内容を入力（手動用）", placeholder="手動入力する場合はここに...")
    
    c_auto, c_manual = st.columns(2)
    with c_manual:
        if st.button("📤 手動で投稿"):
            if user_text:
                if selected_id == "citizen":
                    name, avatar = "市民", "👤"
                else:
                    char = characters_data[selected_id]
                    name, avatar = char.get('name'), f"static/{char.get('image')}"
                st.session_state.messages.append({"role": selected_id, "name": name, "content": user_text, "avatar": avatar})
                st.rerun()

    with c_auto:
        if st.button("🤖 AIが自動作成"):
            # 個別自動投稿ロジック
            with st.spinner("AIが考案中..."):
                if selected_id == "citizen":
                    role_inst = "あなたは当時の庶民です。議論を傍観している立場です。"
                else:
                    char = characters_data[selected_id]
                    role_inst = f"あなたは{char.get('name')}です。{char.get('description')} 絶対に妥協しないでください。"
                
                prompt = f"{role_inst} テーマ『{current_theme}』について、140文字以内でSNS風の投稿を1つだけ作ってください。ハッシュタグも付けてください。"
                res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": prompt}], max_tokens=200)
                ai_text = res.choices[0].message.content
                
                if selected_id == "citizen":
                    name, avatar = "市民", "👤"
                else:
                    char = characters_data[selected_id]
                    name, avatar = char.get('name'), f"static/{char.get('image')}"
                
                st.session_state.messages.append({"role": selected_id, "name": name, "content": ai_text, "avatar": avatar})
                st.rerun()

# --- 6. メイン表示エリア (最新が上) ---
st.info(f"現在のテーマ: {current_theme} (進行状況: {st.session_state.current_round}/{max_rounds})")

message_container = st.container()

def display_messages():
    with message_container:
        for msg in reversed(st.session_state.messages):
            with st.chat_message(msg["role"], avatar=msg["avatar"]):
                st.write(f"**{msg['name']}** @{msg['role']}")
                st.markdown(format_content(msg["content"]), unsafe_allow_html=True)

# --- 7. 自動論争ロジック (市民のつぶやきを混ぜる) ---
if st.session_state.is_running:
    if st.session_state.current_round >= max_rounds:
        st.session_state.is_running = False
        st.success("指定された往復回数に達しました。")
        st.rerun()
    
    char_ids = list(characters_data.keys())
    # 投稿順序の決定 (ルター -> 教皇 -> 時々市民)
    # 直近3件に市民がいなければ、20%の確率で市民が出るように設定
    last_three = [m["role"] for m in st.session_state.messages[-3:]]
    if "citizen" not in last_three and random.random() < 0.3:
        current_char_id = "citizen"
    else:
        last_role = st.session_state.messages[-1]["role"] if st.session_state.messages else char_ids[1]
        current_char_id = char_ids[0] if last_role == char_ids[1] else char_ids[1]

    with st.spinner(f"思考中..."):
        if current_char_id == "luther":
            role_inst = "あなたはマルティン・ルターです。教会の腐敗を許さない改革者。信仰のみを重んじ、教皇を断固拒絶してください。"
            name, avatar = characters_data[current_char_id].get('name'), f"static/{characters_data[current_char_id].get('image')}"
        elif current_char_id == "leo":
            role_inst = "あなたは教皇レオ10世です。教会の絶対的な権威。ルターを迷える異端として見下し、断罪してください。"
            name, avatar = characters_data[current_char_id].get('name'), f"static/{characters_data[current_char_id].get('image')}"
        else:
            role_inst = "あなたは当時の名もなき市民です。ルターと教皇の争いを見て、不安になったり、どちらかを応援したり、世の中の混乱を嘆いたりしてください。"
            name, avatar = "市民のつぶやき", "👤"

        system_prompt = (
            f"{role_inst} テーマは『{current_theme}』。140文字以内で、自分の立場を鮮明にしたSNS投稿をしてください。ハッシュタグも青くなるので必ず入れてください。"
        )
        
        context = [{"role": "system", "content": system_prompt}]
        for m in st.session_state.messages[-5:]:
            context.append({"role": "user", "content": m["content"]})

        try:
            response = client.chat.completions.create(model="gpt-3.5-turbo", messages=context, max_tokens=200)
            answer = response.choices[0].message.content
            st.session_state.messages.append({"role": current_char_id, "name": name, "content": answer, "avatar": avatar})
            st.session_state.current_round += 1
            display_messages()
            time.sleep(4) 
            st.rerun()
        except Exception as e:
            st.error(f"エラー: {e}")
            st.session_state.is_running = False

if not st.session_state.is_running:
    display_messages()
