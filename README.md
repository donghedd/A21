# A21 / SFQA AI

一个基于 `Flask + Vue 3 + Ollama + ChromaDB + MySQL` 的本地智能问答系统，支持：

- 用户注册、登录
- 知识库创建与文件上传
- 文档切分、向量化与检索增强问答（RAG）
- 自定义模型管理
- 将知识库绑定到模型后进行对话
- 管理端用户与对话记录管理
- Neo4j 驱动的知识图谱浏览与路径查询 MVP

当前仓库除了 RAG 主线外，已经新增了一个知识图谱 `MVP` 模块：

- 后端已接入 `Neo4j` 查询服务
- 已提供知识图谱搜索、节点详情、邻居展开、最短路径 API
- 前端用户端左侧导航已新增“知识图谱”入口，位置在“搜索”和“知识库”之间

注意：

- 当前仓库主线仍然是 `RAG 问答系统`
- 知识图谱模块目前是 `MVP`，已可检索和浏览，但还未实现文档中所有高级功能
- `设备专题页`、`故障专题页`、`图谱后台导入/重建` 仍需后续继续开发

本文档覆盖从拿到代码到项目可正常使用的完整过程，所有命令默认都在项目根目录执行。

## 1. 项目结构

```text
.
├── backend/                 # Flask 后端
│   ├── app/                 # API、服务、模型、RAG 逻辑
│   ├── database/init.sql    # MySQL 初始化脚本
│   ├── requirements.txt     # Python 依赖
│   └── run.py               # 后端入口
├── frontend/                # Vue 3 + Vite 前端
├── .env                     # 当前项目使用的环境变量文件
└── README.md
```

## 2. 运行前准备

### 2.1 必需软件

请先在本机安装以下组件：

- Python
- Node.js 和 npm
- MySQL 8.0+
- Ollama
- Neo4j 5.x

### 2.2 建议安装

- Redis

说明：

- 项目核心功能依赖 `MySQL + Ollama`。
- 如果要使用“知识图谱”页面，还需要本地启动 `Neo4j`。
- Redis 连接失败时，后端仍可启动，但退出登录的 token 拉黑能力会失效，预留的 Celery/Redis 能力也无法正常使用。

## 3. 首次拿到代码后的初始化

### 3.1 安装后端依赖

```bash
python -m pip install -r backend/requirements.txt
```

如果你的环境里 `python` 指向 Python 2，请改用：

```bash
python3 -m pip install -r backend/requirements.txt
```

### 3.2 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

## 4. 环境变量配置

项目根目录已经有一个 `.env` 文件，后端默认会读取它。首次使用时请重点检查以下配置是否符合你的本机环境：

```env
# Flask
FLASK_APP=run.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your-secret-key

# JWT
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRES=86400

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的MySQL密码
MYSQL_DATABASE=sfqa_db

# Redis（可选但推荐）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_DEFAULT_MODEL=qwen3:8b

# RAG
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
EMBEDDING_BATCH_SIZE=32

# Upload / Vector DB
MAX_CONTENT_LENGTH=52428800
UPLOAD_FOLDER=uploads
CHROMA_PERSIST_DIRECTORY=vector_db

# Knowledge Graph / Neo4j
KG_ENABLED=true
KG_PROVIDER=neo4j
KG_TYPED_OUTPUT_DIR=kg_typed_output
KG_RAW_OUTPUT_DIR=kg_output
KG_EVIDENCE_REQUIRED=true
KG_DEFAULT_EXPAND_DEPTH=2
KG_MAX_EXPAND_DEPTH=3
KG_DEFAULT_NODE_LIMIT=120
KG_DEFAULT_EDGE_LIMIT=200
KG_HIDE_BOOK_BY_DEFAULT=true
KG_HIDE_COVERS_BY_DEFAULT=true
KG_DEFAULT_VISIBLE_NODE_TYPES=Device,Fault,Cause,Symptom,Action,Parameter
KG_DEFAULT_VISIBLE_REL_TYPES=HAS_FAULT,CAUSED_BY,HAS_SYMPTOM,RESOLVED_BY,TARGETS,AFFECTS_PARAMETER,SHOWS_AS,HAS_COMPONENT
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=neo4j
NEO4J_DATABASE=neo4j
KG_SEARCH_BACKEND=builtin
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=ship_fault_kg
```

如果你不想直接修改现有 `.env`，也可以参考 [backend/.env.example](/mnt/d/contest/A21/code/backend/.env.example) 手动调整项目根目录下的 `.env`。

前端开发环境还预留了以下图谱开关：

