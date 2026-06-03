import pytest
from benchmarks.graders import grade_contract_task, grade_python_task, grade_sql_task

def test_grade_contract_task():
    prompt = "Summarize: 'Uptime is 99.9%. Term is 24 months. Total liability is capped at $50,000.'"
    
    # 100% correct response (contains 99.9%, 24 months, $50,000, liability)
    resp_perfect = "Uptime: 99.9%, Term: 24 months, Liability Cap: $50,000"
    score_perfect = grade_contract_task(prompt, resp_perfect)
    assert score_perfect == 5.0

    # 50% correct response (contains 99.9%, liability)
    resp_half = "Uptime is 99.9%, liability is limited."
    score_half = grade_contract_task(prompt, resp_half)
    assert 0.0 < score_half < 5.0

    # 0% correct response
    resp_bad = "No details here."
    score_bad = grade_contract_task(prompt, resp_bad)
    assert score_bad == 0.0

def test_grade_python_task():
    # mutable default arg
    prompt = "Fix: def append_item(item, items=[]): items.append(item); return items"
    # incorrect
    assert grade_python_task("py04", prompt, "def append_item(item, items=[]): ...") == 0.0
    # correct
    assert grade_python_task("py04", prompt, "def append_item(item, items=None):\n    if items is None:\n        items = []\n    items.append(item)") == 5.0

    # closure late binding
    prompt_closure = "Fix: funcs = [lambda: i for i in range(3)]"
    # incorrect
    assert grade_python_task("py07", prompt_closure, "funcs = [lambda: i for i in range(3)]") == 0.0
    # correct
    assert grade_python_task("py07", prompt_closure, "funcs = [lambda i=i: i for i in range(3)]") == 5.0

def test_grade_sql_task():
    # window functions
    prompt = "Schema: orders(id, customer_id, total, created_at). Use window function for top 3."
    # incorrect (missing partition by / row_number)
    assert grade_sql_task("sql01", prompt, "SELECT * FROM orders ORDER BY total DESC LIMIT 3") == 0.0
    # correct syntax
    assert grade_sql_task("sql01", prompt, "SELECT customer_id, total, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY total DESC) as rn FROM orders") == 5.0
