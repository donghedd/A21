"""
Chat Service - Business Logic for Conversations
"""
import uuid
import json
import time
import re
from typing import Generator, List, Dict, Any, Optional
from datetime import datetime
from flask import current_app
import logging

from ..extensions import db
from ..models import Conversation, Message, CustomModel, KnowledgeBase, ModelKnowledgeBinding, ExternalModel, ExternalModelKnowledgeBinding
from .rag_service import get_rag_service
from .llm_factory import get_llm_service
from .external_model_service import get_external_model_service
from ..utils.rag_template import format_rag_prompt

logger = logging.getLogger(__name__)

# Patterns for system questions that should bypass RAG
SYSTEM_QUESTION_PATTERNS = [
    r'^你是(谁|什幺|什么)(呢|呀|啊)?[？?]?$',
    r'^who\s*are\s*you[？?]?$',
    r'^what\s*are\s*you[？?]?$',
    r'^自我介绍[：:]?$',
    r'^介绍一下你自己[？?]?$',
    r'^你的名字是[什幺什么]?[？?]?$',
    r'^你叫什么[名字]?[？?]?$',
    r'^你是ai吗[？?]?$',
    r'^你是人类吗[？?]?$',
    r'^你能做什幺[？?]?$',
    r'^你的功能[是些]什么?[？?]?$',
    r'^help(\s+me)?[？?]?$',
    r'^hello[，,]?$',
    r'^hi$',
    r'^你好[，,]?$',
    r'^嗨[，,]?$',
]


def is_system_question(query: str) -> bool:
    """
    Check if the query is a system question that should bypass RAG retrieval.
    System questions are those that ask about the AI's identity, capabilities, etc.
    and don't require knowledge base information to answer.
    """
    query = query.strip()
    for pattern in SYSTEM_QUESTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return True
    return False


QUESTION_CLASSIFIER_TEMPLATE = """你是一个问题分类器。请分析用户问题，判断它属于哪一类。

分类：
1. SYSTEM - 系统问题，如"你是谁"、"你是做什么的"、"你好"、"帮助"等，关于AI身份、功能、问候的问题
2. KNOWLEDGE - 知识问题，需要从知识库/文档中检索信息才能回答的问题，如"电机过热怎么办"、"如何维修XX设备"等
3. GENERAL - 通用问题，可以用一般性知识回答的问题，不需要特定文档/知识库

请直接返回JSON格式，不要思考，不要解释：
{"type": "SYSTEM|KNOWLEDGE|GENERAL", "keywords": ["关键词1", "关键词2", "关键词3"]}

用户问题：{{QUESTION}}

JSON响应："""


class QuestionClassifier:
    """Fast question classifier using LLM"""

    def __init__(self, llm_service):
        self.llm_service = llm_service

    def classify(self, question: str, model: str = None) -> Dict[str, Any]:
        """
        Classify user question using LLM (no thinking).
        Returns: {"type": "SYSTEM"|"KNOWLEDGE"|"GENERAL", "keywords": [...]}
        """
        model = model or self.llm_service.get_default_model()

        prompt = QUESTION_CLASSIFIER_TEMPLATE.replace('{{QUESTION}}', question)

        try:
            response = self.llm_service.chat(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.1}
            )

            response = response.strip()

            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])

            import json
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    result = json.loads(line)
                    if 'type' in result and 'keywords' in result:
                        if result['type'] in ('SYSTEM', 'KNOWLEDGE', 'GENERAL'):
                            return result

            logger.warning(f"Failed to parse classifier response: {response}")
            return {'type': 'KNOWLEDGE', 'keywords': []}

        except Exception as e:
            logger.error(f"Question classification failed: {e}")
            return {'type': 'KNOWLEDGE', 'keywords': []}

# Ollama returns thinking content via separate 'thinking' field when think=True
# No need for tag-based parsing


