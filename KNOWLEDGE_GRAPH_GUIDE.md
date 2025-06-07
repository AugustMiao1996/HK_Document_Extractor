# 🏛️ 香港法院文书知识图谱系统使用指南

## 📖 系统介绍

香港法院文书知识图谱系统是一个基于图数据库的可视化分析平台，将香港法院案件数据转换为直观的知识图谱，支持多维度的数据探索和分析。

### 🎯 主要功能

- **📊 数据可视化**：将复杂的法院案件关系以图形化方式展现
- **🔍 智能搜索**：支持案件号、当事人、律师等多种搜索方式  
- **🎛️ 动态筛选**：按案件类型、判决结果、节点类型等维度筛选
- **📱 交互探索**：点击节点查看详细信息，支持多种图布局
- **📈 统计分析**：实时显示节点和关系的统计分布

### 🏗️ 系统架构

```
📁 knowledge_graph/
├── 🔧 config.py          # 配置文件
├── 🗄️ graph_database.py  # 图数据库管理
├── 📥 data_importer.py    # 数据导入模块
├── 🎨 visualizer.py       # 可视化界面
└── 📋 requirements.txt    # 依赖列表
```

## 🚀 快速开始

### 方式一：一键启动（推荐）

```bash
# 进入项目目录
cd HK_Document_Extractor

# 运行一键启动脚本
python start_knowledge_graph.py
```

### 方式二：完整控制

```bash
# 1. 安装依赖
pip install -r knowledge_graph/requirements.txt

# 2. 启动Neo4j数据库
# 方式A：使用Docker
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j

# 方式B：本地安装Neo4j（需要单独下载）

# 3. 运行完整系统
python run_knowledge_graph.py --mode full
```

## 📋 系统要求

### 硬件要求
- **内存**：最低4GB，推荐8GB+
- **存储**：至少2GB可用空间
- **网络**：支持本地端口7474、7687、8050

### 软件要求
- **Python**：3.8+ 
- **Neo4j**：4.0+ 或 Docker
- **浏览器**：Chrome、Firefox、Safari等现代浏览器

### 依赖包
```
neo4j==5.15.0          # Neo4j数据库驱动
dash==2.14.1            # Web界面框架
dash-cytoscape==0.3.0   # 图谱可视化组件
pandas==2.0.3           # 数据处理
plotly==5.17.0          # 图表库
```

## 🎛️ 使用指南

### 1. 启动系统

运行启动脚本后，系统会自动：
1. ✅ 检查环境依赖
2. ✅ 连接Neo4j数据库  
3. ✅ 导入LLM分析数据
4. ✅ 启动Web可视化界面

### 2. 访问界面

启动成功后，在浏览器中访问：
```
http://127.0.0.1:8050
```

### 3. 界面功能

#### 左侧控制面板
- **🔍 搜索栏**：输入关键词搜索相关节点
- **🎛️ 筛选器**：
  - 案件类型：信托纠纷、商业纠纷等
  - 判决结果：胜诉、败诉、上诉被驳回等
  - 节点类型：案件、原告、被告、法官、律师等
- **📐 布局控制**：力导向、分层、圆形等布局方式
- **📊 统计信息**：实时显示图谱统计数据

#### 右侧图谱区域
- **🎨 交互式图谱**：支持缩放、拖拽、选择
- **🔍 节点详情**：点击节点查看详细信息
- **🎯 关系展示**：显示实体间的各种关系

### 4. 节点类型说明

| 节点类型 | 颜色 | 说明 | 示例 |
|---------|------|------|------|
| 📋 案件 | 蓝色 | 法院案件 | HCA000751_2022 |
| 👨‍💼 原告 | 绿色 | 起诉方 | LI DIANXIAO (李殿孝) |
| 👨‍⚖️ 被告 | 红色 | 被起诉方 | CAPITAL CENTURY TEXTILE |
| ⚖️ 法官 | 紫色 | 审理法官 | H. Au-Yeung |
| 👨‍💻 律师 | 棕色 | 代理律师 | Mr Kwok Kam Kwan |
| 🏢 律师事务所 | 粉色 | 法律服务机构 | C. S. Chan & Co |
| 🏛️ 法院 | 灰色 | 审理法院 | 香港特别行政区高等法院 |