```env
VITE_ENABLE_KG=true
VITE_KG_DEFAULT_EXPAND_DEPTH=2
VITE_KG_MAX_EXPAND_DEPTH=3
VITE_KG_MAX_NODES=120
VITE_KG_HIDE_BOOK_BY_DEFAULT=true
VITE_KG_HIDE_COVERS_BY_DEFAULT=true
```

这些变量目前用于后续图谱页面开发时的统一配置，不会影响现有 RAG 问答主流程。

## 4.1 船舶知识图谱开发配置说明

如果你接下来要基于当前仓库继续开发“船舶设备故障维修知识图谱网页”，建议按下面方式配置。

### 推荐数据源

- 优先使用 `kg_typed_output`
- 不建议继续基于旧的 `kg_output` 做前端主展示

### 推荐默认实体类型

- `Device`
- `Fault`
- `Cause`
- `Symptom`
- `Action`
- `Parameter`

### 推荐默认关系类型

- `HAS_FAULT`
- `CAUSED_BY`
- `HAS_SYMPTOM`
- `RESOLVED_BY`
- `TARGETS`
- `AFFECTS_PARAMETER`
- `SHOWS_AS`
- `HAS_COMPONENT`

### 推荐默认隐藏项

- `Book`
- `COVERS`

### 推荐显示策略

- 默认展开层数：`2`
- 最大展开层数：`3`
- 默认节点数上限：`120`
- 默认边数上限：`200`
- 所有高价值关系都要求显示证据

### 当前仓库已完成的图谱部分

- `Neo4j` 连接配置
- 图谱节点/关系默认展示配置
- 图谱搜索 API：`GET /api/kg/search?q=`
- 节点详情 API：`GET /api/kg/node/{id}`
- 邻居展开 API：`GET /api/kg/node/{id}/neighbors?depth=2`
- 路径查询 API：`GET /api/kg/path?source=&target=`
- 前端知识图谱探索页：`/kg`
- 用户端导航入口：“知识图谱”
- 基于 `cytoscape` 的图谱可视化、节点详情、关系过滤、路径查询

### 当前仓库尚未完成的图谱部分

- 设备专题页 / 故障专题页
- 证据追溯页中的原文跳转
- 管理端图谱 CSV 导入 / 重建
- 图谱纠错审核闭环
- 图谱搜索增强（Elasticsearch）

如果后续继续开发知识图谱模块，建议优先按以下顺序推进：

1. 设备专题页 / 故障链路页
2. 证据片段和书籍页码联动
3. 图谱后台导入与重建
4. 图谱反馈审核闭环
5. 搜索增强与缓存

## 5. 初始化外部服务

### 5.1 启动 MySQL

确认 MySQL 已启动，并且 `.env` 中配置的账号有建库权限。

### 5.2 初始化数据库

推荐使用仓库自带 SQL 脚本初始化：

```bash
mysql -u root -p < backend/database/init.sql
```

如果你的 MySQL 用户不是 `root`，请替换成自己的用户名。

这个脚本会完成：

- 创建数据库 `sfqa_db`
- 创建项目所需全部表
- 插入默认管理员账号

默认管理员账号信息：

- 用户名：`admin`
- 密码：`admin123`

如果你不需要默认管理员，也可以只创建空表：

```bash
flask --app backend/run.py init-db
```

但这种方式不会插入默认管理员账号。

### 5.3 启动 Redis（推荐）

本机已安装 Redis 时，直接启动即可，例如：

```bash
redis-server
```

如果你暂时不启 Redis，项目大部分功能依然可以跑通。

### 5.4 启动 Ollama

先启动 Ollama 服务：

```bash
ollama serve
```

然后至少拉取 2 个模型：

- 一个对话模型
- 一个向量模型

例如：

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

注意：

- `OLLAMA_EMBEDDING_MODEL` 必须与本地已下载的向量模型一致。
- `OLLAMA_DEFAULT_MODEL` 最好与本地已下载的聊天模型一致。
- 工作空间页面会读取 `ollama` 当前可用模型列表。

### 5.5 启动 Neo4j（知识图谱功能需要）

确保本地 `Neo4j` 已启动，并且：

- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE`

与实际实例一致。

知识图谱页面默认会直接访问 `Neo4j` 查询图谱节点、邻居关系和路径。

## 6. 启动项目

### 6.1 启动后端

```bash
python backend/run.py
```

默认监听：

- 后端地址：`http://localhost:5000`

后端启动后会自动确保以下目录存在：

- `backend/uploads`
- `backend/vector_db`

### 6.2 启动前端

新开一个终端，在项目根目录执行：

