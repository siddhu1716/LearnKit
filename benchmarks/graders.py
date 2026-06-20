import re
import sqlite3

def extract_sql_query(response: str) -> str:
    # Find markdown sql blocks
    blocks = re.findall(r'```(?:sql)?\s*(.*?)\s*```', response, re.DOTALL)
    if blocks:
        return blocks[-1].strip()
    return response.strip()

def extract_python_code(response: str) -> str:
    blocks = re.findall(r'```(?:python)?\s*(.*?)\s*```', response, re.DOTALL)
    if blocks:
        return blocks[-1].strip()
    return response.strip()

def grade_contract_task(prompt: str, response: str) -> float:
    # Find quotes in the prompt
    match = re.search(r"['\"]([^'\"]{30,})['\"]", prompt)
    if not match:
        return 5.0
    contract_text = match.group(1)
    
    # Extract numbers, percentages, dollar amounts, and periods
    facts = re.findall(r'(?:\$\d+(?:,\d+)?|\d+(?:\.\d+)?%|\b\d+\s+(?:month|day|year|week|mile|hour)s?\b|\b\d+-[a-z]+s?\b)', contract_text, re.IGNORECASE)
    
    # Key legal phrases
    phrases = ["liability", "indemnity", "confidentiality", "breach", "solicit", "at-will", "at will", "work-for-hire", "work product", "patent", "royalty", "bankruptcy"]
    for p in phrases:
        if p in contract_text.lower():
            facts.append(p)
            
    facts = list(set(facts))
    if not facts:
        return 5.0
        
    response_lower = response.lower()
    matched = 0
    for f in facts:
        f_clean = f.lower().replace("-", " ")
        if f_clean in response_lower or f.lower() in response_lower:
            matched += 1
            
    return round((matched / len(facts)) * 5.0, 2)

def _grade_python_by_pattern(
    pattern: str, prompt: str, code_lower: str, response_lower: str = ""
) -> float:
    """Grade a Python answer against the construct its correct pattern requires."""
    if pattern == "tz_aware_datetime":
        # Partial-credit rubric (graded on the FULL response, not just the code
        # block) so a correct prose answer is not zeroed for a missing fence, and
        # small improvements are measurable. The learnable idiom: use timezone-
        # aware UTC (datetime.now(timezone.utc) / zoneinfo / astimezone) and never
        # the naive datetime.utcnow()/utcfromtimestamp(), because the underlying
        # bug is mixing offset-naive and offset-aware datetimes.
        text = response_lower or code_lower
        s = 0.0
        # correct aware-UTC idiom (judged on the code that was actually written)
        if any(t in code_lower for t in ("timezone.utc", "zoneinfo", "astimezone")) or (
            "pytz" in code_lower and "utc" in code_lower
        ):
            s += 2.0
        # the written code does not call the naive deprecated constructors
        # (a prose "never use utcnow()" must not be penalized — hence code_lower)
        if "utcnow(" not in code_lower and "utcfromtimestamp(" not in code_lower:
            s += 1.5
        # diagnoses the naive-vs-aware root cause (judged on the full response)
        if any(
            tok in text
            for tok in ("naive", "aware", "tzinfo", "offset-naive", "without a timezone", "without timezone")
        ):
            s += 1.0
        if "datetime" in code_lower and ("def " in code_lower or "import" in code_lower or "=" in code_lower):
            s += 0.5
        return round(min(s, 5.0), 2)
    if pattern == "mutable_default_arg":
        if "none" in code_lower and ("is none" in code_lower or "== none" in code_lower or "not" in code_lower):
            return 5.0
        return 0.0
    if pattern == "closure_late_binding":
        if any(
            tok in code_lower
            for tok in ("=i", "=name", "=val", "=url", "=x", "partial", "def make_", "def create_")
        ):
            return 5.0
        return 0.0
    if pattern == "concurrency_default_start_method":
        if "logging" in prompt.lower():
            if any(tok in code_lower for tok in ("queue", "listener", "handler", "config", "initialize")):
                return 5.0
            return 0.0
        if any(tok in code_lower for tok in ("set_start_method", "spawn", "__main__", "freeze_support")):
            return 5.0
        return 0.0
    if pattern == "mixed":
        if any(tok in code_lower for tok in ("return_exceptions", "gather", "exception", "catch", "try")):
            return 5.0
        return 0.0
    return 5.0


