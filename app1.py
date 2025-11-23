import streamlit as st
import pandas as pd
import io
import re
import time
import pickle
import os
import random

# --- 1. 核心配置 ---
st.set_page_config(
    page_title="ZenMode Ultimate",
    layout="wide",
    page_icon="🌙",
    initial_sidebar_state="expanded"
)

# --- 2. CSS 样式 ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* HUD */
    .hud-container {
        display: flex; justify-content: space-between; background-color: #1F2128;
        padding: 15px 25px; border-radius: 12px; border: 1px solid #363B45;
        margin-bottom: 25px; align-items: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .hud-item { font-size: 16px; font-weight: 500; color: #A0AEC0; }
    .hud-value { font-size: 20px; font-weight: 700; color: #F8FAFC; margin-left: 8px; }
    .hud-warn { color: #F87171 !important; } 
    .hud-accent { color: #38BDF8 !important; } 

    /* 卡片 */
    .zen-card {
        background-color: #262730; padding: 40px; border-radius: 16px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.5); border: 1px solid #363B45; margin-bottom: 20px;
    }
    .question-text { font-size: 24px; font-weight: 500; color: #E2E8F0; line-height: 1.6; margin-bottom: 30px; }

    .tag { display: inline-block; padding: 5px 12px; background-color: #1E3A8A; color: #93C5FD; border-radius: 6px; font-size: 13px; font-weight: 700; margin-bottom: 20px; }

    /* 选项 */
    .stRadio div[role='radiogroup'] > label {
        background-color: #1A1C23; border: 1px solid #2D3748; color: #CBD5E0 !important;
        padding: 18px 20px; border-radius: 12px; margin-bottom: 12px; transition: all 0.2s;
    }
    .stRadio div[role='radiogroup'] > label:hover {
        border-color: #38BDF8; background-color: #2D3748; color: #FFFFFF !important; transform: translateX(5px); cursor: pointer;
    }

    /* 反馈提示框 */
    .feedback-box {
        padding: 15px; border-radius: 8px; margin: 15px 0; font-weight: bold; text-align: center;
    }
    .feedback-success { background-color: #064E3B; color: #6EE7B7; border: 1px solid #059669; }
    .feedback-error { background-color: #7F1D1D; color: #FCA5A5; border: 1px solid #DC2626; }

    button[kind="primary"] { background-color: #2563EB !important; border: none; }
    button[kind="primary"]:hover { background-color: #3B82F6 !important; }

    @keyframes bounce { 0%, 20%, 50%, 80%, 100% {transform: translateX(0);} 40% {transform: translateX(-10px);} 60% {transform: translateX(-5px);} }
    .arrow-hint { animation: bounce 2s infinite; font-size: 24px; color: #38BDF8; font-weight: bold; display: inline-block; margin-right: 10px; }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "user_data_v16.pkl"

# --- 3. 逻辑函数 ---

# 预编译正则
RE_OPTS_1 = re.compile(r'(^|\s)([A-Z])[.、:．]\s*(.*?)(?=\s+[A-Z][.、:．]|$)', re.DOTALL | re.MULTILINE)
RE_OPTS_2 = re.compile(r'(^|\s)\(?([A-Z])\)[.:]?\s*(.*?)(?=\s+\(?[A-Z]\)?[.:]?|$)', re.DOTALL | re.MULTILINE)
RE_OPTS_3 = re.compile(r'([A-Z])[.、:．](.*?)(?=[A-Z][.、:．]|$)', re.DOTALL | re.MULTILINE)


def normalize_text(text):
    if text is None: return ""
    return str(text).strip().replace('：', ':').replace('（', '(').replace('）', ')').replace('．', '.')


def parse_options_zen(text):
    text = normalize_text(text)
    options = {}
    question_text = text
    patterns = [RE_OPTS_1, RE_OPTS_2, RE_OPTS_3]
    for idx, p in enumerate(patterns):
        matches = list(p.finditer(text))
        if len(matches) >= 2:
            temp_options = {}
            first_match_start = float('inf')
            for m in matches:
                if idx == 2:
                    key, val = m.group(1).upper(), m.group(2).strip()
                else:
                    groups = m.groups()
                    key, val = groups[-2].upper(), groups[-1].strip()
                temp_options[key] = val
                if m.start() < first_match_start: first_match_start = m.start()
            if temp_options: return text[:first_match_start].strip(), temp_options
    return question_text, options


def process_excel(file):
    try:
        df = pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]

        def find_col(kws):
            for c in df.columns:
                for kw in kws:
                    if kw in c:
                     return c
            return None

        col_type = find_col(['类型', 'Type', '题型'])
        col_content = find_col(['内容', 'Content', '题目'])
        col_answer = find_col(['答案', 'Answer', '结果'])
        if not (col_type and col_content and col_answer): return None, "Excel 缺少必要列 (需包含: 类型, 内容, 答案)"

        df[col_type] = df[col_type].fillna("").astype(str)
        df[col_content] = df[col_content].fillna("").astype(str)
        df[col_answer] = df[col_answer].fillna("").astype(str)

        questions = []
        records = df.to_dict('records')
        total_rows = len(records)

        progress_bar = st.progress(0)

        for i, row in enumerate(records):
            if i % (max(1, total_rows // 10)) == 0: progress_bar.progress((i + 1) / total_rows)

            raw_type = normalize_text(row[col_type]).upper()
            raw_content = row[col_content]
            raw_answer = normalize_text(row[col_answer]).upper()

            if any(x in raw_type for x in ['AO', '判断']):
                q_code, q_name = 'AO', '判断题'
            elif any(x in raw_type for x in ['BO', '单选']):
                q_code, q_name = 'BO', '单选题'
            elif any(x in raw_type for x in ['CO', '多选']):
                q_code, q_name = 'CO', '多选题'
            else:
                q_code, q_name = 'UNK', '未知'

            q_text, q_options = parse_options_zen(raw_content)
            if q_code in ['BO', 'CO'] and not q_options: q_options = {}

            questions.append({
                "id": i, "code": q_code, "type": q_name,
                "content": q_text, "options": q_options, "answer": raw_answer,
                "user_answer": None, "raw_content": raw_content
            })

        progress_bar.empty()
        return questions, None
    except Exception as e:
        return None, f"解析错误: {str(e)}"


def export_wrong_questions(q_list):
    """
    导出逻辑优化：
    1. 使用原始的 raw_content 作为“题目内容”，确保包含选项，方便再次导入。
    2. 列名与 import 逻辑对齐。
    """
    if not q_list: return None
    data = []
    for q in q_list:
        data.append({
            "题目类型": q['type'],
            "题目内容": q['raw_content'],  # 使用原始完整内容
            "正确答案": q['answer'],
            "你的误选": q['user_answer']
        })
    df = pd.DataFrame(data)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return out.getvalue()


def save_state():
    data = {
        "banks": st.session_state.banks,
        "progress": st.session_state.progress,
        "active_bank": st.session_state.active_bank,
        "filters": st.session_state.filters
    }
    try:
        with open(DATA_FILE, "wb") as f:
            pickle.dump(data, f)
    except:
        pass


def load_state():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "rb") as f:
                data = pickle.load(f)
                st.session_state.banks = data.get("banks", {})
                st.session_state.progress = data.get("progress", {})
                st.session_state.active_bank = data.get("active_bank", None)
                st.session_state.filters = data.get("filters", {})
                return True
        except:
            pass
    return False


if 'init' not in st.session_state:
    st.session_state.banks = {}
    st.session_state.progress = {}
    st.session_state.active_bank = None
    st.session_state.filters = {}
    load_state()
    st.session_state.init = True

# --- 4. 侧边栏 ---
with st.sidebar:
    st.header("🛠️ 控制台")

    # 题库切换
    st.subheader("📚 题库")
    bank_names = list(st.session_state.banks.keys())
    if bank_names:
        curr_idx = bank_names.index(st.session_state.active_bank) if st.session_state.active_bank in bank_names else 0
        selected = st.selectbox("切换题库", bank_names, index=curr_idx)
        if selected != st.session_state.active_bank:
            st.session_state.active_bank = selected
            save_state()
            st.rerun()

        # 题型筛选
        if st.session_state.active_bank:
            curr_q_list = st.session_state.banks[st.session_state.active_bank]
            all_types = list(set(q['type'] for q in curr_q_list))
            default_sel = st.session_state.filters.get(st.session_state.active_bank, all_types)

            st.markdown("---")
            st.subheader("🎯 题型筛选")
            selected_types = st.multiselect("只刷这些题型:", all_types, default=default_sel)

            if selected_types != default_sel:
                st.session_state.filters[st.session_state.active_bank] = selected_types
                st.session_state.progress[st.session_state.active_bank]["current_idx"] = 0
                save_state()
                st.rerun()
    else:
        st.warning("暂无题库")

    # 错题本
    if st.session_state.active_bank:
        prog = st.session_state.progress[st.session_state.active_bank]
        wrong_cnt = len(prog['wrong'])
        if wrong_cnt > 0:
            st.divider()
            st.subheader(f"📥 错题 ({wrong_cnt})")

            c1, c2 = st.columns(2)
            # 1. 导出
            xls = export_wrong_questions(prog['wrong'])
            c1.download_button(f"📥 导出", xls, f"错题本.xlsx", use_container_width=True)

            # 2. 清空
            with c2.popover("🧹 清空"):
                if st.button("确认清空", type="primary"):
                    prog['wrong'] = []
                    save_state()
                    st.rerun()

            # 3. 直接存为新题库 (新增功能)
            if st.button("💾 直接存为新题库", use_container_width=True):
                new_name = f"{st.session_state.active_bank}_错题本"
                if new_name in st.session_state.banks:
                    new_name += f"_{int(time.time())}"

                # 深拷贝错题，重置用户答案
                new_qs = []
                for wq in prog['wrong']:
                    nq = wq.copy()
                    nq['user_answer'] = None  # 重置作答
                    new_qs.append(nq)

                st.session_state.banks[new_name] = new_qs
                st.session_state.progress[new_name] = {"history": {}, "wrong": [], "current_idx": 0}
                st.session_state.active_bank = new_name
                st.session_state.filters[new_name] = list(set(q['type'] for q in new_qs))

                st.success(f"已创建并切换至: {new_name}")
                time.sleep(1)
                save_state()
                st.rerun()

    # 导入
    st.divider()
    with st.expander("➕ 导入", expanded=(not bank_names)):
        f = st.file_uploader("Excel", type=['xlsx', 'xls'])
        n = st.text_input("命名")
        if f and st.button("导入", type="primary"):
            with st.spinner("解析中..."):
                qs, err = process_excel(f)
            if err:
                st.error(err)
            else:
                final_n = n.strip() if n else f.name.split('.')[0]
                if final_n in st.session_state.banks: final_n += f"_{int(time.time())}"
                st.session_state.banks[final_n] = qs
                st.session_state.progress[final_n] = {"history": {}, "wrong": [], "current_idx": 0}
                st.session_state.active_bank = final_n
                st.session_state.filters[final_n] = list(set(q['type'] for q in qs))
                st.success(f"已导入 {len(qs)} 题")
                time.sleep(1)
                save_state()
                st.rerun()

    # 删除
    if st.session_state.active_bank:
        st.divider()
        with st.popover("🗑️ 删除题库", use_container_width=True):
            if st.button("🔴 确认删除"):
                del st.session_state.banks[st.session_state.active_bank]
                del st.session_state.progress[st.session_state.active_bank]
                del st.session_state.filters[st.session_state.active_bank]
                st.session_state.active_bank = list(st.session_state.banks.keys())[
                    0] if st.session_state.banks else None
                save_state()
                st.rerun()

# --- 5. 主界面 ---
if not st.session_state.active_bank:
    st.markdown(
        """<div style="text-align:center; padding: 100px 0;"><h1>👋 欢迎使用 ZenMode</h1><p style="color:#888;">请在左侧导入题库。</p></div>""",
        unsafe_allow_html=True)
    st.markdown(
        """<div style="text-align:center;"><div class="arrow-hint">👈</div><span style="color:#38BDF8;">请点击箭头展开侧边栏</span></div>""",
        unsafe_allow_html=True)
else:
    bk = st.session_state.active_bank
    full_qs = st.session_state.banks[bk]
    active_filters = st.session_state.filters.get(bk, [])
    qs = [q for q in full_qs if q['type'] in active_filters]

    if not qs:
        st.warning("⚠️ 当前筛选条件下没有题目。")
    else:
        pg = st.session_state.progress[bk]
        idx = pg['current_idx']
        if idx >= len(qs): idx = len(qs)

        # HUD
        total_q = len(qs)
        done_q = idx + 1
        wrong_q = len(pg['wrong'])

        st.markdown(f"""
        <div class="hud-container">
            <div class="hud-item">题库: <span style="color:#E2E8F0; margin-left:5px;">{bk}</span></div>
            <div style="display:flex; gap: 30px;">
                <div class="hud-item">进度 <span class="hud-value hud-accent">{min(done_q, total_q)}</span><span style="font-size:14px;color:#64748B">/{total_q}</span></div>
                <div class="hud-item">错题 <span class="hud-value hud-warn">{wrong_q}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if idx >= len(qs):
            st.balloons()
            st.markdown(
                f"""<div style="text-align:center; padding: 50px; background:#262730; border-radius:15px;"><h2>🎉 练习完成!</h2><p>共 {total_q} 题，错题 {wrong_q} 道</p></div>""",
                unsafe_allow_html=True)
            st.write("")
            if st.button("🔄 再刷一次", type="primary", use_container_width=True):
                pg['current_idx'] = 0
                pg['history'] = {}
                save_state()
                st.rerun()
        else:
            q = qs[idx]
            st.markdown(f"""
            <div class="zen-card">
                <span class="tag">{q['type']}</span>
                <div class="question-text">{q['content']}</div>
            </div>
            """, unsafe_allow_html=True)

            user_choice = None
            saved = pg['history'].get(idx)

            if q['code'] == 'AO':
                sel = 0 if saved == 'A' else (1 if saved == 'B' else None)
                val = st.radio("J", ['A', 'B'], index=sel, format_func=lambda x: "✅ 正确" if x == 'A' else "❌ 错误",
                               horizontal=True, key=f"{bk}_{idx}", label_visibility="collapsed")
                user_choice = val
            elif q['code'] == 'BO':
                if q['options']:
                    ks = list(q['options'].keys())
                    ds = [f"{k}. {v}" for k, v in q['options'].items()]
                    sel = ks.index(saved) if saved in ks else None
                    val = st.radio("S", ds, index=sel, key=f"{bk}_{idx}", label_visibility="collapsed")
                    if val: user_choice = val.split('.')[0]
                else:
                    user_choice = st.text_input("Ans:", value=saved or "", key=f"tx_{bk}_{idx}").strip().upper()
            elif q['code'] == 'CO':
                st.write("多项选择:")
                if q['options']:
                    sl = []
                    for k, v in q['options'].items():
                        chk = (k in saved) if saved else False
                        if st.checkbox(f"{k}. {v}", value=chk, key=f"{bk}_{idx}_{k}"): sl.append(k)
                    if sl: user_choice = "".join(sorted(sl))
                else:
                    user_choice = st.text_input("Ans:", value=saved or "", key=f"tx_{bk}_{idx}").strip().upper()

            feedback_placeholder = st.empty()
            st.write("")
            c1, c2, c3 = st.columns([1, 2, 1])
            if c1.button("⬅", disabled=(idx == 0), use_container_width=True):
                pg['current_idx'] -= 1
                save_state()
                st.rerun()

            if c2.button("提交", type="primary", use_container_width=True):
                if not user_choice:
                    st.toast("请先作答", icon="⚠️")
                else:
                    pg['history'][idx] = user_choice
                    ans = q['answer']
                    if q['code'] == 'AO':
                        if ans == '对': ans = 'A'
                        if ans == '错': ans = 'B'

                    is_cor = (user_choice == ans)
                    if is_cor:
                        feedback_placeholder.markdown(
                            f"""<div class="feedback-box feedback-success">✅ 回答正确！</div>""", unsafe_allow_html=True)
                        time.sleep(0.8)
                    else:
                        feedback_placeholder.markdown(
                            f"""<div class="feedback-box feedback-error">❌ 错误！正确答案是：{q['answer']}</div>""",
                            unsafe_allow_html=True)
                        if not any(w['raw_content'] == q['raw_content'] for w in pg['wrong']):
                            pg['wrong'].append(q)
                        time.sleep(1.5)

                    pg['current_idx'] += 1
                    save_state()
                    st.rerun()

            if c3.button("➡", use_container_width=True):
                pg['current_idx'] += 1
                save_state()
                st.rerun()