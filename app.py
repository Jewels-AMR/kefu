import streamlit as st
import pandas as pd
import io
import sys
import traceback
import os
from pathlib import Path
from datetime import datetime

try:
    _root = Path(os.path.dirname(os.path.abspath(__file__)))
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    if str(_root.parent) not in sys.path:
        sys.path.insert(0, str(_root.parent))
    
    from src.data_loader import DataLoader
    from src.analyzer import TicketAnalyzer
    from src.anomaly_detector import AnomalyDetector
    from src.visualizer import Visualizer
    from src.ai_insights import AIInsightsGenerator
except Exception as e:
    st.error(f"导入错误: {e}")
    st.code(traceback.format_exc())
    st.stop()

st.set_page_config(
    page_title="客服工单智能分析工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 客服工单智能分析工具")
st.markdown("上传工单数据文件，自动分析趋势、检测异常、生成可视化报告")

with st.sidebar:
    st.header("⚙️ 配置")

    api_key = st.text_input(
        "API Key（可选）",
        type="password",
        help="填入后启用 AI 智能解读，留空则使用规则引擎",
        key="api_key"
    )

    if api_key:
        st.success("AI 解读已启用 ✅")
    else:
        st.info("当前使用规则引擎模式")

    st.divider()

    st.subheader("异常检测阈值")
    sla_hours = st.number_input("SLA时限（小时）", value=24, min_value=1)
    std_threshold = st.number_input("标准差倍数阈值", value=2.0, min_value=1.0, max_value=5.0, step=0.5)
    ring_threshold = st.number_input("环比增长阈值", value=0.5, min_value=0.1, max_value=2.0, step=0.1)

    st.divider()
    st.markdown("### 📝 数据格式说明")
    st.markdown("""
    支持 JSON / CSV / Excel 格式，建议包含以下字段：
    - **issue_type**: 问题类型
    - **severity/priority**: 严重程度
    - **created_at**: 创建时间
    - **resolution_time_hours**: 处理时长（小时）
    - **satisfaction**: 满意度（1-5分）
    - **channel**: 来源渠道
    - **is_resolved**: 是否已解决
    """)

uploaded_file = st.file_uploader(
    "📂 上传工单数据文件",
    type=['json', 'csv', 'xlsx', 'xls'],
    help="支持 JSON、CSV、Excel 格式"
)

