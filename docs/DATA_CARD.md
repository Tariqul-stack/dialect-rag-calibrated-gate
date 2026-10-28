# Data card

| File | Content |
|---|---|
| `data/knowledge_base/AISIS_KnowledgeBase_v1.xlsx` | 136 passages, 4 topics (health, agriculture, weather, government services). No passages for unanswerable topics by design. 14 passages flagged `check` (unverified facts). |
| `data/queries/AISIS_Base_Queries_v1.xlsx` | 200 base queries in standard Bangla (90 answerable, 40 tool, 30 unanswerable, 25 ambiguous, 15 high-risk), 5 blocks of 40. Columns for Barishal, Chittagong, Rajshahi, Rangpur, Natore (filled by native-speaking friends; drafts only for block 1 Barishal/Rajshahi/Rangpur). Tools sheet: find_nearest_clinic, get_crop_market_price, get_weather_forecast, check_service_status. |
| `data/dev/AISIS_DevSet_Pilot_v1.xlsx` | 60-row pilot. |
| `data/dev/AISIS_DevSet_v1.xlsx` | 400-row dev set, `split` fit/val, `dialect_method` hand/rule_based, `dialect_differs` yes/no, gold labels for action/supported/specific/emergency/tool, gold args, wrong-passage for abstention tests. |
| `data/gate/gate_questions_v{1,2}.json` | Typed d1 questions (action, supported, specific, emergency, tool); v2 rewords only `emergency`. |

## Provenance and limitations
- All queries, labels, KB passages and synthetic dialect text were written by an LLM (Claude), not collected from users.
- Dialect text in the dev set is partly rule-based and **not validated by native speakers**; it is for tuning only.
- The final evaluation set will be native-speaker translations (same base queries, own dialect, natural rather than word-for-word) with `gold_passage_id` pasted into column I.
- Medical/agricultural content is for research evaluation, not advice.
- Builders in `src/aisis/data_build/` regenerate the committed files byte-for-content identically (verified).
