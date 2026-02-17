import streamlit as st
from openai import OpenAI
import json
import time
import re
import random
import os

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

# --- 安全なアバター取得関数 (大文字小文字対応) ---
def get_safe_avatar(char_key):
    """画像ファイルが存在すればパスを、なければ役職に応じた絵文字を返す"""
    if char_key == "citizen":
        return "👤"
    
    if char_key in characters_data:
        char = characters_data[char_key]
        image_name = char.get('image')
        
        if image_name:
            # パターン1: そのまま探す
            path1 = f"static/{image_name}"
            if os.path.exists(path1):
                return path1
            
            # パターン2: 先頭を大文字にして探す (french... -> French...)
            capitalized_name = image_name[0].upper() + image_name[1:]
            path2 = f"static/{capitalized_name}"
            if os.path.exists(path2):
                return path2
    
    # フォールバック絵文字
    if 'louis' in char_key.lower(): return "👑"
    if 'leo' in char_key.lower(): return "🇻🇦"
    if 'luther' in char_key.lower(): return "✝️"
    if 'minister' in char_key.lower(): return "📜"
    if 'noble' in char_key.lower(): return "⚔️"
    if 'huguenot' in char_key.lower(): return "🔨"
    
    return "🧑‍⚖️" 

# --- 王の名前を動的に決定する関数 ---
def get_dynamic_king_name(base_name, current_theme):
    if "三部会" in current_theme:
        return "ルイ13世"
    return "ルイ14世"