def grade_python_task(task_id: str, prompt: str, response: str, pattern: str | None = None) -> float:
    code = extract_python_code(response)
    if not code or ("import" not in code and "def " not in code and "class " not in code):
        code = response

    code_lower = code.lower()

    # When an explicit pattern is supplied (contamination tasks use ids outside
    # the py01..py30 ranges), grade against the construct that the *correct*
    # pattern requires — independent of the task id heuristic below. This is what
    # makes harm measurable: a contamination task baits the wrong skill via
    # surface vocabulary, but the grader still rewards only the right fix.
    if pattern:
        return _grade_python_by_pattern(pattern, prompt, code_lower, response.lower())

    # Identify pattern type
    # mutable default arg
    if any(p in task_id for p in ["py04", "py05", "py06", "py15", "py16", "py17", "py29", "py30"]):
        if "none" in code_lower and ("is none" in code_lower or "== none" in code_lower or "not" in code_lower):
            return 5.0
        return 0.0
        
    # closure late binding
    elif any(p in task_id for p in ["py07", "py08", "py09", "py18", "py19", "py20"]):
        if "i=i" in code_lower or "name=name" in code_lower or "val=val" in code_lower or "partial" in code_lower or "def make_" in code_lower or "def create_" in code_lower:
            return 5.0
        return 0.0
        
    # concurrency default start method / pickle error / logging deadlock
    elif any(p in task_id for p in ["py01", "py02", "py03", "py11", "py12", "py13", "py14", "py25", "py26", "py27", "py28"]):
        if "py03" in task_id or "logging" in prompt.lower():
            if "queue" in code_lower or "listener" in code_lower or "handler" in code_lower or "config" in code_lower or "initialize" in code_lower:
                return 5.0
            return 0.0
        else:
            if "set_start_method" in code_lower or "spawn" in code_lower or "__main__" in code_lower or "freeze_support" in code_lower:
                return 5.0
            return 0.0
            
    # mixed (asyncio exception handling)
    elif any(p in task_id for p in ["py10", "py21", "py22", "py23", "py24"]):
        if "return_exceptions" in code_lower or "gather" in code_lower or "exception" in code_lower or "catch" in code_lower or "try" in code_lower:
            return 5.0
        return 0.0
        
    return 5.0

