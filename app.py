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
                name, avatar = ("市民", "👤") if selected_id == "citizen" else (characters_data[selected_id].get('name'), f"static/{characters_data[selected_id].get('image')}")
                st.session_state.messages.append({"role": selected_id, "name": name, "content": user_text, "avatar": avatar})
                st.rerun()

    with c_auto:
        if st.button("🤖 AIが自動作成"):
            with st.spinner("AIが考案中..."):
                if selected_id == "citizen":
                    role_inst = "16世紀のドイツの貧しい市民。免罪符が高くて生活が苦しいことへの不満や、地獄への恐怖を素朴な言葉で語れ。"
                elif 'noble' in selected_id.lower():
                    role_inst = "ドイツ諸侯（貴族）。ローマ教会に富を吸い上げられることに怒り、ルターを利用して政治的自立を目指す計算高い権力者。"
                elif 'luther' in selected_id.lower():
                    role_inst = "マルティン・ルター。『信仰のみ』『聖書のみ』を掲げ、教皇の権威を否定する情熱的な改革者。"
                elif 'leo' in selected_id.lower():
                    role_inst = "教皇レオ10世。神の代理人としての絶対的プライドを持ち、ルターを野蛮な異端者として見下す。"
                else:
                    char = characters_data[selected_id]
                    role_inst = f"{char.get('name')}。{char.get('persona', char.get('description', ''))}"
                
                prompt = (
                    f"役割: {role_inst}\n"
                    f"タスク: テーマ『{current_theme}』について、140文字以内のSNS投稿を作成せよ。\n"
                    "絶対ルール:\n"
                    "1. 挨拶、返事、解説、評価コメント（『不合格です』『理解しました』等）は一切書かないこと。\n"
                    "2. 投稿本文のみを出力すること。\n"
                    "3. ハッシュタグ（#）を含めること。"
                )
                
                res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": prompt}], max_tokens=200, temperature=1.0)
                ai_text = res.choices[0].message.content
                clean_text = re.sub(r'^(不合格です|理解しました|申し訳ありません).*?\n?', '', ai_text).strip()

                name, avatar = ("市民", "👤") if selected_id == "citizen" else (characters_data[selected_id].get('name'), f"static/{characters_data[selected_id].get('image')}")
                if clean_text:
                    st.session_state.messages.append({"role": selected_id, "name": name, "content": clean_text, "avatar": avatar})
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

