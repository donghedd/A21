"""Knowledge Graph API Routes
"""
from flask import request
from flask_jwt_extended import jwt_required

from . import kg_bp
from ..services import get_kg_service, get_technology_kg_service
from ..utils.response import success_response, error_response


def _ensure_enabled(service):
    if not service.is_enabled():
        return error_response(400, 'Knowledge graph is disabled')
    if not service.ping():
        return error_response(503, 'Knowledge graph service is unavailable')
    return None


@kg_bp.route('/health', methods=['GET'])
@jwt_required()
def kg_health():
    """Knowledge graph health and statistics check."""
    service = get_kg_service()
    health = service.get_health()
    return success_response(data=health)


@kg_bp.route('/search', methods=['GET'])
@jwt_required()
def search_kg():
    service = get_kg_service()
    blocked = _ensure_enabled(service)
    if blocked:
        return blocked

    keyword = request.args.get('q', '').strip()
    limit = request.args.get('limit', 20, type=int)
    book_id = request.args.get('book_id', '').strip() or None
    # 允许空关键词搜索，这样前端可以获取所有节点

    data = service.search(keyword, limit=min(limit, 500), book_id=book_id)
    return success_response(data=data)


@kg_bp.route('/books', methods=['GET'])
@jwt_required()
def get_kg_books():
    service = get_kg_service()
    blocked = _ensure_enabled(service)
    if blocked:
        return blocked
    data = service.list_books(limit=200)
    return success_response(data=data)


@kg_bp.route('/node/<node_id>', methods=['GET'])
@jwt_required()
def get_kg_node(node_id):
    service = get_kg_service()
    blocked = _ensure_enabled(service)
    if blocked:
        return blocked

    node = service.get_node(node_id)
    if not node:
        return error_response(404, 'Node not found')
    return success_response(data=node)


@kg_bp.route('/node/<node_id>/neighbors', methods=['GET'])
@jwt_required()
def get_kg_neighbors(node_id):
    service = get_kg_service()
    blocked = _ensure_enabled(service)
    if blocked:
        return blocked

    depth = request.args.get('depth', 2, type=int)
    node_limit = request.args.get('node_limit', 120, type=int)
    edge_limit = request.args.get('edge_limit', 200, type=int)
    book_id = request.args.get('book_id', '').strip() or None
    rel_types = request.args.getlist('rel_type')

    data = service.get_neighbors(
        node_id=node_id,
        depth=max(1, min(depth, 3)),
        rel_types=rel_types or None,
        node_limit=max(10, min(node_limit, 150)),
        book_id=book_id,
        edge_limit=max(10, min(edge_limit, 250))
    )
    return success_response(data=data)


@kg_bp.route('/path', methods=['GET'])
@jwt_required()
def find_kg_path():
    service = get_kg_service()
    blocked = _ensure_enabled(service)
    if blocked:
        return blocked

    source = request.args.get('source', '').strip()
    target = request.args.get('target', '').strip()
    max_hops = request.args.get('max_hops', 4, type=int)
    if not source or not target:
        return error_response(400, 'source and target are required')

    data = service.find_path(source, target, max_hops=max(1, min(max_hops, 6)))
    return success_response(data=data)


# 技术图谱相关接口
@kg_bp.route('/tech/search', methods=['GET'])
@jwt_required()
def search_tech_kg():
    service = get_technology_kg_service()
    blocked = _ensure_enabled(service)
    if blocked:
        return blocked
    
    keyword = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 20, type=int)
    
    data = service.search_keywords(keyword, page=page, size=min(size, 100))
    return success_response(data=data)


@kg_bp.route('/tech/relations/<node_id>', methods=['GET'])
@jwt_required()
def get_tech_relations(node_id):
    service = get_technology_kg_service()
    blocked = _ensure_enabled(service)
    if blocked:
        return blocked
    
    relation_type = request.args.get('relation_type', '').strip() or None
    
    data = service.get_keyword_relations(node_id, relation_type=relation_type)
    return success_response(data=data)


@kg_bp.route('/tech/visualize', methods=['GET'])
@jwt_required()
def visualize_tech_kg():
    service = get_technology_kg_service()
    blocked = _ensure_enabled(service)
    if blocked:
        return blocked
    
    keyword = request.args.get('q', '').strip()
    depth = request.args.get('depth', 2, type=int)
    
    data = service.visualize_graph(keyword, depth=max(1, min(depth, 3)))
    return success_response(data=data)


@kg_bp.route('/tech/resources/<node_id>', methods=['GET'])
@jwt_required()
def get_tech_resources(node_id):
    service = get_technology_kg_service()
    blocked = _ensure_enabled(service)
    if blocked:
        return blocked
    
    data = service.get_node_resources(node_id)
    return success_response(data=data)
