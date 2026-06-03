import os
import re
import litellm

# Set API base for local Qwen
os.environ["OPENAI_API_BASE"] = "http://localhost:8001/v1"
os.environ["OPENAI_API_KEY"] = "dummy"

original_snippet = """    def run(self, mod: ast.Module) -> None:
        \"\"\"Find all assert statements in *mod* and rewrite them.\"\"\"
        if not mod.body:
            # Nothing to do.
            return

        # We'll insert some special imports at the top of the module, but after any
        # docstrings and __future__ imports, so first figure out where that is.
        doc = getattr(mod, "docstring", None)
        expect_docstring = doc is None
        if doc is not None and self.is_rewrite_disabled(doc):
            return
        pos = 0
        item = None
        for item in mod.body:
            if (
                expect_docstring
                and isinstance(item, ast.Expr)
                and isinstance(item.value, ast.Constant)
            ):
                doc = item.value.value
                if self.is_rewrite_disabled(doc):
                    return
                expect_docstring = False"""

problem = "Rewrite fails when first expression of file is a number and mistaken as docstring"

system_prompt = (
    "You are a senior Python software engineer. Your task is to fix a bug in a file.\n"
    "You are given the issue description, the path of the file, and the file's content.\n\n"
    "Propose the change using a Search-and-Replace block. Format:\n\n"
    "<<<<<<< ORIGINAL\n"
    "[lines of original code to replace]\n"
    "=======\n"
    "[lines of replacement code]\n"
    ">>>>>>> SUGGESTED\n\n"
    "Ensure the ORIGINAL block matches the file content exactly, including whitespace.\n"
    "Do not output the entire file. Output ONLY the search-and-replace block."
)

user_prompt = f"ISSUE:\n{problem}\n\nFILE: src/_pytest/assertion/rewrite.py\n\nCODE SNIPPET:\n{original_snippet}"

print("Calling local Qwen for search-and-replace block...")
try:
    response = litellm.completion(
        model="openai/Qwen/Qwen2.5-72B-Instruct",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=500
    )
    print("Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error calling local Qwen: {e}")
