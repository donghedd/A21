# RAG 召回率评测工具

这套工具是独立新增的，目标是尽量不改你现有的 `RAG` 主链代码，方便你直接把新增文件推到 GitHub。

它提供三件事：

1. 列出当前可评测的知识库和自定义模型
2. 从问题列表生成标注模板
3. 基于 gold 标注跑真正的检索评测，输出 `Recall@K / Hit@K / MRR@K`

现在还额外提供第 4 件事：

4. 从本地文档自动切 chunk 并调用 LLM 合成评测问题，直接生成带 `relevant_files / relevant_chunks` 的数据集

## 目录

```text
backend/rag_eval/
├── __init__.py
├── cli.py
├── dataset.py
├── evaluator.py
├── README.md
└── examples/
    ├── questions.example.txt
    └── rag_eval_dataset.example.json
```

## 1. 先看可评测目标

在项目根目录执行：

```bash
python backend/rag_eval/cli.py list-targets
```

它会打印：

- 知识库 `id`
- 知识库对应的 `collection_name`
- 自定义模型 `id`
- 自定义模型绑定了哪些知识库

如果你想评估真实聊天链路，建议直接用 `--custom-model-id`，因为它会自动取这个模型绑定的知识库集合。

## 2. 生成标注模板

先准备问题列表。

文本格式示例：

```text
电机过热的原因有哪些？
发电机电压不稳定怎么排查？
```

然后生成模板：

```bash
python backend/rag_eval/cli.py build-template \
  --questions backend/rag_eval/examples/questions.example.txt \
  --output backend/rag_eval/examples/my_eval_template.json \
  --name "船舶维修RAG评测集" \
  --description "第一版人工标注集" \
  --k 1 3 5 10
```

生成后的模板里，重点填两个字段：

- `relevant_files`
- `relevant_chunks`

## 3. 标注格式

### file-level 标注

适合判断“该问句应该召回哪些文件”：

```json
{
  "id": "q001",
  "query": "电机过热的原因有哪些？",
  "relevant_files": [
    { "file_name": "船舶电气设备维修指南.md" },
    { "file_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" }
  ],
  "relevant_chunks": []
}
```

### chunk-level 标注

适合判断“该问句应该召回哪些具体 chunk”：

```json
{
  "id": "q002",
  "query": "发电机电压不稳定怎么排查？",
  "relevant_files": [],
  "relevant_chunks": [
    { "file_name": "船舶电气设备维修指南.md", "chunk_index": 7 },
    { "file_name": "船舶电气设备维修指南.md", "chunk_index": 8 }
  ]
}
```

说明：

- `file_name` 和 `file_id` 二选一即可
- `chunk-level` 标注必须带 `chunk_index`
- 如果你只标了 `relevant_chunks`，工具也会自动推导 `file-level gold`

## 4. 跑评测

### 评测某个知识库

```bash
python backend/rag_eval/cli.py evaluate \
  --dataset backend/rag_eval/examples/rag_eval_dataset.example.json \
  --kb-id YOUR_KB_ID \
  --output backend/rag_eval/examples/rag_eval_results.json
```

### 评测某个自定义模型绑定的整套知识库

```bash
python backend/rag_eval/cli.py evaluate \
  --dataset backend/rag_eval/examples/rag_eval_dataset.example.json \
  --custom-model-id YOUR_CUSTOM_MODEL_ID \
  --output backend/rag_eval/examples/rag_eval_results.json
```

### 做“纯召回”测试

如果你想尽量看检索召回，不想让阈值过滤把结果提前裁掉，建议把阈值临时设为 `0`：

```bash
python backend/rag_eval/cli.py evaluate \
  --dataset backend/rag_eval/examples/rag_eval_dataset.example.json \
  --kb-id YOUR_KB_ID \
  --relevance-threshold 0.0 \
  --output backend/rag_eval/examples/rag_eval_results.json
```

### 做消融实验

禁用混合检索：

```bash
python backend/rag_eval/cli.py evaluate \
  --dataset backend/rag_eval/examples/rag_eval_dataset.example.json \
  --kb-id YOUR_KB_ID \
  --disable-hybrid
```

禁用重排：

```bash
python backend/rag_eval/cli.py evaluate \
  --dataset backend/rag_eval/examples/rag_eval_dataset.example.json \
  --kb-id YOUR_KB_ID \
  --disable-rerank
```

禁用多源过滤：

```bash
python backend/rag_eval/cli.py evaluate \
  --dataset backend/rag_eval/examples/rag_eval_dataset.example.json \
  --kb-id YOUR_KB_ID \
  --disable-multi-source
```

