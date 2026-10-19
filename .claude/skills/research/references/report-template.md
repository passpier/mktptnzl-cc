# Report template (`research/<slug>/report.md`)

What `hooks/check_report.py` enforces on this file:
- Every line that contains a number needs a `[E#]` citation.
- Numbers are allowed without citations in three places: under 放棄條件 / 驗證實驗 / 來源附錄 headings, and on lines tagged `[假設]` or `[門檻]`.
- Every bullet under 結論 needs ≥2 source_groups and a `信心:` label.
- Tier D is allowed only under 資料缺口.

```markdown
# <App / idea> 市場與行銷研究 — <YYYY-MM-DD>

> 模式：idea | app | niche · 市場：TW / US · 商店：iOS / Google Play · 資料抓取日：見來源附錄

## 結論與信心等級
- **判定：GO / PIVOT / NO-GO** — <一句話理由> [E3, E12]，信心: Med
- <結論 2> [E5, E9]，信心: High
- <結論 3> [E7, E14]，信心: Low — 若 <什麼證據> 出現則翻轉

## 放棄條件檢核
| 條件（研究前設定） | 結果 | 通過？ |
|---|---|---|
| <criterion> | <observed, cite in the 結果 column when it is a number [E#]> | ✅/❌ |

## 市場潛力評分
| 維度 | TW | US | 依據 | 信心 |
|---|---|---|---|---|
| Demand | 3/5 [E4] | 4/5 [E6] | Google 量 vs App Store hints 分開列 | Med |
| Competition | … | … | … | … |
| Monetization | … | … | … | … |
| Gap | … | … | … | … |
| Solo-reachability | … | … | … | … |

## 競品
| App | 商店/市場 | 評分數 | 平均 | 最後更新 | 價格/IAP | 動能代理 |
|---|---|---|---|---|---|---|

## 使用者痛點（評論挖掘）
- 群集、占比、原話引用 [E#]；標註樣本偏誤

## 需求訊號
- Google 搜尋（網頁需求）[E#] ／ App Store 站內（hints、ASA popularity）[E#] ／ 社群討論 [E#] — 分開呈現

## 行銷切入點（低預算 GTM）
<!-- idea：lean-gtm 短版；app：lean-gtm 完整版；niche：刪除本節 -->
- 前 3 渠道：理由 [E#]、成本、第一個實驗

## 偏誤與限制
- 評論負偏、社群少數聲音、榜單倖存者、TW/US 不可互推…

## 資料缺口
- <未知事項>：最便宜取得方式 <實驗>，成本 <…>（D 級線索只能出現在這裡 [E#]）

## 下一步驗證實驗
| 實驗 | 假設 | 設定 | 成本 | 期間 | 成功門檻 | 放棄門檻 |
|---|---|---|---|---|---|---|

## 來源附錄
<paste output of: uv run scripts/ledger.py render <slug> --report research/<slug>/report.md>
```
