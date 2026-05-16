# 📸 MemoryCard 拾光卡

上传照片，自动提取主色调，生成精美卡片。

## 功能

- 🎨 自动提取主色调
- 📍 添加地点、时间
- ☁️ 自动获取天气
- 💭 记录心情
- 🌐 支持繁简转换

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 部署

[Streamlit Cloud](https://share.streamlit.io) 一键部署

## 项目结构

```
photo-card-gen/
├── app.py              # 主入口
├── requirements.txt    # 依赖
├── utils/photo_card.py # 核心逻辑 
└── fonts/              # 字体文件
```
