"""NL2BI Agent — Streamlit Web 界面"""
import os
import io
import uuid
import time
import json as json_mod
import http.client
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from io import BytesIO

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

API_HOST = "127.0.0.1"
API_PORT = 8000

def _api_request(method, path, body=None, timeout=30):
    """用 http.client 直接发请求，绕过 urllib 的代理自动检测"""
    conn = http.client.HTTPConnection(API_HOST, API_PORT, timeout=timeout)
    try:
        headers = {"Content-Type": "application/json"} if body else {}
        body_bytes = json_mod.dumps(body).encode("utf-8") if body else None
        conn.request(method, path, body=body_bytes, headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        return json_mod.loads(data) if data else None
    except Exception:
        return None
    finally:
        conn.close()

def api_get(path, timeout=3):
    return _api_request("GET", path, timeout=timeout)

def api_post(path, body, timeout=120):
    return _api_request("POST", path, body=body, timeout=timeout)

st.set_page_config(page_title="NL2BI Agent", page_icon="📊", layout="wide")

# ── Custom CSS ──
st.markdown("""
<style>
    /* ── Taste-Skill Applied: Streamlit BI Dashboard ── */
    /* Design Read: data-analytics tool, clean-functional, sans-serif */
    /* Dials: VARIANCE=5, MOTION=3, DENSITY=5 */

    /* Typography — avoid Inter (taste Section 4.1), use Geist fallback */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        color: #1a1a1a;
    }

    .main .block-container {
        padding-top: 1.25rem;
        padding-bottom: 0.75rem;
    }

    /* Card — one radius system: 10px (taste Section 4.4: all-soft) */
    .stContainer, [data-testid="stExpander"] {
        border-radius: 10px !important;
        border: 1px solid #e5e7eb !important;
    }

    /* Metric — clean elevation, tinted shadow (taste Section 4.4) */
    [data-testid="stMetric"] {
        background: #fafafa;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 0.75rem 1rem;
    }
    [data-testid="stMetric"] label {
        font-size: 0.78rem;
        color: #6b7280;
        font-weight: 500;
        letter-spacing: -0.01em;
    }

    /* Button — restrained accent, not AI-blue (taste Section 4.2: LILA RULE) */
    .stButton > button {
        border-radius: 10px;
        font-weight: 500;
        border: 1px solid #d1d5db;
        background: #f9fafb;
        color: #1f2937;
        transition: background 0.15s ease, border-color 0.15s ease;
    }
    .stButton > button:hover {
        background: #f3f4f6;
        border-color: #9ca3af;
    }
    .stButton > button[kind="primary"] {
        background: #1f2937;
        color: #ffffff;
        border-color: #1f2937;
    }
    .stButton > button[kind="primary"]:hover {
        background: #374151;
        border-color: #374151;
    }

    /* Input — labels above, clean border (taste Section 4.6) */
    [data-testid="stTextInput"] input {
        border-radius: 10px;
        border: 1.5px solid #d1d5db;
        padding: 0.65rem 0.9rem;
        font-size: 0.95rem;
        background: #fafafa;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #1f2937;
        box-shadow: 0 0 0 2px rgba(31,41,55,0.08);
        background: #ffffff;
    }

    /* Sidebar — neutral, not purple-adjacent (taste Section 4.2) */
    [data-testid="stSidebar"] {
        background: #fafafa;
        border-right: 1px solid #e5e7eb;
    }

    /* Dataframe — single radius system */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #e5e7eb;
    }

    /* Typography scale */
    h1 { font-weight: 700; font-size: 1.6rem; color: #111827; letter-spacing: -0.02em; }
    h2 { font-weight: 600; font-size: 1.2rem; color: #1f2937; letter-spacing: -0.01em; }
    h3 { font-weight: 600; font-size: 1.05rem; color: #374151; }
    .stCaption { color: #6b7280; font-size: 0.83rem; }

    /* Divider */
    hr { margin: 0.5rem 0; border-color: #e5e7eb; opacity: 0.6; }

    /* Spinner — dark monochrome accent (taste: one accent per page) */
    [data-testid="stSpinner"] { border-top-color: #1f2937; }

    /* Scroll */
    html { scroll-behavior: smooth; }

    /* Dark mode — respect system, maintain hierarchy parity (taste Section 6.C) */
    @media (prefers-color-scheme: dark) {
        html, body, [class*="css"] { color: #e5e7eb; }
        .stContainer, [data-testid="stExpander"] { border-color: #374151 !important; }
        [data-testid="stMetric"] {
            background: #1f2937;
            border-color: #374151;
        }
        [data-testid="stSidebar"] {
            background: #111827;
            border-right-color: #1f2937;
        }
        [data-testid="stTextInput"] input {
            background: #1f2937;
            border-color: #374151;
            color: #e5e7eb;
        }
        [data-testid="stTextInput"] input:focus {
            border-color: #6b7280;
            background: #111827;
        }
        .stButton > button {
            background: #1f2937;
            border-color: #374151;
            color: #d1d5db;
        }
        .stButton > button:hover {
            background: #374151;
            border-color: #4b5563;
        }
        .stButton > button[kind="primary"] {
            background: #e5e7eb;
            color: #111827;
            border-color: #e5e7eb;
        }
        [data-testid="stDataFrame"] { border-color: #374151; }
        h1 { color: #f3f4f6; }
        h2 { color: #e5e7eb; }
        h3 { color: #d1d5db; }
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
        <span style="font-size:1.8rem;">📊</span>
        <span style="font-weight:700;font-size:1.2rem;color:#0f172a;">NL2BI Agent</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption("自然语言驱动 · 智能数据分析")

    # Login
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    if not st.session_state.logged_in:
        with st.container(border=True):
            st.markdown("#### 🔐 登录")
            uname = st.text_input("用户名", value="demo", key="login_user")
            pwd = st.text_input("密码", type="password", value="demo123", key="login_pwd")
            if st.button("登 录", use_container_width=True, type="primary"):
                try:
                    r = api_post("/api/login", {"username": uname, "password": pwd}, timeout=5)
                    if r and r.get("success"):
                        st.session_state.logged_in = True
                        st.session_state.username = uname
                        st.rerun()
                    else:
                        st.error("用户名或密码错误")
                except Exception:
                    st.error("无法连接服务器")
        st.caption("账号: admin / admin123 或 demo / demo123")
        st.stop()

    st.success(f"👋 你好，{st.session_state.username}")

    if "session_id" not in st.session_state:
        st.session_state.session_id = f"sess_{uuid.uuid4().hex[:12]}"
    if "history" not in st.session_state:
        st.session_state.history = []

    # 连接状态
    with st.container(border=True):
        st.markdown("#### ⚙️ 服务状态")
        import socket
        api_alive = False
        try:
            s = socket.create_connection(("127.0.0.1", 8000), timeout=2)
            s.close()
            api_alive = True
        except Exception:
            pass

        if api_alive:
            st.markdown("🟢 服务正常　`API` · `DB` · `AI`")
        else:
            st.markdown("🔴 服务离线")

    # 历史记录
    st.markdown("#### 📝 历史记录")
    history_count = len(st.session_state.history)
    if history_count == 0:
        st.caption("暂无查询记录，去问一个问题吧 👇")

    for i, h in enumerate(reversed(st.session_state.history[-15:])):
        with st.expander(f"{h['query'][:30]}..." if len(h['query']) > 30 else h['query'], expanded=False):
            st.caption(f"⏱ {h.get('elapsed_ms', 0):.0f}ms · {h.get('row_count', 0)} 行")
            if h.get('sql'):
                st.code(h['sql'][:120], language="sql")

    if history_count > 0:
        c1, c2 = st.columns(2)
        if c1.button("🔄 清空", use_container_width=True):
            st.session_state.history = []
            st.session_state.session_id = f"sess_{uuid.uuid4().hex[:12]}"
            st.rerun()
        if c2.button("🚪 退出", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

# ── Main ──
st.markdown("""
<div style="margin-bottom:0.5rem;">
    <h1 style="margin-bottom:0.25rem;">💬 用中文提问，AI 帮你查数据</h1>
    <p style="color:#64748b;font-size:0.95rem;margin:0;">自动生成 SQL · 智能可视化 · 自然语言解读</p>
</div>
""", unsafe_allow_html=True)

# 快捷提问
if len(st.session_state.get("history", [])) == 0:
    st.markdown("##### 💡 试试这些问题：")
    examples = st.columns(4)
    sample_questions = [
        "有多少个客户？",
        "每个产品的销量排名",
        "退款金额最多的5个订单",
        "本月销售额是多少？",
    ]
    for idx, sq in enumerate(sample_questions):
        with examples[idx]:
            st.caption(sq)

# Input card
with st.container(border=True):
    col1, col2 = st.columns([7, 1])
    with col1:
        query = st.text_input(
            "查询输入",
            placeholder="输入你的数据问题，例如：上个月销售额最高的前 5 个产品是哪些？",
            label_visibility="collapsed",
            key="query_input",
        )
    with col2:
        go_btn = st.button("🚀 查 询", use_container_width=True, type="primary")

if go_btn and query.strip():
    with st.spinner("🤔 AI 正在分析中..."):
        data = api_post("/api/query",
            {"query": query.strip(), "session_id": st.session_state.session_id},
            timeout=120)
        if data is None:
            st.error("❌ 无法连接到 API 服务，请确认已启动: uvicorn src.main:app --port 8000")
        elif "detail" in data:
            st.error(f"请求失败: {data.get('detail', '未知错误')}")
        else:
                # ── Metrics row ──
                st.markdown("---")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("🎯 意图", data.get("intent", "?"))
                m2.metric("📋 行数", f"{data.get('row_count', 0):,}")
                m3.metric("⚡ 耗时", f"{data.get('elapsed_ms', 0):.0f}ms")
                m4.metric("🔒 安全", data.get("sql_risk_level", "?"))

                # ── SQL (collapsible) ──
                sql = data.get("generated_sql", "")
                if sql:
                    with st.expander("🔍 SQL 与解释", expanded=False):
                        st.code(sql, language="sql", line_numbers=False)
                        if data.get("sql_explanation"):
                            st.info(data['sql_explanation'])

                # ── Error ──
                if data.get("error"):
                    st.warning(f"⚠️ {data['error']}")

                # ── Results ──
                rows = data.get("rows", [])
                columns = data.get("columns", [])
                if rows and columns:
                    df = pd.DataFrame(rows, columns=columns)
                    # 自动将数字字符串转为数值类型
                    for col in df.columns:
                        try:
                            converted = pd.to_numeric(df[col], errors='coerce')
                            # 如果大部分值能转成数字，就替换
                            valid_pct = converted.notna().sum() / max(len(converted), 1)
                            if valid_pct > 0.5:
                                df[col] = converted
                        except Exception:
                            pass
                    num_cols = df.select_dtypes(include="number").columns.tolist()
                    non_num_cols = [c for c in df.columns if c not in num_cols]
                    # 找最佳分类列：跳过 ID 类、选第一个非数字非ID列
                    cat_col = None
                    for c in non_num_cols:
                        if 'id' not in c.lower():
                            cat_col = c
                            break
                    if cat_col is None and non_num_cols:
                        cat_col = non_num_cols[0]
                    # 找最佳数值列：跳过 ID 类
                    num_val = None
                    for n in num_cols:
                        if 'id' not in n.lower():
                            num_val = n
                            break
                    if num_val is None and num_cols:
                        num_val = num_cols[0]
                    n_categories = df[cat_col].nunique() if cat_col and cat_col in df.columns else 0

                    # ── Auto Chart (始终输出图表) ──
                    chart_type = data.get("chart_suggestion", {}).get("type", "auto")
                    row_count = len(rows)

                    if row_count == 1 and num_val:
                        # 单行结果 → 大数字卡片 + 迷你环形图
                        c1, c2 = st.columns([3, 2])
                        val = float(df[num_val].iloc[0])
                        label = df[cat_col].iloc[0] if cat_col and cat_col in df.columns else str(columns[0])
                        c1.metric(label=str(label)[:40], value=f"{val:,.2f}")
                        fig = go.Figure(go.Indicator(
                            mode="gauge+number", value=val,
                            title={"text": num_val[:20]},
                            gauge={"axis": {"range": [0, max(val * 1.5, 1)]}},
                        ))
                        fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
                        c2.plotly_chart(fig, use_container_width=True)

                    elif row_count >= 2 and row_count <= 30:
                        df_chart = df.sort_values(num_val, ascending=False) if num_val else df

                        if chart_type == "pie" and 2 <= n_categories <= 8 and num_val:
                            fig = px.pie(df_chart.head(8), names=cat_col, values=num_val,
                                         title=f"📊 {num_val} 分布")
                            st.plotly_chart(fig, use_container_width=True)

                        elif chart_type == "line" and num_val:
                            x_col = cat_col or df.columns[0]
                            fig = px.line(df_chart, x=x_col, y=num_val,
                                          title=f"📈 {num_val} 趋势", markers=True)
                            st.plotly_chart(fig, use_container_width=True)

                        elif num_val and n_categories >= 2:
                            if n_categories <= 12:
                                fig = px.bar(df_chart, x=cat_col, y=num_val,
                                             title=f"📊 {num_val} 排名",
                                             color=num_val, color_continuous_scale="Blues")
                            else:
                                fig = px.bar(df_chart.head(20), y=cat_col, x=num_val,
                                             title=f"📊 {num_val} 排名（Top 20）",
                                             orientation='h', color=num_val,
                                             color_continuous_scale="Blues")
                            st.plotly_chart(fig, use_container_width=True)

                        elif len(num_cols) >= 2:
                            # 多数值列 → 并排柱状图
                            fig = px.bar(df_chart, x=df_chart.columns[0], y=num_cols[:3],
                                         title="📊 数据概览", barmode="group")
                            st.plotly_chart(fig, use_container_width=True)

                        else:
                            # 兜底：用索引画柱状图
                            df_plot = df.reset_index()
                            x_col = df_plot.columns[0]
                            y_col = num_cols[0] if num_cols else df_plot.columns[-1]
                            fig = px.bar(df_plot.head(20), x=x_col, y=y_col,
                                         title=f"📊 {y_col} 概览")
                            st.plotly_chart(fig, use_container_width=True)

                    elif row_count > 30:
                        # 大量数据 → Top 10 + 说明
                        if num_val and n_categories >= 2:
                            df_chart = df.sort_values(num_val, ascending=False)
                            fig = px.bar(df_chart.head(10), y=cat_col, x=num_val,
                                         title=f"📊 {num_val} Top 10",
                                         orientation='h', color=num_val,
                                         color_continuous_scale="Blues")
                            st.plotly_chart(fig, use_container_width=True)
                        st.caption(f"💡 共 {row_count} 条数据，仅展示前 10 项。可加筛选条件缩小范围。")

                    # ── Quick Stats ──
                    if num_cols:
                        stats_cols = st.columns(min(len(num_cols), 4))
                        for i, nc in enumerate(num_cols[:4]):
                            vals = df[nc].dropna()
                            if len(vals) > 0 and not vals.isnull().all():
                                try:
                                    stats_cols[i].metric(
                                        f"📊 {nc}",
                                        f"{float(vals.mean()):,.1f}",
                                    )
                                except Exception:
                                    pass

                    # Table
                    st.subheader("📋 查询结果")
                    st.dataframe(df, use_container_width=True)

                    # Excel download
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='查询结果')
                    st.download_button(
                        label="📥 下载 Excel",
                        data=output.getvalue(),
                        file_name=f"NL2BI_{time.strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                # ── Report Results ──
                report_data = data.get("report_data", [])
                if report_data and len(report_data) > 1:
                    st.subheader(f"📈 报表结果（{len(report_data)} 个指标）")
                    rcols = st.columns(min(len(report_data), 3))
                    for i, rd in enumerate(report_data):
                        with rcols[i % 3]:
                            q = rd.get("question", f"指标{i+1}")
                            n = rd.get("row_count", 0)
                            err = rd.get("error", "")
                            rr = rd.get("rows", [])
                            rc = rd.get("columns", [])

                            if err:
                                st.warning(f"**{q}**\n\n{err}")
                                continue
                            if n == 0:
                                st.info(f"**{q}**\n\n暂无匹配数据")
                                continue

                            with st.container(border=True):
                                st.caption(q)
                                st.metric("结果", f"{n} 条")
                                if rr and rc and len(rc) >= 2:
                                    try:
                                        pdf = pd.DataFrame(rr, columns=rc)
                                        for c in pdf.columns:
                                            pdf[c] = pd.to_numeric(pdf[c], errors='coerce')
                                        ncols = pdf.select_dtypes(include='number').columns.tolist()
                                        ccols = [c for c in pdf.columns if c not in ncols and 'id' not in c.lower()]
                                        if ncols and ccols:
                                            fig = px.bar(pdf, x=ccols[0], y=ncols[0],
                                                         height=180, color_discrete_sequence=["#1f77b4"])
                                            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0),
                                                              xaxis_tickangle=-45, font_size=10)
                                            st.plotly_chart(fig, use_container_width=True)
                                        else:
                                            st.dataframe(pdf, use_container_width=True, hide_index=True)
                                    except Exception:
                                        st.dataframe(pd.DataFrame(rr, columns=rc), use_container_width=True, hide_index=True)

                # ── Interpretation ──
                interp = data.get("interpretation", "")
                if interp:
                    with st.container(border=True):
                        st.markdown("#### 💡 AI 解读")
                        st.markdown(interp.replace("## ", "### "))

                # ── Follow-ups ──
                fuq = data.get("follow_up_questions", [])
                if fuq:
                    st.markdown("##### 💭 继续追问")
                    cols = st.columns(min(len(fuq), 3))
                    for i, q in enumerate(fuq[:6]):
                        with cols[i % 3]:
                            st.markdown(f"""
                            <div class="card" style="padding:0.6rem 1rem;cursor:pointer;font-size:0.9rem;">
                                {q}
                            </div>
                            """, unsafe_allow_html=True)

                # ── Highlights ──
                highlights = data.get("highlights", [])
                if highlights:
                    with st.expander("🔦 关键发现", expanded=True):
                        for h in highlights:
                            st.markdown(f"✨ {h}")

                # Record history
                st.session_state.history.append({
                    "query": query.strip(),
                    "intent": data.get("intent", ""),
                    "sql": sql,
                    "elapsed_ms": data.get("elapsed_ms", 0),
                    "row_count": data.get("row_count", 0),
                })

# (已移除 httpx 异常处理，改用 urllib)

# ── Footer ──
st.divider()
f1, f2, f3 = st.columns([2, 1, 1])
f1.caption("🛡️ 只读查询 · 三层安全校验 · 混合模型架构")
f2.caption("⚡ LangGraph 编排 · 9.9x 缓存加速")
f3.caption("💰 每次查询 < ¥0.002")
