import json
from typing import Dict, Any, Optional
from config import API_KEY, API_BASE, MODEL_NAME


class AIInsightsGenerator:
    def __init__(self):
        self.available = bool(API_KEY)

    def generate_insights(
        self,
        analysis_result: Dict[str, Any],
        anomaly_summary: Dict[str, Any]
    ) -> str:
        if not self.available:
            return self._generate_rule_based_insights(analysis_result, anomaly_summary)

        return self._generate_ai_insights(analysis_result, anomaly_summary)

    def _generate_rule_based_insights(
        self,
        analysis_result: Dict[str, Any],
        anomaly_summary: Dict[str, Any]
    ) -> str:
        insights = []

        insights.append("### 趋势解读\n")

        time_trend = analysis_result.get('time_trend', {})
        if time_trend.get('daily_counts') is not None:
            daily = time_trend['daily_counts']
            if len(daily) > 0:
                peak = daily.loc[daily['count'].idxmax()]
                low = daily.loc[daily['count'].idxmin()]
                insights.append(f"- **工单高峰**: {peak['date']}，共 {peak['count']} 条工单")
                insights.append(f"- **工单低谷**: {low['date']}，共 {low['count']} 条工单")
                avg_daily = daily['count'].mean()
                insights.append(f"- **日均工单量**: {avg_daily:.1f} 条")

        insights.append("\n### 问题类型解读\n")

        issue_types = analysis_result.get('issue_types', {})
        if issue_types.get('top_types') is not None:
            top = issue_types['top_types']
            insights.append("**Top 5 高频问题类型**：")
            for _, row in top.iterrows():
                insights.append(f"- {row['issue_type']}: {row['count']} 条 ({row['percentage']}%)")

        insights.append("\n### 满意度解读\n")

        satisfaction = analysis_result.get('satisfaction', {})
        if satisfaction.get('avg_score') is not None:
            avg = satisfaction['avg_score']
            if avg >= 4:
                insights.append(f"- 整体满意度良好（{avg} 分），继续保持")
            elif avg >= 3:
                insights.append(f"- 满意度中等（{avg} 分），有提升空间")
            else:
                insights.append(f"- 满意度偏低（{avg} 分），需要重点改进")

            if satisfaction.get('by_type') is not None:
                by_type = satisfaction['by_type']
                best = by_type.iloc[0]
                worst = by_type.iloc[-1]
                insights.append(f"- 满意度最高类型: {worst['issue_type']}（{worst['mean']} 分）")
                insights.append(f"- 满意度最低类型: {best['issue_type']}（{best['mean']} 分）")

        insights.append("\n### 解决率解读\n")

        resolution_rate = analysis_result.get('resolution_rate', {})
        if resolution_rate.get('overall_rate') is not None:
            rate = resolution_rate['overall_rate']
            if rate >= 95:
                insights.append(f"- 解决率优秀（{rate}%）")
            elif rate >= 85:
                insights.append(f"- 解决率良好（{rate}%）")
            else:
                insights.append(f"- 解决率需要提升（{rate}%）")

        insights.append("\n### 异常解读\n")

        if anomaly_summary.get('total', 0) > 0:
            insights.append(f"共发现 **{anomaly_summary['total']}** 个异常信号：")

            by_severity = anomaly_summary.get('by_severity', {})
            severity_map = {'high': '🔴 高危', 'medium': '🟡 中等', 'low': '🟢 低危'}
            for sev, count in by_severity.items():
                insights.append(f"- {severity_map.get(sev, sev)}: {count} 个")

            insights.append("\n**建议优先处理**：")
            for a in anomaly_summary.get('anomalies', [])[:5]:
                insights.append(f"- [{a['type']}] {a['description']}")
                insights.append(f"  - 建议: {a['recommendation']}")
        else:
            insights.append("✅ 当前未检测到明显异常信号")

        return '\n'.join(insights)

    def _generate_ai_insights(
        self,
        analysis_result: Dict[str, Any],
        anomaly_summary: Dict[str, Any]
    ) -> str:
        try:
            import requests

            prompt = self._build_prompt(analysis_result, anomaly_summary)

            response = requests.post(
                f"{API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL_NAME,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个专业的数据分析顾问，擅长从客服工单数据中发现趋势和异常，并给出 actionable 的建议。请用中文回答。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                print(f"AI API 调用失败: {response.status_code}")
                return self._generate_rule_based_insights(analysis_result, anomaly_summary)

        except Exception as e:
            print(f"AI 生成失败: {e}")
            return self._generate_rule_based_insights(analysis_result, anomaly_summary)

    def _build_prompt(
        self,
        analysis_result: Dict[str, Any],
        anomaly_summary: Dict[str, Any]
    ) -> str:
        prompt_parts = []
        prompt_parts.append("请分析以下客服工单数据，并给出专业的趋势解读和改进建议。\n")

        prompt_parts.append("## 统计数据\n")
        prompt_parts.append(f"- 总工单数: {analysis_result.get('total_tickets', 'N/A')}")

        time_trend = analysis_result.get('time_trend', {})
        if time_trend.get('daily_counts') is not None:
            daily = time_trend['daily_counts']
            if len(daily) > 0:
                prompt_parts.append(f"- 数据日期范围: {daily['date'].min()} 至 {daily['date'].max()}")

        issue_types = analysis_result.get('issue_types', {})
        if issue_types.get('type_distribution') is not None:
            prompt_parts.append("\n## 问题类型分布\n")
            type_dist = issue_types['type_distribution']
            for _, row in type_dist.iterrows():
                prompt_parts.append(f"- {row['issue_type']}: {row['count']} 条 ({row['percentage']}%)")

        severity = analysis_result.get('severity', {})
        if severity.get('severity_distribution') is not None:
            prompt_parts.append("\n## 严重程度分布\n")
            sev_dist = severity['severity_distribution']
            for _, row in sev_dist.iterrows():
                prompt_parts.append(f"- {row['severity']}: {row['count']} 条 ({row['percentage']}%)")

        resolution = analysis_result.get('resolution_efficiency', {})
        if resolution.get('avg_resolution_hours') is not None:
            prompt_parts.append(f"\n## 处理效率\n")
            prompt_parts.append(f"- 平均处理时长: {resolution['avg_resolution_hours']} 小时")
            if resolution.get('sla_compliance'):
                sla = resolution['sla_compliance']
                prompt_parts.append(f"- SLA 达标率: {sla['compliance_rate']}%")

        satisfaction = analysis_result.get('satisfaction', {})
        if satisfaction.get('avg_score') is not None:
            prompt_parts.append(f"\n## 满意度\n")
            prompt_parts.append(f"- 平均满意度: {satisfaction['avg_score']} 分")
            if satisfaction.get('correlation_resolution') is not None:
                prompt_parts.append(f"- 满意度与处理时长相关性: {satisfaction['correlation_resolution']}")

        channel = analysis_result.get('channel', {})
        if channel.get('distribution') is not None:
            prompt_parts.append("\n## 渠道分布\n")
            ch_dist = channel['distribution']
            for _, row in ch_dist.iterrows():
                prompt_parts.append(f"- {row['channel']}: {row['count']} 条 ({row['percentage']}%)")

        resolution_rate = analysis_result.get('resolution_rate', {})
        if resolution_rate.get('overall_rate') is not None:
            prompt_parts.append(f"\n## 解决率\n")
            prompt_parts.append(f"- 整体解决率: {resolution_rate['overall_rate']}%")

        if anomaly_summary.get('total', 0) > 0:
            prompt_parts.append("\n## 检测到的异常\n")
            for a in anomaly_summary.get('anomalies', []):
                prompt_parts.append(f"- [{a['severity']}] {a['type']}: {a['description']}")
                prompt_parts.append(f"  - 建议: {a['recommendation']}")

        prompt_parts.append("\n请从以下角度进行解读：")
        prompt_parts.append("1. 整体趋势判断")
        prompt_parts.append("2. 核心问题领域")
        prompt_parts.append("3. 需要关注的异常点")
        prompt_parts.append("4. 满意度分析与改善建议")
        prompt_parts.append("5. 渠道优化建议")
        prompt_parts.append("6. 改进建议和行动优先级")

        return '\n'.join(prompt_parts)
