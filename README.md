# Merlin LINE AI News Bot

Azure Functions application that generates AI and cybersecurity news digests,
creates a workplace-English lesson, stores the results in Azure Blob Storage,
and serves them through a LINE webhook.

![alt text](image.png)

![alt text](image-1.png)

![alt text](image-2.png)

![alt text](image-3.png)

## 架構風格

本專案採用**模組化單體（Modular Monolith）與分層架構**。所有功能部署在同一個
Azure Function App，但程式碼依責任拆成獨立模組。設計借用了 Clean Architecture、
Dependency Injection 與 Repository Pattern 的概念，同時避免在目前規模下建立過多抽象層。

```text
Azure Functions / LINE
          │
          ▼
┌─────────────────────┐
│ function_app.py     │  Composition Root / Trigger
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Application Layer   │
│ jobs.py             │
│ line_service.py     │
└──────┬───────┬──────┘
       ▼       ▼
┌──────────┐ ┌──────────────┐
│ feeds.py │ │ generation.py│  External service adapters
└──────────┘ └──────────────┘
       │       │
       └───┬───┘
           ▼
┌─────────────────────┐
│ storage.py          │  Azure Blob repository
└─────────────────────┘

models.py     → 共用資料契約與驗證
prompts.py    → AI prompt 定義
constants.py  → RSS、Blob 名稱與時區
news_views.py → LINE Flex Message 表現層
```

### Composition Root 與依賴注入

`function_app.py` 是唯一的正式應用程式入口。它負責建立 Azure OpenAI、Blob repository、
LINE service 與排程 job，再把這些 dependency 傳給需要它們的物件。其他模組不自行讀取
環境變數或建立 global client。

```python
repository = BlobJsonRepository(...)
generator = ContentGenerator(...)
daily_content_job = DailyContentJob(generator, repository)
line_service = LineBotService(..., repository)
```

這種方式讓依賴關係明確可見，也讓服務更容易替換和測試。

### 主要資料流

LINE 查詢流程：

```text
LINE webhook
  → function_app.callback()
  → LineBotService
  → BlobJsonRepository.load()
  → news_views 建立 Flex Message
  → LINE Messaging API
```

定時產生內容流程：

```text
Azure Timer
  → DailyContentJob.run()
  → feeds 抓取並清理 RSS
  → ContentGenerator 呼叫 Azure OpenAI
  → Pydantic 驗證輸出與新聞來源
  → BlobJsonRepository 儲存結果
```

耗時的 RSS 與 AI 工作由 Timer 預先完成；LINE webhook 只讀取已生成的結果，因此能快速回覆，
也能降低 webhook timeout 的風險。

### 模組責任

| 模組 | 責任 |
| --- | --- |
| `function_app.py` | Azure Functions trigger 與 dependency wiring |
| `config.py` | 讀取並驗證環境變數 |
| `models.py` | Pydantic 資料結構及商業規則 |
| `feeds.py` | RSS 下載、解析、日期過濾與去重 |
| `generation.py` | Prompt 組裝、structured output 與來源驗證 |
| `storage.py` | 封裝 Azure Blob Storage 存取 |
| `jobs.py` | 協調每日內容產生流程 |
| `line_service.py` | LINE 指令路由、資料讀取與回覆 |
| `news_views.py` | 將資料轉換成 LINE Flex Message |
| `tests/` | 驗證核心規則，避免修改造成回歸 |

### 設計原則

- **單一責任**：RSS、AI、儲存、LINE 與畫面組裝分開維護。
- **外部 I/O 留在邊界**：網路、OpenAI、Blob 和 LINE SDK 集中在 adapter/service 模組。
- **資料進入時立即驗證**：Pydantic 驗證格式，provenance validation 防止模型捏造來源。
- **錯誤不靜默忽略**：排程失敗會向 Azure 拋出，webhook 則轉成適合使用者的回覆。
- **顯式依賴優於隱藏 global state**：需要的服務由 constructor 傳入。
- **適度抽象**：目前直接使用具體 repository；等出現第二種儲存實作時再抽出 Protocol。

這不是嚴格的完整 Clean Architecture，而是針對目前專案規模保留重要邊界的務實版本。
新增功能時，通常依序擴充 model、prompt/generator、job、view、LINE command 和 tests，
不應把新的商業邏輯放回 `function_app.py`。

## Project layout

- `function_app.py`: Azure Functions triggers and dependency wiring only.
- `merlin_bot/config.py`: environment configuration validation.
- `merlin_bot/feeds.py`: RSS ingestion and normalization.
- `merlin_bot/generation.py`: structured Azure OpenAI generation.
- `merlin_bot/storage.py`: Blob Storage JSON repository.
- `merlin_bot/jobs.py`: scheduled content workflow.
- `merlin_bot/line_service.py`: LINE command routing and replies.
- `news_views.py`: LINE Flex Message presentation builders.
- `tests/`: unit tests that do not contact external services.

## Local setup

1. Create a supported Python virtual environment.
2. Install `requirements.txt`.
3. Copy `local.settings.example.json` to `local.settings.json` and replace its placeholders.
4. Start Azurite when using `UseDevelopmentStorage=true`.
5. Run `func start`.

Run tests with:

```powershell
python -m unittest discover -s tests -v
```

The timer schedule is `0 0 */6 * * *`, which runs every six hours. Azure timer
schedules use UTC unless the Function App timezone is configured separately.
