import pandas as pd
from pathlib import Path
from typing import Optional


class DataLoader:
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.df: Optional[pd.DataFrame] = None

    def load(self) -> pd.DataFrame:
        if self.data_path.suffix == '.csv':
            self.df = pd.read_csv(self.data_path)
        elif self.data_path.suffix in ['.xlsx', '.xls']:
            self.df = pd.read_excel(self.data_path)
        elif self.data_path.suffix == '.json':
            self.df = pd.read_json(self.data_path)
        else:
            raise ValueError(f"不支持的文件格式: {self.data_path.suffix}")

        self.df = self._standardize_columns(self.df)
        self.df = self._parse_dates(self.df)
        print(f"数据加载完成: {len(self.df)} 条工单记录")
        print(f"字段列表: {list(self.df.columns)}")
        return self.df

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        column_mapping = {
            '工单ID': 'ticket_id',
            '工单号': 'ticket_id',
            '问题类型': 'issue_type',
            '问题分类': 'issue_type',
            'category': 'issue_type',
            '严重程度': 'severity',
            '优先级': 'severity',
            'priority': 'severity',
            '创建时间': 'created_at',
            '创建日期': 'created_at',
            '提交时间': 'created_at',
            '处理时间': 'resolved_at',
            '解决时间': 'resolved_at',
            '关闭时间': 'resolved_at',
            'resolution_time_hours': 'resolution_hours',
            '处理人': 'handler',
            '负责人': 'handler',
            '状态': 'status',
            '工单状态': 'status',
            '客户': 'customer',
            '客户名称': 'customer',
            '问题描述': 'description',
            '描述': 'description',
            '标签': 'tags',
            '分类': 'category',
            '子分类': 'sub_category',
        }

        rename_map = {}
        for col in df.columns:
            if col in column_mapping:
                rename_map[col] = column_mapping[col]

        if rename_map:
            df = df.rename(columns=rename_map)
            print(f"字段映射完成: {rename_map}")

        return df

    def _parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        date_columns = ['created_at', 'resolved_at']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        return df

    def get_summary(self) -> dict:
        if self.df is None:
            raise RuntimeError("请先调用 load() 方法加载数据")

        summary = {
            'total_tickets': len(self.df),
            'columns': list(self.df.columns),
            'date_range': None,
            'issue_types': None,
            'severity_levels': None,
            'channels': None,
            'avg_satisfaction': None,
            'resolution_rate': None,
        }

        if 'created_at' in self.df.columns:
            summary['date_range'] = {
                'start': self.df['created_at'].min(),
                'end': self.df['created_at'].max(),
            }

        if 'issue_type' in self.df.columns:
            summary['issue_types'] = self.df['issue_type'].unique().tolist()

        if 'severity' in self.df.columns:
            summary['severity_levels'] = self.df['severity'].unique().tolist()

        if 'channel' in self.df.columns:
            summary['channels'] = self.df['channel'].unique().tolist()

        if 'satisfaction' in self.df.columns:
            summary['avg_satisfaction'] = round(self.df['satisfaction'].mean(), 2)

        if 'is_resolved' in self.df.columns:
            summary['resolution_rate'] = round(self.df['is_resolved'].mean() * 100, 2)

        return summary
