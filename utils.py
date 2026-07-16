import json
import datetime
import time
import os
import re
import argparse
import os
import importlib
from langchain_core.tools import BaseTool

def load_all_tools(tools_dir="tools"):
    """
    自动扫描并加载目录下所有的 LangChain 工具
    """
    all_tools = []
    
    # 遍历 tools 目录及其所有子目录 (如 caffe, yolo 等)
    for root, dirs, files in os.walk(tools_dir):
        # 跳过缓存文件夹
        if "__pycache__" in root:
            continue
            
        for file in files:
            # 只处理 .py 文件，排除 __init__.py
            if file.endswith(".py") and file != "__init__.py":
                # 构造模块路径，例如: tools/caffe/carPedDetTool.py
                file_path = os.path.join(root, file)
                
                # 【修改点开始】安全去除后缀并转换为模块名
                # 1. os.path.splitext 会把路径拆成 ('tools/basicTools/pythonSandboxTool', '.py')
                file_path_without_ext = os.path.splitext(file_path)[0]
                # 2. 兼容 Windows 和 Linux 的路径分隔符，将 '/' 替换为 '.'
                module_name = file_path_without_ext.replace(os.sep, ".")
                # 【修改点结束】
                
                try:
                    # 动态导入这个文件
                    module = importlib.import_module(module_name)
                    
                    # 遍历文件里面的所有对象
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        # 判断这个对象是不是 LangChain 的工具 (被 @tool 装饰过的都会变成 BaseTool 的子类)
                        if isinstance(attr, BaseTool):
                            # 防止重复加载
                            if attr not in all_tools:
                                all_tools.append(attr)
                except Exception as e:
                    print(f"⚠️ 加载模块 {module_name} 失败: {e}")
                    
    return all_tools

def mkpath(path):
    if not os.path.exists(path):
        os.mkdir(path)


def print_now(return_flag=0):
    t_delta = datetime.timedelta(hours=9)
    JST = datetime.timezone(t_delta, 'JST')
    now = datetime.datetime.now(JST)
    now = now.strftime('%Y/%m/%d %H:%M:%S')
    if return_flag == 0:
        print(now)
    elif return_flag == 1:
        return now
    else:
        pass


def print_exp(args, return_flag=0):
    info = ''
    for k, v in vars(args).items():
        info += '{}:{}\n'.format(k, v)
    print('---------------experiment args---------------')
    print(info)
    print('---------------------------------------------')
    if return_flag == 0:
        return
    elif return_flag == 1:
        return info
    else:
        pass                                                               
    
def write_json(data, path):
    f = open(path, mode='a', encoding='utf-8')
    json.dump(data, f, indent=4, ensure_ascii=False)
    f.close()

def standardize(string):
    res = re.compile("[^\\u4e00-\\u9fa5^a-z^A-Z^0-9^_]")
    string = res.sub("_", string)
    string = re.sub(r"(_)\1+","_", string).lower()
    while True:
        if len(string) == 0:
            return string
        if string[0] == "_":
            string = string[1:]
        else:
            break
    while True:
        if len(string) == 0:
            return string
        if string[-1] == "_":
            string = string[:-1]
        else:
            break
    if string[0].isdigit():
        string = "get_" + string
    return string

def change_name(name):
    change_list = ["from", "class", "return", "false", "true", "id", "and"]
    if name in change_list:
        name = "is_" + name
    return name

# def fix_seed(seed):
#     # random
#     random.seed(seed)
#     # Numpy
#     np.random.seed(seed)
#     # Pytorch
#     torch.manual_seed(seed)
#     torch.cuda.manual_seed_all(seed)
#     torch.backends.cudnn.deterministic = True
def find_json_files(target_directory):
    """
    Find json suffix
    """
    json_files = []
    for root, dirs, files in os.walk(target_directory):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files

def list_directories(path):
    try:
        items = os.listdir(path)
        directories = [item for item in items if os.path.isdir(os.path.join(path, item))]
        return directories
    except Exception as e:
        print(f"Error: {e}")
        return []
    
def save_generated_script(output_dir, index, query, code):
    """
    将生成的代码追加保存到同一个 .py 文件中 (续写模式)
    """
    # 1. 确保目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 2. 固定文件名，所有 query 都写入这个文件
    #    如果你希望每次运行都清空重新写，可以在 main 开始时先删除这个文件
    filename = os.path.join(output_dir, "all_generated_plans.py")
    
    # 3. 使用 'a' (append) 模式打开文件
    with open(filename, "a", encoding="utf-8") as f:
        # 添加分隔符，方便区分不同的 Query
        f.write('\n' + '#' * 60 + '\n')
        f.write(f'# [Query ID: {index}]\n')
        f.write(f'# Time: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'# Content: {query.strip()}\n')
        f.write('#' * 60 + '\n\n')
        
        # 写入生成的代码
        f.write(code)
        
        # 确保末尾有换行
        f.write("\n\n")
    
    print(f"[Saved Code]: Appended to {filename}")

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')