import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from config import ANOMALY_STD_THRESHOLD, ANOMALY_RING_THRESHOLD, CLUSTER_WINDOW_HOURS, CLUSTER_MIN_COUNT, SLA_HOURS


class AnomalyDetector:
    def __init__(self, df: pd.DataFrame, sla_hours: Optional[float] = None, 
                 std_threshold: Optional[float] = None, ring_threshold: Optional[float] = None):
        self.df = df.copy()
        self.anomalies: List[Dict[str, Any]] = []
        self.sla_hours = sla_hours or SLA_HOURS
        self.std_threshold = std_threshold or ANOMALY_STD_THRESHOLD
        self.ring_threshold = ring_threshold or ANOMALY_RING_THRESHOLD

    def detect_all(self) -> List[Dict[str, Any]]:
        self.anomalies = []
        self._detect_spike_by_type()
        self._detect_ring_growth_anomaly()
        self._detect_cluster_outbreak()
        self._detect_severity_anomaly()
        self._detect_resolution_anomaly()
        self._detect_time_anomaly()
        self._detect_satisfaction_anomaly()
        self._detect_unresolved_anomaly()
        return self.anomalies

    def _detect_spike_by_type(self):
        if 'issue_type' not in self.df.columns or 'date' not in self.df.columns:
            return

        daily_type = self.df.groupby(['date', 'issue_type']).size().reset_index(name='count')

        for issue_type in daily_type['issue_type'].unique():
            type_data = daily_type[daily_type['issue_type'] == issue_type].sort_values('date')

            if len(type_data) < 2:
                continue

            mean_count = type_data['count'].mean()
            std_count = type_data['count'].std()

            if std_count == 0 or pd.isna(std_count):
                continue

            threshold = mean_count + self.std_threshold * std_count

            spike_days = type_data[type_data['count'] > threshold]

            for _, row in spike_days.iterrows():
                self.anomalies.append({
                    'type': '突增异常',
                    'severity': 'high',
                    'description': f"问题类型「{issue_type}」在 {row['date']} 工单量 {row['count']} 条，超过阈值 {threshold:.1f}（均值 {mean_count:.1f} + {self.std_threshold}倍标准差）",
                    'evidence': {
                        'date': str(row['date']),
                        'issue_type': issue_type,
                        'count': int(row['count']),
                        'threshold': round(threshold, 2),
                        'mean': round(mean_count, 2),
                        'std': round(std_count, 2),
                    },
                    'recommendation': f"关注「{issue_type}」是否有批量问题爆发，检查是否需要增派人力",
                })

    def _detect_ring_growth_anomaly(self):
        if 'issue_type' not in self.df.columns or 'date' not in self.df.columns:
            return

        daily_type = self.df.groupby(['date', 'issue_type']).size().reset_index(name='count')

        for issue_type in daily_type['issue_type'].unique():
            type_data = daily_type[daily_type['issue_type'] == issue_type].sort_values('date')

            if len(type_data) < 2:
                continue

            type_data = type_data.copy()
            type_data['prev_count'] = type_data['count'].shift(1)
            type_data['growth_rate'] = (type_data['count'] - type_data['prev_count']) / type_data['prev_count']

            anomalies = type_data[type_data['growth_rate'] > self.ring_threshold]

            for _, row in anomalies.iterrows():
                self.anomalies.append({
                    'type': '环比增长异常',
                    'severity': 'medium',
                    'description': f"问题类型「{issue_type}」在 {row['date']} 环比增长 {row['growth_rate']*100:.0f}%（前一天 {row['prev_count']} 条 → 当天 {row['count']} 条）",
                    'evidence': {
                        'date': str(row['date']),
                        'issue_type': issue_type,
                        'prev_count': int(row['prev_count']),
                        'curr_count': int(row['count']),
                        'growth_rate': f"{row['growth_rate']*100:.1f}%",
                    },
                    'recommendation': f"分析「{issue_type}」增长原因，判断是否需要临时调整优先级",
                })

    def _detect_cluster_outbreak(self):
        if 'issue_type' not in self.df.columns or 'created_at' not in self.df.columns:
            return

        for issue_type in self.df['issue_type'].unique():
            type_tickets = self.df[self.df['issue_type'] == issue_type].sort_values('created_at')

            if len(type_tickets) < CLUSTER_MIN_COUNT:
                continue

            for i in range(len(type_tickets) - CLUSTER_MIN_COUNT + 1):
                window = type_tickets.iloc[i:i + CLUSTER_MIN_COUNT]
                time_span = (window['created_at'].max() - window['created_at'].min()).total_seconds() / 3600

                if time_span <= CLUSTER_WINDOW_HOURS:
                    first_ticket = window.iloc[0]
                    last_ticket = window.iloc[-1]

                    self.anomalies.append({
                        'type': '聚集爆发异常',
                        'severity': 'high',
                        'description': f"问题类型「{issue_type}」在 {time_span:.1f} 小时内集中出现 {CLUSTER_MIN_COUNT} 条工单（{first_ticket['created_at']} 至 {last_ticket['created_at']}）",
                        'evidence': {
                            'issue_type': issue_type,
                            'window_start': str(first_ticket['created_at']),
                            'window_end': str(last_ticket['created_at']),
                            'time_span_hours': round(time_span, 2),
                            'ticket_count': CLUSTER_MIN_COUNT,
                        },
                        'recommendation': f"可能存在系统性问题，建议立即排查「{issue_type}」相关的服务或产品状态",
                    })
                    break

    def _detect_severity_anomaly(self):
        if 'severity' not in self.df.columns:
            return

        high_keywords = ['高', '紧急', '严重', 'critical', 'high', 'urgent']
        is_high = self.df['severity'].astype(str).str.lower().apply(
            lambda x: any(kw in x for kw in high_keywords)
        )

        high_ratio = is_high.sum() / len(self.df)

        if high_ratio > 0.4:
            self.anomalies.append({
                'type': '高优比例异常',
                'severity': 'high',
                'description': f"高严重程度工单占比 {high_ratio*100:.1f}%，超过 40% 警戒线",
                'evidence': {
                    'high_count': int(is_high.sum()),
                    'total_count': len(self.df),
                    'high_ratio': f"{high_ratio*100:.1f}%",
                },
                'recommendation': "评估团队工作负荷，考虑调整优先级处理策略",
            })

    def _detect_resolution_anomaly(self):
        if 'resolution_hours' not in self.df.columns:
            return

        valid = self.df[self.df['resolution_hours'] > 0]

        if len(valid) == 0:
            return

        overdue = valid[valid['resolution_hours'] > self.sla_hours]
        overdue_ratio = len(overdue) / len(valid)

        if overdue_ratio > 0.3:
            self.anomalies.append({
                'type': '超时比例异常',
                'severity': 'medium',
                'description': f"工单超时率 {overdue_ratio*100:.1f}%，超过 30% 警戒线（SLA: {self.sla_hours}小时）",
                'evidence': {
                    'overdue_count': len(overdue),
                    'valid_count': len(valid),
                    'overdue_ratio': f"{overdue_ratio*100:.1f}%",
                },
                'recommendation': "分析超时原因，优化处理流程或增加资源投入",
            })

        if len(overdue) > 0 and 'issue_type' in self.df.columns:
            overdue_by_type = overdue.groupby('issue_type').size().reset_index(name='overdue_count')
            overdue_by_type = overdue_by_type.sort_values('overdue_count', ascending=False)

            for _, row in overdue_by_type.head(3).iterrows():
                self.anomalies.append({
                    'type': '特定类型超时',
                    'severity': 'medium',
                    'description': f"问题类型「{row['issue_type']}」有 {row['overdue_count']} 条工单处理超时",
                    'evidence': {
                        'issue_type': row['issue_type'],
                        'overdue_count': int(row['overdue_count']),
                    },
                    'recommendation': f"深入分析「{row['issue_type']}」超时原因，可能需要专项培训或流程优化",
                })

        if len(overdue) > 0 and 'severity' in self.df.columns:
            overdue_by_sev = overdue.groupby('severity').size().reset_index(name='overdue_count')
            overdue_by_sev = overdue_by_sev.sort_values('overdue_count', ascending=False)

            for _, row in overdue_by_sev.iterrows():
                if row['overdue_count'] >= 2:
                    self.anomalies.append({
                        'type': '特定优先级超时',
                        'severity': 'high',
                        'description': f"{row['severity']}优先级工单中有 {row['overdue_count']} 条处理超时",
                        'evidence': {
                            'severity': row['severity'],
                            'overdue_count': int(row['overdue_count']),
                        },
                        'recommendation': f"重新评估{row['severity']}优先级工单的处理能力",
                    })

    def _detect_time_anomaly(self):
        if 'hour' not in self.df.columns:
            return

        hourly = self.df.groupby('hour').size()
        mean_hourly = hourly.mean()
        std_hourly = hourly.std()

        if std_hourly == 0 or pd.isna(std_hourly):
            return

        for hour, count in hourly.items():
            if count > mean_hourly + 2 * std_hourly:
                self.anomalies.append({
                    'type': '时段异常',
                    'severity': 'low',
                    'description': f"{hour}:00 时段工单量 {count} 条，高于平均水平（均值 {mean_hourly:.1f}）",
                    'evidence': {
                        'hour': int(hour),
                        'count': int(count),
                        'mean': round(mean_hourly, 2),
                    },
                    'recommendation': f"检查 {hour}:00 时段是否有批量问题触发，考虑该时段增派人手",
                })

    def _detect_satisfaction_anomaly(self):
        if 'satisfaction' not in self.df.columns:
            return

        low_score = self.df[self.df['satisfaction'] <= 2]
        low_ratio = len(low_score) / len(self.df)

        if low_ratio > 0.3:
            self.anomalies.append({
                'type': '满意度异常',
                'severity': 'high',
                'description': f"低分工单（≤2分）占比 {low_ratio*100:.1f}%，超过 30% 警戒线",
                'evidence': {
                    'low_score_count': len(low_score),
                    'total_count': len(self.df),
                    'low_ratio': f"{low_ratio*100:.1f}%",
                },
                'recommendation': "急需改进服务质量，分析低分原因并制定改善计划",
            })

        if 'issue_type' in self.df.columns:
            sat_by_type = self.df.groupby('issue_type')['satisfaction'].mean().sort_values()
            for issue_type, avg_score in sat_by_type.head(2).items():
                if avg_score < 3.0:
                    self.anomalies.append({
                        'type': '特定类型满意度低',
                        'severity': 'medium',
                        'description': f"问题类型「{issue_type}」平均满意度 {avg_score:.2f}，低于 3.0 分",
                        'evidence': {
                            'issue_type': issue_type,
                            'avg_score': round(avg_score, 2),
                            'ticket_count': int(self.df[self.df['issue_type'] == issue_type].shape[0]),
                        },
                        'recommendation': f"分析「{issue_type}」满意度低的具体原因，加强该类型问题的处理培训",
                    })

        if 'channel' in self.df.columns:
            sat_by_ch = self.df.groupby('channel')['satisfaction'].mean().sort_values()
            for channel, avg_score in sat_by_ch.items():
                if avg_score < 3.0:
                    self.anomalies.append({
                        'type': '特定渠道满意度低',
                        'severity': 'medium',
                        'description': f"渠道「{channel}」平均满意度 {avg_score:.2f}，低于 3.0 分",
                        'evidence': {
                            'channel': channel,
                            'avg_score': round(avg_score, 2),
                        },
                        'recommendation': f"优化「{channel}」渠道的服务流程",
                    })

    def _detect_unresolved_anomaly(self):
        if 'is_resolved' not in self.df.columns:
            return

        unresolved = self.df[~self.df['is_resolved']]
        unresolved_ratio = len(unresolved) / len(self.df)

        if unresolved_ratio > 0.1:
            self.anomalies.append({
                'type': '未解决比例异常',
                'severity': 'high',
                'description': f"未解决工单占比 {unresolved_ratio*100:.1f}%，超过 10% 警戒线",
                'evidence': {
                    'unresolved_count': len(unresolved),
                    'total_count': len(self.df),
                    'unresolved_ratio': f"{unresolved_ratio*100:.1f}%",
                },
                'recommendation': "立即处理未解决工单，分析无法解决的原因",
            })

        if len(unresolved) > 0 and 'issue_type' in self.df.columns:
            unres_by_type = unresolved.groupby('issue_type').size().sort_values(ascending=False)
            for issue_type, count in unres_by_type.items():
                if count >= 2:
                    self.anomalies.append({
                        'type': '特定类型未解决',
                        'severity': 'high',
                        'description': f"问题类型「{issue_type}」有 {count} 条工单未解决",
                        'evidence': {
                            'issue_type': issue_type,
                            'unresolved_count': int(count),
                        },
                        'recommendation': f"集中解决「{issue_type}」的积压工单，排查系统性原因",
                    })

        if len(unresolved) > 0 and 'resolution_hours' in self.df.columns:
            long_unresolved = unresolved[unresolved['resolution_hours'] > 48]
            if len(long_unresolved) > 0:
                self.anomalies.append({
                    'type': '长期未解决工单',
                    'severity': 'high',
                    'description': f"有 {len(long_unresolved)} 条工单处理超过 48 小时仍未解决",
                    'evidence': {
                        'count': len(long_unresolved),
                        'max_hours': round(long_unresolved['resolution_hours'].max(), 1),
                    },
                    'recommendation': "紧急处理长期积压工单，必要时升级到主管介入",
                })

    def get_anomaly_summary(self) -> Dict[str, Any]:
        if not self.anomalies:
            return {'total': 0, 'by_type': {}, 'by_severity': {}}

        by_type = {}
        by_severity = {}

        for a in self.anomalies:
            t = a['type']
            s = a['severity']
            by_type[t] = by_type.get(t, 0) + 1
            by_severity[s] = by_severity.get(s, 0) + 1

        return {
            'total': len(self.anomalies),
            'by_type': by_type,
            'by_severity': by_severity,
            'anomalies': self.anomalies,
        }
