import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv

from src.llm_client import LLMClient
from src.logger import get_logger, init_logging


@dataclass
class RawNode:
    level: int
    title: str
    raw_content: str


@dataclass
class CleanedNode:
    level: int
    title: str
    content: str


def parse_markdown_from_string(md_text: str) -> List[RawNode]:
    lines = md_text.splitlines(keepends=True)
        
    nodes = []
    current_level = 0
    current_title = "Document Root"
    current_content_lines = []
    
    # 正则匹配 Markdown 标题
    header_re = re.compile(r'^(#{1,6})\s+(.*)')
    
    for line in lines:
        match = header_re.match(line)
        if match:
            if current_content_lines or nodes:
                nodes.append(RawNode(
                    level=current_level,
                    title=current_title,
                    raw_content="".join(current_content_lines)
                ))
            current_level = len(match.group(1))
            current_title = match.group(2).strip()
            current_content_lines = []
        else:
            current_content_lines.append(line)
            
    nodes.append(RawNode(
        level=current_level,
        title=current_title,
        raw_content="".join(current_content_lines)
    ))
    
    return nodes


def get_parent_node(cleaned_nodes: List[CleanedNode], current_level: int) -> Optional[CleanedNode]:
    """在已清洗的节点中向上遍历寻找真实的父节点。"""
    if current_level <= 0:
        return None
        
    for i in range(len(cleaned_nodes) - 1, -1, -1):
        if cleaned_nodes[i].level < current_level:
            return cleaned_nodes[i]
    return None


def clean_markdown_nodes(raw_nodes: List[RawNode], llm: LLMClient, limit: int = 0, debug: bool = False) -> List[CleanedNode]:
    log = get_logger()
    cleaned_nodes: List[CleanedNode] = []
    
    total = limit if limit > 0 else len(raw_nodes)
    
    for i in range(total):
        node = raw_nodes[i]
        log.info("[%d/%d] 正在清洗并重组节点: %s %s", i + 1, total, '#' * node.level, node.title)
        
        # 1. 动态构建全局大纲
        past_titles = [f"{'#' * n.level} {n.title}" for n in cleaned_nodes if n.level > 0]
        future_titles = [f"{'#' * n.level} {n.title}" for n in raw_nodes[i+1:] if n.level > 0]
        global_structure = "\n".join(past_titles + [f"-> 📍 当前位置: {'#' * node.level} {node.title}"] + future_titles)
        
        # 2. 寻找上下文
        parent = get_parent_node(cleaned_nodes, node.level)
        previous = cleaned_nodes[-1] if cleaned_nodes else None
        next_raw_node = raw_nodes[i+1] if i + 1 < len(raw_nodes) else None
        
        parent_ctx = "无"
        if parent:
            parent_ctx = f"标题：{'#' * parent.level} {parent.title}\n内容：\n{parent.content}"
            
        previous_ctx = "无"
        if previous:
            previous_ctx = f"标题：{'#' * previous.level} {previous.title}\n内容：\n{previous.content}"
            
        next_ctx = "无"
        if next_raw_node:
            next_text = next_raw_node.raw_content[:500] + "..." if len(next_raw_node.raw_content) > 500 else next_raw_node.raw_content
            next_ctx = f"{'#' * next_raw_node.level} {next_raw_node.title}\n{next_text}"
            
        prompt = f"""你是一个高级 TRPG 模组文本重组专家。请对【当前待清理节点】的原始文本进行清理、排版和层级重组。

【核心任务】
返回一个 JSON 对象。在返回节点列表前，你必须先输出一段简短的推演过程 (`reasoning`)。你需要：
1. **去噪与排版修正 (核心)**：
   - 去掉 PDF 换页产生的页眉页脚（如“快乐王子”、“1”、“The Happy Prince”）。**注意：如果一个节点既包含有效正文，又混杂了页眉页脚，你必须只剔除无用文本，保留有效正文！**
   - **修复断句与多余空行**：PDF 转换会导致同一段落的句子被强行从中间断开（例如一句话被切成好几行，甚至中间隔着空行）。你必须把这些属于同一自然段的碎片文本**重新拼接成完整、连贯的一段话**，去除多余的换行符和空格。
2. **动态层级重整 (Level)**：原 Markdown 的层级通常都是错的。请通过 `reasoning` 分析：
   - 它是全新大章吗？如果是，设为 `level: 1`。
   - 它是前一个节点的子分类吗？如果是，设为 `level: 前一节点 level + 1`。
   - 它和前一个节点是并列的小节吗？如果是，保持 `level` 相同。
3. **节点删除 (慎用)**：只有当清理完所有页眉页脚后，当前节点**完全没有实质内容**了，或者是毫无用处的**纯【目录/TOC】**时，才可以将其彻底删除（即 `nodes` 数组为空）。
4. **接续前文与下文 (关键修复)**：由于 PDF 的物理换页，常常会在一段话中间强行插入一个带 `#` 的页眉（比如上一页还在讲 `1.4 宝石病`，下一页开头冒出个 `## Chapter 2.` 的页眉，后面跟着宝石病没说完的半句话）。
   - 如果你通过观察【前一节点】和【下文窥探】，发现当前节点的标题其实是个伪标题/页眉，而它的 `content` 实际上是上一节未说完的正文，**请将该节点的 `title` 设为空字符串 `""`，并将 `level` 设为 `0`**。这样系统就不会为它打上标题，而是直接把它当作纯文本接在上一个节点后面。
5. **内容拆分**：如果原文隐藏了多个逻辑平行的子区块（如连续的人物介绍），可将其拆分为多个新节点。

【输出格式】
严格输出 JSON 格式，包含推演过程：
{{
  "reasoning": "简短分析当前节点的层级关系，以及需要剔除的噪音",
  "nodes": [
    {{
      "level": 2,
      "title": "修复后的标题名",
      "content": "清洗后的正文..."
    }}
  ]
}}

【全局动态目录大纲】
{global_structure}

【真实的父节点上下文】
{parent_ctx}

【直接前一节点上下文】
{previous_ctx}

【下文窥探】（下个原始节点的开头）
{next_ctx}

请注意：不要篡改、不要总结模组原意。如果当前节点是一个空白标题或无用废话，你可以返回空的 `nodes` 数组。
"""
        
        user_message = f"""【当前待清理节点】
原标题：{'#' * node.level} {node.title}
原内容：
{node.raw_content}
"""
        try:
            response, _ = llm.chat(
                system_prompt=prompt,
                user_message=user_message,
                temperature=0.2,
                json_mode=True
            )
            
            if debug:
                with open("md_cleaner_debug.log", "a", encoding="utf-8") as df:
                    df.write(f"\\n{'='*50}\\n")
                    df.write(f"NODE [{i+1}/{total}] - 原标题: {'#' * node.level} {node.title}\\n")
                    df.write(f"{'='*50}\\n\\n")
                    df.write(f"【SYSTEM PROMPT】\\n{prompt}\\n\\n")
                    df.write(f"【USER MESSAGE】\\n{user_message}\\n\\n")
                    df.write(f"【LLM RESPONSE】\\n{response}\\n\\n")

            data = json.loads(response)
            
            for item in data.get("nodes", []):
                cleaned_nodes.append(CleanedNode(
                    level=item.get("level", node.level),
                    title=item.get("title", node.title),
                    content=item.get("content", "")
                ))
                
        except Exception as e:
            log.error("处理节点 %s 时出错: %s", node.title, e)
            # Fallback
            cleaned_nodes.append(CleanedNode(
                level=node.level,
                title=node.title,
                content=node.raw_content
            ))
            
    return cleaned_nodes
            
            
