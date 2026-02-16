import streamlit as st
import json
import time
import re
import os
import base64
from openai import OpenAI

# --- 1. OpenAI APIキー ---
OPENAI_API_KEY = "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"

def load_characters():
    with open('characters.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_image_base64(img_path):
    full_path = os.path.join("static", img_path)
    if os.path.exists(full_path):
        with open(full_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:image/jpeg;base64,{data}"
    return "https://via.placeholder.com/60"

def ask_ai(character, current_chaos, context=""):
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""あなたは歴史上の人物「{character['name']}」として、1517年の状況でSNS投稿してください。
    性格: {character['persona']}
    現在の炎上度: {current_chaos}%
    直前の議論: {context}
    
    【ルール】
    1. 100文字以内で、相手に反論または威厳を持って答えてください。
    2. ハッシュタグを1つ含めてください。
    3. 現代風ではなく、当時の重々しい口調を貫いてください。"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"通信エラー: {e}"

def set_design(chaos):
    r = min(255, int(chaos * 2.5))
    opacity = min(0.6, chaos / 150)
    bg_color = f"rgba({r}, 0, 0, {opacity})" if chaos >= 30 else "#f0f2f5"
    st.markdown(f"""
        <style>
        .stApp {{ background-color: {bg_color}; transition: background-color 2s ease; }}
        .tweet-card {{
            display: flex; border: 1px solid #e1e8ed; padding: 15px; border-radius: 12px;
            margin-bottom: 12px; background-color: white; color: #14171a;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); animation: slideIn 0.8s ease-out;
        }}
        @keyframes slideIn {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .icon {{ width: 55px; height: 55px; border-radius: 50%; object-fit: cover; margin-right: 15px; border: 2px solid #1DA1F2; }}
        .hashtag {{ color: #1DA1F2; font-weight: bold; }}
        </style>
        """, unsafe_allow_html=True)

def format_content(text):
    return re.sub(r'(#\w+)', r'<span class="hashtag">\1</span>', text)

def main():
    st.set_page_config(page_title="歴ッター (Rekitter) PRO", layout="wide")
    
    # --- セッション状態の初期化 ---
    if 'posts' not in st.session_state: st.session_state.posts = []
    if 'chaos' not in st.session_state: st.session_state.chaos = 0
    # 「あと何人が発言すべきか」を管理するカウンター
    if 'debate_steps_left' not in st.session_state: st.session_state.debate_steps_left = 0
    # 今どちらの番か（0か1か）
    if 'current_speaker_idx' not in st.session_state: st.session_state.current_speaker_idx = 0

    set_design(st.session_state.chaos)
    st.title("📜 歴ッター (Rekitter) - リアルタイム論争")

    chars = load_characters()
    
    # --- サイドバー操作 ---
    st.sidebar.title("🛠️ 操作パネル")
    
    # 単発投稿
    selected_name = st.sidebar.selectbox("人物を選択", [c['name'] for c in chars])
    char_info = next(c for c in chars if c['name'] == selected_name)
    if st.sidebar.button(f"✨ {char_info['name']}として投稿"):
        content = ask_ai(char_info, st.session_state.chaos)
        st.session_state.posts.insert(0, {"name": char_info['name'], "id": char_info['id'], "content": content, "img": char_info.get('image','')})
        st.session_state.chaos = min(100, st.session_state.chaos + 10)
        st.rerun()

    st.sidebar.markdown("---")
    
    # 論争モードの設定
    st.sidebar.subheader("⚔️ 自動論争モード")
    rounds_input = st.sidebar.slider("論争の往復回数", 1, 5, 2)
    
    # 重要：ボタンを押したときは「回数」をセットするだけ
    if st.sidebar.button("🔥 論争をスタート"):
        st.session_state.debate_steps_left = rounds_input * 2
        st.session_state.current_speaker_idx = 0
        st.rerun()

    if st.sidebar.button("🗑️ リセット"):
        st.session_state.posts = []; st.session_state.chaos = 0; st.session_state.debate_steps_left = 0
        st.rerun()

    # --- メインタイムライン表示 ---
    st.write(f"現在の世論の荒れ具合: **{st.session_state.chaos}%**")
    
    # 先に現在のタイムラインを描画する
    for p in st.session_state.posts:
        formatted_text = format_content(p['content'])
        img_data = get_image_base64(p['img'])
        st.markdown(f"""
            <div class="tweet-card">
                <img src="{img_data}" class="icon">
                <div>
                    <div><span style="font-weight:bold;">{p['name']}</span><span style="color:#657786; margin-left:5px;">@{p['id']}</span></div>
                    <p style="margin-top:5px; line-height:1.5;">{formatted_text}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # --- 【プロ仕様】論争の自動ステップ実行ロジック ---
    # タイムライン描画の「後」に実行することで、1つずつ出るように見せる
    if st.session_state.debate_steps_left > 0:
        # 今の番の人を決める
        c = chars[st.session_state.current_speaker_idx]
        last_content = st.session_state.posts[0]['content'] if st.session_state.posts else ""
        
        # 思考中を演出
        with st.status(f"💬 {c['name']}が反論を執筆中...", expanded=True) as status:
            content = ask_ai(c, st.session_state.chaos, last_content)
            st.session_state.posts.insert(0, {
                "name": c['name'], "id": c['id'], 
                "content": content, "img": c.get('image','')
            })
            st.session_state.chaos = min(100, st.session_state.chaos + 12)
            
            # 状態を更新
            st.session_state.debate_steps_left -= 1
            st.session_state.current_speaker_idx = (st.session_state.current_speaker_idx + 1) % len(chars)
            
            status.update(label="✅ 書き込み完了！", state="complete")
            
            # ここで「読む時間」として2.5秒停止
            time.sleep(2.5)
            
            # 自分を再起動（これで次の人の番がトップから始まる）
            st.rerun()

if __name__ == "__main__":
    main()