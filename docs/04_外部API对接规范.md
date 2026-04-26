# 《外部 API 对接规范》

> **版本**：v1.0
> **适用范围**：LLM 调用 + 知识库调用

---

## 一、LLM 调用规范（Anthropic Claude）

### 1.1 基本参数

| 项 | 值 |
|----|----|
| SDK | `anthropic` (Python) |
| 默认模型 | `claude-sonnet-4-5` |
| 最大输出 | 2048 tokens |
| 超时 | 60s |
| 重试 | 指数退避 3 次（1s → 2s → 4s） |

### 1.2 Prompt 模板

```python
SYSTEM_PROMPT = """你是一名资深农业技术推广顾问，服务对象是中国农户。

【行为准则】
1. 回答基于用户的【区域】【作物】【物候期】【长期记忆】【检索到的资料】
2. 提供方案时必须说明：操作步骤、预期效果、可能风险
3. 涉及农药/化肥的建议必须给出：剂量范围、安全间隔期
4. 不确定时明确说"我不确定"，不要臆造数据
5. 语言简洁通俗，避免学术词汇，适合 50 岁左右农户理解
6. 篇幅控制在 300 字以内，除非用户追问细节

【输出格式】
- 结论先行
- 步骤编号
- 必要时附警告 ⚠️
"""

USER_PROMPT_TEMPLATE = """
【位置】{region_full_name}
【作物】{crop_name}
【当前物候期】{phenology_stage}（{stage_description}）
【您的地块信息】
{memory_items}

【参考资料】
{knowledge_snippets}

【问题】
{question}
"""
```

### 1.3 Function Calling（记忆抽取）

```python
MEMORY_EXTRACTION_TOOL = {
    "name": "propose_memory_update",
    "description": "若用户在本轮对话中透露了地块/种植习惯的新事实，调用此工具提出记忆更新",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "enum": [
                                "soil_type", "variety", "irrigation",
                                "pest_history", "fertilizer_habit",
                                "terrain", "planting_date", "area", "other"
                            ]
                        },
                        "value": {"type": "string"},
                        "action": {"enum": ["add", "update"]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "reason": {"type": "string"}
                    },
                    "required": ["key", "value", "action", "confidence"]
                }
            }
        }
    }
}
```

### 1.4 Prompt Caching

为降低成本：
- System prompt 设置 `cache_control = ephemeral`（长期缓存 5 分钟）
- 对话历史超过 10 轮时，将前 N 轮打包进缓存块

### 1.5 环境变量

```
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-4-5
LLM_MAX_TOKENS=2048
LLM_TIMEOUT_SEC=60
```

---

## 二、知识库 API 对接规范

> 此接口由客户提供。下面是通用 RESTful 对接模板，收到具体接口文档后按此模板适配。

### 2.1 基本参数

| 项 | 值 |
|----|----|
| 协议 | HTTPS REST |
| 认证 | `Authorization: Bearer <API_KEY>` |
| 内容类型 | `application/json; charset=utf-8` |
| 超时 | 15s |
| 重试 | 2 次 |

### 2.2 检索接口（搜索 Top-K 文档）

**请求**

```
POST {KNOWLEDGE_API_BASE_URL}/search
{
  "query": "玉米大喇叭口期追肥建议",
  "filters": {
    "crop": "maize",
    "region": "huabei_plain"
  },
  "top_k": 5
}
```

**响应**

```json
{
  "items": [
    {
      "doc_id": "doc_123",
      "title": "玉米高产栽培技术",
      "snippet": "大喇叭口期追施尿素 15-20 kg/亩…",
      "source": "农业农村部种植业司",
      "score": 0.89,
      "url": "https://..."
    }
  ],
  "total": 5
}
```

### 2.3 问答接口（若知识库支持直接 QA）

**请求**

```
POST {KNOWLEDGE_API_BASE_URL}/qa
{
  "question": "…",
  "context": { "region": "…", "crop": "…" }
}
```

**响应**

```json
{
  "answer": "...",
  "references": [{"doc_id":"doc_123","title":"…"}]
}
```

### 2.4 我方使用策略（RAG）

1. 先调 **知识库 search** 取 Top-3~5 片段
2. 片段拼入 LLM Prompt 的"参考资料"部分
3. LLM 回答中引用来源（显式标注 `[1]`, `[2]` 并在响应中返回 references）

### 2.5 环境变量

```
KNOWLEDGE_API_BASE_URL=https://your-kb.example.com/api
KNOWLEDGE_API_KEY=xxxx
KNOWLEDGE_TOP_K=5
KNOWLEDGE_TIMEOUT_SEC=15
```

### 2.6 客户需补充确认的字段

待您提供接口文档后，需要确认：

- [ ] 实际 base URL
- [ ] 鉴权方式（Bearer / AppId+Sign / 其他）
- [ ] 请求字段名（`query` vs `q` vs `question`）
- [ ] 过滤器字段与枚举值
- [ ] 是否支持流式响应
- [ ] 限流策略（QPS）

> 拿到文档后只需改 `backend/app/services/knowledge.py` 中的请求/响应映射函数。

---

## 三、错误与降级

| 外部依赖 | 失败时策略 |
|---------|-----------|
| LLM 不可达 | 返回友好提示"系统繁忙，请稍后再试"，记日志 |
| 知识库不可达 | 降级为**无 RAG 模式**（仅 LLM），并在回答末尾提示"当前无法检索知识库来源" |
| LLM 输出超时 | 截断 + "回答被截断，请追问" |
| 记忆抽取失败 | 跳过（不影响主回答） |

---

## 四、监控指标

```
llm_call_count_total            # LLM 调用计数
llm_call_duration_seconds       # 耗时分布
llm_call_error_total            # 错误计数
knowledge_call_duration_seconds
knowledge_call_error_total
memory_proposal_count           # 每日记忆候选产生数
memory_proposal_acceptance_rate # 用户接受率
```

通过 `/metrics` 暴露给 Prometheus（生产环境）。