# --- 宰相の名前を動的に決定する関数 ---
def get_dynamic_minister_name(base_name, current_theme):
    if "三部会" in current_theme:
        return "リシュリュー"
    elif "フロンド" in current_theme:
        return "マザラン"
    return "王の側近"

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
    theme_options = [
        "全国三部会の停止 (1614年・身分制の対立)",
        "フロンドの乱 (1648年・貴族と高等法院の反乱)",
        "ナントの勅令廃止 (1685年・宗教弾圧と亡命)",
        "宗教改革 (免罪符について)", 
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
                    name = "市民"
                else:
                    char_data = characters_data[selected_id]
                    # 名前の動的変更ロジック
                    if 'louis' in selected_id.lower():
                        name = get_dynamic_king_name(char_data.get('name'), current_theme)
                    elif 'minister' in selected_id.lower():
                        name = get_dynamic_minister_name(char_data.get('name'), current_theme)
                    else:
                        name = char_data.get('name')
                
                avatar = get_safe_avatar(selected_id)
                st.session_state.messages.append({"role": selected_id, "name": name, "content": user_text, "avatar": avatar})
                st.rerun()

    with c_auto:
        if st.button("🤖 AIが自動作成"):
            with st.spinner("AIが考案中..."):
                role_inst = "" # 初期化
                if selected_id == "citizen":
                    if "三部会" in current_theme: role_inst = "【重要：あなたは貧しい市民です。王や貴族ではありません】1614年の第三身分。貴族の横暴と重税に苦しみ、王に救済を求める陳情者。"
                    elif "フロンド" in current_theme: role_inst = "【重要：あなたは貧しい市民です】1648年のパリ市民。重税を課すマザラン枢機卿への憎悪を燃やし、バリケードを築く暴徒。"
                    elif "ナント" in current_theme: role_inst = "【重要：あなたは市民です】1685年の市民。異端追放を歓迎するか、経済の混乱を憂う者。"
                    elif "宗教改革" in current_theme: role_inst = "【重要：あなたは市民です】16世紀ドイツの市民。免罪符が高すぎると嘆く。"
                    else: role_inst = "名もなき市民。野次馬。"
                else:
                    if 'louis' in selected_id.lower():
                        if "三部会" in current_theme: role_inst = "13歳のルイ13世。『貴族どもは特権ばかり主張して文句が多く、本当にうざい』。三部会など時間の無駄であり、『そもそもこんなもの開かなくても、余と母上がいれば政治は回るのだ』と、議会不要論を不機嫌につぶやけ。"
                        elif "フロンド" in current_theme: role_inst = "ルイ14世（少年期）。パリを追われた屈辱を忘れず、王権への反逆を心に刻む。"
                        elif "ナント" in current_theme: 
                            role_inst = "1685年のルイ14世（太陽王）。ユグノーたちが『信仰のために国を捨てる』と宣言したことに、『余の国よりも神を選ぶというのか？』と驚愕し、嘆け。そして『だが待てよ、彼らが出て行けば、フランスの富はどうなる？』と、経済崩壊の予感に震えろ。"
                        else: role_inst = "ルイ14世（太陽王）。『朕は国家なり』。異端を許さず、フランスの統一を完成させる絶対君主。"
                    elif 'minister' in selected_id.lower():
                        if "三部会" in current_theme: role_inst = "リシュリュー（若き司教）。第三身分を利用して貴族を牽制する。"
                        elif "フロンド" in current_theme: role_inst = "マザラン枢機卿。フロンド派の貴族を冷徹に計算して抑え込む。"
                        else: role_inst = "王の側近。王の命令を冷徹に実行する。"
                    elif 'french_noble' in selected_id.lower() or ('noble' in selected_id.lower() and 'german' not in selected_id.lower()):
                        if "三部会" in current_theme: role_inst = "1614年のフランス貴族（名門）。第三身分が貴族を『弟』と呼んだことに激怒せよ。『靴屋の息子と兄弟になった覚えはない』と吐き捨て、特権こそが正義だと主張せよ。"
                        elif "フロンド" in current_theme: role_inst = "フロンド派の貴族。『王はマザランに騙されている』と主張し、武力で権力を取り戻そうとする。"
                        else: role_inst = "ヴェルサイユの廷臣。王にへつらい、ご機嫌取りをする太鼓持ちになれ。"
                    elif 'german_noble' in selected_id.lower():
                        role_inst = "ドイツ諸侯。ローマへの送金を嫌い、ルターを利用して政治的自立を狙う。"
                    elif 'huguenot' in selected_id.lower():
                        if "ナント" in current_theme:
                            role_inst = "1685年のユグノー（商工業者）。【重要：経済の話は一切するな】。『カトリックへの強制改宗は魂の死である』と訴えよ。『信仰を捨てるくらいなら、愛するフランスを捨てて亡命する』という悲壮な決意だけを投稿せよ。"
                        else:
                            role_inst = "ユグノー。信仰の自由を奪われ、亡命か改宗かの選択を迫られている。"
                    elif 'luther' in selected_id.lower():
                        role_inst = "マルティン・ルター。カトリックの腐敗を許さない改革者。"
                    elif 'leo' in selected_id.lower():
                        role_inst = "教皇レオ10世。教会の絶対権威。"
                    else:
                        char = characters_data[selected_id]
                        role_inst = f"{char.get('name')}。{char.get('persona', char.get('description', ''))}"
                
                # メタ発言禁止
                prompt = (
                    f"役割: {role_inst}\n"
                    f"タスク: テーマ『{current_theme}』について、140文字以内のSNS投稿を作成せよ。\n"
                    "絶対ルール: 挨拶・解説・メタ発言（『不合格です』等）は一切禁止。投稿本文のみを直接出力せよ。ハッシュタグ（#）必須。"
                )
                
                res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": prompt}], max_tokens=200, temperature=1.0, stop=["不合格", "理解しました", "申し訳", "システムエラー"])
                ai_text = res.choices[0].message.content
                clean_text = re.sub(r'^(不合格です|理解しました|申し訳ありません|システム上のエラー|回答は無効|この投稿は).*?\n?', '', ai_text).strip()

                name = "市民" if selected_id == "citizen" else characters_data[selected_id].get('name')
                
                if selected_id != "citizen":
                    if 'louis' in selected_id.lower():
                        name = get_dynamic_king_name(characters_data[selected_id].get('name'), current_theme)
                    elif 'minister' in selected_id.lower():
                        name = get_dynamic_minister_name(characters_data[selected_id].get('name'), current_theme)

                avatar = get_safe_avatar(selected_id)

                if clean_text:
                    st.session_state.messages.append({"role": selected_id, "name": name, "content": clean_text, "avatar": avatar})
                    st.rerun()

# --- 6. メイン表示エリア ---
st.info(f"現在のテーマ: {current_theme} (進行状況: {st.session_state.current_round}/{max_rounds})")
message_container = st.container()

def display_messages():
    with message_container:
        for msg in reversed(st.session_state.messages):
            role = msg["role"]
            avatar_path = msg["avatar"]
            # 画像パスが存在しない場合、安全なアバターに置き換え
            if avatar_path and avatar_path.startswith("static/") and not os.path.exists(avatar_path):
                avatar_path = get_safe_avatar(role)

            with st.chat_message(role, avatar=avatar_path):
                st.write(f"**{msg['name']}** @{msg['role']}")
                st.markdown(format_content(msg["content"]), unsafe_allow_html=True)

# --- 7. 自動論争ロジック (100%分離 & エラー回避 & 王・宰相名自動切替) ---
if st.session_state.is_running:
    if st.session_state.current_round >= max_rounds:
        st.session_state.is_running = False
        st.success("論争終了。")
        st.rerun()
    
    char_ids = list(characters_data.keys())
    
    german_noble_id = next((k for k in char_ids if 'german' in k.lower()), None)
    french_noble_id = next((k for k in char_ids if ('french' in k.lower() or 'fronde' in k.lower()) or ('noble' in k.lower() and 'german' not in k.lower())), None)
    
    louis_id = next((k for k in char_ids if 'louis' in k.lower()), None)
    minister_id = next((k for k in char_ids if 'minister' in k.lower()), None)
    huguenot_id = next((k for k in char_ids if 'huguenot' in k.lower()), None)
    luther_id = next((k for k in char_ids if 'luther' in k.lower()), None)
    leo_id = next((k for k in char_ids if 'leo' in k.lower()), None)

    last_role = st.session_state.messages[-1]["role"] if st.session_state.messages else "none"
    
    if st.session_state.current_round > 1 and last_role != "citizen" and (random.random() < 0.25 or st.session_state.current_round % 4 == 0):
        current_char_id = "citizen"
    else:
        candidates = []
        if "三部会" in current_theme:
            candidates = [c for c in [louis_id, minister_id, french_noble_id] if c]
        elif "フロンド" in current_theme:
            candidates = [c for c in [louis_id, minister_id, french_noble_id] if c]
        elif "ナント" in current_theme:
            # ナントの勅令廃止：ルイ14世とユグノーのみ
            # ★ 交互に発言させて「宣言」→「嘆き」の流れを作るロジック
            last_main_role = [m["role"] for m in reversed(st.session_state.messages) if m["role"] in [louis_id, huguenot_id]]
            
            # まだ誰も喋ってない、または最後がルイ14世なら -> ユグノーが宣言する
            if not last_main_role or last_main_role[0] == louis_id:
                current_char_id = huguenot_id
            # 最後がユグノーなら -> ルイ14世が嘆く
            else:
                current_char_id = louis_id

        elif luther_id and leo_id: 
            candidates = [c for c in [luther_id, leo_id, german_noble_id] if c]
            recent_roles = [m["role"] for m in st.session_state.messages[-2:]]
            remaining = [c for c in candidates if c not in recent_roles]
            current_char_id = random.choice(remaining) if remaining else random.choice(candidates)
        else:
            candidates = char_ids
            recent_roles = [m["role"] for m in st.session_state.messages[-2:]]
            remaining = [c for c in candidates if c not in recent_roles]
            current_char_id = random.choice(remaining) if remaining else random.choice(candidates)
        
        # ナント以外の場合の選出ロジック（上の分岐で決まってなければ）
        if "ナント" not in current_theme and 'current_char_id' not in locals():
             # fallback (should be covered by elif luther.. or else)
             current_char_id = random.choice(candidates)


    with st.spinner(f"思考中..."):
        # 名前決定 (AI自動投稿時)
        if current_char_id == "citizen":
            name = "市民のつぶやき"
        elif 'louis' in current_char_id.lower():
            name = get_dynamic_king_name(characters_data[current_char_id].get('name'), current_theme)
        elif 'minister' in current_char_id.lower():
            name = get_dynamic_minister_name(characters_data[current_char_id].get('name'), current_theme)
        else:
            name = characters_data[current_char_id].get('name')

        # 思考回路分岐
        if current_char_id == "citizen":
            if "三部会" in current_theme: role_inst = "【重要：あなたは貧しい市民です。王や貴族ではありません】1614年の第三身分。貴族も聖職者も免税で、自分たちだけが重税を負わされる不条理に怒れ。"
            elif "フロンド" in current_theme: role_inst = "【重要：あなたは貧しい市民です】1648年のパリ市民。重税を課すマザラン枢機卿を罵り、高等法院を支持してバリケードを築け。"
            elif "ナント" in current_theme: role_inst = "【重要：あなたは市民です】1685年の市民。異端追放を歓迎するか、経済の混乱を憂う者。"
            elif "宗教改革" in current_theme: role_inst = "【重要：あなたは市民です】16世紀ドイツの市民。免罪符が高すぎると嘆く。"
            else: role_inst = "名もなき市民。"
        
        elif current_char_id == louis_id:
            char = characters_data[current_char_id]
            if "三部会" in current_theme:
                role_inst = f"13歳のルイ13世。『貴族どもは特権ばかり主張して文句が多く、本当にうざい』。三部会など時間の無駄であり、『そもそもこんなもの開かなくても、余と母上がいれば政治は回るのだ』と、不機嫌に断言せよ。"
            elif "フロンド" in current_theme:
                role_inst = f"少年ルイ14世。パリの民衆に寝室まで侵入された屈辱。『王である余に対して、この無礼は何だ』と震える怒りを表現せよ。"
            elif "ナント" in current_theme:
                role_inst = "1685年のルイ14世（太陽王）。ユグノーたちが『信仰のために国を捨てる』と宣言したことに、『余の国よりも神を選ぶというのか？』と驚愕し、嘆け。そして『だが待てよ、彼らが出て行けば、フランスの富はどうなる？』と、経済崩壊の予感に震えろ。"
            else: 
                role_inst = f"絶頂期のルイ14世。『朕は国家なり』。異端を許さず、フランスの統一を完成させる絶対君主。"

        elif current_char_id == minister_id:
            char = characters_data[current_char_id]
            if "三部会" in current_theme: role_inst = f"若きリシュリュー。第三身分を利用して貴族を牽制しつつ、王権の絶対性を説け。"
            elif "フロンド" in current_theme: role_inst = f"マザラン枢機卿。貴族や民衆からの憎悪を一身に受けながら、冷徹に王家を守れ。"
            else: role_inst = f"王の側近。王の命令を冷徹に実行せよ。"

        elif current_char_id == french_noble_id:
            char = characters_data[current_char_id]
            if "三部会" in current_theme: role_inst = f"1614年のフランス貴族（名門）。第三身分が貴族を『弟』と呼んだことに激怒せよ。『靴屋の息子と兄弟になった覚えはない！』と吐き捨て、特権こそが正義だと主張せよ。"
            elif "フロンド" in current_theme: role_inst = f"フロンド派の大貴族。『マザランごとき外国人が国を牛耳るとは！』と激怒し、王を取り戻すために戦う。"
            else: role_inst = f"ヴェルサイユの廷臣。王にへつらい、ご機嫌取りをする太鼓持ちになれ。"

        elif current_char_id == german_noble_id:
            char = characters_data[current_char_id]
            role_inst = f"ドイツ諸侯。『ローマ教会にドイツの富が吸い上げられるのは我慢ならん』。ルターを保護し、教皇と皇帝の干渉を排除して自立を狙え。"

        elif current_char_id == huguenot_id:
            char = characters_data[current_char_id]
            if "ナント" in current_theme:
                role_inst = "1685年のユグノー（商工業者）。【重要：経済の話は一切するな】。『カトリックへの強制改宗は魂の死である』と訴えよ。『信仰を捨てるくらいなら、愛するフランスを捨てて亡命する』という悲壮な決意だけを投稿せよ。"
            else:
                role_inst = f"ユグノーの商工業者。『国のために尽くしてきたのに、なぜ追い出されねばならないのか』。経済的損失を警告せよ。"

        elif current_char_id == luther_id:
            char = characters_data[current_char_id]
            role_inst = f"マルティン・ルター。カトリックの腐敗を激しく非難し、聖書のみを掲げよ。"
        elif current_char_id == leo_id:
            char = characters_data[current_char_id]
            role_inst = f"教皇レオ10世。異端者ルターを断罪し、教会の権威を誇示せよ。"
        
        else:
            char = characters_data[current_char_id]
            role_inst = f"{char.get('name')}。{char.get('persona', char.get('description', ''))} 自説を主張せよ。"

        # stopパラメータを4つに修正済み
        system_prompt = (
            f"役割: {role_inst}\n"
            f"タスク: テーマ『{current_theme}』について、140文字以内のSNS投稿を作成せよ。\n"
            "絶対ルール: 挨拶・解説・メタ発言（『不合格です』『理解しました』等）は一切禁止。投稿本文のみを直接出力せよ。ハッシュタグ（#）必須。"
        )
        
        context = [{"role": "system", "content": system_prompt}]
        for m in st.session_state.messages[-4:]:
            context.append({"role": "user", "content": f"{m['name']}: {m['content']}"})

        try:
            # 修正完了: response変数の定義とstopパラメータ数
            response = client.chat.completions.create(model="gpt-3.5-turbo", messages=context, max_tokens=150, temperature=1.0, stop=["不合格", "理解しました", "申し訳", "システムエラー"])
            ai_text = response.choices[0].message.content
            
            clean_text = re.sub(r'^(不合格です|理解しました|申し訳ありません|システム上のエラー|回答は無効|この投稿は).*?\n?', '', ai_text).strip()
            
            avatar = get_safe_avatar(current_char_id)

            if clean_text:
                st.session_state.messages.append({"role": current_char_id, "name": name, "content": clean_text, "avatar": avatar})
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
