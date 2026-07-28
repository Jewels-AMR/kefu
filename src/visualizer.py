import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path


class Visualizer:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.chart_files = []

    def create_time_trend_chart(self, time_trend: Dict[str, Any]) -> Optional[go.Figure]:
        if time_trend['daily_counts'] is None:
            return None

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=time_trend['daily_counts']['date'].astype(str),
            y=time_trend['daily_counts']['count'],
            name='每日工单量',
            marker_color='#1f77b4',
        ))

        if time_trend['growth_rate'] is not None:
            fig.add_trace(go.Scatter(
                x=time_trend['growth_rate']['date'].astype(str),
                y=time_trend['growth_rate']['growth'],
                name='环比增长率(%)',
                yaxis='y2',
                mode='lines+markers',
                marker_color='#ff7f0e',
            ))

        fig.update_layout(
            title='工单时间趋势分析',
            xaxis_title='日期',
            yaxis_title='工单数量',
            hovermode='x unified',
            barmode='group',
        )

        if time_trend['growth_rate'] is not None:
            fig.update_layout(
                yaxis2=dict(
                    title='增长率(%)',
                    overlaying='y',
                    side='right',
                )
            )

        return fig

    def create_hourly_chart(self, time_trend: Dict[str, Any]) -> Optional[go.Figure]:
        if time_trend['hourly_counts'] is None:
            return None

        fig = px.bar(
            time_trend['hourly_counts'],
            x='hour',
            y='count',
            title='工单时段分布',
            labels={'hour': '小时', 'count': '工单数量'},
            color_discrete_sequence=['#2ca02c'],
        )

        fig.update_layout(
            xaxis=dict(tickmode='linear', tick0=0, dtick=2),
        )

        return fig

    def create_issue_type_chart(self, issue_types: Dict[str, Any]) -> Optional[go.Figure]:
        if issue_types['type_distribution'] is None:
            return None

        df = issue_types['type_distribution']

        fig = go.Figure(data=[
            go.Pie(
                labels=df['issue_type'],
                values=df['count'],
                hole=0.4,
                textinfo='label+percent',
            )
        ])

        fig.update_layout(
            title='问题类型分布',
            annotations=[dict(text='问题类型', showarrow=False, font_size=20)],
        )

        return fig

    def create_severity_chart(self, severity: Dict[str, Any]) -> Optional[go.Figure]:
        if severity['severity_distribution'] is None:
            return None

        df = severity['severity_distribution']

        fig = px.bar(
            df,
            x='severity',
            y='count',
            color='severity',
            title='严重程度分布',
            labels={'severity': '严重程度', 'count': '工单数量'},
            text='percentage',
        )

        fig.update_traces(texttemplate='%{text}%', textposition='outside')

        return fig

    def create_heatmap(self, cross_analysis: Dict[str, Any]) -> Optional[go.Figure]:
        if cross_analysis['type_severity_heatmap'] is None:
            return None

        heatmap_data = cross_analysis['type_severity_heatmap']

        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale='YlOrRd',
            hoverongaps=False,
        ))

        fig.update_layout(
            title='问题类型 × 严重程度 热力图',
            xaxis_title='严重程度',
            yaxis_title='问题类型',
        )

        return fig

    def create_resolution_chart(self, resolution: Dict[str, Any]) -> Optional[go.Figure]:
        if resolution['resolution_by_type'] is None:
            return None

        df = resolution['resolution_by_type']

        fig = make_subplots(rows=1, cols=2, subplot_titles=('平均处理时长', '各类型工单数'))

        fig.add_trace(
            go.Bar(x=df['issue_type'], y=df['mean'], name='平均时长(小时)', marker_color='#1f77b4'),
            row=1, col=1
        )

        fig.add_trace(
            go.Bar(x=df['issue_type'], y=df['count'], name='工单数量', marker_color='#ff7f0e'),
            row=1, col=2
        )

        fig.update_layout(
            title='处理效率分析',
            showlegend=True,
            height=500,
        )

        return fig

    def create_satisfaction_chart(self, satisfaction: Dict[str, Any]) -> Optional[go.Figure]:
        if satisfaction['distribution'] is None:
            return None

        fig = make_subplots(rows=1, cols=2, subplot_titles=('满意度分布', '各类型平均满意度'))

        dist = satisfaction['distribution']
        fig.add_trace(
            go.Bar(x=dist['score'], y=dist['count'], name='分布', marker_color='#9467bd'),
            row=1, col=1
        )

        if satisfaction['by_type'] is not None:
            by_type = satisfaction['by_type']
            fig.add_trace(
                go.Bar(x=by_type['issue_type'], y=by_type['mean'], name='平均分', marker_color='#8c564b'),
                row=1, col=2
            )

        fig.update_layout(
            title='满意度分析',
            showlegend=True,
            height=500,
        )

        return fig

    def create_channel_chart(self, channel: Dict[str, Any]) -> Optional[go.Figure]:
        if channel['distribution'] is None:
            return None

        fig = make_subplots(rows=1, cols=2, subplot_titles=('渠道分布', '各渠道严重程度分布'))

        dist = channel['distribution']
        fig.add_trace(
            go.Bar(x=dist['channel'], y=dist['count'], name='渠道分布', marker_color='#e377c2'),
            row=1, col=1
        )

        if channel['by_severity'] is not None:
            by_sev = channel['by_severity'].reset_index()
            for sev in by_sev.columns[1:]:
                fig.add_trace(
                    go.Bar(x=by_sev['channel'], y=by_sev[sev], name=sev),
                    row=1, col=2
                )

        fig.update_layout(
            title='渠道分析',
            showlegend=True,
            height=500,
        )

        return fig

    def create_resolution_rate_chart(self, resolution_rate: Dict[str, Any]) -> Optional[go.Figure]:
        if resolution_rate['overall_rate'] is None:
            return None

        fig = make_subplots(rows=1, cols=2, subplot_titles=('整体解决率', '各类型解决率'))

        fig.add_trace(
            go.Bar(
                x=['已解决', '未解决'],
                y=[resolution_rate['overall_rate'], 100 - resolution_rate['overall_rate']],
                name='解决率',
                marker_color=['#2ca02c', '#d62728']
            ),
            row=1, col=1
        )

        if resolution_rate['by_type'] is not None:
            by_type = resolution_rate['by_type']
            fig.add_trace(
                go.Bar(x=by_type['issue_type'], y=by_type['resolution_rate'], name='解决率(%)', marker_color='#1f77b4'),
                row=1, col=2
            )

        fig.update_layout(
            title='解决率分析',
            showlegend=True,
            height=500,
        )

        return fig

    def create_anomaly_dashboard(self, anomaly_summary: Dict[str, Any]) -> Optional[go.Figure]:
        if anomaly_summary['total'] == 0:
            return None

        anomalies = anomaly_summary['anomalies']

        by_type = anomaly_summary['by_type']
        types = list(by_type.keys())
        counts = list(by_type.values())

        severity_colors = {'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'}
        colors = []
        for t in types:
            sev = next((a['severity'] for a in anomalies if a['type'] == t), 'low')
            colors.append(severity_colors.get(sev, '#9467bd'))

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=types,
            y=counts,
            name='异常数量',
            marker_color=colors,
        ))

        fig.update_layout(
            title='异常信号统计',
            xaxis_title='异常类型',
            yaxis_title='数量',
        )

        return fig

    def create_all_charts(self, analysis_result: Dict[str, Any], anomaly_summary: Dict[str, Any]) -> Dict[str, go.Figure]:
        charts = {}

        fig = self.create_time_trend_chart(analysis_result['time_trend'])
        if fig:
            charts['time_trend'] = fig

        fig = self.create_hourly_chart(analysis_result['time_trend'])
        if fig:
            charts['hourly'] = fig

        fig = self.create_issue_type_chart(analysis_result['issue_types'])
        if fig:
            charts['issue_types'] = fig

        fig = self.create_severity_chart(analysis_result['severity'])
        if fig:
            charts['severity'] = fig

        fig = self.create_heatmap(analysis_result['cross_analysis'])
        if fig:
            charts['heatmap'] = fig

        fig = self.create_resolution_chart(analysis_result['resolution_efficiency'])
        if fig:
            charts['resolution'] = fig

        fig = self.create_satisfaction_chart(analysis_result['satisfaction'])
        if fig:
            charts['satisfaction'] = fig

        fig = self.create_channel_chart(analysis_result['channel'])
        if fig:
            charts['channel'] = fig

        fig = self.create_resolution_rate_chart(analysis_result['resolution_rate'])
        if fig:
            charts['resolution_rate'] = fig

        fig = self.create_anomaly_dashboard(anomaly_summary)
        if fig:
            charts['anomaly'] = fig

        return charts

    def save_charts(self, charts: Dict[str, go.Figure]) -> Dict[str, str]:
        paths = {}
        for name, fig in charts.items():
            html_path = self.output_dir / f'{name}.html'
            fig.write_html(str(html_path))
            paths[name] = str(html_path)
            print(f"图表已保存: {html_path}")
        return paths