# --- 7. 自動論争ロジック (歴史的思考の完全実装) ---
if st.session_state.is_running:
    if st.session_state.current_round >= max_rounds:
        st.session_state.is_running = False
        st.success("論争終了。")
        st.rerun()
    
    char_ids = list(characters_data.keys())
    luther_id = next((k for k in char_ids if 'luther' in k.lower()), None)
    leo_id = next((k for k in char_ids if 'leo' in k.lower()), None)
    noble_id = next((k for k in char_ids if 'noble' in k.lower()), None)
    
    if not luther_id: luther_id = char_ids[0]
    if not leo_id: leo_id = char_ids[1] if len(char_ids) > 1 else char_ids[0]

    last_role = st.session_state.messages[-1]["role"] if st.session_state.messages else "none"
    if st.session_state.current_round > 1 and last_role != "citizen" and (random.random() < 0.25 or st.session_state.current_round % 4 == 0):
        current_char_id = "citizen"
    else:
        main_chars = [c for c in [luther_id, leo_id, noble_id] if c is not None]
        recent_roles = [m["role"] for m in st.session_state.messages[-2:]]
        remaining = [c for c in main_chars if c not in recent_roles]
        current_char_id = random.choice(remaining) if remaining else random.choice(main_chars)

    with st.spinner(f"思考中..."):
        # 【重要】ここが歴史的リサーチに基づく正確な思考回路の実装部分
        if current_char_id == "citizen":
            role_inst = (
                "あなたは16世紀ドイツの貧しい市民です。神学的な難しい議論は分かりませんが、以下の感情を持っています。\n"
                "1. 免罪符（贖宥状）が高すぎて生活が苦しい。\n"
                "2. ローマの教皇は遠い存在だが、地獄には落ちたくない。\n"
                "3. ルターの言う『信仰だけで救われる』という言葉に希望を感じつつも、教会に逆らう恐怖もある。\n"
                "庶民の素朴な言葉遣いで、生活実感に基づいた不満や不安を叫んでください。"
            )
            name, avatar = "市民のつぶやき", "👤"
        elif current_char_id == luther_id:
            char = characters_data[current_char_id]
            role_inst = (
                f"あなたは{char.get('name')}です。以下の思想を徹底してください。\n"
                "1. 『信仰のみ(Sola Fide)』：金銭で救いは買えない。\n"
                "2. 『聖書のみ(Sola Scriptura)』：教皇や公会議の権威よりも聖書の言葉が上である。\n"
                "3. 教皇は『反キリスト』であり、教会を金儲けの道具にしていると激しく糾弾する。\n"
                "決して妥協せず、情熱的かつ攻撃的な神学者として振る舞ってください。"
            )
            name, avatar = char.get('name'), f"static/{char.get('image')}"
        elif current_char_id == leo_id:
            char = characters_data[current_char_id]
            role_inst = (
                f"あなたは{char.get('name')}です。以下の立場を崩さないでください。\n"
                "1. 教皇はペテロの後継者であり、地上のキリストの代理人である（絶対的権威）。\n"
                "2. サン・ピエトロ大聖堂の再建は神の栄光のためであり、その資金集め（免罪符）は正当な行為である。\n"
                "3. ルターは『主のぶどう畑を荒らす野猪』であり、破門されるべき異端者である。\n"
                "高圧的で優雅な口調で、反乱分子を見下してください。"
            )
            name, avatar = char.get('name'), f"static/{char.get('image')}"
        elif current_char_id == noble_id:
            char = characters_data[current_char_id]
            role_inst = (
                f"あなたは{char.get('name')}（ドイツ諸侯）です。信仰心よりも政治的利害を重視します。\n"
                "1. ローマ教会にドイツの富が吸い上げられることに強い不満がある（グラヴァミナ）。\n"
                "2. ルターを保護することで、皇帝や教皇の干渉を排除し、自領の権限を強化したい。\n"
                "3. 『ドイツの自由』を掲げ、政治的な計算高さを見せてください。\n"
                "教皇を批判しつつ、ルターを政治利用する立場をとってください。"
            )
            name, avatar = char.get('name'), f"static/{char.get('image')}"
        else:
            char = characters_data[current_char_id]
            role_inst = f"{char.get('name')}。{char.get('persona', char.get('description', ''))} 自説を主張せよ。"
            name, avatar = char.get('name'), f"static/{char.get('image')}"

        # メタ発言を物理的に封印するシステムプロンプト
        system_prompt = (
            f"### 命令: あなたは今から【{role_inst}】そのものとして振る舞い、テーマ『{current_theme}』についてSNS投稿を行います。\n"
            "### 制約:\n"
            "1. 140文字以内の【投稿内容のみ】を出力せよ。\n"
            "2. 前置き、解説、相槌（『理解しました』『ありがとうございます』『不合格です』等）、AIとしてのメタ発言は【システム上のエラー】として一切禁止する。\n"
            "3. なりきりを貫き、相手の意見に安易に同調しないこと。\n"
            "4. ハッシュタグ（#）を含めよ。"
        )
        
        context = [{"role": "system", "content": system_prompt}]
        for m in st.session_state.messages[-4:]:
            context.append({"role": "user", "content": f"{m['name']}: {m['content']}"})

        try:
            response = client.chat.completions.create(model="gpt-3.5-turbo", messages=context, max_tokens=150, temperature=0.9, stop=["不合格", "理解しました", "申し訳"])
            answer = response.choices[0].message.content
            
            clean_answer = re.sub(r'^(不合格です|理解しました|申し訳ありません|そのSNS投稿は|あなたの感情が|このキャラクターでの).*?\n?', '', answer).strip()
            
            if clean_answer:
                st.session_state.messages.append({"role": current_char_id, "name": name, "content": clean_answer, "avatar": avatar})
                st.session_state.current_round += 1
                display_messages()
                time.sleep(4) 
                st.rerun()
            else:
                st.session_state.is_running = True
                st.rerun()
        except Exception as e:
            st.error(f"エラー: {e}")
            st.session_state.is_running = False

if not st.session_state.is_running:
    display_messages()
