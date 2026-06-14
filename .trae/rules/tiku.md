项目框架
SmartQbank_Project/
├── app.py                # 项目入口：Streamlit 界面与路由逻辑
├── config.py             # 配置管理：API Key, 数据库路径, 默认难度比例
├── db/
│   └── qbank.db          # SQLite 数据库文件（自动生成）
├── core/
│   ├── __init__.py
│   ├── extractor.py      # 模块1：Docx 文本与表格提取
│   ├── classifier.py     # 模块2：AI 结构化与标签自动打标
│   ├── retriever.py      # 模块3：混合检索与组卷逻辑
│   └── processor.py      # 模块4：实时解析生成与回写
├── memory/
│   └── chat_history.py   # 模块5：短期对话与长期错题记忆管理
├── data/
│   └── uploads/          # 存放用户上传的原始 .docx 文件
└── utils/
    └── formatter.py      # 模块6：Markdown 与 LaTeX 格式化处理
在生成文本内容时使用中文
生成的代码要减少冗余，避免重复逻辑
不要对代码进行过多注释