## 5. 输出结果说明

结果会写到一个 `.json` 文件，里面包含：

- `summary`
  - `file` 粒度平均指标
  - `chunk` 粒度平均指标
- `queries`
  - 每条问题的检索结果
  - 每个 `K` 下的 `Recall / Hit / MRR`
- `resolved_targets`
  - 本次实际评测到的知识库、模型、集合名

## 6. 指标含义

- `Recall@K`
  - Top-K 里召回了多少个 gold target，除以 gold target 总数
- `Hit@K`
  - Top-K 里是否至少命中一个 gold target
- `MRR@K`
  - Top-K 内第一个命中项的倒数排名

## 7. 建议的实际工作流

1. 先用 `build-template` 生成模板
2. 业务同学或标注同学补 `relevant_files / relevant_chunks`
3. 用 `evaluate` 跑当前线上检索参数
4. 再分别禁用 `hybrid / rerank / multi-source` 做对比
5. 把结果 JSON 提交到 GitHub 或单独归档

## 8. 这套工具为什么适合直接推 GitHub

因为这次实现是“新增文件为主”：

- 不改原聊天接口
- 不改原知识库接口
- 不改原前端页面
- 不改原数据库结构

你后续直接把 `backend/rag_eval/` 整个目录提交上去就可以。

## 9. 自动生成评测集

如果你不想手工标注一大堆 `file_name` 和 `chunk_index`，可以直接用：

```bash
python backend/rag_eval/generate_samples.py \
  --input data \
  --output backend/rag_eval/examples/auto_dataset.json \
  --model qwen2.5:7b \
  --mode fact \
  --mode colloquial \
  --mode reasoning \
  --questions-per-mode 1 \
  --max-chunks 50 \
  --name "自动生成评测集" \
  --description "基于本地文档自动出题"
```

或者走统一入口：

```bash
python backend/rag_eval/cli.py generate-samples \
  --input data \
  --output backend/rag_eval/examples/auto_dataset.json \
  --model qwen2.5:7b
```

### 自动生成时做了什么

1. 用你当前项目的同款 loader 读取文件
2. 用你当前项目的同款 `split_documents` 做 chunk 切分
3. 对每个 chunk 调用 LLM 自动出题
4. 自动写入：
   - `relevant_files`
   - `relevant_chunks`
   - `file_name`
   - `chunk_index`

### 支持的出题模式

- `fact`
  - 简单直给，事实型问题
- `colloquial`
  - 模拟不专业船员的口语化提问
- `reasoning`
  - 参数、条件、因果关系相关的轻推理问题

### 常用参数

- `--input`
  - 输入文件或目录，可重复传多个
- `--mode`
  - 选择题型，可重复传多个
- `--questions-per-mode`
  - 每个 chunk 每种模式最多生成几个问题
- `--max-chunks`
  - 只抽前 N 个 chunk 生成，方便先小规模试跑
- `--max-questions`
  - 限制最终总题数
- `--shuffle`
  - 打乱 chunk 顺序后再抽样
- `--chunk-size / --chunk-overlap / --min-chunk-size`
  - 覆盖默认切块配置

### 一个很重要的注意点

自动生成出来的数据集虽然已经自动带上了 gold 信息，但它本质上仍然是“合成标注”。
建议你至少人工抽检一部分，特别是：

- 问题是否真的能由对应 chunk 回答
- 问题是否太宽泛
- `file_name` 是否和你最终上传进知识库的文件名一致
- `chunk_index` 是否跟当前入库逻辑保持一致

## 10. 本地离线评测

如果你当前没有跑起 MySQL / Chroma / Ollama，也可以先直接对本地文档语料做离线评测：

```bash
python backend/rag_eval/local_eval.py \
  --dataset backend/rag_eval/examples/local_eval_dataset.ship.json \
  --input data \
  --output backend/rag_eval/examples/local_eval_results.ship.json
```

或者用统一入口：

```bash
python backend/rag_eval/cli.py evaluate-local \
  --dataset backend/rag_eval/examples/local_eval_dataset.ship.json \
  --input data \
  --output backend/rag_eval/examples/local_eval_results.ship.json
```

这个模式的特点是：

- 不依赖 Flask / SQLAlchemy / Chroma / MySQL
- 直接读取本地文档
- 使用本地纯 Python 的 BM25 风格词法检索
- 仍然复用同一套 `Recall@K / Hit@K / MRR@K` 评测逻辑

适合在“线上环境还没完全起来”时，先把评测集和召回指标跑通。