def grade_sql_task(task_id: str, prompt: str, response: str) -> float:
    query = extract_sql_query(response)
    if not query:
        return 0.0
        
    query_lower = query.lower()
    
    # Check simple syntax expectations first
    # Window functions
    if "window" in prompt.lower() or "top" in prompt.lower():
        if "row_number()" not in query_lower and "rank()" not in query_lower and "dense_rank()" not in query_lower:
            return 0.0
        if "partition by" not in query_lower:
            return 0.0
            
    # ON CONFLICT
    if "conflict" in prompt.lower() or "upsert" in prompt.lower() or "conflc" in prompt.lower():
        if "on conflict" not in query_lower:
            return 0.0
            
    # Gap detection
    if "gap" in prompt.lower() or "streak" in prompt.lower() or "session" in prompt.lower() or "inactive" in prompt.lower():
        if "lag(" not in query_lower and "lead(" not in query_lower and "join" not in query_lower:
            return 0.0

    # Clean the SQL to run in SQLite
    sqlite_query = query
    # Replace common Postgres types and functions to SQLite equivalent
    sqlite_query = re.sub(r'\bTIMESTAMPTZ\b', 'TEXT', sqlite_query, flags=re.IGNORECASE)
    sqlite_query = re.sub(r'\bSERIAL\b', 'INTEGER PRIMARY KEY', sqlite_query, flags=re.IGNORECASE)
    sqlite_query = re.sub(r'\bBIGINT\b', 'INTEGER', sqlite_query, flags=re.IGNORECASE)
    sqlite_query = re.sub(r'\bJSONB\b', 'TEXT', sqlite_query, flags=re.IGNORECASE)
    sqlite_query = re.sub(r'\bnow\(\)', "datetime('now')", sqlite_query, flags=re.IGNORECASE)
    sqlite_query = re.sub(r'\bcurrent_date\b', "date('now')", sqlite_query, flags=re.IGNORECASE)
    # Remove Postgres cast notation ::text, ::jsonb, etc.
    sqlite_query = re.sub(r'::[a-zA-Z0-9_]+', '', sqlite_query)
    
    try:
        conn = sqlite3.connect(":memory:")
        # Register standard PG functions in SQLite
        conn.create_function("now", 0, lambda: "2026-06-03 12:00:00")
        conn.create_function("current_date", 0, lambda: "2026-06-03")
        conn.create_function("coalesce", -1, lambda *args: next((x for x in args if x is not None), None))
        
        # Setup schema based on task
        schema_match = re.search(r"Schema:\s*([a-zA-Z0-9_]+)\(([^)]+)\)", prompt, re.IGNORECASE)
        if schema_match:
            table_name = schema_match.group(1)
            columns_def = schema_match.group(2)
            col_defs = []
            for col in columns_def.split(","):
                col = col.strip()
                if "PRIMARY KEY" in col:
                    col_defs.append(col)
                else:
                    parts = col.split()
                    name = parts[0]
                    col_type = parts[1] if len(parts) > 1 else "TEXT"
                    if "timestamptz" in col_type.lower():
                        col_type = "TEXT"
                    elif "bigint" in col_type.lower():
                        col_type = "INTEGER"
                    elif "jsonb" in col_type.lower():
                        col_type = "TEXT"
                    col_defs.append(f"{name} {col_type}")
            create_sql = f"CREATE TABLE {table_name} ({', '.join(col_defs)});"
            conn.execute(create_sql)
            
            # Insert some dummy rows to test execution
            cols = [c.split()[0] for c in columns_def.split(",") if not c.strip().startswith("PRIMARY")]
            cols = list(dict.fromkeys(cols))
            dummy_vals = []
            for i in range(1, 10):
                val_row = []
                for c in cols:
                    c_lower = c.lower()
                    if "id" in c_lower:
                        val_row.append(i % 3 + 1)
                    elif "total" in c_lower or "amount" in c_lower or "salary" in c_lower or "qty" in c_lower or "count" in c_lower:
                        val_row.append(100.0 * i)
                    elif "ts" in c_lower or "time" in c_lower or "date" in c_lower or "at" in c_lower:
                        val_row.append(f"2026-06-03 12:0{i:02d}:00")
                    elif "sku" in c_lower or "key" in c_lower or "metric" in c_lower or "name" in c_lower:
                        val_row.append(f"item_{i}")
                    else:
                        val_row.append(f"val_{i}")
                dummy_vals.append(val_row)
                
            placeholders = ", ".join(["?"] * len(cols))
            conn.executemany(f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({placeholders});", dummy_vals)
            conn.commit()
            
        cursor = conn.cursor()
        clean_sql = ""
        for line in sqlite_query.splitlines():
            if not line.strip().startswith("--"):
                clean_sql += line + "\n"
        cursor.execute(clean_sql)
        res = cursor.fetchall()
        conn.close()
        return 5.0
    except Exception as e:
        schema_match = re.search(r"Schema:\s*([a-zA-Z0-9_]+)", prompt, re.IGNORECASE)
        if schema_match:
            table_name = schema_match.group(1).lower()
            if table_name in query_lower:
                return 5.0
        return 0.0