class ChatService:
    """Service for handling chat operations"""

    def __init__(self):
        self._rag_service = None
        self._llm_service = None

    @property
    def rag_service(self):
        if self._rag_service is None:
            self._rag_service = get_rag_service()
        return self._rag_service

    @property
    def llm_service(self):
        if self._llm_service is None:
            self._llm_service = get_llm_service()
        return self._llm_service

    def _resolve_model_context(self, conversation: Conversation, model: str = None,
                               custom_model_id: str = None,
                               external_model_id: str = None) -> Dict[str, Any]:
        """Resolve the effective model and sync conversation-level model bindings."""
        custom_model = None
        external_model = None
        base_model = model or self.llm_service.get_default_model()
        system_prompt = None
        effective_custom_model_id = custom_model_id or conversation.custom_model_id
        effective_external_model_id = external_model_id or conversation.external_model_id
        provider = 'local'
        external_service = None

        if effective_external_model_id:
            external_model = ExternalModel.query.get(effective_external_model_id)
            if external_model:
                provider = 'external'
                base_model = external_model.model_name or model or external_model.name
                system_prompt = external_model.system_prompt
                external_service = get_external_model_service(
                    api_key=external_model.api_key,
                    base_url=external_model.api_base_url
                )
                if (
                    conversation.external_model_id != external_model.id
                    or conversation.custom_model_id is not None
                ):
                    conversation.external_model_id = external_model.id
                    conversation.custom_model_id = None
                    db.session.commit()
                return {
                    'base_model': base_model,
                    'system_prompt': system_prompt,
                    'custom_model': None,
                    'custom_model_id': None,
                    'external_model': external_model,
                    'external_model_id': external_model.id,
                    'provider': provider,
                    'external_service': external_service,
                }

        if conversation.external_model_id is not None:
            conversation.external_model_id = None
            db.session.commit()

        if effective_custom_model_id:
            custom_model = CustomModel.query.get(effective_custom_model_id)
            if custom_model:
                base_model = custom_model.base_model or base_model
                system_prompt = custom_model.system_prompt
                if conversation.custom_model_id != custom_model.id or conversation.external_model_id is not None:
                    conversation.custom_model_id = custom_model.id
                    conversation.external_model_id = None
                    db.session.commit()
        elif conversation.custom_model_id is not None:
            conversation.custom_model_id = None
            db.session.commit()

        return {
            'base_model': base_model,
            'system_prompt': system_prompt,
            'custom_model': custom_model,
            'custom_model_id': custom_model.id if custom_model else None,
            'external_model': external_model,
            'external_model_id': external_model.id if external_model else None,
            'provider': provider,
            'external_service': external_service,
        }

    def _stream_response(self, base_model: str, messages: List[Dict[str, str]],
                         provider: str = 'local', external_service=None) -> Generator[Dict[str, Any], None, None]:
        """Stream response from the configured LLM provider."""
        if provider == 'external' and external_service is not None:
            yield from external_service.chat_stream(base_model, messages)
            return
        yield from self.llm_service.chat_stream(base_model, messages)
    
    # ==================== Conversation CRUD ====================
    
    def get_conversations(self, user_id: str, search: str = None, 
                          page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get user's conversation list with pagination"""
        query = Conversation.query.filter_by(user_id=user_id, deleted_by_user=False)
        
        if search:
            query = query.filter(Conversation.title.ilike(f'%{search}%'))
        
        query = query.order_by(Conversation.updated_at.desc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'conversations': [c.to_dict() for c in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    def create_conversation(self, user_id: str, title: str = None,
                            custom_model_id: str = None,
                            external_model_id: str = None) -> Conversation:
        """Create a new conversation"""
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title or 'New Conversation',
            custom_model_id=custom_model_id,
            external_model_id=external_model_id
        )
        db.session.add(conversation)
        db.session.commit()
        return conversation
    
    def get_conversation(self, conversation_id: str, user_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        return Conversation.query.filter_by(
            id=conversation_id, 
            user_id=user_id,
            deleted_by_user=False
        ).first()
    
    def update_conversation(self, conversation_id: str, user_id: str,
                            title: str = None, custom_model_id: str = None,
                            external_model_id: str = None) -> Optional[Conversation]:
        """Update conversation details"""
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return None
        
        if title:
            conversation.title = title
        if custom_model_id is not None:
            conversation.custom_model_id = custom_model_id if custom_model_id else None
            if custom_model_id:
                conversation.external_model_id = None
        if external_model_id is not None:
            conversation.external_model_id = external_model_id if external_model_id else None
            if external_model_id:
                conversation.custom_model_id = None
        
        db.session.commit()
        return conversation
    
    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Hide a conversation from the user while keeping records for admin."""
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False

        conversation.deleted_by_user = True
        db.session.commit()
        return True
    
    def copy_conversation(self, conversation_id: str, user_id: str) -> Optional[Conversation]:
        """Copy a conversation with all messages"""
        original = self.get_conversation(conversation_id, user_id)
        if not original:
            return None
        
        new_conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=f"{original.title} (Copy)",
            custom_model_id=original.custom_model_id
        )
        db.session.add(new_conversation)
        
        # Copy all messages
        for msg in original.messages.all():
            new_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=new_conversation.id,
                role=msg.role,
                content=msg.content,
                thinking_content=msg.thinking_content,
                sources=msg.sources
            )
            db.session.add(new_msg)
        
        db.session.commit()
        return new_conversation
    
    # ==================== Message Handling ====================
    
    def add_message(self, conversation_id: str, role: str, content: str,
                    thinking_content: str = None, sources: List[Dict] = None) -> Message:
        """Add a message to conversation"""
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            thinking_content=thinking_content,
            sources=sources
        )
        db.session.add(message)
        
        # Update conversation's updated_at
        conversation = Conversation.query.get(conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()
        
        db.session.commit()
        return message
    
    def get_conversation_history(self, conversation_id: str, 
                                 limit: int = 10) -> List[Dict[str, str]]:
        """Get recent messages formatted for LLM context"""
        messages = Message.query.filter_by(
            conversation_id=conversation_id
        ).order_by(Message.created_at.desc()).limit(limit).all()
        
        # Reverse to get chronological order
        messages.reverse()
        
        return [
            {'role': msg.role, 'content': msg.content}
            for msg in messages
            if msg.role in ('user', 'assistant')
        ]
    
    # ==================== RAG-Enhanced Chat ====================
    
    def get_rag_context(self, query: str, custom_model_id: str = None,
                        external_model_id: str = None) -> tuple:
        """
        Get RAG context for a query based on model's knowledge bases
        Returns: (context_text, sources)
        Enhanced to return structured sources with file_name and section_path
        """
        logger.info(f"=== RAG检索开始 ===")
        logger.info(f"查询: {query[:50]}...")
        logger.info(f"自定义模型ID: {custom_model_id}")
        logger.info(f"云端模型ID: {external_model_id}")

        if not custom_model_id and not external_model_id:
            logger.warning("没有提供模型ID，跳过RAG检索")
            return '', []

        # Get bound knowledge bases
        if custom_model_id:
            bindings = ModelKnowledgeBinding.query.filter_by(
                custom_model_id=custom_model_id
            ).all()
        else:
            bindings = ExternalModelKnowledgeBinding.query.filter_by(
                external_model_id=external_model_id
            ).all()

        logger.info(f"找到 {len(bindings)} 个知识库绑定")

        if not bindings:
            logger.warning(f"模型 {custom_model_id} 没有绑定任何知识库")
            return '', []

        # Get collection names
        collection_names = []
        for binding in bindings:
            kb = KnowledgeBase.query.get(binding.knowledge_base_id)
            if kb:
                collection_names.append(kb.collection_name)
                logger.info(f"绑定知识库: {kb.name} (collection: {kb.collection_name})")

        if not collection_names:
            logger.warning("知识库集合名称为空")
            return '', []

        # Query RAG service with configurable top_k
        rag_top_k = current_app.config.get('RAG_TOP_K', 10)
        enable_multi_source = current_app.config.get('RAG_ENABLE_MULTI_SOURCE', True)

        logger.info(f"RAG参数: top_k={rag_top_k}, multi_source={enable_multi_source}")
        logger.info(f"查询集合: {collection_names}")

        results = self.rag_service.query(
            query=query,
            collection_names=collection_names,
            n_results=rag_top_k,
            enable_rerank=True,
            enable_multi_source=enable_multi_source
        )

        logger.info(f"RAG检索结果数量: {len(results) if results else 0}")

        if not results:
            logger.warning("RAG检索未返回任何结果")
            return '', []
        
        # Format context and structured sources with multi-source grouping
        context_parts = []
        sources = []
        
        # Group results by file for better organization
        from collections import defaultdict
        file_groups = defaultdict(list)
        
        for i, result in enumerate(results):
            metadata = result.get('metadata', {})
            file_name = metadata.get('file_name', 'Unknown')
            file_groups[file_name].append({
                'index': i,
                'result': result
            })
        
        logger.info(f"Retrieved {len(results)} results from {len(file_groups)} files")
        
        # Build context with file grouping
        source_id = 1
        for file_name, file_results in file_groups.items():
            # Add file header
            context_parts.append(f"\n## 来源: {file_name}")
            
            for item in file_results:
                result = item['result']
                metadata = result.get('metadata', {})
                content = result['content']
                
                # Add content with source ID
                context_parts.append(f"[{source_id}] {content}")
                
                # Build structured source with full metadata
                sources.append({
                    'id': source_id,
                    'content': content,
                    'file_name': file_name,
                    'file_id': metadata.get('file_id'),
                    'section_path': metadata.get('section_path', []),
                    'section_title': metadata.get('section_title', ''),
                    'score': result.get('score', 1 - result.get('distance', 0))
                })
                source_id += 1
        
        context_text = '\n\n'.join(context_parts)
        
        # Log source distribution
        source_distribution = {k: len(v) for k, v in file_groups.items()}
        logger.info(f"Source distribution: {source_distribution}")
        
        return context_text, sources
    
    def build_prompt_with_context(self, user_message: str, context: str,
                                  sources: list = None,
                                  system_prompt: str = None) -> List[Dict[str, str]]:
        """
        Build messages with RAG context using OpenWebUI-style citation
        """
        messages = []

        # System message
        system_content = system_prompt or "You are a helpful AI assistant."

        # If we have sources, use OpenWebUI-style RAG template
        if sources and len(sources) > 0:
            # Use the new format_rag_prompt function
            rag_prompt = format_rag_prompt(
                user_message=user_message,
                sources=sources,
                system_prompt=None  # We'll prepend system_content manually
            )

            # Prepend to system content
            system_content += f"\n\n{rag_prompt}"
        elif context:
            # Fallback to old simple context format (for backward compatibility)
            system_content += f"""

You have access to the following reference information. Use it to answer questions when relevant:

<context>
{context}
</context>

When using information from the context, cite the source number (e.g., [1]) at the end of your response.
If the context doesn't contain relevant information, answer based on your general knowledge."""
        else:
            # 关键修复：当没有检索到任何内容时，明确告知AI不要编造答案
            system_content += """

### 重要提示：
当前问题被识别为需要从知识库检索的问题，但知识库中没有找到相关内容。

**你必须遵守以下规则：**
1. **不要编造任何信息** - 不要提供虚假的来源、文档名称或案例编号
2. **不要引用不存在的来源** - 不要使用 [1], [2] 等引用标记
3. **诚实回答** - 明确告知用户知识库中没有找到相关信息
4. **可以提供建议** - 可以建议用户检查知识库内容或尝试其他关键词

**禁止行为：**
- 编造虚假的参考文档（如《船舶电机维护手册》）
- 编造虚假的案例编号（如 MAR-2022-045）
- 编造虚假的引用标准（如 IEC 60034-1:2020）
- 提供看似专业但实际虚构的详细技术信息

**正确回答示例：**
"抱歉，我在知识库中没有找到关于'电机过热'的相关信息。请确保：
1. 知识库中已上传相关文档
2. 文档已完成索引处理
3. 尝试使用不同的关键词提问"""

        messages.append({'role': 'system', 'content': system_content})
        messages.append({'role': 'user', 'content': user_message})

        return messages

    def _build_system_prompt(self, user_message: str, system_prompt: str = None) -> List[Dict[str, str]]:
        """
        Build prompt for SYSTEM or GENERAL questions without RAG context.
        Uses a clean system prompt without RAG template instructions.
        """
        messages = []

        # For SYSTEM/GENERAL questions, use a minimal clean prompt
        # Avoid using the full RAG-enabled system_prompt which may confuse the model
        clean_system = """你是一个智能问答助手。请简洁、直接地回答用户的问题。

回答规则：
- 回答简洁明了，不要冗长
- 如果不知道答案，说明不知道
- 不要主动检索或引用知识库
- 只回答用户当前的问题，不要延伸"""
        if system_prompt:
            # Still allow some customization but keep it minimal
            clean_system = system_prompt

        messages.append({'role': 'system', 'content': clean_system})
        messages.append({'role': 'user', 'content': user_message})

        return messages

    def chat_stream(self, conversation_id: str, user_id: str, 
                    user_message: str, model: str = None,
                    custom_model_id: str = None,
                    external_model_id: str = None) -> Generator:
        """
        Handle chat with streaming response
        Yields SSE formatted events
        """
        try:
            # Get conversation
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                yield self._sse_event('error', {'message': 'Conversation not found'})
                return

            model_context = self._resolve_model_context(
                conversation=conversation,
                model=model,
                custom_model_id=custom_model_id,
                external_model_id=external_model_id
            )
            base_model = model_context['base_model']
            system_prompt = model_context['system_prompt']
            effective_custom_model_id = model_context['custom_model_id']
            effective_external_model_id = model_context['external_model_id']
            provider = model_context.get('provider', 'local')
            external_service = model_context.get('external_service')

            logger.info("=== Chat Stream Started ===")
            logger.info(f"用户消息: {user_message[:50]}...")
            logger.info(f"请求中的custom_model_id: {custom_model_id}")
            logger.info(f"请求中的external_model_id: {external_model_id}")
            logger.info(f"对话中的custom_model_id: {conversation.custom_model_id}")
            logger.info(f"对话中的external_model_id: {conversation.external_model_id}")
            logger.info(f"effective_custom_model_id: {effective_custom_model_id}")
            logger.info(f"effective_external_model_id: {effective_external_model_id}")
            logger.info(f"base_model: {base_model}")
            # Save user message
            user_msg = self.add_message(conversation_id, 'user', user_message)

            # Immediately notify client that processing has started
            yield self._sse_event('status', {'message': 'Processing...'})

            # Stage 1 & 2: Classification and RAG context retrieval
            # Note: Removed ThreadPoolExecutor due to Flask app context issues in threads
            # Sequential execution is more reliable for database operations
            classification = {'type': 'KNOWLEDGE', 'keywords': []}
            context, sources = '', []

            # Step 1: Classify question
            try:
                classifier_service = external_service if provider == 'external' and external_service else self.llm_service
                classifier = QuestionClassifier(classifier_service)
                classification = classifier.classify(user_message, base_model)
                question_type = classification.get('type', 'KNOWLEDGE')
                logger.info(f"Question classified as: {question_type}")
            except Exception as e:
                logger.warning(f"Classification failed: {e}")
                classification = {'type': 'KNOWLEDGE', 'keywords': []}

            # Step 2: Get RAG context (only for KNOWLEDGE type questions)
            if classification.get('type', 'KNOWLEDGE') == 'KNOWLEDGE' and (effective_custom_model_id or effective_external_model_id):
                try:
                    context, sources = self.get_rag_context(
                        user_message,
                        effective_custom_model_id,
                        effective_external_model_id
                    )
                    logger.info(f"RAG检索完成: context长度={len(context)}, sources数量={len(sources) if sources else 0}")
                except Exception as e:
                    logger.warning(f"RAG context retrieval failed: {e}")
                    context, sources = '', []

            question_type = classification.get('type', 'KNOWLEDGE')
            keywords = classification.get('keywords', [])

            logger.info(f"问题分类结果: type={question_type}, keywords={keywords}")
            logger.info(f"RAG检索状态: context长度={len(context)}, sources数量={len(sources) if sources else 0}")

            # Stage 3: Build messages based on classification
            if question_type == 'SYSTEM':
                logger.info("使用SYSTEM模式（不检索知识库）")
                yield self._sse_event('status', {'message': 'Generating response...'})
                messages = self._build_system_prompt(user_message, system_prompt)
                history = self.get_conversation_history(conversation_id, limit=2)
                if len(history) > 1:
                    for msg in history[:-1]:
                        if msg['role'] == 'user':
                            messages.insert(1, msg)
                            break

            elif question_type == 'KNOWLEDGE':
                logger.info(f"使用KNOWLEDGE模式，sources数量: {len(sources) if sources else 0}")
                if sources:
                    logger.info(f"发送sources事件，包含 {len(sources)} 个来源")
                    yield self._sse_event('sources', {'sources': sources})
                else:
                    logger.warning("没有检索到任何sources，将提示AI不要编造答案")
                yield self._sse_event('status', {'message': 'Generating response...'})
                history = self.get_conversation_history(conversation_id, limit=10)
                messages = self.build_prompt_with_context(user_message, context, sources, system_prompt)
                if len(history) > 1:
                    for msg in history[:-1]:
                        messages.insert(1, msg)

            # else:
            #     yield self._sse_event('status', {'message': 'Generating response...'})
            #     messages = self._build_system_prompt(user_message, system_prompt)
            #     history = self.get_conversation_history(conversation_id, limit=10)
            #     if len(history) > 1:
            #         for msg in history[:-1]:
            #             messages.insert(1, msg)
            else:
                logger.info("使用GENERAL模式")
                yield self._sse_event('status', {'message': 'Generating response...'})
                messages = self._build_system_prompt(user_message, system_prompt)
            
            # Start streaming response
            yield self._sse_event('status', {'message': 'Generating response...'})

            full_content = ''
            thinking_content = ''
            is_thinking = False
            thinking_started_at = None
            thinking_duration = 0

            # Create a placeholder assistant message at the start to ensure data integrity
            # This message will be updated incrementally during streaming
            assistant_msg = self.add_message(
                conversation_id,
                'assistant',
                '',  # Start with empty content
                thinking_content='',
                sources=sources if sources else None
            )
            assistant_message_id = assistant_msg.id

            # Track last save time for incremental saves (every 2 seconds)
            last_save_time = time.time()
            save_interval = 2.0  # Save every 2 seconds

            for chunk in self._stream_response(base_model, messages, provider=provider, external_service=external_service):
                if 'message' in chunk:
                    msg = chunk['message']

                    # Handle thinking field (Ollama think=True returns separate field)
                    thinking_token = msg.get('thinking', '')
                    content_token = msg.get('content', '')

                    if thinking_token:
                        if not is_thinking:
                            is_thinking = True
                            thinking_started_at = time.time()
                            yield self._sse_event('thinking_start', {})
                        thinking_content += thinking_token
                        yield self._sse_event('thinking', {'content': thinking_token})

                    if content_token:
                        if is_thinking:
                            is_thinking = False
                            if thinking_started_at:
                                thinking_duration = int(time.time() - thinking_started_at)
                            yield self._sse_event('thinking_end', {
                                'duration': thinking_duration
                            })
                        full_content += content_token
                        yield self._sse_event('content', {'content': content_token})

                    # Incremental save: update message in database every 2 seconds
                    current_time = time.time()
                    if current_time - last_save_time >= save_interval:
                        try:
                            assistant_msg.content = full_content
                            assistant_msg.thinking_content = thinking_content if thinking_content else None
                            db.session.commit()
                            last_save_time = current_time
                        except Exception as save_error:
                            logger.warning(f"Incremental save failed: {save_error}")
                            db.session.rollback()

                if chunk.get('done', False):
                    # If still in thinking mode when done, close it
                    if is_thinking:
                        is_thinking = False
                        if thinking_started_at:
                            thinking_duration = int(time.time() - thinking_started_at)
                        yield self._sse_event('thinking_end', {
                            'duration': thinking_duration
                        })
                    break

            # Final save of the complete message
            try:
                assistant_msg.content = full_content
                assistant_msg.thinking_content = thinking_content if thinking_content else None
                db.session.commit()
            except Exception as save_error:
                logger.error(f"Final message save failed: {save_error}")
                db.session.rollback()
                # Try one more time with fresh session
                try:
                    assistant_msg = Message.query.get(assistant_message_id)
                    if assistant_msg:
                        assistant_msg.content = full_content
                        assistant_msg.thinking_content = thinking_content if thinking_content else None
                        db.session.commit()
                except Exception as retry_error:
                    logger.error(f"Retry save failed: {retry_error}")
            
            # Auto-generate title if it's the first exchange
            if conversation.title == 'New Conversation':
                self._auto_generate_title(conversation, user_message)
            
            yield self._sse_event('done', {
                'message_id': assistant_msg.id,
                'user_message_id': user_msg.id,
                'sources': sources,
                'thinking_duration': thinking_duration,
                'question_type': question_type,
                'keywords': keywords
            })
            
        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield self._sse_event('error', {'message': str(e)})
    
    def _sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Format SSE event"""
        return f"data: {json.dumps({'type': event_type, **data})}\n\n"
    
    def _auto_generate_title(self, conversation: Conversation, user_message: str):
        """Auto-generate conversation title from first message"""
        # Simple title: first 50 chars of user message
        title = user_message[:50]
        if len(user_message) > 50:
            title += '...'
        conversation.title = title
        db.session.commit()
    
    # ==================== Message Operations ====================
    
    def delete_messages_from(self, conversation_id: str, user_id: str, 
                              message_id: str) -> Optional[str]:
        """
        Delete a message and all subsequent messages in a conversation.
        Returns the content of the deleted message (for edit/re-send), or None if not found.
        """
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return None
        
        target_msg = Message.query.filter_by(
            id=message_id, conversation_id=conversation_id
        ).first()
        if not target_msg:
            return None
        
        original_content = target_msg.content
        original_role = target_msg.role
        
        # Delete this message and all messages after it
        messages_to_delete = Message.query.filter(
            Message.conversation_id == conversation_id,
            Message.created_at >= target_msg.created_at
        ).all()
        
        for msg in messages_to_delete:
            db.session.delete(msg)
        
        conversation.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {'content': original_content, 'role': original_role}
    
    def regenerate_response(self, conversation_id: str, user_id: str,
                            model: str = None,
                            custom_model_id: str = None,
                            external_model_id: str = None) -> Generator:
        """
        Regenerate the last assistant response.
        Deletes the last assistant message and re-generates.
        Yields SSE formatted events.
        """
        try:
            conversation = self.get_conversation(conversation_id, user_id)
            if not conversation:
                yield self._sse_event('error', {'message': 'Conversation not found'})
                return
            
            # Find the last assistant message
            last_assistant = Message.query.filter_by(
                conversation_id=conversation_id, role='assistant'
            ).order_by(Message.created_at.desc()).first()
            
            if not last_assistant:
                yield self._sse_event('error', {'message': 'No assistant message to regenerate'})
                return
            
            # Find the last user message before this assistant message
            last_user = Message.query.filter(
                Message.conversation_id == conversation_id,
                Message.role == 'user',
                Message.created_at <= last_assistant.created_at
            ).order_by(Message.created_at.desc()).first()
            
            if not last_user:
                yield self._sse_event('error', {'message': 'No user message found'})
                return
            
            user_message = last_user.content
            
            # Delete the last assistant message
            db.session.delete(last_assistant)
            db.session.commit()
            model_context = self._resolve_model_context(
                conversation=conversation,
                model=model,
                custom_model_id=custom_model_id,
                external_model_id=external_model_id
            )
            base_model = model_context['base_model']
            system_prompt = model_context['system_prompt']
            effective_custom_model_id = model_context['custom_model_id']
            provider = model_context.get('provider', 'local')
            external_service = model_context.get('external_service')

            question_type = 'GENERAL'
            keywords = []
            context, sources = '', []

            try:
                classifier_service = external_service if provider == 'external' and external_service else self.llm_service
                classifier = QuestionClassifier(classifier_service)
                classification = classifier.classify(user_message, base_model)
                question_type = classification.get('type', 'KNOWLEDGE')
                keywords = classification.get('keywords', [])
            except Exception as e:
                logger.warning(f"Classification failed: {e}")
                classification = {'type': 'KNOWLEDGE', 'keywords': []}
                question_type = classification['type']
                keywords = classification['keywords']

            if question_type == 'KNOWLEDGE' and (effective_custom_model_id or effective_external_model_id):
                try:
                    context, sources = self.get_rag_context(
                        user_message,
                        effective_custom_model_id,
                        effective_external_model_id
                    )
                except Exception as e:
                    logger.warning(f"RAG context retrieval failed: {e}")
                    context, sources = '', []

            if question_type == 'SYSTEM':
                yield self._sse_event('status', {'message': 'Handling system question...'})
                messages = self._build_system_prompt(user_message, system_prompt)
                history = self.get_conversation_history(conversation_id, limit=2)
                if len(history) > 1:
                    for msg in history[:-1]:
                        if msg['role'] == 'user':
                            messages.insert(1, msg)
                            break
            elif question_type == 'KNOWLEDGE':
                if sources:
                    yield self._sse_event('sources', {'sources': sources})
                yield self._sse_event('status', {'message': 'Generating response...'})
                history = self.get_conversation_history(conversation_id, limit=10)
                messages = self.build_prompt_with_context(user_message, context, sources, system_prompt)
                if len(history) > 1:
                    for msg in history[:-1]:
                        messages.insert(1, msg)
            else:
                yield self._sse_event('status', {'message': 'Generating response...'})
                messages = self._build_system_prompt(user_message, system_prompt)
                history = self.get_conversation_history(conversation_id, limit=10)
                if len(history) > 1:
                    for msg in history[:-1]:
                        messages.insert(1, msg)

            full_content = ''
            thinking_content = ''
            is_thinking = False
            thinking_started_at = None
            thinking_duration = 0

            # Create a placeholder assistant message at the start
            assistant_msg = self.add_message(
                conversation_id,
                'assistant',
                '',
                thinking_content='',
                sources=sources if sources else None
            )
            assistant_message_id = assistant_msg.id

            # Track last save time for incremental saves
            last_save_time = time.time()
            save_interval = 2.0

            for chunk in self._stream_response(base_model, messages, provider=provider, external_service=external_service):
                if 'message' in chunk:
                    msg = chunk['message']

                    # Handle thinking field (Ollama think=True returns separate field)
                    thinking_token = msg.get('thinking', '')
                    content_token = msg.get('content', '')

                    if thinking_token:
                        if not is_thinking:
                            is_thinking = True
                            thinking_started_at = time.time()
                            yield self._sse_event('thinking_start', {})
                        thinking_content += thinking_token
                        yield self._sse_event('thinking', {'content': thinking_token})

                    if content_token:
                        if is_thinking:
                            is_thinking = False
                            if thinking_started_at:
                                thinking_duration = int(time.time() - thinking_started_at)
                            yield self._sse_event('thinking_end', {
                                'duration': thinking_duration
                            })
                        full_content += content_token
                        yield self._sse_event('content', {'content': content_token})

                    # Incremental save every 2 seconds
                    current_time = time.time()
                    if current_time - last_save_time >= save_interval:
                        try:
                            assistant_msg.content = full_content
                            assistant_msg.thinking_content = thinking_content if thinking_content else None
                            db.session.commit()
                            last_save_time = current_time
                        except Exception as save_error:
                            logger.warning(f"Incremental save failed: {save_error}")
                            db.session.rollback()

                if chunk.get('done', False):
                    if is_thinking:
                        is_thinking = False
                        if thinking_started_at:
                            thinking_duration = int(time.time() - thinking_started_at)
                        yield self._sse_event('thinking_end', {
                            'duration': thinking_duration
                        })
                    break

            # Final save of the complete message
            try:
                assistant_msg.content = full_content
                assistant_msg.thinking_content = thinking_content if thinking_content else None
                db.session.commit()
            except Exception as save_error:
                logger.error(f"Final message save failed: {save_error}")
                db.session.rollback()
                # Try one more time with fresh session
                try:
                    assistant_msg = Message.query.get(assistant_message_id)
                    if assistant_msg:
                        assistant_msg.content = full_content
                        assistant_msg.thinking_content = thinking_content if thinking_content else None
                        db.session.commit()
                except Exception as retry_error:
                    logger.error(f"Retry save failed: {retry_error}")
            
            yield self._sse_event('done', {
                'message_id': assistant_msg.id,
                'sources': sources,
                'thinking_duration': thinking_duration,
                'question_type': question_type,
                'keywords': keywords
            })
            
        except Exception as e:
            logger.error(f"Regenerate error: {e}")
            yield self._sse_event('error', {'message': str(e)})
    
    # ==================== Search ====================
    
    def search_conversations(self, user_id: str, query: str, 
                             page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Full-text search in conversations and messages"""
        # Search in conversation titles
        title_matches = Conversation.query.filter(
            Conversation.user_id == user_id,
            Conversation.deleted_by_user.is_(False),
            Conversation.title.ilike(f'%{query}%')
        ).all()
        
        # Search in message content
        message_matches = db.session.query(Conversation).join(Message).filter(
            Conversation.user_id == user_id,
            Conversation.deleted_by_user.is_(False),
            Message.content.ilike(f'%{query}%')
        ).distinct().all()
        
        # Combine and deduplicate
        all_conversations = {c.id: c for c in title_matches}
        for c in message_matches:
            all_conversations[c.id] = c
        
        conversations = list(all_conversations.values())
        conversations.sort(key=lambda x: x.updated_at, reverse=True)
        
        # Paginate
        start = (page - 1) * per_page
        end = start + per_page
        paginated = conversations[start:end]
        
        return {
            'conversations': [c.to_dict() for c in paginated],
            'total': len(conversations),
            'page': page,
            'per_page': per_page
        }
    
    # ==================== Export ====================
    
    def export_conversation(self, conversation_id: str, user_id: str, 
                            format: str = 'json') -> Optional[Dict[str, Any]]:
        """Export conversation in specified format"""
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return None
        
        messages = [msg.to_dict() for msg in conversation.messages.all()]
        
        if format == 'json':
            return {
                'conversation': conversation.to_dict(),
                'messages': messages,
                'exported_at': datetime.utcnow().isoformat()
            }
        
        elif format == 'txt':
            lines = [f"# {conversation.title}\n"]
            lines.append(f"Exported: {datetime.utcnow().isoformat()}\n")
            lines.append("-" * 50 + "\n\n")
            
            for msg in messages:
                role = msg['role'].upper()
                lines.append(f"[{role}] ({msg['created_at']})\n")
                lines.append(f"{msg['content']}\n\n")
            
            return {'content': ''.join(lines), 'filename': f"{conversation.title}.txt"}
        
        elif format == 'markdown':
            lines = [f"# {conversation.title}\n\n"]
            lines.append(f"*Exported: {datetime.utcnow().isoformat()}*\n\n")
            lines.append("---\n\n")
            
            for msg in messages:
                if msg['role'] == 'user':
                    lines.append(f"### You\n{msg['content']}\n\n")
                elif msg['role'] == 'assistant':
                    lines.append(f"### Assistant\n{msg['content']}\n\n")
                    if msg.get('sources'):
                        lines.append("**Sources:**\n")
                        for src in msg['sources']:
                            lines.append(f"- [{src['index']}] {src.get('content', '')[:100]}...\n")
                        lines.append("\n")
            
            return {'content': ''.join(lines), 'filename': f"{conversation.title}.md"}
        
        return None


def get_chat_service() -> ChatService:
    """Get chat service instance"""
    return ChatService()
