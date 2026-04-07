# COOVOAMAE Amazon Ads Data

每日自动拉取广告数据，供 Cheetah Agent 分析使用。

## 数据结构
- `data/summary/latest.json` — Agent 日常分析读这个（几KB）
- `data/summary/weekly_trend.json` — 7天趋势
- `data/daily/YYYY-MM-DD/` — 全量 CSV（搜索词/关键词/活动）
- `data/actions/YYYY-MM-DD.json` — 优化操作记录

## 定时任务
每日 UTC 08:00（北京 16:00）自动拉取前一天数据。