### 5. 关系类型说明

| 关系类型 | 说明 | 示例 |
|---------|------|------|
| 起诉 | 原告起诉被告 | 原告 → 被告 |
| 涉及原告 | 案件涉及的原告 | 案件 → 原告 |
| 涉及被告 | 案件涉及的被告 | 案件 → 被告 |
| 由...审理 | 法官审理案件 | 案件 → 法官 |
| 在...法院审理 | 案件在法院审理 | 案件 → 法院 |
| 由...代理 | 律师代理当事人 | 律师 → 当事人 |
| 受雇于 | 律师受雇于律师事务所 | 律师 → 律师事务所 |

## 🔧 高级功能

### 1. 数据导入模式

```bash
# 仅导入数据（不启动界面）
python run_knowledge_graph.py --mode import

# 清空数据库后重新导入
python run_knowledge_graph.py --mode import --clear-db

# 指定数据文件
python run_knowledge_graph.py --data-file path/to/your/data.json
```

### 2. 可视化模式

```bash
# 仅启动可视化界面（假设数据已导入）
python run_knowledge_graph.py --mode visualize
```

### 3. 自定义配置

创建 `.env` 文件进行自定义配置：

```bash
# Neo4j配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j  
NEO4J_PASSWORD=your_password

# Web界面配置
WEB_HOST=127.0.0.1
WEB_PORT=8050
WEB_DEBUG=True
```

## 📊 数据分析示例

### 1. 律师胜率分析
- 筛选特定律师的所有案件
- 查看判决结果分布
- 评估律师专业水平

### 2. 案件类型模式
- 筛选特定类型案件
- 分析涉案金额分布
- 研究审理时间模式

### 3. 法官专业领域
- 查看法官审理的案件类型
- 分析判决倾向
- 研究专业化程度

### 4. 律师事务所实力
- 统计律师事务所代理案件数
- 分析胜败比例
- 评估专业领域

## 🛠️ 故障排除

### 1. Neo4j连接失败

**症状**：`❌ Neo4j连接失败`

**解决方案**：
```bash
# 检查Neo4j是否运行
sudo systemctl status neo4j

# 使用Docker启动Neo4j
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j

# 检查端口占用
netstat -tuln | grep 7687
```

### 2. 依赖包安装失败

**症状**：`ModuleNotFoundError`

**解决方案**：
```bash
# 升级pip
python -m pip install --upgrade pip

# 安装依赖
pip install -r knowledge_graph/requirements.txt

# 如果网络问题，使用国内镜像
pip install -r knowledge_graph/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 3. 数据文件未找到

**症状**：`❌ 数据文件不存在`

**解决方案**：
```bash
# 检查文件是否存在
ls -la output/llm_analysis_*.json

# 重新运行LLM分析
python run_llm_analysis.py

# 指定正确的数据文件路径
python run_knowledge_graph.py --data-file /path/to/your/data.json
```

### 4. Web界面无法访问

**症状**：浏览器无法打开界面

**解决方案**：
```bash
# 检查端口占用
netstat -tuln | grep 8050

# 更换端口
WEB_PORT=8051 python run_knowledge_graph.py

# 检查防火墙设置
sudo ufw status
```

## 📈 性能优化

### 1. 大数据集处理
- 使用分批导入避免内存溢出
- 创建适当的数据库索引
- 限制可视化节点数量

### 2. 响应速度优化
- 调整图布局算法
- 使用筛选功能减少显示节点
- 定期清理数据库日志

## 🤝 技术支持

### 联系方式
- 📧 邮件支持：[技术支持邮箱]
- 📖 文档中心：[在线文档链接]
- 🐛 问题反馈：[GitHub Issues]

### 常见问题
1. **Q**: 系统支持多少数据？
   **A**: 推荐单次导入不超过1万个案件，可分批处理大数据集。

2. **Q**: 可以自定义节点颜色吗？
   **A**: 可以，修改 `config.py` 中的 `NODE_COLORS` 配置。

3. **Q**: 支持导出图谱吗？
   **A**: 当前版本支持浏览器截图，未来版本将支持图片导出。

---

🎉 **恭喜！** 您已成功掌握香港法院文书知识图谱系统的使用方法。开始探索数据中的深层关系吧！ 