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
    st.error("APIキーが設定されていません。StreamlitのSecretsを確認してください。")
    st.stop()

# --- 2. データ読み込み (詳細なpersona・era項目に対応 / リスト・辞書両対応) ---
def load_characters():
    try:
        with open('characters.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            # IDを優先し、詳細な属性を保持した辞書に変換
            return {item.get('id', item.get('image', f'char_{i}').split('.')[0]): item for i, item in enumerate(data)}
        return data
    except Exception as e:
        st.error(f"JSON読み込みエラー: {e}")
        st.stop()

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
    # ハッシュタグを青くし、改行を維持する
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
    max_rounds = st.number_input("往復回数（総投稿数）", min_value=1, max_value=50, value=10)
    
    st.divider()
    
    # テーマ選択
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
    
    # 個別投稿機能 (AI自動・手動を維持)
    st.header("✍️ 個別投稿")
    char_ids = list(characters_data.keys())
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
            with st.spinner("AIが考案中..."):
                if selected_id == "citizen":
                    role_inst = "16世紀の庶民。歴史の解説者ではなく、今目の前で起きてる騒動に驚く野次馬になりきれ。"
                else:
                    char = characters_data[selected_id]
                    role_inst = f"{char.get('name')}。{char.get('persona', char.get('description', ''))}。時代は{char.get('era', '不明')}。絶対に信念を曲げるな。"
                
                prompt = f"【完全没入】あなたは{role_inst}。テーマ『{current_theme}』について、140文字以内のSNS投稿を1つだけ出力せよ。解説、挨拶、メタ発言（『理解しました』等）は一切禁止。"
                res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": prompt}], max_tokens=200)
                ai_text = res.choices[0].message.content
                
                if selected_id == "citizen":
                    name, avatar = "市民", "👤"
                else:
                    char = characters_data[selected_id]
                    name, avatar = char.get('name'), f"static/{char.get('image')}"
                
                st.session_state.messages.append({"role": selected_id, "name": name, "content": ai_text, "avatar": avatar})
                st.rerun()

# --- 6. メイン表示エリア (最新を上) ---
st.info(f"現在のテーマ: {current_theme} (進行状況: {st.session_state.current_round}/{max_rounds})")
message_container = st.container()

def display_messages():
    with message_container:
        for msg in reversed(st.session_state.messages):
            with st.chat_message(msg["role"], avatar=msg["avatar"]):
                st.write(f"**{msg['name']}** @{msg['role']}")
                st.markdown(format_content(msg["content"]), unsafe_allow_html=True)

# --- 7. 自動論争ロジック (詳細ペルソナ対応＆三つ巴配役) ---
if st.session_state.is_running:
    if st.session_state.current_round >= max_rounds:
        st.session_state.is_running = False
        st.success("指定された往復回数に達しました。")
        st.rerun()
    
    char_ids = list(characters_data.keys())
    
    # 次の投稿者を決定するロジック
    last_role = st.session_state.messages[-1]["role"] if st.session_state.messages else "none"
    
    # 市民の出現条件 (20%の確率、かつ連続しない、かつ最初は出ない)
    if st.session_state.current_round > 1 and last_role != "citizen" and random.random() < 0.20:
        current_char_id = "citizen"
    else:
        # 主要人物の中でまだ喋っていない、または直近でない人を選ぶ
        recent_roles = [m["role"] for m in st.session_state.messages[-2:]]
        remaining = [c for c in char_ids if c not in recent_roles]
        current_char_id = random.choice(remaining) if remaining else random.choice(char_ids)

    with st.spinner(f"思考中..."):
        if current_char_id == "citizen":
            role_inst = "16世紀の庶民。難しい言葉は使わず、感情的な叫びや独り言をSNS風に投稿せよ。"
            name, avatar = "市民のつぶやき", "👤"
        else:
            char = characters_data[current_char_id]
            role_inst = f"{char.get('name')}。{char.get('persona', char.get('description', ''))} 時代設定は{char.get('era', '不明')}。相手に同調せず、自説を貫き通せ。"
            name, avatar = char.get('name'), f"static/{char.get('image')}"

        system_prompt = (
            f"【歴史没入命令】あなたは{role_inst}です。\n"
            f"1. テーマ『{current_theme}』について、140文字以内でSNS投稿せよ。\n"
            f"2. 解説・挨拶・「理解しました」等のメタ発言は禁忌。投稿文のみを出力せよ。\n"
            f"3. ハッシュタグ（#）を必ず含めよ。"
        )
        
        context = [{"role": "system", "content": system_prompt}]
        # 過去の文脈を反映
        for m in st.session_state.messages[-5:]:
            context.append({"role": "user", "content": m["content"]})

        try:
            response = client.chat.completions.create(model="gpt-3.5-turbo", messages=context, max_tokens=200, temperature=0.9)
            answer = response.choices[0].message.content
            # 万が一のメタ発言除去
            answer = re.sub(r'^(理解しました|申し訳ありません|そのSNS投稿は).*?\n?', '', answer).strip()
            
            st.session_state.messages.append({"role": current_char_id, "name": name, "content": answer, "avatar": avatar})
            st.session_state.current_round += 1
            display_messages()
            time.sleep(4) 
            st.rerun()
        except Exception as e:
            st.error(f"AI通信エラー: {e}")
            st.session_state.is_running = False

if not st.session_state.is_running:
    display_messages()
