import streamlit as st
import pandas as pd
import io
import time
import pickle
import os
import random

from quiz_utils import normalize_text, normalize_answer, parse_options_zen

# --- 1. 核心配置 ---
st.set_page_config(
    page_title="ZenMode Ultimate",
    layout="wide",
    page_icon="🌙",
    initial_sidebar_state="expanded"
)

# --- 2. CSS 样式 (修复侧边栏唤起) ---
st.markdown("""
<style>
    /* --- 关键修复区 --- */
    /* 只隐藏右上角的三点菜单，保留 Header 区域以便能点击左上角的侧边栏箭头 */
    #MainMenu {visibility: hidden;}

    /* 隐藏底部 Footer */
    footer {visibility: hidden;}

    /* 将顶部 Header 背景设为透明，保持沉浸感，但保留交互能力 */
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
    }

    /* --- 全局样式 --- */
    /* 使用系统字体支持中文显示，避免依赖外部字体 */
    * {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", "WenQuanYi Micro Hei", "Noto Sans CJK SC", sans-serif !important;
    }
    
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", "WenQuanYi Micro Hei", "Noto Sans CJK SC", sans-serif !important;
    }
    
    .stApp { background-color: #0a0a0a; color: #FFFFFF; }

    /* 侧边栏样式优化 */
    [data-testid="stSidebar"] {
        background-color: #111111;
        border-right: 1px solid #2a2a2a;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
    }

    /* HUD 进度条样式 */
    .hud-container {
        display: flex; 
        justify-content: space-between; 
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 18px 24px; 
        border-radius: 16px; 
        border: 1px solid #2a2a4a;
        margin-bottom: 24px; 
        align-items: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    .hud-item { 
        font-size: 15px; 
        font-weight: 600; 
        color: #a0a0b0; 
    }
    .hud-value { 
        font-size: 22px; 
        font-weight: 800; 
        color: #FFFFFF; 
        margin-left: 8px; 
    }
    .hud-warn { color: #ff6b6b !important; } 
    .hud-accent { color: #4ecdc4 !important; } 

    /* 题目卡片样式优化 */
    .zen-card {
        background: linear-gradient(145deg, #1a1a2e 0%, #0f0f1a 100%);
        padding: 30px; 
        border-radius: 20px;
        border: 1px solid #2a2a4a; 
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    .question-text { 
        font-size: 22px; 
        font-weight: 600; 
        color: #FFFFFF; 
        line-height: 1.7; 
        margin-bottom: 25px;
        letter-spacing: 0.3px;
    }

    .tag { 
        display: inline-block; 
        padding: 6px 14px; 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #FFFFFF; 
        border-radius: 20px; 
        font-size: 12px; 
        font-weight: bold; 
        margin-bottom: 18px;
        box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
    }

    /* 选项样式优化 */
    .stRadio div[role='radiogroup'] > label {
        background: linear-gradient(145deg, #1e1e2e 0%, #151520 100%);
        border: 1px solid #3a3a5a; 
        color: #FFFFFF !important; 
        font-size: 17px !important; 
        font-weight: 500;
        padding: 18px 22px; 
        border-radius: 14px; 
        margin-bottom: 12px; 
        transition: all 0.2s ease;
        opacity: 1 !important;
    }
    .stRadio div[role='radiogroup'] > label:hover {
        background: linear-gradient(145deg, #252540 0%, #1a1a30 100%);
        border-color: #4ecdc4; 
        color: #FFFFFF !important;
        transform: translateX(4px);
        box-shadow: 0 4px 15px rgba(78, 205, 196, 0.2);
    }
    div[role="radiogroup"] div[data-testid="stMarkdownContainer"] p {
        color: #FFFFFF !important;
    }

    /* 复选框样式 */
    .stCheckbox label {
        color: #FFFFFF !important;
    }

    /* 按钮样式优化 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border-radius: 12px;
        font-weight: 600;
        border: none !important;
        padding: 12px 24px;
        transition: all 0.2s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    button[kind="primary"] { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border-radius: 12px;
        font-weight: bold;
        border: none !important; 
        height: 50px;
    }

    /* 反馈框样式优化 */
    .feedback-box { 
        padding: 18px; 
        border-radius: 12px; 
        margin: 18px 0; 
        font-weight: bold; 
        text-align: center; 
        font-size: 18px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    .feedback-success { 
        background: linear-gradient(135deg, #0d4d0d 0%, #1a5a1a 100%);
        color: #4ade80; 
        border: 1px solid #22c55e;
    }
    .feedback-error { 
        background: linear-gradient(135deg, #4d0d0d 0%, #5a1a1a 100%);
        color: #f87171; 
        border: 1px solid #ef4444;
    }

    /* 完成页面样式 */
    .completion-card {
        text-align: center;
        padding: 50px;
        background: linear-gradient(145deg, #1a1a2e 0%, #0f0f1a 100%);
        border-radius: 20px;
        border: 1px solid #2a2a4a;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }

    /* 欢迎页面样式 */
    .welcome-container {
        text-align: center;
        padding: 80px 20px;
    }
    .welcome-title {
        font-size: 48px;
        margin-bottom: 20px;
    }
    .welcome-subtitle {
        color: #888;
        font-size: 18px;
        margin-bottom: 40px;
    }
    .welcome-hint {
        color: #4ecdc4;
        font-size: 16px;
    }

    @keyframes bounce { 
        0%, 20%, 50%, 80%, 100% {transform: translateX(0);} 
        40% {transform: translateX(-10px);} 
        60% {transform: translateX(-5px);} 
    }
    .arrow-hint { 
        animation: bounce 2s infinite; 
        font-size: 28px; 
        color: #4ecdc4; 
        font-weight: bold; 
        display: inline-block; 
        margin-right: 12px; 
    }

    /* 输入框样式 */
    .stTextInput input {
        background-color: #1a1a2e !important;
        color: #FFFFFF !important;
        border: 1px solid #3a3a5a !important;
        border-radius: 10px !important;
    }
    
    /* 选择框样式 */
    .stSelectbox > div > div {
        background-color: #1a1a2e !important;
        color: #FFFFFF !important;
    }

    /* 警告框样式 */
    .stAlert {
        background-color: #2a2a3e !important;
        border-radius: 10px !important;
    }

    /* 分隔线样式 */
    hr {
        border-color: #2a2a4a !important;
    }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "user_data_v18.pkl"

# --- 3. 逻辑函数 ---
# Core parsing functions are imported from quiz_utils module


def process_excel(file):
    """Process Excel file and extract questions. Returns (questions_list, error_message)."""
    try:
        df = pd.read_excel(file)
        if df.empty:
            return None, "Excel文件为空"
        
        df.columns = [str(c).strip() for c in df.columns]

        def find_col(kws):
            """Find column by keywords (case-insensitive)."""
            for c in df.columns:
                c_lower = c.lower()
                for kw in kws:
                    if kw.lower() in c_lower:
                        return c
            return None

        col_type = find_col(['类型', 'Type', '题型', 'type', 'kind'])
        col_content = find_col(['内容', 'Content', '题目', '问题', 'question', 'content'])
        col_answer = find_col(['答案', 'Answer', '结果', '正确答案', 'answer', 'result'])
        
        missing_cols = []
        if not col_type:
            missing_cols.append("类型/Type/题型")
        if not col_content:
            missing_cols.append("内容/Content/题目")
        if not col_answer:
            missing_cols.append("答案/Answer/结果")
        
        if missing_cols:
            return None, f"缺少必要列: {', '.join(missing_cols)}。可用列: {', '.join(df.columns)}"

        # Safely fill NA values
        df[col_type] = df[col_type].fillna("").astype(str)
        df[col_content] = df[col_content].fillna("").astype(str)
        df[col_answer] = df[col_answer].fillna("").astype(str)

        questions = []
        records = df.to_dict('records')
        total_rows = len(records)
        
        if total_rows == 0:
            return None, "Excel文件中没有数据行"
            
        progress_bar = st.progress(0)
        skipped_count = 0

        for i, row in enumerate(records):
            try:
                if i % (max(1, total_rows // 10)) == 0:
                    progress_bar.progress((i + 1) / total_rows)
                
                raw_type = normalize_text(row.get(col_type, "")).upper()
                raw_content = row.get(col_content, "")
                raw_answer = row.get(col_answer, "")
                
                # Skip empty rows
                if not raw_content or not raw_content.strip():
                    skipped_count += 1
                    continue

                # Determine question type with expanded keywords
                if any(x in raw_type for x in ['AO', '判断', 'TRUE', 'FALSE', 'TF', '对错', '是非']):
                    q_code, q_name = 'AO', '判断题'
                elif any(x in raw_type for x in ['BO', '单选', 'SINGLE', '单项', 'RADIO']):
                    q_code, q_name = 'BO', '单选题'
                elif any(x in raw_type for x in ['CO', '多选', 'MULTI', '多项', 'CHECKBOX']):
                    q_code, q_name = 'CO', '多选题'
                else:
                    q_code, q_name = 'UNK', '未知'

                q_text, q_options = parse_options_zen(raw_content)
                
                # Normalize answer (works for all question types)
                normalized_answer = normalize_answer(raw_answer)
                
                if q_code in ['BO', 'CO'] and not q_options:
                    q_options = {}
                    
                questions.append({
                    "id": i, "code": q_code, "type": q_name,
                    "content": q_text, "options": q_options, "answer": normalized_answer,
                    "user_answer": None, "raw_content": raw_content
                })
            except Exception as row_error:
                # Skip problematic rows but continue processing
                skipped_count += 1
                continue
        
        progress_bar.empty()
        
        if not questions:
            return None, f"未能解析出任何有效题目 (跳过了 {skipped_count} 行)"
        
        return questions, None
    except Exception as e:
        return None, f"解析错误: {str(e)}"


def export_wrong_questions(q_list):
    """Export wrong questions to Excel format."""
    if not q_list:
        return None
    data = []
    for q in q_list:
        data.append({
            "题目类型": q.get('type', '未知'),
            "题目内容": q.get('raw_content', ''),
            "正确答案": q.get('answer', ''),
            "你的误选": q.get('user_answer', '')
        })
    df = pd.DataFrame(data)
    out = io.BytesIO()
    try:
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        return out.getvalue()
    except Exception:
        return None


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

    st.subheader("📚 题库")
    bank_names = list(st.session_state.banks.keys())
    if bank_names:
        curr_idx = bank_names.index(st.session_state.active_bank) if st.session_state.active_bank in bank_names else 0
        selected = st.selectbox("切换题库", bank_names, index=curr_idx)
        if selected != st.session_state.active_bank:
            st.session_state.active_bank = selected
            save_state()
            st.rerun()

        if st.session_state.active_bank:
            curr_q_list = st.session_state.banks[st.session_state.active_bank]
            all_types = list(set(q['type'] for q in curr_q_list))
            default_sel = st.session_state.filters.get(st.session_state.active_bank, all_types)
            st.markdown("---")
            st.subheader("🎯 筛选")
            selected_types = st.multiselect("只刷:", all_types, default=default_sel)
            if selected_types != default_sel:
                st.session_state.filters[st.session_state.active_bank] = selected_types
                st.session_state.progress[st.session_state.active_bank]["current_idx"] = 0
                save_state()
                st.rerun()
    else:
        st.warning("暂无题库")

    if st.session_state.active_bank:
        prog = st.session_state.progress[st.session_state.active_bank]
        wrong_cnt = len(prog['wrong'])
        if wrong_cnt > 0:
            st.divider()
            st.subheader(f"📥 错题 ({wrong_cnt})")
            c1, c2 = st.columns(2)
            xls = export_wrong_questions(prog['wrong'])
            c1.download_button(f"导出", xls, f"错题.xlsx", use_container_width=True)
            with c2.popover("清空"):
                if st.button("确认", type="primary"):
                    prog['wrong'] = []
                    save_state()
                    st.rerun()
            if st.button("💾 存为新题库", use_container_width=True):
                new_name = f"{st.session_state.active_bank}_错题本"
                if new_name in st.session_state.banks: new_name += f"_{int(time.time())}"
                new_qs = []
                for wq in prog['wrong']:
                    nq = wq.copy()
                    nq['user_answer'] = None
                    new_qs.append(nq)
                st.session_state.banks[new_name] = new_qs
                st.session_state.progress[new_name] = {"history": {}, "wrong": [], "current_idx": 0}
                st.session_state.active_bank = new_name
                st.session_state.filters[new_name] = list(set(q['type'] for q in new_qs))
                st.success(f"已切换至: {new_name}")
                time.sleep(1)
                save_state()
                st.rerun()

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
                st.success(f"导入 {len(qs)} 题")
                time.sleep(1)
                save_state()
                st.rerun()

    if st.session_state.active_bank:
        st.divider()
        with st.popover("🗑️ 删除", use_container_width=True):
            if st.button("🔴 确认"):
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
        """<div class="welcome-container">
            <div class="welcome-title">👋 欢迎使用</div>
            <p class="welcome-subtitle">ZenMode 专注刷题模式</p>
            <p style="color:#666; margin-bottom: 30px;">请点击左上角箭头，打开侧边栏导入题库开始学习</p>
            <div><span class="arrow-hint">👈</span><span class="welcome-hint">点击这里展开菜单</span></div>
        </div>""",
        unsafe_allow_html=True)
else:
    bk = st.session_state.active_bank
    full_qs = st.session_state.banks[bk]
    active_filters = st.session_state.filters.get(bk, [])
    qs = [q for q in full_qs if q['type'] in active_filters]

    if not qs:
        st.warning("⚠️ 无题目，请检查筛选。")
    else:
        pg = st.session_state.progress[bk]
        idx = pg['current_idx']
        total_q = len(qs)
        
        # 当索引超出范围时，表示已完成所有题目
        if idx >= total_q:
            idx = total_q
            pg['current_idx'] = idx  # 修复：同步更新进度状态

        # 计算显示的进度（完成时显示总数，否则显示当前题号）
        done_q = total_q if idx >= total_q else idx + 1
        wrong_q = len(pg['wrong'])

        st.markdown(f"""
        <div class="hud-container">
            <div class="hud-item" style="max-width: 40%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{bk}</div>
            <div style="display:flex; gap: 15px;">
                <div class="hud-item">进度 <span class="hud-value hud-accent">{min(done_q, total_q)}</span>/{total_q}</div>
                <div class="hud-item">错题 <span class="hud-value hud-warn">{wrong_q}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if idx >= len(qs):
            st.balloons()
            st.markdown(
                f"""<div class="completion-card">
                    <h2 style="font-size: 36px; margin-bottom: 20px;">🎉 恭喜完成!</h2>
                    <p style="font-size: 18px; color: #a0a0b0;">本轮共 <span style="color: #4ecdc4; font-weight: bold;">{total_q}</span> 题</p>
                    <p style="font-size: 18px; color: #a0a0b0;">错题 <span style="color: #ff6b6b; font-weight: bold;">{wrong_q}</span> 道</p>
                </div>""",
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
                    ans = q.get('answer', '')
                    
                    # Normalize user choice for comparison
                    normalized_user_choice = normalize_answer(user_choice)
                    normalized_ans = normalize_answer(ans)

                    is_cor = (normalized_user_choice == normalized_ans)
                    if is_cor:
                        feedback_placeholder.markdown(
                            f"""<div class="feedback-box feedback-success">✅ 回答正确！</div>""", unsafe_allow_html=True)
                        time.sleep(0.8)
                    else:
                        # Display original answer format if available
                        display_ans = q.get('answer', ans)
                        feedback_placeholder.markdown(
                            f"""<div class="feedback-box feedback-error">❌ 错误！正确答案是：{display_ans}</div>""",
                            unsafe_allow_html=True)
                        if not any(w.get('raw_content') == q.get('raw_content') for w in pg['wrong']):
                            wrong_q = q.copy()  # 保存问题的副本而不是引用
                            wrong_q['user_answer'] = user_choice
                            pg['wrong'].append(wrong_q)
                        time.sleep(1.5)

                    pg['current_idx'] += 1
                    save_state()
                    st.rerun()

            if c3.button("➡", use_container_width=True):
                pg['current_idx'] += 1
                save_state()
                st.rerun()