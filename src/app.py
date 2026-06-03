"""NL2BI Agent — Streamlit Web 界面"""
import os
import uuid
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import httpx

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

st.set_page_config(page_title="NL2BI Agent", page_icon="📊", layout="wide")

# ── Sidebar ──
with st.sidebar:
    st.title("📊 NL2BI Agent")
    st.caption("企业级自然语言数据分析")
    st.divider()

    if "session_id" not in st.session_state:
        st.session_state.session_id = f"sess_{uuid.uuid4().hex[:12]}"
    if "history" not in st.session_state:
        st.session_state.history = []

    st.subheader("⚙️ 连接状态")
    try:
        resp = httpx.get("http://localhost:8000/api/health", timeout=5)
        health = resp.json()
        st.success("🟢 API 服务正常")
        st.caption(f"数据库: {health['database']} | Ollama: {health['ollama']} | ChromaDB: {health['chromadb']}")
    except Exception:
        st.error("🔴 API 未启动")

    st.subheader("📝 历史记录")
    for i, h in enumerate(reversed(st.session_state.history[-20:])):
        with st.expander(f"Q{i+1}: {h['query'][:25]}...", expanded=False):
            st.caption(f"意图: {h.get('intent', '?')} | {h.get('elapsed_ms', 0):.0f}ms")
            st.caption(f"SQL: {h.get('sql', '')[:80]}...")

    if st.button("🔄 清空历史", use_container_width=True):
        st.session_state.history = []
        st.session_state.session_id = f"sess_{uuid.uuid4().hex[:12]}"
        st.rerun()

# ── Main ──
st.title("📊 NL2BI — 自然语言数据分析 Agent")
st.caption("用中文提问，AI 自动查数据库、画图、出报告。")

# Input
col1, col2 = st.columns([6, 1])
with col1:
    query = st.text_input(
        "💬 输入你的数据问题",
        placeholder="例如：哪个区域的销售额最高？客单价最低的渠道是哪个？退款率最高的产品类目？",
        label_visibility="collapsed",
    )
with col2:
    go_btn = st.button("🚀 查询", use_container_width=True, type="primary")

if go_btn and query.strip():
    with st.spinner("🤔 AI 正在分析中..."):
        try:
            resp = httpx.post(
                "http://localhost:8000/api/query",
                json={"query": query.strip(), "session_id": st.session_state.session_id},
                timeout=120.0,
            )
            if resp.status_code != 200:
                st.error(f"请求失败: {resp.json().get('detail', '未知错误')}")
            else:
                data = resp.json()

                # ── Metrics row ──
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("🎯 意图", data.get("intent", "?"))
                m2.metric("📋 返回行数", f"{data.get('row_count', 0):,}")
                m3.metric("⚡ 耗时", f"{data.get('elapsed_ms', 0):.0f}ms")
                m4.metric("🔒 安全等级", data.get("sql_risk_level", "?"))
                m5.metric("📝 会话", data["session_id"][:8])

                # ── SQL (collapsible) ──
                sql = data.get("generated_sql", "")
                if sql:
                    with st.expander("🔍 查看生成的 SQL", expanded=False):
                        st.code(sql, language="sql")
                        if data.get("sql_explanation"):
                            st.caption(f"💡 {data['sql_explanation']}")

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
                    # 找最佳分类列（跳过 ID 类列名）
                    cat_col = None
                    for c in columns:
                        if c not in num_cols and 'id' not in c.lower():
                            cat_col = c
                            break
                    if cat_col is None:
                        cat_col = columns[0] if columns[0] not in num_cols else (columns[1] if len(columns) > 1 else None)
                    num_val = num_cols[0] if num_cols else (num_cols[1] if len(num_cols) > 1 else None)
                    # 跳过 ID 类数值列
                    for n in num_cols:
                        if 'id' not in n.lower():
                            num_val = n
                            break
                    n_categories = df[cat_col].nunique() if cat_col else 0

                    # ── Auto Chart ──
                    chart_type = data.get("chart_suggestion", {}).get("type", "table")

                    should_chart = (
                        len(columns) >= 2
                        and num_val
                        and n_categories >= 2
                    )

                    if should_chart:
                        # Sort by numeric value for better visualization
                        df_chart = df.sort_values(num_val, ascending=False)

                        if chart_type == "pie" and 2 <= n_categories <= 8:
                            fig = px.pie(df_chart.head(8), names=cat_col, values=num_val,
                                         title=f"📊 {num_val} 分布")
                            st.plotly_chart(fig, use_container_width=True)

                        elif chart_type == "line" and len(columns) >= 2:
                            fig = px.line(df_chart, x=cat_col or columns[0], y=num_val,
                                          title=f"📈 {num_val} 趋势", markers=True)
                            st.plotly_chart(fig, use_container_width=True)

                        elif n_categories <= 15:
                            fig = px.bar(df_chart, x=cat_col, y=num_val,
                                         title=f"📊 {num_val} 排名",
                                         color=num_val, color_continuous_scale="Blues")
                            st.plotly_chart(fig, use_container_width=True)

                        elif n_categories <= 30:
                            # Horizontal bar for medium datasets
                            fig = px.bar(df_chart.head(20), y=cat_col, x=num_val,
                                         title=f"📊 {num_val} 排名（Top 20）",
                                         orientation='h', color=num_val,
                                         color_continuous_scale="Blues")
                            st.plotly_chart(fig, use_container_width=True)
                            if n_categories > 20:
                                st.caption(f"⚠️ 共 {n_categories} 项，仅展示前 20 项。可加筛选条件缩小范围。")
                        else:
                            # Too many categories — just table + top-N mini chart
                            st.subheader(f"📊 {num_val} Top 10 排名")
                            fig = px.bar(df_chart.head(10), y=cat_col, x=num_val,
                                         title=f"Top 10 {num_val}",
                                         orientation='h', color=num_val,
                                         color_continuous_scale="Blues")
                            st.plotly_chart(fig, use_container_width=True)
                            st.caption(f"💡 共 {n_categories} 项，仅展示前 10。")

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

                # ── Interpretation ──
                interp = data.get("interpretation", "")
                if interp:
                    st.info(f"**📊 AI 解读：** {interp}")

                # ── Follow-ups ──
                fuq = data.get("follow_up_questions", [])
                if fuq:
                    st.subheader("💡 你可以继续问")
                    cols = st.columns(min(len(fuq), 3))
                    for i, q in enumerate(fuq[:6]):
                        with cols[i % 3]:
                            st.caption(f"• {q}")

                # ── Highlights ──
                highlights = data.get("highlights", [])
                if highlights:
                    with st.expander("🔦 关键发现"):
                        for h in highlights:
                            st.markdown(f"- {h}")

                # Record history
                st.session_state.history.append({
                    "query": query.strip(),
                    "intent": data.get("intent", ""),
                    "sql": sql,
                    "elapsed_ms": data.get("elapsed_ms", 0),
                    "row_count": data.get("row_count", 0),
                })

        except httpx.ConnectError:
            st.error("❌ 无法连接到 API 服务，请确认已启动: `uvicorn src.main:app --port 8000`")
        except Exception as e:
            st.error(f"❌ 出错了: {e}")

# ── Footer ──
st.divider()
st.caption("🛡️ 只读查询 · 三层安全校验 · 本地+云端混合模型 · 每次查询 < 0.002 元")
