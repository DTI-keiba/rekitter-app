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

# --- 5. サイドバー (全機能維持) ---
with st.sidebar:
    st.header("🎮 操作パネル")
    
    st.subheader("🔁 論争の長さ")
    max_rounds = st.number_input("往復回数（総投稿数）", min_value=1, max_value=50, value=10)
    
    st.divider()
    
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
                    role_inst = "16世紀の庶民。歴史の解説ではなく、今起きてることに驚く野次馬になりきれ。"
                else:
                    char = characters_data[selected_id]
                    # 各キャラになりきるための個別性格付け
                    if 'luther' in selected_id.lower():
                        role_inst = "マルティン・ルター。カトリックの腐敗を激しく攻撃せよ。信仰のみを強調せよ。"
                    elif 'leo' in selected_id.lower():
                        role_inst = "教皇レオ10世。教会の絶対権威。ルターを異端として見下せ。"
                    else:
                        role_inst = f"{char.get('name')}。{char.get('description')}"
                
                prompt = f"【完全没入】あなたは{role_inst}。テーマ『{current_theme}』について、140文字以内のSNS投稿を1つだけ出力せよ。解説やメタ発言は一切禁止。"
                res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": prompt}], max_tokens=200)
                ai_text = res.choices[0].message.content
                
                if selected_id == "citizen":
                    name, avatar = "市民", "👤"
                else:
                    char = characters_data[selected_id]
                    name, avatar = char.get('name'), f"static/{char.get('image')}"
                
                st.session_state.messages.append({"role": selected_id, "name": name, "content": ai_text, "avatar": avatar})
                st.rerun()

# --- 6. メイン表示エリア ---
st.info(f"現在のテーマ: {current_theme} (進行状況: {st.session_state.current_round}/{max_rounds})")

message_container = st.container()

def display_messages():
    with message_container:
        for msg in reversed(st.session_state.messages):
            with st.chat_message(msg["role"], avatar=msg["avatar"]):
                st.write(f"**{msg['name']}** @{msg['role']}")
                st.markdown(format_content(msg["content"]), unsafe_allow_html=True)

# --- 7. 自動論争ロジック (思想対立を極限まで強化) ---
if st.session_state.is_running:
    if st.session_state.current_round >= max_rounds:
        st.session_state.is_running = False
        st.success("指定された往復回数に達しました。")
        st.rerun()
    
    char_ids = list(characters_data.keys())
    luther_id = next((k for k in char_ids if 'luther' in k.lower()), char_ids[0])
    leo_id = next((k for k in char_ids if 'leo' in k.lower()), char_ids[1] if len(char_ids) > 1 else char_ids[0])
    
    if st.session_state.current_round == 0:
        current_char_id = luther_id
    elif st.session_state.current_round == 1:
        current_char_id = leo_id
    else:
        last_role = st.session_state.messages[-1]["role"] if st.session_state.messages else "none"
        if last_role != "citizen" and (random.random() < 0.25 or st.session_state.current_round % 4 == 0):
            current_char_id = "citizen"
        else:
            main_history = [m["role"] for m in reversed(st.session_state.messages) if m["role"] in [luther_id, leo_id]]
            last_main = main_history[0] if main_history else leo_id
            current_char_id = luther_id if last_main == leo_id else leo_id

    with st.spinner(f"思考中..."):
        # キャラクターごとの「絶対に譲れない一線」をプロンプトに刻印
        if current_char_id == luther_id:
            char_role = "マルティン・ルター。免罪符は嘘であり、教皇は反キリストだと確信している。激しい怒りを持って投稿せよ。"
            char_info = characters_data[current_char_id]
            name, avatar = char_info.get('name'), f"static/{char_info.get('image')}"
        elif current_char_id == leo_id:
            char_role = "教皇レオ10世。メディチ家出身のプライド。ルターを『ぶどう畑を荒らす野猪』と呼び、地獄へ落ちるべきゴミだと断罪せよ。絶対に歩み寄るな。"
            char_info = characters_data[current_char_id]
            name, avatar = char_info.get('name'), f"static/{char_info.get('image')}"
        else:
            char_role = "16世紀の庶民。難しい分析はせず、目の前の喧嘩に怯えたり、どちらかの味方をして叫べ。"
            name, avatar = "市民のつぶやき", "👤"

        # 【最重要】なりきり・メタ発言禁止の徹底
        system_prompt = (
            f"あなたは今、歴史シミュレーター内のキャラクターである【{char_role}】に完全になりきっています。\n"
            f"指示1: テーマ『{current_theme}』について、140文字以内で相手を攻撃、または自説を叫べ。\n"
            f"指示2: 相手への同情、妥協、理解は一切不要。あなたは敵対している。\n"
            f"指示3: 解説や『理解しました』等のメタ発言は厳禁。投稿内容のみを出力せよ。\n"
            f"指示4: 必ずハッシュタグ（#）を含めること。"
        )
        
        context = [{"role": "system", "content": system_prompt}]
        for m in st.session_state.messages[-5:]:
            context.append({"role": "user", "content": m["content"]})

        try:
            response = client.chat.completions.create(model="gpt-3.5-turbo", messages=context, max_tokens=200, temperature=0.9)
            answer = response.choices[0].message.content
            # 万が一のメタ発言除去
            answer = re.sub(r'^(理解しました|申し訳ありません|投稿は理解).*?\n?', '', answer).strip()
            
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
