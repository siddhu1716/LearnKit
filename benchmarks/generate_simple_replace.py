import json
import random
from pathlib import Path

random.seed(42)

def generate_task(task_id, num_rules):
    # Alphabet characters
    chars = "abcdefghijklmnopqrstuvwxyz"
    
    # Generate random input corpus (5 strings of length 3-5)
    inputs = []
    for _ in range(5):
        length = random.randint(3, 5)
        inputs.append("".join(random.choice(chars) for _ in range(length)))
        
    # Generate 1 or 2 replacement rules
    programs = []
    original_programs = []
    
    used_sources = set()
    for _ in range(num_rules):
        # Choose source char/substring of length 1
        src = random.choice(chars)
        while src in used_sources:
            src = random.choice(chars)
        used_sources.add(src)
        
        # Choose dest char/substring of length 1 or 2
        dst = random.choice(chars)
        if random.random() > 0.5:
            dst += random.choice(chars)
            
        programs.append(f"replace(\\\"{src}\\\", \\\"{dst}\\\")")
        original_programs.append(f"replace(\"{src}\", \"{dst}\")")
        
    # Evaluate output corpus
    outputs = []
    for inp in inputs:
        out = inp
        for prog in original_programs:
            # Parse replace(A, B)
            # e.g. replace("a", "b")
            parts = prog.replace('replace("', '').replace('")', '').split('", "')
            out = out.replace(parts[0], parts[1])
        outputs.append(out)
        
    # Build prompt
    prompt = (
        "Follow the instructions below to solve the code completion task:\n\n"
        "We will provide the input corpus and corresponding output corpus. Each element in the corpus is a string, and the output is transformed from the corresponding input using an ordered sequence of \"replace\" programs. You need to find the correctly constructed and ordered sequence of \"replace\" programs to transform the entire input corpus into the output corpus. Note that the programs can interact with each other in a way that reduces or increases the number of times they are applied on a given input based on where they are ordered in the sequence. This makes it very important to apply them in the correct order. \n\n"
        "The programs should be written using only the Python replace function. For example, for a program that replaces all occurrences of \"ab\" with \"bc\" it should be written as: ```replace('ab', 'bc')```\n\n"
        "Here is an example of the full task:\n"
        "### Inputs \n"
        "[\"abc\", \"ebc\", \"aba\"]\n\n"
        "### Outputs\n"
        "[\"edc\", \"edc\", \"aba\"]\n\n"
        "### Program Sequence\n"
        "```python\n"
        "[\"replace('bc','dc')\", \"replace('ad','ed')\"]\n"
        "```\n\n"
        "While generating the program sequence, you need to abide by the following restrictions:\n"
        "1. Each program in the sequence should have the form \"replace(A, B)\", where A and B are both strings.\n"
        "2. Both argument strings A and B in \"replace(A, B)\" should have <= 3 characters. A should have at least 1 character but B can be null (or \"\").\n"
        "3. The maximum number of programs in a sequence is 5\n"
        "4. You should only consider the Python \u2018replace\u2019 function for specifying programs (each program is a Python replace function). You can not use any other Python modules or functions.  \n"
        "5. Strictly follow the markdown style convention while presenting your final program sequence, and make sure to enclose it in the ```python``` markdown style code block. \n\n"
        "Now, please generate the sequence of programs corresponding to the following input corpus and output corpus:\n\n"
        f"### Inputs \n"
        f"{inputs}\n\n"
        f"### Outputs\n"
        f"{outputs}\n\n"
        "### Program Sequence\n"
    )
    
    return {
        "id": task_id,
        "inputs": inputs,
        "outputs": outputs,
        "programs": programs,
        "original_programs": original_programs,
        "prompt": prompt,
        "reward": "pbebench"
    }

def main():
    tasks = []
    # 15 single-rule tasks
    for i in range(1, 16):
        tasks.append(generate_task(i, num_rules=1))
    # 5 double-rule tasks
    for i in range(16, 21):
        tasks.append(generate_task(i, num_rules=2))
        
    out_file = Path(__file__).parent / "tasks" / "simple_replace.jsonl"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_file, "w", encoding="utf-8") as f:
        for t in tasks:
            f.write(json.dumps(t) + "\n")
            
    print(f"Generated {len(tasks)} simple replace tasks to {out_file}")

if __name__ == "__main__":
    main()