if uploaded_file:
    file_details = {"文件名": uploaded_file.name, "大小": f"{uploaded_file.size / 1024:.1f} KB"}
    st.write(file_details)

    file_bytes = uploaded_file.read()
    file_suffix = Path(uploaded_file.name).suffix

    try:
        if file_suffix == '.json':
            df = pd.read_json(io.BytesIO(file_bytes))
        elif file_suffix in ['.csv', '.CSV']:
            df = pd.read_csv(io.BytesIO(file_bytes))
        elif file_suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            st.error(f"不支持的文件格式: {file_suffix}")
            st.stop()

        st.success(f"✅ 文件加载成功，共 {len(df)} 条工单记录")
        st.write("**数据预览：**")
        st.dataframe(df.head(5), use_container_width=True)

        with st.spinner("正在分析数据..."):
            loader = DataLoader(uploaded_file.name)
            loader.df = df
            loader.df = loader._standardize_columns(loader.df)
            loader.df = loader._parse_dates(loader.df)

            summary = loader.get_summary()

            analyzer = TicketAnalyzer(loader.df)
            analysis_result = analyzer.run_full_analysis()

            detector = AnomalyDetector(
                loader.df,
                sla_hours=sla_hours,
                std_threshold=std_threshold,
                ring_threshold=ring_threshold
            )
            anomaly_list = detector.detect_all()
            anomaly_summary = detector.get_anomaly_summary()

            visualizer = Visualizer("output")
            charts = visualizer.create_all_charts(analysis_result, anomaly_summary)

            st.success("✅ 分析完成！")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 趋势分析",
            "📊 分类分析",
            "⚠️ 异常检测",
            "🎯 满意度 & 渠道",
            "🤖 AI 智能解读"
        ])

        with tab1:
            st.header("趋势分析")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总工单数", analysis_result['total_tickets'])
            with col2:
                if summary.get('date_range'):
                    st.metric("日期范围", f"{summary['date_range']['start'].strftime('%m-%d')} 至 {summary['date_range']['end'].strftime('%m-%d')}")
            with col3:
                if summary.get('avg_satisfaction') is not None:
                    st.metric("平均满意度", f"{summary['avg_satisfaction']} 分")
            with col4:
                if summary.get('resolution_rate') is not None:
                    st.metric("解决率", f"{summary['resolution_rate']}%")

            st.divider()

            if 'time_trend' in charts:
                st.plotly_chart(charts['time_trend'], use_container_width=True)

            if 'hourly' in charts:
                st.plotly_chart(charts['hourly'], use_container_width=True)

        with tab2:
            st.header("分类分析")

            col1, col2 = st.columns(2)

            with col1:
                if 'issue_types' in charts:
                    st.plotly_chart(charts['issue_types'], use_container_width=True)

            with col2:
                if 'severity' in charts:
                    st.plotly_chart(charts['severity'], use_container_width=True)

            if 'heatmap' in charts:
                st.plotly_chart(charts['heatmap'], use_container_width=True)

            if 'resolution' in charts:
                st.plotly_chart(charts['resolution'], use_container_width=True)

            if 'resolution_rate' in charts:
                st.plotly_chart(charts['resolution_rate'], use_container_width=True)

        with tab3:
            st.header("⚠️ 异常信号检测")

            if anomaly_summary['total'] == 0:
                st.success("✅ 当前未检测到明显异常信号")
            else:
                st.warning(f"共检测到 **{anomaly_summary['total']}** 个异常信号")

                col1, col2, col3 = st.columns(3)
                with col1:
                    by_sev = anomaly_summary.get('by_severity', {})
                    st.metric("🔴 高危", by_sev.get('high', 0))
                with col2:
                    st.metric("🟡 中等", by_sev.get('medium', 0))
                with col3:
                    st.metric("🟢 低危", by_sev.get('low', 0))

                if 'anomaly' in charts:
                    st.plotly_chart(charts['anomaly'], use_container_width=True)

                st.subheader("异常详情列表")
                for idx, a in enumerate(anomaly_summary['anomalies'], 1):
                    severity_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(a['severity'], '⚪')
                    with st.expander(f"{severity_icon} #{idx} [{a['type']}] {a['description'][:50]}..."):
                        st.markdown(f"**描述**: {a['description']}")
                        st.markdown(f"**建议**: {a['recommendation']}")
                        with st.expander("查看判断依据"):
                            st.json(a['evidence'])

        with tab4:
            st.header("满意度 & 渠道分析")

            col1, col2 = st.columns(2)

            with col1:
                if 'satisfaction' in charts:
                    st.plotly_chart(charts['satisfaction'], use_container_width=True)

                if analysis_result['satisfaction'].get('correlation_resolution') is not None:
                    corr = analysis_result['satisfaction']['correlation_resolution']
                    strength = '强' if abs(corr) > 0.5 else '中等' if abs(corr) > 0.3 else '弱'
                    direction = '负' if corr < 0 else '正'
                    st.info(f"📌 满意度与处理时长相关性: {corr}（{strength}{direction}相关）")

            with col2:
                if 'channel' in charts:
                    st.plotly_chart(charts['channel'], use_container_width=True)

        with tab5:
            st.header("🤖 AI 智能解读")

            insights_gen = AIInsightsGenerator()
            insights_gen.available = bool(api_key)

            if not api_key:
                st.info("💡 未配置 API Key，以下为规则引擎生成的解读。配置 API Key 可获得更智能的分析。")

            with st.spinner("正在生成智能解读..."):
                insights = insights_gen.generate_insights(analysis_result, anomaly_summary)

            st.markdown(insights)

            st.divider()
            st.markdown("### 📋 关键发现摘要")

            findings = []

            issue_types_data = analysis_result.get('issue_types', {})
            if issue_types_data.get('top_types') is not None:
                top = issue_types_data['top_types']
                findings.append(f"- **高频问题**: {top.iloc[0]['issue_type']}（{top.iloc[0]['count']} 条，{top.iloc[0]['percentage']}%）")

            severity_data = analysis_result.get('severity', {})
            if severity_data.get('high_severity_ratio') is not None:
                ratio = severity_data['high_severity_ratio']
                icon = "⚠️" if ratio > 40 else "✅"
                findings.append(f"- **高优工单占比**: {ratio}% {icon}")

            satisfaction_data = analysis_result.get('satisfaction', {})
            if satisfaction_data.get('avg_score') is not None:
                avg = satisfaction_data['avg_score']
                icon = "😞" if avg < 3 else "😐" if avg < 4 else "😊"
                findings.append(f"- **平均满意度**: {avg} 分 {icon}")

            resolution_data = analysis_result.get('resolution_efficiency', {})
            if resolution_data.get('avg_resolution_hours') is not None:
                findings.append(f"- **平均处理时长**: {resolution_data['avg_resolution_hours']} 小时")

            resolution_rate_data = analysis_result.get('resolution_rate', {})
            if resolution_rate_data.get('overall_rate') is not None:
                findings.append(f"- **工单解决率**: {resolution_rate_data['overall_rate']}%")

            for finding in findings:
                st.markdown(finding)

    except Exception as e:
        st.error(f"❌ 分析失败: {e}")
        import traceback
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())

else:
    st.info("👆 请上传工单数据文件开始分析")

    st.markdown("---")
    st.markdown("## 📖 使用说明")
    st.markdown("""
    1. **点击上方区域**上传工单数据文件（支持 JSON / CSV / Excel）
    2. **可选配置**：在侧边栏填入 API Key 启用 AI 智能解读
    3. **查看分析**：分析完成后可在各个标签页查看结果
    4. **异常关注**：⚠️ 标签页显示所有检测到的异常信号和建议

    ### 📊 分析维度
    - **时间趋势**：每日工单量变化、环比增长、时段分布
    - **分类分析**：问题类型分布、严重程度、处理效率、解决率
    - **异常检测**：突增异常、聚集爆发、超时异常、满意度异常等
    - **满意度 & 渠道**：用户满意度分析、各渠道表现
    - **AI 解读**：智能趋势解读与改进建议
    """)

    st.markdown("---")
    st.markdown("### 💡 快速测试数据格式")
    st.code("""
{
  "ticket_id": "T001",
  "created_at": "2024-06-01 10:00:00",
  "category": "支付问题",
  "description": "无法完成支付",
  "priority": "高",
  "resolution_time_hours": 4.5,
  "satisfaction": 2,
  "channel": "在线",
  "is_resolved": true
}
""", language="json")
