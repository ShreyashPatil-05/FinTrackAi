# DSA Concepts in FinTrack

## Already Implemented (Implicit)

| Concept | File | How |
|---|---|---|
| B-Tree Index | `dashboard/models.py`, `expenses/models.py` | 6 composite indexes on user+date, user+category — O(log n) lookup |
| Hashing | `expenses/webhook.py` | HMAC-SHA256 signature verification |
| Hashing | `accounts/views.py` | UUID token generation for email verification |
| Hash Map | `accounts/views.py` | Rate limiting via `cache.get(cache_key)` — O(1) lookup |
| Set | `dashboard/utils.py` | `set([d.year for d in year_dates])` — deduplication in `get_available_years()` |
| Chunking | `expenses/views.py` | Django Paginator — divide list into fixed-size pages |
| Clamping | `dashboard/utils.py` | `max(0, min(100, savings_rate))` — bounded range in `calculate_savings_rate()` |

---

## Can Be Explicitly Implemented

### `dashboard/utils.py`
| Concept | Function | Complexity Gain |
|---|---|---|
| Sliding Window | `rolling_7day_average(daily_amounts)` | O(n) vs O(n×w) naive |
| Prefix Sum | `cumulative_spending(daily_amounts)` | O(n) precompute, O(1) range queries |
| Binary Search | `find_month_index(sorted_years, target)` | O(log n) vs O(n) linear scan |
| LRU Cache | `@lru_cache on get_available_years()` | Avoid repeated DB hits |

### `dashboard/views/dashboard.py`
| Concept | Use Case | Complexity Gain |
|---|---|---|
| Min-Heap | `heapq.nlargest(5, cat_data)` for top categories | O(k log n) vs O(k log k) full sort |
| Frequency Map | `Counter(expenses.values_list('category'))` | O(n) single pass category count |
| Prefix Sum | Cumulative spending array for running total chart | O(n) precompute |
| Sliding Window | 7-day rolling average for forecast smoothing | O(n) vs O(n×w) |

### `dashboard/views/budget.py`
| Concept | Use Case | Complexity Gain |
|---|---|---|
| Two Pointers | Merge sorted budget vs actual category lists | O(n) single pass vs O(n²) nested |
| Greedy | Suggest which categories to cut to stay within budget | O(n log n) |

### `dashboard/views/savings.py`
| Concept | Use Case | Notes |
|---|---|---|
| Priority Queue | Rank goals by urgency (deadline + progress) | `heapq` based |
| Graph (DAG) | Goal dependencies (emergency fund before vacation) | Directed acyclic graph |

### `dashboard/views/subscriptions.py`
| Concept | Use Case | Complexity Gain |
|---|---|---|
| Min-Heap | `heapq.nsmallest()` for next N billing dates | O(k log n) vs O(n log n) full sort |

### `dashboard/views/export.py`
| Concept | Use Case | Complexity Gain |
|---|---|---|
| Merge Sort | Merge income + expenses into one date-sorted timeline | O(n log n), stable |
| Two Pointers | Merge two sorted date-ordered lists | O(n) single pass |

### `expenses/views.py`
| Concept | Use Case | Complexity Gain |
|---|---|---|
| Binary Search | Date range search on sorted expense list | O(log n) vs O(n) |
| Hash Set | `selected_categories` deduplication | O(1) lookup vs O(n) list |

### `expenses/webhook.py`
| Concept | Use Case | Notes |
|---|---|---|
| Hash Map | Category mapping dict for O(1) lookup | Replace list search |

### `accounts/views.py`
| Concept | Use Case | Notes |
|---|---|---|
| Stack | Process expired tokens LIFO in cleanup | Batch processing pattern |

### `accounts/management/commands/cleanup_expired_tokens.py`
| Concept | Use Case | Notes |
|---|---|---|
| Stack/Queue | Batch process expired tokens | LIFO stack or FIFO queue |
| Partition | Split tokens into expired/valid | Single pass O(n) |

### `fintrack/middleware.py`
| Concept | Use Case | Complexity Gain |
|---|---|---|
| Trie | CSP domain prefix matching | O(m) per lookup vs O(n×m) |
| Hash Set | Allowed origins O(1) lookup | O(1) vs O(n) list scan |

---

## Priority — Best to Implement First

| Priority | Concept | File | Why |
|---|---|---|---|
| 1 | Sliding Window | `dashboard/utils.py` | Natural fit, improves forecast feature |
| 2 | Min-Heap | `dashboard/views/dashboard.py` | Replaces existing DB sort cleanly |
| 3 | Prefix Sum | `dashboard/utils.py` | Adds visible cumulative chart feature |
| 4 | Two Pointers | `dashboard/views/budget.py` | Clean algorithmic improvement |
| 5 | Priority Queue | `dashboard/views/savings.py` | Adds goal urgency ranking feature |

---

## Interview Answer

> "DSA is applied throughout at both the systems level and application level.
> The most direct examples are the B-tree indexes I added on frequently queried
> fields — reducing lookups from O(n) full scans to O(log n). I also used hashing
> directly for HMAC webhook verification and UUID token generation, and a hash map
> via Django's cache layer for rate limiting. Additional opportunities exist to
> implement sliding window for rolling averages, min-heap for top category extraction,
> and two pointers for merging sorted budget vs actual spend lists."
