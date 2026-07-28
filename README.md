# 客服工单智能分析工具

## 🌟 快速体验 Web 版

### 方式一：本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Web 应用
streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`，上传文件即可分析。

### 方式二：在线部署（推荐）

#### Streamlit Cloud（免费）

1. 将本项目推送到 GitHub
2. 访问 [share.streamlit.io](https://share.streamlit.io) 连接仓库
3. 自动部署完成，获得在线访问链接

#### Hugging Face Spaces（免费）

1. 访问 [huggingface.co/spaces](https://huggingface.co/spaces) 创建新 Space
2. 选择 "Streamlit" SDK
3. 上传代码或连接 GitHub 仓库
4. 添加 `app.py` 作为启动文件
5. 部署完成

---

## 📊 功能特性

| 功能 | 说明 |
|------|------|
| 📤 文件上传 | 支持 JSON / CSV / Excel 格式 |
| 📈 趋势分析 | 时间趋势、时段分布、环比增长 |
| 📊 分类分析 | 问题类型、严重程度、处理效率 |
| ⚠️ 异常检测 | 8类异常信号自动识别 |
| ⭐ 满意度分析 | 满意度分布、类型对比、相关性 |
| 📞 渠道分析 | 渠道分布、渠道特点 |
| 🤖 AI 解读 | 可选启用大模型智能分析 |
| 📱 响应式 | PC / 移动端自适应 |

## 分析维度

### 1. 时间趋势分析
- 每日工单量变化、环比增长率
- 工单时段分布（24小时）
- 工作日 vs 周末差异

### 2. 问题类型分布
- 各工单类别占比
- Top5 高频问题识别

### 3. 严重程度分析
- 高/中/低优先级占比
- 高优比例监控

### 4. 处理效率分析
- 平均处理时长
- SLA 达标率
- 分类型效率对比

### 5. 满意度分析
- 满意度分布（1-5分）
- 各类型满意度对比
- 满意度与处理时长相关性

### 6. 渠道分析
- 渠道分布
- 各渠道特点对比

### 7. 解决率分析
- 整体解决率
- 各类型解决率
- 未解决工单追踪

### 8. 交叉关联分析
- 类型 × 严重程度热力图
- 渠道 × 严重程度分析

## 异常检测规则

| 规则 | 说明 | 默认阈值 |
|------|------|----------|
| 突增检测 | 某类工单量超过均值+N倍标准差 | 2倍标准差 |
| 环比异常 | 某类工单环比增长超过阈值 | 50% |
| 聚集爆发 | 短时间内同一问题集中出现 | 24小时内≥3条 |
| 高优比例异常 | 高优工单占比过高 | >40% |
| 超时异常 | 工单处理时间超过SLA | 24小时 |
| 满意度异常 | 低分工单占比过高 | >30% |
| 未解决比例 | 未解决工单占比过高 | >10% |

## 字段格式说明

支持 JSON / CSV / Excel 格式，字段名会自动映射：

| 常见字段名 | 映射字段 | 说明 |
|-----------|----------|------|
| ticket_id / 工单号 | ticket_id | 工单标识 |
| category / 问题类型 | issue_type | 问题分类 |
| priority / 严重程度 | severity | 优先级 |
| created_at / 创建时间 | created_at | 创建时间 |
| resolution_time_hours | resolution_hours | 处理时长(小时) |
| satisfaction / 满意度 | satisfaction | 1-5分 |
| channel / 渠道 | channel | 来源渠道 |
| is_resolved / 已解决 | is_resolved | true/false |

**JSON 示例**：
```json
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
```

## CLI 命令行模式

除了 Web 版，还支持命令行运行：

```bash
# 基本用法
python main.py data/tickets.json

# 指定输出目录
python main.py data/tickets.csv -o output/

# 不使用AI解读
python main.py data/tickets.xlsx --no-ai
```

## 配置说明

### 本地配置

编辑 `config.py`：
```python
# AI API配置（使用环境变量更安全）
API_KEY = os.environ.get("API_KEY", "")
API_BASE = os.environ.get("API_BASE", "https://api.deepseek.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-chat")

# 异常检测阈值
SLA_HOURS = 24
ANOMALY_STD_THRESHOLD = 2
ANOMALY_RING_THRESHOLD = 0.5
CLUSTER_WINDOW_HOURS = 24
CLUSTER_MIN_COUNT = 3
```

### 平台部署配置

#### Streamlit Cloud
在项目 Settings → Secrets 中添加：
```
API_KEY=你的API_KEY
```

#### Hugging Face Spaces
在 Space Settings → Repository secrets 中添加环境变量。

## 项目结构

```
kefu/
├── app.py                 # Streamlit Web 应用
├── main.py                # CLI 命令行入口
├── config.py              # 配置文件
├── requirements.txt       # 依赖列表
├── .streamlit/
│   └── config.toml        # Streamlit 配置
├── src/
│   ├── data_loader.py     # 数据加载与清洗
│   ├── analyzer.py        # 核心分析引擎
│   ├── anomaly_detector.py # 异常检测模块
│   ├── visualizer.py      # 可视化生成
│   └── ai_insights.py     # AI 智能解读
└── README.md              # 说明文档
```

## 技术栈

- **Python 3.8+**
- **Streamlit**：Web 应用框架
- **Pandas**：数据处理与分析
- **Plotly**：交互式可视化
- **Matplotlib**：静态图表生成

## 使用建议

1. 首次使用先用 Web 版上传测试数据
2. 在侧边栏调整异常检测阈值
3. 可选填 API Key 启用 AI 智能解读
4. CLI 模式适合批量处理和集成

## 安全提示

- ⚠️ **不要**将 API Key 提交到 GitHub
- 使用环境变量或 Streamlit Secrets 管理密钥
- `.gitignore` 已配置排除敏感文件
