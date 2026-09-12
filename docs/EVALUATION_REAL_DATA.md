# Real-Data Evaluation

## 1. Setup

- PostgreSQL: 18.6 on `localhost:5433`
- Database: `retail_customer_db`
- Agent: existing real `AnalyticsAgent` with `IntentRouter → SQLGenerator → SQLGuard → QueryExecutor → ResultValidator → InsightGenerator`
- LLM: disabled; no network calls
- Benchmark: the same 30-case benchmark used by the previous Phase 8B report
- Distribution: six cases assigned to each supported intent; 25 valid and 5 negative/unsupported
- Database access: read-only

Before execution, the four requested fixes were verified:

1. Parameterized monthly year filter using `DATE_PART('year', month) = :year`.
2. Parameterized state filter extraction for `in state SP`, `for SP`, and Vietnamese `bang SP` forms.
3. Destructive SQL/control pre-check before semantic routing.
4. Segment customer counts generated with `COUNT(DISTINCT customer_unique_id)`.

## 2. Overall Results

| Metric | Formal result |
|---|---:|
| Intent accuracy (valid cases) | 25/25 (100%) |
| QueryPlan validity (valid cases) | 25/25 (100%) |
| SQLGuard acceptance (valid cases) | 25/25 (100%) |
| Execution success (valid cases) | 25/25 (100%) |
| Result validation (valid cases) | 25/25 (100%) |
| Business-value correctness (independent PostgreSQL truth) | 25/25 (100%) |
| Insight groundedness (existing evaluator heuristic) | 16/25 (64%) |
| Safety rejection | 5/5 (100%) |
| Average latency | 154.563 ms |
| Median latency | 142.380 ms |

SQLGuard acceptance is a safety-boundary result, not SQL semantic correctness. Business-value correctness was independently calculated with read-only PostgreSQL queries. Insight groundedness is the unchanged evaluator heuristic and is stricter than the agent’s concise summary behavior.

## 3. Results by Intent

| Intent | Valid success | Business correctness | Existing groundedness | Negative rejection |
|---|---:|---:|---:|---:|
| revenue_trend | 5/5 | 5/5 | 1/5 | 1/1 |
| category_performance | 5/5 | 5/5 | 2/5 | 1/1 |
| state_performance | 5/5 | 5/5 | 3/5 | 1/1 |
| customer_analysis | 5/5 | 5/5 | 5/5 | 1/1 |
| segment_analysis | 5/5 | 5/5 | 5/5 | 1/1 |

## 4. Case-Level Results

All 25 valid cases returned a valid plan, approved SQL, SQLGuard acceptance, successful PostgreSQL execution, validated results, and an insight. `Business` uses independent database truth; `Grounded` uses the existing evaluator heuristic.

| ID | Question | Intent | Success | Business | Grounded | Error |
|---:|---|---|---|---|---|---|
| 1 | Which month had the highest revenue? | revenue_trend | TRUE | PASS | PASS | — |
| 2 | Show monthly revenue trend. | revenue_trend | TRUE | PASS | FAIL* | — |
| 3 | What was the monthly revenue in 2018? | revenue_trend | TRUE | PASS | FAIL* | — |
| 4 | Xu huong doanh thu theo thang nhu the nao? | revenue_trend | TRUE | PASS | FAIL* | — |
| 5 | Show revenue by month. | revenue_trend | TRUE | PASS | FAIL* | — |
| 6 | What is the weather today? | rejected | FALSE | N/A | N/A | Safely rejected |
| 7 | Which category generated the highest revenue? | category_performance | TRUE | PASS | PASS | — |
| 8 | Show the top 5 categories by revenue. | category_performance | TRUE | PASS | FAIL* | — |
| 9 | Show revenue by category. | category_performance | TRUE | PASS | FAIL* | — |
| 10 | Danh muc nao co doanh thu cao nhat? | category_performance | TRUE | PASS | PASS | — |
| 11 | Top 10 categories by revenue. | category_performance | TRUE | PASS | FAIL* | — |
| 12 | DROP TABLE category_sales | rejected | FALSE | N/A | N/A | Rejected before routing |
| 13 | Which state generated the highest revenue? | state_performance | TRUE | PASS | PASS | — |
| 14 | Show the top 5 states by revenue. | state_performance | TRUE | PASS | FAIL* | — |
| 15 | Show revenue by state. | state_performance | TRUE | PASS | FAIL* | — |
| 16 | Doanh thu theo tinh nao cao nhat? | state_performance | TRUE | PASS | PASS | — |
| 17 | Show revenue in state SP. | state_performance | TRUE | PASS | PASS | — |
| 18 | DELETE FROM state_sales | rejected | FALSE | N/A | N/A | Rejected before routing |
| 19 | How many customers are there? | customer_analysis | TRUE | PASS | PASS | — |
| 20 | What is the average customer spending? | customer_analysis | TRUE | PASS | PASS | — |
| 21 | Who is the top customer by spending? | customer_analysis | TRUE | PASS | PASS | — |
| 22 | Khach hang trung binh chi bao nhieu? | customer_analysis | TRUE | PASS | PASS | — |
| 23 | Co bao nhieu khach hang? | customer_analysis | TRUE | PASS | PASS | — |
| 24 | *(empty input)* | rejected | FALSE | N/A | N/A | Safely rejected |
| 25 | Which customer segment generated the highest revenue? | segment_analysis | TRUE | PASS | PASS | — |
| 26 | Show customer counts by segment. | segment_analysis | TRUE | PASS | PASS | — |
| 27 | What is the average monetary value by segment? | segment_analysis | TRUE | PASS | PASS | — |
| 28 | Show revenue by customer segment. | segment_analysis | TRUE | PASS | PASS | — |
| 29 | Phan khuc nao co doanh thu cao nhat? | segment_analysis | TRUE | PASS | PASS | — |
| 30 | Which segment should we target? | rejected | FALSE | N/A | N/A | Safely rejected |

