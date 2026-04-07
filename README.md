# COOVOAMAE Amazon Ads Data

每日自动拉取广告数据，供 Cheetah Agent 分析使用。

## 数据结构
- `data/summary/latest.json` — 最新日摘要（Agent主要读这个）
- `data/summary/weekly_trend.json` — 7天趋势
- `data/daily/YYYY-MM-DD/` — 全量CSV（搜索词/关键词/活动）
- `data/actions/YYYY-MM-DD.json` — 优化操作记录

## 手动拉取
```bash
python3 scripts/daily_pull.py           # 昨天
python3 scripts/daily_pull.py 2026-04-05 # 指定日期
```
