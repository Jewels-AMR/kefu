import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import DataLoader
from src.analyzer import TicketAnalyzer
from src.anomaly_detector import AnomalyDetector
from src.visualizer import Visualizer
from src.ai_insights import AIInsightsGenerator
from config import OUTPUT_DIR, REPORT_FILENAME


def generate_report(
    data_path: str,
    output_dir: str = None,
    use_ai: bool = True
) -> str:
    if output_dir is None:
        output_dir = OUTPUT_DIR

    print("=" * 60)
    print("客服工单数据分析工具")
    print("=" * 60)
    print()

    print(f"[1/5] 加载数据: {data_path}")
    loader = DataLoader(data_path)
    df = loader.load()
    summary = loader.get_summary()
    print(f"      数据概览: {summary['total_tickets']} 条工单")
    if summary.get('date_range'):
        print(f"      日期范围: {summary['date_range']['start']} 至 {summary['date_range']['end']}")
    print()

    print("[2/5] 执行多维度分析...")
    analyzer = TicketAnalyzer(df)
    analysis_result = analyzer.run_full_analysis()
    print(f"      分析完成: 8个维度")
    print()

    print("[3/5] 检测异常信号...")
    detector = AnomalyDetector(df)
    detector.detect_all()
    anomaly_summary = detector.get_anomaly_summary()
    print(f"      发现异常: {anomaly_summary['total']} 个")
    if anomaly_summary['total'] > 0:
        for a in anomaly_summary['anomalies'][:5]:
            print(f"        [{a['severity'].upper()}] {a['type']}: {a['description'][:60]}...")
    print()

    print("[4/5] 生成可视化图表...")
    visualizer = Visualizer(output_dir)
    charts = visualizer.create_all_charts(analysis_result, anomaly_summary)
    chart_paths = visualizer.save_charts(charts)
    print(f"      生成图表: {len(chart_paths)} 个")
    for name, path in chart_paths.items():
        print(f"        - {name}: {path}")
    print()

    print("[5/5] 生成分析报告...")
    insights_gen = AIInsightsGenerator()
    ai_available = insights_gen.available

    if use_ai and ai_available:
        print("      AI 解读: 启用")
    else:
        print("      AI 解读: 未启用（使用规则引擎）")

    ai_insights = insights_gen.generate_insights(analysis_result, anomaly_summary)

    report_content = build_markdown_report(
        summary,
        analysis_result,
        anomaly_summary,
        chart_paths,
        ai_insights,
        ai_available
    )

    output_path = Path(output_dir) / REPORT_FILENAME
    output_path.write_text(report_content, encoding='utf-8')
    print(f"      报告已生成: {output_path}")
    print()

    print("=" * 60)
    print("分析完成！")
    print(f"报告路径: {output_path}")
    print("=" * 60)

    return str(output_path)