def save_nodes_to_file(nodes: List[CleanedNode], output_path: str):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        last_written_title = ""
        for node in nodes:
            current_title = node.title.strip()
            # 只有当 title 不为空且 level > 0 时，才打印标题
            if current_title and node.level > 0:
                # 避免连续打印两个完全相同的标题（大模型有时会忘记把伪标题的 level 置 0）
                if current_title != last_written_title:
                    f.write(f"{'#' * node.level} {current_title}\n\n")
                    last_written_title = current_title
            
            if node.content.strip():
                f.write(node.content.strip() + "\n\n")


def get_raw_markdown(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.pdf':
        print(f"检测到输入为 PDF，正在提取 Markdown 内容（内存处理，不产生中间文件）...")
        import pymupdf4llm
        md_text = pymupdf4llm.to_markdown(filepath)
        return md_text
    elif ext == '.md':
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError(f"不支持的文件类型: {ext}")


def main():
    parser = argparse.ArgumentParser(description="TRPG 模组自动化导入清洗工具 (支持 PDF/MD)")
    parser.add_argument("-i", "--input", required=True, help="输入的源文件路径 (支持 .pdf 或 .md)")
    parser.add_argument("-o", "--output", required=True, help="输出的 clean markdown 文件路径")
    parser.add_argument("--limit", type=int, default=0, help="最多处理的节点数量 (默认: 0代表全部)")
    parser.add_argument("--debug", action="store_true", help="开启调试模式，输出与 LLM 交互的完整上下文至 md_cleaner_debug.log")
    
    args = parser.parse_args()
    
    if args.debug and os.path.exists("md_cleaner_debug.log"):
        os.remove("md_cleaner_debug.log")
    
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")  # 可以使用较快的模型
    
    if not api_key:
        print("错误: 请在 .env 文件中设置 DEEPSEEK_API_KEY")
        sys.exit(1)
        
    init_logging(os.getcwd(), debug_mode=True)
    llm = LLMClient(api_key=api_key, base_url=base_url, model=model, thinking=False)
    
    print(f"正在读取 {args.input} ...")
    raw_md_text = get_raw_markdown(args.input)
    
    print("正在进行文本节点切片...")
    raw_nodes = parse_markdown_from_string(raw_md_text)
    print(f"共解析到 {len(raw_nodes)} 个原始节点。")
    
    print("开始调用 LLM 动态结构重组...")
    cleaned_nodes = clean_markdown_nodes(raw_nodes, llm, args.limit, args.debug)
    
    print(f"保存结果至 {args.output} ...")
    save_nodes_to_file(cleaned_nodes, args.output)
    print("完成！")


if __name__ == "__main__":
    main()
