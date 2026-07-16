import os
import subprocess
import tempfile
import ast
from datetime import datetime
from pydantic import BaseModel, Field
from langchain.tools import tool

# 基础安全模块（去除了系统级危险模块）
LIST_SAFE_MODULES = ["math", "collections", "itertools", "re", "typing", "random", "hashlib"]

# 你的自定义模块白名单
# 警告：强烈建议移除 "os" 和 "pickle"！为了演示我这里暂且保留你的原始设计。
SAFE_MODULES = set(LIST_SAFE_MODULES + [
    "os", "pandas", "numpy", "sympy", "json", "sklearn", "scipy", "io",
    "PIL", "datetime", "csv", "fractions", "matplotlib", "pickle", "cv2",
])

# 沙箱输出根目录：所有代码生成的文件（图片、数据等）都会落在这里，不污染项目根目录
SANDBOX_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox_output")

class PythonSandboxInput(BaseModel):
    code: str = Field(
        description="要执行的 Python 代码。必须使用 print() 输出结果，并且只能导入白名单中的库。"
    )

def check_imports_in_code(code: str) -> str | None:
    """
    检查代码中的 import 语句是否在白名单内。
    返回 None 表示安全通过；返回字符串表示具体的错误信息。
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Syntax Error in code: {e}"

    for node in ast.walk(tree):
        # 检查 'import xxx' 语法
        if isinstance(node, ast.Import):
            for alias in node.names:
                base_module = alias.name.split('.')[0] # 获取根模块名，如 'matplotlib.pyplot' 取 'matplotlib'
                if base_module not in SAFE_MODULES:
                    return f"Security Error: Importing module '{base_module}' is not allowed."
        
        # 检查 'from xxx import yyy' 语法
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base_module = node.module.split('.')[0]
                if base_module not in SAFE_MODULES:
                    return f"Security Error: Importing from module '{base_module}' is not allowed."
    
    return None # 检查通过

@tool("python_code_sandbox", args_schema=PythonSandboxInput)
def python_code_sandbox(code: str) -> str:
    """在受限沙箱环境中执行 Python 代码。

    允许导入的模块：
      math, collections, itertools, re, typing, random, hashlib,
      os, pandas, numpy, sympy, json, sklearn, scipy, io, PIL, datetime,
      csv, fractions, matplotlib, pickle, cv2

    禁止导入的模块（将直接拒绝）：
      glob, base64, subprocess, urllib, socket, shutil, sys, imp, importlib

    读取文件：当前目录是项目根目录，请使用相对路径，例如 Image.open("benchmark/images/a.png")。
    保存文件：必须使用 SANDBOX_DIR 变量，例如 plt.savefig(os.path.join(SANDBOX_DIR, "result.png"))。
    文本结果必须通过 print() 输出。

    category: 数值参数类

    """

    # 1. 前置安全检查：AST 白名单验证
    security_error = check_imports_in_code(code)
    if security_error:
        # 直接把错误信息返回给 Agent，让它知道哪些库不能用并重试
        return (
            f"{security_error}\n请修改代码，只导入允许的库："
            f"{', '.join(sorted(SAFE_MODULES)[:10])}..."
        )

    # 2. 创建独立的工作目录（避免并行执行时文件互相覆盖）
    os.makedirs(SANDBOX_OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    work_dir = os.path.join(SANDBOX_OUTPUT_DIR, f"run_{timestamp}")
    os.makedirs(work_dir, exist_ok=True)

    # 3. 创建临时 .py 文件，注入 sandbox 输出目录
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        preamble = (
            "import os\n"
            f"SANDBOX_DIR = r'{work_dir}'\n"
            "os.makedirs(SANDBOX_DIR, exist_ok=True)\n"
        )
        f.write(preamble + code)
        temp_file_path = f.name

    try:
        # 4. 执行代码：cwd 设为项目根目录，让代码能读到 agent 传入的本地图片路径
        #    同时 os.path.abspath 确保相对路径可以正确解析
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        # 将 sandbox_output 的绝对路径注入到代码的环境变量中
        sandbox_env = os.environ.copy()
        sandbox_env["SANDBOX_OUTPUT_DIR"] = work_dir
        result = subprocess.run(
            ['python', temp_file_path],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_root,
            env=sandbox_env,
        )

        output = result.stdout
        error = result.stderr

        if result.returncode != 0:
            return f"Execution Failed:\n{error}"

        if not output.strip():
            output = "Execution Success, but no output was printed."
        else:
            output = f"Execution Success. Output:\n{output[:10000]}"

        # 5. 列出本次执行生成的文件
        generated = []
        for root, _, files in os.walk(work_dir):
            for fname in files:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, work_dir)
                size = os.path.getsize(full)
                generated.append(f"  {rel} ({size:,} bytes)")

        if generated:
            output += f"\n\n[Sandbox] 工作目录: {work_dir}"
            output += f"\n[Sandbox] 生成文件 ({len(generated)} 个):\n" + "\n".join(generated)
        else:
            output += f"\n\n[Sandbox] 工作目录: {work_dir}\n[Sandbox] 本次执行未生成文件。"

        return output

    except subprocess.TimeoutExpired:
        return f"Error: Execution Timeout (10s).\n[Sandbox] 工作目录: {work_dir}"
    except Exception as e:
        return f"Sandbox Error: {str(e)}\n[Sandbox] 工作目录: {work_dir}"
    finally:
        # 清理临时 .py 文件（但保留工作目录里的产物）
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