def build_markdown_report(
    data_summary: dict,
    analysis_result: dict,
    anomaly_summary: dict,
    chart_paths: dict,
    ai_insights: str,
    ai_available: bool
) -> str:
    lines = []
    lines.append("# 📊 客服工单数据分析报告")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**总工单数**: {data_summary['total_tickets']}")
    lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## 一、数据概览")
    lines.append("")

    if data_summary.get('date_range'):
        lines.append(f"- **日期范围**: {data_summary['date_range']['start']} 至 {data_summary['date_range']['end']}")

    if data_summary.get('issue_types'):
        lines.append(f"- **问题类型数**: {len(data_summary['issue_types'])} 种")
        lines.append(f"- **问题类型**: {', '.join(data_summary['issue_types'])}")

    if data_summary.get('severity_levels'):
        lines.append(f"- **严重程度**: {', '.join(data_summary['severity_levels'])}")

    if data_summary.get('channels'):
        lines.append(f"- **来源渠道**: {', '.join(data_summary['channels'])}")

    if data_summary.get('avg_satisfaction') is not None:
        lines.append(f"- **平均满意度**: {data_summary['avg_satisfaction']} 分")

    if data_summary.get('resolution_rate') is not None:
        lines.append(f"- **工单解决率**: {data_summary['resolution_rate']}%")

    lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## 二、趋势分析")
    lines.append("")

    time_trend = analysis_result.get('time_trend', {})

    if time_trend.get('daily_counts') is not None:
        lines.append("### 2.1 时间趋势")
        lines.append("")
        daily = time_trend['daily_counts']
        lines.append("| 日期 | 工单数 |")
        lines.append("|------|--------|")
        for _, row in daily.iterrows():
            lines.append(f"| {row['date']} | {row['count']} |")
        lines.append("")

        if 'time_trend' in chart_paths:
            lines.append(f"📈 [查看时间趋势图表]({chart_paths['time_trend']})")
            lines.append("")

    if time_trend.get('hourly_counts') is not None:
        lines.append("### 2.2 时段分布")
        lines.append("")
        hourly = time_trend['hourly_counts']
        lines.append("| 时段 | 工单数 |")
        lines.append("|------|--------|")
        for _, row in hourly.iterrows():
            lines.append(f"| {row['hour']}:00 | {row['count']} |")
        lines.append("")

        if 'hourly' in chart_paths:
            lines.append(f"📈 [查看时段分布图]({chart_paths['hourly']})")
            lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## 三、问题类型分析")
    lines.append("")

    issue_types = analysis_result.get('issue_types', {})

    if issue_types.get('type_distribution') is not None:
        lines.append("### 3.1 类型分布")
        lines.append("")
        type_dist = issue_types['type_distribution']
        lines.append("| 排名 | 问题类型 | 数量 | 占比 |")
        lines.append("|------|----------|------|------|")
        for idx, (_, row) in enumerate(type_dist.iterrows(), 1):
            lines.append(f"| {idx} | {row['issue_type']} | {row['count']} | {row['percentage']}% |")
        lines.append("")

        if 'issue_types' in chart_paths:
            lines.append(f"🥧 [查看问题类型分布图]({chart_paths['issue_types']})")
            lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## 四、严重程度分析")
    lines.append("")

    severity = analysis_result.get('severity', {})

    if severity.get('severity_distribution') is not None:
        lines.append("### 4.1 严重程度分布")
        lines.append("")
        sev_dist = severity['severity_distribution']
        lines.append("| 严重程度 | 数量 | 占比 |")
        lines.append("|----------|------|------|")
        for _, row in sev_dist.iterrows():
            lines.append(f"| {row['severity']} | {row['count']} | {row['percentage']}% |")
        lines.append("")

        if severity.get('high_severity_ratio') is not None:
            lines.append(f"- **高优工单占比**: {severity['high_severity_ratio']}%")
            lines.append("")

        if 'severity' in chart_paths:
            lines.append(f"📊 [查看严重程度分布图]({chart_paths['severity']})")
            lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## 五、处理效率分析")
    lines.append("")

    resolution = analysis_result.get('resolution_efficiency', {})

    if resolution.get('avg_resolution_hours') is not None:
        lines.append(f"- **平均处理时长**: {resolution['avg_resolution_hours']} 小时")
        lines.append("")

    if resolution.get('sla_compliance') is not None:
        sla = resolution['sla_compliance']
        lines.append(f"- **SLA 达标率**: {sla['compliance_rate']}%（SLA: {sla['sla_hours']}小时）")
        lines.append(f"- **达标工单**: {sla['compliant_count']} 条")
        lines.append(f"- **超时工单**: {sla['overdue_count']} 条")
        lines.append("")

    if resolution.get('resolution_by_type') is not None:
        lines.append("### 5.1 各类型处理效率")
        lines.append("")
        by_type = resolution['resolution_by_type']
        lines.append("| 问题类型 | 平均时长(小时) | 中位数(小时) | 工单数 |")
        lines.append("|----------|----------------|--------------|--------|")
        for _, row in by_type.iterrows():
            lines.append(f"| {row['issue_type']} | {row['mean']} | {row['median']} | {int(row['count'])} |")
        lines.append("")

    if 'resolution' in chart_paths:
        lines.append(f"⏱️ [查看处理效率图]({chart_paths['resolution']})")
        lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## 六、满意度分析")
    lines.append("")

    satisfaction = analysis_result.get('satisfaction', {})

    if satisfaction.get('avg_score') is not None:
        lines.append(f"- **整体平均满意度**: {satisfaction['avg_score']} 分")
        lines.append("")

    if satisfaction.get('distribution') is not None:
        lines.append("### 6.1 满意度分布")
        lines.append("")
        dist = satisfaction['distribution']
        lines.append("| 评分 | 数量 | 占比 |")
        lines.append("|------|------|------|")
        for _, row in dist.iterrows():
            lines.append(f"| {int(row['score'])} 分 | {row['count']} | {row['percentage']}% |")
        lines.append("")

    if satisfaction.get('by_type') is not None:
        lines.append("### 6.2 各类型满意度")
        lines.append("")
        by_type = satisfaction['by_type']
        lines.append("| 问题类型 | 平均分 | 中位数 | 工单数 |")
        lines.append("|----------|--------|--------|--------|")
        for _, row in by_type.iterrows():
            lines.append(f"| {row['issue_type']} | {row['mean']} | {row['median']} | {int(row['count'])} |")
        lines.append("")

    if satisfaction.get('correlation_resolution') is not None:
        corr = satisfaction['correlation_resolution']
        strength = '强' if abs(corr) > 0.5 else '中等' if abs(corr) > 0.3 else '弱'
        direction = '负' if corr < 0 else '正'
        lines.append(f"- **满意度与处理时长相关性**: {corr}（{strength}{direction}相关）")
        lines.append("")

    if satisfaction.get('low_score_tickets') is not None:
        lines.append("### 6.3 低分工单详情")
        lines.append("")
        lines.append("| 工单ID | 类型 | 严重度 | 满意度 | 描述 |")
        lines.append("|--------|------|--------|--------|------|")
        for _, row in satisfaction['low_score_tickets'].iterrows():
            lines.append(f"| {row['ticket_id']} | {row['issue_type']} | {row['severity']} | {row['satisfaction']} | {str(row['description'])[:30]}... |")
        lines.append("")

    if 'satisfaction' in chart_paths:
        lines.append(f"⭐ [查看满意度分析图]({chart_paths['satisfaction']})")
        lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## 七、渠道分析")
    lines.append("")

    channel = analysis_result.get('channel', {})

    if channel.get('distribution') is not None:
        lines.append("### 7.1 渠道分布")
        lines.append("")
        dist = channel['distribution']
        lines.append("| 渠道 | 数量 | 占比 |")
        lines.append("|------|------|------|")
        for _, row in dist.iterrows():
            lines.append(f"| {row['channel']} | {row['count']} | {row['percentage']}% |")
        lines.append("")

    if channel.get('by_severity') is not None:
        lines.append("### 7.2 各渠道严重程度分布")
        lines.append("")
        by_sev = channel['by_severity'].reset_index()
        lines.append("| 渠道 | " + " | ".join(by_sev.columns[1:]) + " |")
        lines.append("|------|" + "|".join(["------" for _ in by_sev.columns[1:]]) + "|")
        for _, row in by_sev.iterrows():
            lines.append("| " + " | ".join([str(x) for x in row.values]) + " |")
        lines.append("")

    if channel.get('satisfaction_by_channel') is not None:
        lines.append("### 7.3 各渠道满意度")
        lines.append("")
        sat_ch = channel['satisfaction_by_channel']
        lines.append("| 渠道 | 平均分 | 中位数 | 工单数 |")
        lines.append("|------|--------|--------|--------|")
        for _, row in sat_ch.iterrows():
            lines.append(f"| {row['channel']} | {row['mean']} | {row['median']} | {int(row['count'])} |")
        lines.append("")

    if 'channel' in chart_paths:
        lines.append(f"📞 [查看渠道分析图]({chart_paths['channel']})")
        lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## 八、解决率分析")
    lines.append("")

    resolution_rate = analysis_result.get('resolution_rate', {})

    if resolution_rate.get('overall_rate') is not None:
        lines.append(f"- **整体解决率**: {resolution_rate['overall_rate']}%")
        lines.append("")

    if resolution_rate.get('by_type') is not None:
        lines.append("### 8.1 各类型解决率")
        lines.append("")
        by_type = resolution_rate['by_type']
        lines.append("| 问题类型 | 解决率 | 已解决 | 总数 |")
        lines.append("|----------|--------|--------|------|")
        for _, row in by_type.iterrows():
            lines.append(f"| {row['issue_type']} | {row['resolution_rate']}% | {int(row['resolved_count'])} | {int(row['total_count'])} |")
        lines.append("")

    if resolution_rate.get('by_severity') is not None:
        lines.append("### 8.2 各优先级解决率")
        lines.append("")
        by_sev = resolution_rate['by_severity']
        lines.append("| 严重程度 | 解决率 | 已解决 | 总数 |")
        lines.append("|----------|--------|--------|------|")
        for _, row in by_sev.iterrows():
            lines.append(f"| {row['severity']} | {row['resolution_rate']}% | {int(row['resolved_count'])} | {int(row['total_count'])} |")
        lines.append("")

    if resolution_rate.get('unresolved_tickets') is not None:
        lines.append("### 8.3 未解决工单详情")
        lines.append("")
        lines.append("| 工单ID | 类型 | 严重度 | 处理时长(小时) | 描述 |")
        lines.append("|--------|------|--------|----------------|------|")
        for _, row in resolution_rate['unresolved_tickets'].head(10).iterrows():
            lines.append(f"| {row['ticket_id']} | {row['issue_type']} | {row['severity']} | {row['resolution_hours']} | {str(row['description'])[:30]}... |")
        lines.append("")

    if 'resolution_rate' in chart_paths:
        lines.append(f"✅ [查看解决率分析图]({chart_paths['resolution_rate']})")
        lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## 九、交叉分析")
    lines.append("")

    if 'heatmap' in chart_paths:
        lines.append(f"🔥 [查看问题类型×严重程度热力图]({chart_paths['heatmap']})")
        lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## 十、异常信号检测")
    lines.append("")

    if anomaly_summary['total'] > 0:
        lines.append(f"共检测到 **{anomaly_summary['total']}** 个异常信号\n")

        by_severity = anomaly_summary.get('by_severity', {})
        if by_severity:
            lines.append("### 异常统计")
            lines.append("")
            lines.append("| 严重程度 | 数量 |")
            lines.append("|----------|------|")
            severity_labels = {'high': '🔴 高危', 'medium': '🟡 中等', 'low': '🟢 低危'}
            for sev, count in by_severity.items():
                lines.append(f"| {severity_labels.get(sev, sev)} | {count} |")
            lines.append("")

        by_type = anomaly_summary.get('by_type', {})
        if by_type:
            lines.append("### 异常类型统计")
            lines.append("")
            lines.append("| 异常类型 | 数量 |")
            lines.append("|----------|------|")
            for t, count in by_type.items():
                lines.append(f"| {t} | {count} |")
            lines.append("")

        lines.append("### 异常详情")
        lines.append("")
        lines.append("| # | 类型 | 严重度 | 描述 | 判断依据 | 建议 |")
        lines.append("|---|------|--------|------|----------|------|")
        for idx, a in enumerate(anomaly_summary['anomalies'], 1):
            lines.append(
                f"| {idx} | {a['type']} | {a['severity']} | "
                f"{a['description']} | "
                f"统计分析 | "
                f"{a['recommendation']} |"
            )
        lines.append("")

        if 'anomaly' in chart_paths:
            lines.append(f"📊 [查看异常信号统计图]({chart_paths['anomaly']})")
            lines.append("")
    else:
        lines.append("✅ 当前未检测到明显异常信号\n")

    lines.append("---")
    lines.append("")

    lines.append("## 十一、智能解读与建议")
    lines.append("")
    lines.append(f"*AI 引擎状态: {'启用' if ai_available else '未启用（使用规则引擎）'}*")
    lines.append("")
    lines.append(ai_insights)
    lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## 附录：分析维度说明")
    lines.append("")
    lines.append("| 维度 | 分析角度 | 决策价值 |")
    lines.append("|------|----------|----------|")
    lines.append("| 时间趋势 | 每日工单量变化、环比增长率 | 发现业务波动规律，识别突增异常 |")
    lines.append("| 问题类型 | 各工单类别占比、Top5高频问题 | 定位核心问题领域，集中资源攻关 |")
    lines.append("| 严重程度 | 高/中/低优先级占比 | 确保高优问题得到及时响应 |")
    lines.append("| 处理效率 | 平均处理时长、SLA达标率 | 评估团队工作负荷和流程瓶颈 |")
    lines.append("| 满意度 | 平均分、各类型满意度、相关性分析 | 识别服务薄弱环节，提升用户体验 |")
    lines.append("| 渠道分析 | 渠道分布、各渠道特点 | 优化渠道配置，提升服务效率 |")
    lines.append("| 解决率 | 整体解决率、各类型解决率 | 评估问题闭环能力，关注未解决工单 |")
    lines.append("| 交叉关联 | 类型×严重程度、渠道×严重程度 | 发现特定维度的关联问题 |")
    lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='客服工单数据分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py data/tickets.json
  python main.py data/tickets.csv -o output/
  python main.py data/tickets.xlsx --no-ai
        """
    )

    parser.add_argument(
        'data_path',
        help='工单数据文件路径 (JSON/CSV/Excel)'
    )

    parser.add_argument(
        '-o', '--output',
        default=None,
        help=f'输出目录 (默认: {OUTPUT_DIR})'
    )

    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='不使用 AI 生成解读（使用规则引擎）'
    )

    args = parser.parse_args()

    if not Path(args.data_path).exists():
        print(f"错误: 数据文件不存在 - {args.data_path}")
        sys.exit(1)

    try:
        output_path = generate_report(
            data_path=args.data_path,
            output_dir=args.output,
            use_ai=not args.no_ai
        )
        print(f"\n✅ 分析完成，报告已保存至: {output_path}")
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