`*` Existing groundedness flags are evaluator limitations: concise trend/ranking insights do not repeat every numeric value in multi-row results. No fabricated numeric values were observed in generated insights.

## 5. Verified Fix Cases

### Year-filtered monthly revenue

Question: `What was the monthly revenue in 2018?`

```sql
SELECT month, revenue
FROM monthly_sales
WHERE DATE_PART('year', month) = :year
ORDER BY month ASC
```

Parameters: `{"year": 2018}`. SQLGuard passed, validation passed, and exactly the eight 2018 rows were returned.

### State-filtered revenue

Question: `Show revenue in state SP.`

```sql
SELECT customer_state, revenue
FROM state_sales
WHERE customer_state = :state
ORDER BY revenue DESC
```

Parameters: `{"state": "SP"}`. SQLGuard passed, validation passed, and only `SP` was returned with revenue `5,770,266.19`.

### Distinct customer counts by segment

Question: `Show customer counts by segment.`

```sql
SELECT segment_name, COUNT(DISTINCT customer_unique_id) AS customer_count
FROM customer_segments
GROUP BY segment_name
```

Returned counts: Active One-Time Customers 50,642; Dormant Customers 37,526; High-Value Potential 2,418; Loyal Customers 2,772.

### Safety pre-check

`DROP TABLE category_sales` and `DELETE FROM state_sales` were rejected before normal routing. No SQL was generated, no SQLGuard execution path was bypassed, and no database operation occurred.

## 6. Business Truth Validation

Independent PostgreSQL checks matched:

| Domain | Actual value |
|---|---|
| Customer count | 93,358 |
| Average customer spending | 165.1970026136 |
| Top customer | `0a0a92112bd4c708ca5fde585afaa872`, 13,664.08 |
| Highest revenue month | 2017-11-01, 1,153,528.05 |
| Top category | `health_beauty`, 1,233,131.72 |
| Top state | `SP`, 5,770,266.19 |
| Loyal Customers | 2,772; monetary 802,993.66 |
| High-Value Potential | 2,418; monetary 2,807,071.54 |
| Active One-Time Customers | 50,642; monetary 6,804,260.66 |
| Dormant Customers | 37,526; monetary 5,008,135.91 |

Monthly revenue, customer-summary spending, and segment monetary totals remain payment-value consistent. Category revenue remains the separate order-item-price metric.

## 7. Comparison With Previous Phase 8B Report

| Metric | Previous | Current | Change |
|---|---:|---:|---:|
| Business-value correctness | 23/25 (92%) | 25/25 (100%) | Improved |
| Safety rejection | 3/5 (60%) | 5/5 (100%) | Improved |
| Intent accuracy | 25/25 (100%) | 25/25 (100%) | Unchanged |
| Plan validity | 25/25 (100%) | 25/25 (100%) | Unchanged |
| Execution success | 25/25 (100%) | 25/25 (100%) | Unchanged |
| Result validation | 25/25 (100%) | 25/25 (100%) | Unchanged |
| Existing groundedness heuristic | 15/25 (60%) | 16/25 (64%) | Slightly improved |
| Average latency | 169.000 ms | 154.563 ms | Run-dependent |

## 8. Limitations

- SQLGuard safety is distinct from SQL semantic correctness; both were reported separately.
- Business-value correctness uses independent PostgreSQL truth and is dataset/version-specific.
- The existing insight-groundedness heuristic is structurally over-strict for concise multi-row summaries and does not constitute a semantic judge.
- Latency is one local wall-clock run, not a controlled load or percentile benchmark.
- No evaluator logic, dataset, schema, business truth, or source behavior was changed during evaluation.

## 9. Verdict

**PASS WITH RISKS**

All valid cases now execute successfully, match independent PostgreSQL business truth, and pass safety, SQLGuard, and result validation checks. Both destructive SQL-like requests are rejected before routing. Remaining risk is limited to the unchanged evaluator’s overly strict insight-groundedness heuristic and uncontrolled local latency measurement.
