"""
RAG Template and Source Context Builder
Implements OpenWebUI-style citation mechanism with <source> tags
Enhanced with multi-source support for better context richness
"""
from typing import List, Dict, Any
from collections import defaultdict


# Default RAG Template - OpenWebUI style with multi-source support
DEFAULT_RAG_TEMPLATE = """### 任务:
使用提供的上下文回答用户问题。上下文可能同时包含文档片段和知识图谱节点，请综合所有相关信息给出完整、全面的回答。

### 指南:
- **综合多个来源的信息**：不要只依赖单一来源，请整合文档片段和知识图谱节点中的相关信息
- **使用[id]格式标注引用**：在回答中使用[1], [2]等格式标注引用来源
- **按来源组织信息**：如果不同文件或图谱节点包含相关信息，请分别说明
- **如果不知道答案**，明确说明知识库中没有相关信息
- **如果不同来源有冲突**，请说明并给出你的判断
- **使用与用户问题相同的语言回答**
- **不要在没有id属性的<source>标签上添加引用**
- **不要在回答中使用XML标签**

### 示例:
如果用户询问"电动机过热的原因"，且上下文中有来自多个文件的相关信息，回答应该像这样:

"电动机过热的常见原因包括:

**来自文件1的相关信息:**
1. 负载过大：超过额定负载运行导致电流过载 [1]
2. 散热不良：通风道堵塞、环境温度过高或风扇故障 [2]

**来自文件2的相关信息:**
3. 绕组短路或接地：绝缘损坏引发局部过热 [3]
4. 轴承故障：润滑不良或轴承损坏增加摩擦 [4]

**综合建议:**
建议首先检查负载情况和散热系统，然后检测绕组绝缘性能。"

### 输出要求:
- 提供清晰、全面、结构化的回答
- 综合多个来源的信息，避免遗漏重要内容
- 只在有<source id="N">时才使用[N]格式标注引用
- 引用标记放在相关语句的末尾
- 多个来源时用逗号分隔，如[1], [3]

### 上下文:
<context>
{{CONTEXT}}
</context>

### 用户问题:
{{QUESTION}}
"""


def get_source_context(sources: List[Dict[str, Any]], include_content: bool = True) -> str:
    """
    Build <source> tag context string from citation sources.
    OpenWebUI style with multi-source grouping: <source id="1" name="文件名 - 章节路径">内容</source>
    
    Enhanced for multi-source RAG:
    - Groups sources by file for better organization
    - Shows multiple chunks from the same file
    - Provides clear file-level organization
    
    Args:
        sources: List of source dictionaries with keys:
            - content: The text content
            - file_name: Source file name
            - section_path: List of section hierarchy ["第五章", "第三节"]
            - file_id: File identifier
        include_content: Whether to include the content body in the tag
        
    Returns:
        Formatted XML-style source context string with file grouping
    """
    if not sources:
        return ''
    
    # Group sources by file for better organization
    file_sources = defaultdict(list)
    for source in sources:
        source_type = source.get('source_type', 'document')
        file_name = source.get('file_name', 'Unknown')
        if source_type == 'kg':
            file_name = file_name or '知识图谱'
        file_sources[file_name].append(source)
    
    context_string = ''
    global_id = 1
    
    # Process each file's sources
    for file_name, file_chunks in file_sources.items():
        # Add file header comment for clarity
        context_string += f'<!-- 来源文件: {file_name} -->\n'
        
        for source in file_chunks:
            # Build descriptive name with section path
            section_path = source.get('section_path', '')
            section_title = source.get('section_title', '')
            
            # Construct name: "文件名 - 章节路径"
            name_parts = []
            if source.get('source_type') == 'kg':
                name_parts.append(source.get('file_name') or '知识图谱')
                if source.get('node_name'):
                    name_parts.append(source['node_name'])
            elif source.get('file_name'):
                name_parts.append(source['file_name'])
            
            if section_path:
                if isinstance(section_path, list):
                    name_parts.append(' > '.join(section_path))
                elif isinstance(section_path, str) and section_path.strip():
                    name_parts.append(section_path)
            elif section_title:
                name_parts.append(section_title)
            
            name = ' - '.join(name_parts) if name_parts else 'Unknown'
            
            # Build source tag with global sequential ID
            body = source.get('content', '') if include_content else ''
            context_string += f'<source id="{global_id}" name="{name}">{body}</source>\n'
            global_id += 1
        
        # Add separator between files
        context_string += '\n'
    
    return context_string


def format_rag_prompt(user_message: str, sources: List[Dict[str, Any]], 
                     system_prompt: str = None, 
                     template: str = None) -> str:
    """
    Format a complete RAG prompt with source context.
    
    Args:
        user_message: The user's question
        sources: List of retrieved sources
        system_prompt: Optional custom system prompt
        template: Optional custom RAG template (defaults to DEFAULT_RAG_TEMPLATE)
        
    Returns:
        Formatted prompt string
    """
    if not sources:
        return user_message
    
    # Build source context
    source_context = get_source_context(sources, include_content=True)
    
    if not source_context.strip():
        return user_message
    
    # Use provided template or default
    rag_template = template or DEFAULT_RAG_TEMPLATE
    
    # Replace placeholders
    prompt = rag_template.replace('{{CONTEXT}}', source_context)
    prompt = prompt.replace('{{QUESTION}}', user_message)
    
    # Prepend system prompt if provided
    if system_prompt:
        prompt = f"{system_prompt}\n\n{prompt}"
    
    return prompt


def parse_citation_markers(text: str) -> Dict[int, List[str]]:
    """
    Parse [id] citation markers from text.
    
    Args:
        text: Text containing [1], [2], etc. markers
        
    Returns:
        Dict mapping citation ID to list of sentences/segments
    """
    import re
    
    citations = {}
    # Find all [N] patterns
    pattern = r'\[(\d+)\]'
    
    # Split text by citation markers
    parts = re.split(pattern, text)
    
    # Reconstruct segments with their citations
    current_text = ''
    for i, part in enumerate(parts):
        if i % 2 == 0:  # Text segment
            current_text = part
        else:  # Citation ID
            citation_id = int(part)
            if citation_id not in citations:
                citations[citation_id] = []
            # Extract the sentence or segment containing this citation
            citations[citation_id].append(current_text.strip())
    
    return citations
