import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


class TicketAnalyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._preprocess()

    def _preprocess(self):
        if 'created_at' in self.df.columns:
            self.df['date'] = self.df['created_at'].dt.date
            self.df['hour'] = self.df['created_at'].dt.hour
            self.df['weekday'] = self.df['created_at'].dt.dayofweek
            self.df['month'] = self.df['created_at'].dt.month

        if 'resolution_hours' not in self.df.columns and 'created_at' in self.df.columns and 'resolved_at' in self.df.columns:
            self.df['resolution_hours'] = (
                (self.df['resolved_at'] - self.df['created_at']).dt.total_seconds() / 3600
            )

    def analyze_time_trend(self) -> Dict[str, Any]:
        result = {
            'daily_counts': None,
            'hourly_counts': None,
            'weekday_counts': None,
            'growth_rate': None,
        }

        if 'date' in self.df.columns:
            daily = self.df.groupby('date').size().reset_index(name='count')
            daily = daily.sort_values('date')
            result['daily_counts'] = daily

            if len(daily) >= 2:
                daily['prev_count'] = daily['count'].shift(1)
                daily['growth'] = ((daily['count'] - daily['prev_count']) / daily['prev_count'] * 100).round(2)
                result['growth_rate'] = daily[['date', 'count', 'growth']].dropna()

        if 'hour' in self.df.columns:
            hourly = self.df.groupby('hour').size().reset_index(name='count')
            result['hourly_counts'] = hourly

        if 'weekday' in self.df.columns:
            weekday_map = {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'}
            weekday = self.df.groupby('weekday').size().reset_index(name='count')
            weekday['weekday_name'] = weekday['weekday'].map(weekday_map)
            result['weekday_counts'] = weekday

        return result

    def analyze_issue_types(self) -> Dict[str, Any]:
        result = {
            'type_distribution': None,
            'type_by_severity': None,
            'top_types': None,
        }

        if 'issue_type' in self.df.columns:
            type_dist = self.df['issue_type'].value_counts().reset_index()
            type_dist.columns = ['issue_type', 'count']
            type_dist['percentage'] = (type_dist['count'] / len(self.df) * 100).round(2)
            result['type_distribution'] = type_dist

            result['top_types'] = type_dist.head(5)

            if 'severity' in self.df.columns:
                cross = pd.crosstab(
                    self.df['issue_type'],
                    self.df['severity'],
                    margins=True,
                    margins_name='合计'
                )
                result['type_by_severity'] = cross

        return result

    def analyze_severity(self) -> Dict[str, Any]:
        result = {
            'severity_distribution': None,
            'severity_by_type': None,
            'high_severity_ratio': None,
        }

        if 'severity' in self.df.columns:
            sev_dist = self.df['severity'].value_counts().reset_index()
            sev_dist.columns = ['severity', 'count']
            sev_dist['percentage'] = (sev_dist['count'] / len(self.df) * 100).round(2)
            result['severity_distribution'] = sev_dist

            high_keywords = ['高', '紧急', '严重', 'critical', 'high', 'urgent']
            is_high = self.df['severity'].astype(str).str.lower().apply(
                lambda x: any(kw in x for kw in high_keywords)
            )
            result['high_severity_ratio'] = round(is_high.sum() / len(self.df) * 100, 2)

        return result

    def analyze_resolution_efficiency(self) -> Dict[str, Any]:
        result = {
            'avg_resolution_hours': None,
            'resolution_by_type': None,
            'sla_compliance': None,
            'overdue_tickets': None,
        }

        if 'resolution_hours' in self.df.columns:
            valid_resolution = self.df[self.df['resolution_hours'] > 0]
            if len(valid_resolution) > 0:
                result['avg_resolution_hours'] = round(valid_resolution['resolution_hours'].mean(), 2)

                if 'issue_type' in self.df.columns:
                    by_type = valid_resolution.groupby('issue_type')['resolution_hours'].agg(['mean', 'median', 'count'])
                    by_type = by_type.round(2).reset_index()
                    result['resolution_by_type'] = by_type

                try:
                    from config import SLA_HOURS
                except ImportError:
                    SLA_HOURS = 24
                overdue = valid_resolution[valid_resolution['resolution_hours'] > SLA_HOURS]
                result['sla_compliance'] = {
                    'sla_hours': SLA_HOURS,
                    'compliant_count': len(valid_resolution) - len(overdue),
                    'overdue_count': len(overdue),
                    'compliance_rate': round((len(valid_resolution) - len(overdue)) / len(valid_resolution) * 100, 2) if len(valid_resolution) > 0 else 0,
                }
                result['overdue_tickets'] = overdue[['ticket_id', 'issue_type', 'severity', 'resolution_hours']].head(10)

        return result

    def analyze_satisfaction(self) -> Dict[str, Any]:
        result = {
            'avg_score': None,
            'distribution': None,
            'by_type': None,
            'by_severity': None,
            'low_score_tickets': None,
            'correlation_resolution': None,
        }

        if 'satisfaction' in self.df.columns:
            result['avg_score'] = round(self.df['satisfaction'].mean(), 2)

            dist = self.df['satisfaction'].value_counts().sort_index().reset_index()
            dist.columns = ['score', 'count']
            dist['percentage'] = (dist['count'] / len(self.df) * 100).round(2)
            result['distribution'] = dist

            if 'issue_type' in self.df.columns:
                by_type = self.df.groupby('issue_type')['satisfaction'].agg(['mean', 'median', 'count'])
                by_type = by_type.round(2).reset_index()
                by_type = by_type.sort_values('mean', ascending=True)
                result['by_type'] = by_type

            if 'severity' in self.df.columns:
                by_sev = self.df.groupby('severity')['satisfaction'].agg(['mean', 'median', 'count'])
                by_sev = by_sev.round(2).reset_index()
                result['by_severity'] = by_sev

            low_score = self.df[self.df['satisfaction'] <= 2]
            if len(low_score) > 0:
                result['low_score_tickets'] = low_score[['ticket_id', 'issue_type', 'severity', 'satisfaction', 'description']].head(10)

            if 'resolution_hours' in self.df.columns:
                valid = self.df[self.df['resolution_hours'] > 0]
                if len(valid) > 0:
                    corr = valid['satisfaction'].corr(valid['resolution_hours'])
                    result['correlation_resolution'] = round(corr, 3)

        return result

    def analyze_channel(self) -> Dict[str, Any]:
        result = {
            'distribution': None,
            'by_severity': None,
            'by_type': None,
            'satisfaction_by_channel': None,
        }

        if 'channel' in self.df.columns:
            dist = self.df['channel'].value_counts().reset_index()
            dist.columns = ['channel', 'count']
            dist['percentage'] = (dist['count'] / len(self.df) * 100).round(2)
            result['distribution'] = dist

            if 'severity' in self.df.columns:
                by_sev = pd.crosstab(self.df['channel'], self.df['severity'], normalize='index')
                by_sev = (by_sev * 100).round(2)
                result['by_severity'] = by_sev

            if 'issue_type' in self.df.columns:
                by_type = pd.crosstab(self.df['channel'], self.df['issue_type'])
                result['by_type'] = by_type

            if 'satisfaction' in self.df.columns:
                sat_by_ch = self.df.groupby('channel')['satisfaction'].agg(['mean', 'median', 'count'])
                sat_by_ch = sat_by_ch.round(2).reset_index()
                result['satisfaction_by_channel'] = sat_by_ch

        return result

    def analyze_resolution_rate(self) -> Dict[str, Any]:
        result = {
            'overall_rate': None,
            'by_type': None,
            'by_severity': None,
            'unresolved_tickets': None,
        }

        if 'is_resolved' in self.df.columns:
            result['overall_rate'] = round(self.df['is_resolved'].mean() * 100, 2)

            if 'issue_type' in self.df.columns:
                by_type = self.df.groupby('issue_type')['is_resolved'].agg(['mean', 'sum', 'count'])
                by_type['mean'] = (by_type['mean'] * 100).round(2)
                by_type = by_type.reset_index()
                by_type.columns = ['issue_type', 'resolution_rate', 'resolved_count', 'total_count']
                result['by_type'] = by_type

            if 'severity' in self.df.columns:
                by_sev = self.df.groupby('severity')['is_resolved'].agg(['mean', 'sum', 'count'])
                by_sev['mean'] = (by_sev['mean'] * 100).round(2)
                by_sev = by_sev.reset_index()
                by_sev.columns = ['severity', 'resolution_rate', 'resolved_count', 'total_count']
                result['by_severity'] = by_sev

            unresolved = self.df[~self.df['is_resolved']]
            if len(unresolved) > 0:
                result['unresolved_tickets'] = unresolved[['ticket_id', 'issue_type', 'severity', 'resolution_hours', 'description']].head(20)

        return result

    def analyze_cross_analysis(self) -> Dict[str, Any]:
        result = {
            'type_severity_heatmap': None,
            'type_time_heatmap': None,
            'channel_severity_heatmap': None,
        }

        if 'issue_type' in self.df.columns and 'severity' in self.df.columns:
            heatmap_data = pd.crosstab(self.df['issue_type'], self.df['severity'])
            result['type_severity_heatmap'] = heatmap_data

        if 'issue_type' in self.df.columns and 'date' in self.df.columns:
            type_time = pd.crosstab(self.df['date'], self.df['issue_type'])
            result['type_time_heatmap'] = type_time

        if 'channel' in self.df.columns and 'severity' in self.df.columns:
            ch_sev = pd.crosstab(self.df['channel'], self.df['severity'])
            result['channel_severity_heatmap'] = ch_sev

        return result

    def run_full_analysis(self) -> Dict[str, Any]:
        return {
            'time_trend': self.analyze_time_trend(),
            'issue_types': self.analyze_issue_types(),
            'severity': self.analyze_severity(),
            'resolution_efficiency': self.analyze_resolution_efficiency(),
            'satisfaction': self.analyze_satisfaction(),
            'channel': self.analyze_channel(),
            'resolution_rate': self.analyze_resolution_rate(),
            'cross_analysis': self.analyze_cross_analysis(),
            'total_tickets': len(self.df),
        }
