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

# --- 2. データ読み込み (詳細属性・リスト/辞書完全対応) ---
def load_characters():
    try:
        with open('characters.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            # IDを優先し、全ての詳細属性(persona, era等)を保持した辞書に変換
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
                    # 貴族かどうかを判定
                    if 'noble' in selected_id.lower():
                        role_inst = "ドイツ諸侯（貴族）。ローマへの送金を嫌い、教会の支配から脱却して領地の権力を強めたい政治的な野心家。"
                    elif 'luther' in selected_id.lower():
                        role_inst = "マルティン・ルター。カトリックの腐敗を許さない改革者。"
                    elif 'leo' in selected_id.lower():
                        role_inst = "教皇レオ10世。教会の絶対権威。"
                    else:
                        char = characters_data[selected_id]
                        role_inst = f"{char.get('name')}。{char.get('persona', char.get('description', ''))}"
                
                # メタ発言完全禁止プロンプト
                prompt = f"あなたは{role_inst}です。テーマ『{current_theme}』について、140文字以内で投稿文のみを出力しなさい。挨拶、感謝、メタ発言（『理解しました』等）は一切不要。投稿そのものだけを書きなさい。"
                res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": prompt}], max_tokens=200, temperature=1.0)
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

# --- 7. 自動論争ロジック (三つ巴 + 市民乱入 + メタ発言破壊) ---
if st.session_state.is_running:
    if st.session_state.current_round >= max_rounds:
        st.session_state.is_running = False
        st.success("論争終了。")
        st.rerun()
    
    char_ids = list(characters_data.keys())
    # キャラクターIDの特定 (部分一致検索)
    luther_id = next((k for k in char_ids if 'luther' in k.lower()), None)
    leo_id = next((k for k in char_ids if 'leo' in k.lower()), None)
    noble_id = next((k for k in char_ids if 'noble' in k.lower()), None)
    
    # 必須キャラがいない場合のフォールバック
    if not luther_id: luther_id = char_ids[0]
    if not leo_id: leo_id = char_ids[1] if len(char_ids) > 1 else char_ids[0]

    # 次の投稿者を決めるロジック
    last_role = st.session_state.messages[-1]["role"] if st.session_state.messages else "none"
    
    # 市民の出現条件: 2回目以降、直前が市民でない、かつ 25%の確率 (または4回に1回強制検討)
    if st.session_state.current_round > 1 and last_role != "citizen" and (random.random() < 0.25 or st.session_state.current_round % 4 == 0):
        current_char_id = "citizen"
    else:
        # メインキャラクター（ルター、教皇、貴族）から選ぶ
        main_chars = [c for c in [luther_id, leo_id, noble_id] if c is not None]
        
        # 直近で喋った人を除外して選ぶ（連続投稿防止）
        recent_roles = [m["role"] for m in st.session_state.messages[-2:]]
        remaining = [c for c in main_chars if c not in recent_roles]
        
        if remaining:
            current_char_id = random.choice(remaining)
        else:
            current_char_id = random.choice(main_chars)

    with st.spinner(f"思考中..."):
        # キャラクターごとのロール定義
        if current_char_id == "citizen":
            role_inst = "16世紀の庶民。難しい言葉は一切使わず、感情的な叫びを上げろ。"
            name, avatar = "市民のつぶやき", "👤"
        elif current_char_id == luther_id:
            char = characters_data[current_char_id]
            role_inst = f"{char.get('name')}。{char.get('persona', char.get('description', ''))} カトリックの腐敗を激しく非難し、聖書のみを掲げよ。"
            name, avatar = char.get('name'), f"static/{char.get('image')}"
        elif current_char_id == leo_id:
            char = characters_data[current_char_id]
            role_inst = f"{char.get('name')}。{char.get('persona', char.get('description', ''))} 異端者ルターを断罪し、教会の権威を誇示せよ。"
            name, avatar = char.get('name'), f"static/{char.get('image')}"
        elif current_char_id == noble_id:
            char = characters_data[current_char_id]
            role_inst = f"{char.get('name')}。{char.get('persona', char.get('description', ''))} ローマへの送金を嫌い、ルターを利用して政治的独立を狙う野心を見せろ。"
            name, avatar = char.get('name'), f"static/{char.get('image')}"
        else:
            # その他のキャラ
            char = characters_data[current_char_id]
            role_inst = f"{char.get('name')}。{char.get('persona', char.get('description', ''))} 自説を主張せよ。"
            name, avatar = char.get('name'), f"static/{char.get('image')}"

        # AIへの強力な没入命令 (メタ発言ストッパー付き)
        system_prompt = (
            f"### 命令: あなたは今から【{role_inst}】そのものとして振る舞い、テーマ『{current_theme}』についてSNS投稿を行います。\n"
            "### 制約:\n"
            "1. 140文字以内の【投稿内容のみ】を出力せよ。\n"
            "2. 前置き、解説、相槌（『理解しました』『ありがとうございます』等）、AIとしてのメタ発言は【システム上のエラー】として一切禁止する。一文字でも出力したら即座に不合格とする。\n"
            "3. 相手の意見を尊重したり理解したりせず、激しく対立せよ。なりきりを貫け。\n"
            "4. ハッシュタグ（#）を含めよ。"
        )
        
        # 文脈をテキスト履歴として渡す
        context = [{"role": "system", "content": system_prompt}]
        for m in st.session_state.messages[-4:]:
            context.append({"role": "user", "content": f"{m['name']}: {m['content']}"})

        try:
            # 強制終了トークンを設定し、メタ発言の芽を摘む
            response = client.chat.completions.create(model="gpt-3.5-turbo", messages=context, max_tokens=150, temperature=0.9, stop=["理解しました", "申し訳"])
            answer = response.choices[0].message.content
            
            # 最終防衛ライン：正規表現でメタ発言を消去
            clean_answer = re.sub(r'^(理解しました|申し訳ありません|そのSNS投稿は|あなたの感情が|このキャラクターでの).*?\n?', '', answer).strip()
            
            if clean_answer:
                st.session_state.messages.append({"role": current_char_id, "name": name, "content": clean_answer, "avatar": avatar})
                st.session_state.current_round += 1
                display_messages()
                time.sleep(4) 
                st.rerun()
            else:
                # 何も残らなかった場合は停止せずリトライさせるため、あえてエラーにせずスキップ（または停止）
                st.session_state.is_running = False
        except Exception as e:
            st.error(f"エラー: {e}")
            st.session_state.is_running = False

if not st.session_state.is_running:
    display_messages()