```bash
cd frontend
npm run dev
```

默认监听：

- 前端地址：`http://localhost:3000`

前端开发服务器已配置代理：

- `/api` -> `http://localhost:5000`

因此本地开发时只需要打开前端地址即可。

## 7. 首次使用完整流程

项目启动后，按下面顺序操作即可进入正常使用状态。

### 7.1 进入系统

浏览器打开：

```text
http://localhost:3000
```

你可以选择：

- 直接使用默认管理员账号登录：`admin / admin123`
- 或者在注册页新建自己的账号

### 7.2 创建知识库

登录后进入“知识库”页面，创建一个新的知识库。

### 7.3 上传文档

在知识库的“管理文件”中上传文档，支持格式：

- `pdf`
- `doc`
- `docx`
- `txt`
- `md`
- `xlsx`
- `xls`

上传后系统会自动：

- 保存原文件
- 解析文本
- 切分 chunk
- 调用 Ollama 生成 embedding
- 写入 Chroma 向量库

等待文件状态从：

- `pending`
- `processing`

变成：

- `completed`

只有处理完成后，知识库内容才能参与 RAG 检索。

### 7.4 创建自定义模型

进入“工作空间”页面：

1. 先确认页面能读取到 Ollama 本地模型。
2. 点击“新建模型”。
3. 选择一个基础模型，例如 `qwen3:8b`。
4. 按需填写系统提示词和描述。

### 7.5 绑定知识库到模型

在工作空间里打开模型的“知识库绑定”：

1. 选择刚才创建的知识库
2. 完成绑定

绑定后，这个自定义模型在对话时才会走知识库检索增强流程。

### 7.6 开始对话

回到首页聊天页：

1. 新建对话
2. 选择模型
3. 输入问题并发送

说明：

- 选择普通 Ollama 模型时，主要是纯模型对话。
- 选择已绑定知识库的自定义模型时，会使用 RAG 检索文档内容后再生成答案。

### 7.7 浏览知识图谱

登录后，在左侧导航栏中点击：

- `知识图谱`

即可进入图谱页面。

当前图谱页面支持：

- 关键词搜索节点
- 展开邻居网络
- 按关系类型过滤
- 查看节点属性详情
- 查询两个节点之间的最短路径

## 8. 常用命令

### 安装依赖

```bash
python -m pip install -r backend/requirements.txt
cd frontend && npm install
```

### 启动后端

```bash
python backend/run.py
```

### 启动前端

```bash
cd frontend && npm run dev
```

### 初始化数据库

```bash
mysql -u root -p < backend/database/init.sql
```

### 只创建表结构

```bash
flask --app backend/run.py init-db
```

## 9. 常见问题

### 9.1 前端能打开，但接口全报错

优先检查：

- 后端是否已经启动在 `5000` 端口
- MySQL 是否可连接
- `.env` 中数据库配置是否正确

### 9.2 工作空间里看不到 Ollama 模型

优先检查：

- `ollama serve` 是否正在运行
- 是否已经执行过 `ollama pull ...`
- `.env` 中 `OLLAMA_BASE_URL` 是否正确

### 9.3 文件一直停留在 `failed`

优先检查：

- Ollama 的向量模型是否已拉取，例如 `nomic-embed-text`
- 上传文件格式是否在允许列表内
- 文件内容是否可被正常解析

### 9.4 登录后立刻掉回登录页

优先检查：

- 后端 `JWT_SECRET_KEY` 是否稳定
- 浏览器控制台和后端日志里是否有 `401`
- Redis 未启动时，虽然通常不影响登录，但建议仍按配置启动

## 10. 生产部署前建议

当前仓库默认是本地开发配置，正式部署前至少应调整：

- 替换 `.env` 中所有默认密钥
- 不要使用示例数据库密码
- 为 MySQL、Redis、Ollama 配置固定可用地址
- 前端改为生产构建：`cd frontend && npm run build`
- 为后端增加正式 WSGI/反向代理部署方案

## 11. 当前项目的标准启动顺序

从零开始时，建议严格按这个顺序执行：

1. 安装 Python 和 Node.js 依赖
2. 启动 MySQL
3. 执行数据库初始化脚本
4. 启动 Redis（推荐）
5. 启动 Ollama，并拉取聊天模型和向量模型
6. 启动后端 `python backend/run.py`
7. 启动前端 `cd frontend && npm run dev`
8. 浏览器打开 `http://localhost:3000`
9. 登录或注册
10. 创建知识库并上传文件
11. 在工作空间创建自定义模型并绑定知识库
12. 回到聊天页开始使用
