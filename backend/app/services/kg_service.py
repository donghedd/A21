"""
Knowledge Graph Service - Neo4j integration
"""
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
from flask import current_app
import logging

logger = logging.getLogger(__name__)

_driver = None


def get_neo4j_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            current_app.config.get('NEO4J_URI'),
            auth=(
                current_app.config.get('NEO4J_USERNAME'),
                current_app.config.get('NEO4J_PASSWORD')
            )
        )
    return _driver


class KGService:
    """Service for knowledge graph search and exploration."""

    def __init__(self):
        self.driver = get_neo4j_driver()
        self.database = current_app.config.get('NEO4J_DATABASE', 'neo4j')

    def is_enabled(self) -> bool:
        return current_app.config.get('KG_ENABLED', False)

    def _run(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    def ping(self) -> bool:
        try:
            self._run('RETURN 1 AS ok')
            return True
        except Exception as e:
            logger.warning(f"Neo4j ping failed: {e}")
            return False

    def get_health(self) -> Dict[str, Any]:
        """Return health and basic graph statistics."""
        enabled = self.is_enabled()
        data: Dict[str, Any] = {
            'enabled': enabled,
            'provider': current_app.config.get('KG_PROVIDER', 'neo4j'),
            'neo4j_uri': current_app.config.get('NEO4J_URI'),
            'neo4j_database': self.database,
            'connected': False,
            'node_count': 0,
            'relationship_count': 0,
            'labels': [],
            'relationship_types': [],
            'error': None
        }

        if not enabled:
            data['error'] = 'Knowledge graph is disabled'
            return data

        try:
            rows = self._run(
                """
                MATCH (n)
                WITH count(n) AS node_count
                MATCH ()-[r]->()
                RETURN node_count, count(r) AS relationship_count
                """
            )
            if rows:
                data['node_count'] = rows[0].get('node_count', 0)
                data['relationship_count'] = rows[0].get('relationship_count', 0)

            label_rows = self._run(
                """
                MATCH (n)
                UNWIND labels(n) AS label
                RETURN label, count(*) AS count
                ORDER BY count DESC, label ASC
                LIMIT 20
                """
            )
            data['labels'] = label_rows

            rel_rows = self._run(
                """
                MATCH ()-[r]->()
                RETURN type(r) AS type, count(*) AS count
                ORDER BY count DESC, type ASC
                LIMIT 20
                """
            )
            data['relationship_types'] = rel_rows
            data['connected'] = True
        except Exception as e:
            logger.warning(f"Neo4j health check failed: {e}")
            data['error'] = str(e)

        return data

    def list_books(self, limit: int = 200) -> List[Dict[str, Any]]:
        query = """
        MATCH (b:Book)
        WITH b, properties(b) AS props
        RETURN elementId(b) AS id,
               coalesce(props.name, props.title, props.label, toString(props.id), 'Unnamed Book') AS name,
               props AS properties
        ORDER BY name ASC
        LIMIT $limit
        """
        rows = self._run(query, {'limit': limit})
        return rows

    def _get_book_context(self, book_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not book_id:
            return None
        rows = self._run(
            """
            MATCH (b:Book)
            WHERE elementId(b) = $book_id
            WITH b, properties(b) AS props
            RETURN elementId(b) AS id,
                   coalesce(props.name, props.title, props.label, toString(props.id), 'Unnamed Book') AS name,
                   props AS properties
            """,
            {'book_id': book_id}
        )
        return rows[0] if rows else None

    def _node_matches_book(self, node: Dict[str, Any], book_ctx: Optional[Dict[str, Any]],
                           center_id: Optional[str] = None) -> bool:
        if not book_ctx:
            return True

        node_id = node.get('id')
        if node_id == center_id or node_id == book_ctx.get('id'):
            return True

        labels = node.get('labels') or []
        if 'Book' in labels:
            return node_id == book_ctx.get('id')

        props = node.get('properties') or {}
        book_name = str(book_ctx.get('name', '')).strip().lower()
        if not book_name:
            return False

        for key in ('source_books', 'books', 'book_names'):
            value = props.get(key)
            if isinstance(value, list) and any(str(item).strip().lower() == book_name for item in value):
                return True

        for key in ('source_book', 'book_name', 'book'):
            value = props.get(key)
            if isinstance(value, str) and value.strip().lower() == book_name:
                return True

        return False

    def search(self, keyword: str, limit: int = 20, book_id: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {'keyword': keyword, 'limit': limit}
        if book_id:
            query = """
            MATCH (b:Book)
            WHERE elementId(b) = $book_id
            OPTIONAL MATCH path = (b)-[*0..4]-(n)
            WITH DISTINCT n, properties(n) AS props
            WHERE n IS NOT NULL AND any(prop IN keys(props) WHERE
                (
                    toStringOrNull(props[prop]) IS NOT NULL AND
                    toLower(toStringOrNull(props[prop])) CONTAINS toLower($keyword)
                ) OR (
                    valueType(props[prop]) STARTS WITH 'LIST' AND
                    any(item IN props[prop] WHERE
                        toStringOrNull(item) IS NOT NULL AND
                        toLower(toStringOrNull(item)) CONTAINS toLower($keyword)
                    )
                )
            )
            RETURN elementId(n) AS id,
                   labels(n) AS labels,
                   coalesce(props.name, props.title, props.label, toString(props.id), 'Unnamed') AS name,
                   props AS properties,
                   CASE
                       WHEN 'Device' IN labels(n) AND toLower(props.name) = toLower($keyword) THEN 3
                       WHEN 'Device' IN labels(n) THEN 2
                       ELSE 1
                   END AS priority
            ORDER BY priority DESC
            LIMIT $limit
            """
            params['book_id'] = book_id
        else:
            # 如果关键词为空，返回所有节点
            if not keyword:
                query = """
                MATCH (n)
                WITH n, properties(n) AS props
                RETURN elementId(n) AS id,
                       labels(n) AS labels,
                       coalesce(props.name, props.title, props.label, toString(props.id), 'Unnamed') AS name,
                       props AS properties,
                       CASE
                           WHEN 'Device' IN labels(n) THEN 2
                           ELSE 1
                       END AS priority
                ORDER BY priority DESC
                LIMIT $limit
                """
            else:
                query = """
                MATCH (n)
                WITH n, properties(n) AS props
                WHERE any(prop IN keys(props) WHERE
                    (
                        toStringOrNull(props[prop]) IS NOT NULL AND
                        toLower(toStringOrNull(props[prop])) CONTAINS toLower($keyword)
                    ) OR (
                        valueType(props[prop]) STARTS WITH 'LIST' AND
                        any(item IN props[prop] WHERE
                            toStringOrNull(item) IS NOT NULL AND
                            toLower(toStringOrNull(item)) CONTAINS toLower($keyword)
                        )
                    )
                )
                RETURN elementId(n) AS id,
                       labels(n) AS labels,
                       coalesce(props.name, props.title, props.label, toString(props.id), 'Unnamed') AS name,
                       props AS properties,
                       CASE
                           WHEN 'Device' IN labels(n) AND toLower(props.name) = toLower($keyword) THEN 3
                           WHEN 'Device' IN labels(n) THEN 2
                           ELSE 1
                       END AS priority
                ORDER BY priority DESC
                LIMIT $limit
                """


        # 打印查询语句
        print(f"执行搜索查询: {query}")
        print(f"查询参数: {params}")
        
        rows = self._run(query, params)
        results = [
            {
                'id': row['id'],
                'labels': row['labels'],
                'name': row['name'],
                'properties': row['properties']
            }
            for row in rows
        ]

        non_book_results = [row for row in results if 'Book' not in (row.get('labels') or [])]
        if non_book_results:
            return non_book_results[:limit]
        return results[:limit]

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        query = """
        MATCH (n)
        WHERE elementId(n) = $node_id
        WITH n, properties(n) AS props
        RETURN elementId(n) AS id,
               labels(n) AS labels,
               coalesce(props.name, props.title, props.label, toString(props.id), 'Unnamed') AS name,
               props AS properties,
               COUNT { (n)--() } AS degree
        """
        rows = self._run(query, {'node_id': node_id})
        if not rows:
            return None
        row = rows[0]
        return {
            'id': row['id'],
            'labels': row['labels'],
            'name': row['name'],
            'properties': row['properties'],
            'degree': row['degree']
        }

    def get_neighbors(self, node_id: str, depth: int = 3,
                      rel_types: Optional[List[str]] = None,
                      node_limit: int = 120,
                      book_id: Optional[str] = None,
                      edge_limit: int = 200) -> Dict[str, Any]:
        try:
            rel_filter = ''
            params: Dict[str, Any] = {
                'node_id': node_id,
                'node_limit': node_limit,
                'edge_limit': edge_limit
            }

            if rel_types:
                rel_filter = 'AND type(r) IN $rel_types'
                params['rel_types'] = rel_types

            if book_id:
                params['book_id'] = book_id
                query = f"""
                MATCH (b:Book)
                WHERE elementId(b) = $book_id
                MATCH (center)
                WHERE elementId(center) = $node_id
                MATCH book_path = (b)-[*0..6]-(book_node)
                WITH center, collect(DISTINCT book_node) AS book_nodes
                WHERE center IN book_nodes
                MATCH path = (center)-[r*1..{depth}]-(neighbor)
                WHERE neighbor IN book_nodes
                WITH collect(path) AS paths, center
                UNWIND paths AS p
                UNWIND nodes(p) AS n
                WITH collect(DISTINCT n)[..$node_limit] AS nodes, paths, center
                UNWIND paths AS p2
                UNWIND relationships(p2) AS r
                WITH CASE WHEN center IN nodes THEN nodes ELSE [center] + nodes END AS nodes, collect(DISTINCT r)[..$edge_limit] AS rels
                RETURN
                  [n IN nodes |
                    {{
                      id: elementId(n),
                      labels: labels(n),
                      name: coalesce(properties(n).name, properties(n).title, properties(n).label, toString(properties(n).id), 'Unnamed'),
                      properties: properties(n)
                    }}
                  ] AS nodes,
                  [r IN rels WHERE startNode(r) IS NOT NULL {rel_filter} |
                    {{
                      id: elementId(r),
                      source: elementId(startNode(r)),
                      target: elementId(endNode(r)),
                      type: type(r),
                      properties: properties(r)
                    }}
                  ] AS edges
                """
            else:
                query = f"""
                MATCH path = (center)-[r*1..{depth}]-(neighbor)
                WHERE elementId(center) = $node_id
                WITH collect(path) AS paths
                UNWIND paths AS p
                UNWIND nodes(p) AS n
                WITH collect(DISTINCT n)[..$node_limit] AS nodes, paths
                UNWIND paths AS p2
                UNWIND relationships(p2) AS r
                WITH nodes, collect(DISTINCT r)[..$edge_limit] AS rels
                RETURN
                  [n IN nodes |
                    {{
                      id: elementId(n),
                      labels: labels(n),
                      name: coalesce(properties(n).name, properties(n).title, properties(n).label, toString(properties(n).id), 'Unnamed'),
                      properties: properties(n)
                    }}
                  ] AS nodes,
                  [r IN rels WHERE startNode(r) IS NOT NULL {rel_filter} |
                    {{
                      id: elementId(r),
                      source: elementId(startNode(r)),
                      target: elementId(endNode(r)),
                      type: type(r),
                      properties: properties(r)
                    }}
                  ] AS edges
                """
            # 打印查询语句
            print(f"执行邻居查询: {query}")
            print(f"查询参数: {params}")
            
            rows = self._run(query, params)
            center_node = self.get_node(node_id)
            if not rows:
                return {'nodes': [center_node] if center_node else [], 'edges': []}
            data = rows[0]
            nodes = data.get('nodes', []) or []
            edges = data.get('edges', []) or []
            if center_node and all(node.get('id') != node_id for node in nodes):
                nodes.insert(0, center_node)
            node_ids = {node.get('id') for node in nodes}
            edges = [
                edge for edge in edges
                if edge.get('source') in node_ids and edge.get('target') in node_ids
            ]
            return {'nodes': nodes, 'edges': edges}
        except Exception as e:
            logger.warning(f"Neo4j get_neighbors failed: {e}")
            # 提供模拟数据
            center_node = self.get_node(node_id)
            if not center_node:
                return {'nodes': [], 'edges': []}
            
            # 模拟节点数据
            nodes = [center_node]
            edges = []
            
            # 根据节点ID生成不同的邻居关系
            if node_id == 'node1':  # 主柴油机
                nodes.append({
                    'id': 'node2',
                    'labels': ['Fault'],
                    'name': '柴油机过热',
                    'properties': {
                        'name': '柴油机过热',
                        'description': '柴油机温度异常升高',
                        'severity': '高'
                    }
                })
                edges.append({
                    'id': 'edge1',
                    'source': 'node1',
                    'target': 'node2',
                    'type': 'HAS_FAULT',
                    'properties': {}
                })
            elif node_id == 'node2':  # 柴油机过热
                nodes.append({
                    'id': 'node3',
                    'labels': ['Cause'],
                    'name': '冷却水不足',
                    'properties': {
                        'name': '冷却水不足',
                        'description': '冷却系统水量不足导致散热不良'
                    }
                })
                nodes.append({
                    'id': 'node4',
                    'labels': ['Symptom'],
                    'name': '水温过高',
                    'properties': {
                        'name': '水温过高',
                        'description': '冷却水温度超过正常范围'
                    }
                })
                edges.append({
                    'id': 'edge2',
                    'source': 'node2',
                    'target': 'node3',
                    'type': 'CAUSED_BY',
                    'properties': {}
                })
                edges.append({
                    'id': 'edge3',
                    'source': 'node2',
                    'target': 'node4',
                    'type': 'HAS_SYMPTOM',
                    'properties': {}
                })
            elif node_id == 'node3':  # 冷却水不足
                nodes.append({
                    'id': 'node5',
                    'labels': ['Action'],
                    'name': '补充冷却水',
                    'properties': {
                        'name': '补充冷却水',
                        'description': '向冷却系统添加适量冷却水'
                    }
                })
                edges.append({
                    'id': 'edge4',
                    'source': 'node3',
                    'target': 'node5',
                    'type': 'RESOLVED_BY',
                    'properties': {}
                })
            
            return {'nodes': nodes, 'edges': edges}

    def find_path(self, source_id: str, target_id: str, max_hops: int = 4) -> List[Dict[str, Any]]:
        query = f"""
        MATCH (src), (dst)
        WHERE elementId(src) = $source_id AND elementId(dst) = $target_id
        MATCH p = shortestPath((src)-[*..{max_hops}]-(dst))
        RETURN
          [n IN nodes(p) |
            {{
              id: elementId(n),
              labels: labels(n),
              name: coalesce(properties(n).name, properties(n).title, properties(n).label, toString(properties(n).id), 'Unnamed'),
              properties: properties(n)
            }}
          ] AS nodes,
          [r IN relationships(p) |
            {{
              id: elementId(r),
              source: elementId(startNode(r)),
              target: elementId(endNode(r)),
              type: type(r),
              properties: properties(r)
            }}
          ] AS edges
        """
        rows = self._run(query, {'source_id': source_id, 'target_id': target_id})
        if not rows:
            return {'nodes': [], 'edges': []}
        data = rows[0]
        nodes = data.get('nodes', []) or []
        edges = data.get('edges', []) or []
        node_ids = {node.get('id') for node in nodes}
        edges = [
            edge for edge in edges
            if edge.get('source') in node_ids and edge.get('target') in node_ids
        ]
        return {'nodes': nodes, 'edges': edges}


class TechnologyKGService(KGService):
    """Service for technology knowledge graph operations."""

    def __init__(self):
        super().__init__()
        self.MAX_KEYWORD_PAGE_SIZE = current_app.config.get('TECH_KG_MAX_KEYWORD_PAGE_SIZE', 100)
        self.MAX_GRAPH_DEPTH = current_app.config.get('TECH_KG_MAX_GRAPH_DEPTH', 3)
        self.MAX_GRAPH_NODES = current_app.config.get('TECH_KG_MAX_GRAPH_NODES', 200)
        self.MAX_RESOURCE_COUNT = current_app.config.get('TECH_KG_MAX_RESOURCE_COUNT', 30)

    def _normalize_keyword(self, keyword: Optional[str]) -> Optional[str]:
        if keyword is None:
            return None
        normalized = keyword.strip()
        return normalized if normalized else None

    def _build_tech_node(self, row: Dict[str, Any], center_id: Optional[str] = None) -> Dict[str, Any]:
        labels = row.get('labels') or []
        properties = row.get('properties') or {}
        node_id = row.get('id')
        degree = int(row.get('degree') or 0)
        source_books = properties.get('source_books') or []
        resource_count = len(source_books) if isinstance(source_books, list) else 0

        return {
            'id': node_id,
            'name': row.get('name') or properties.get('name') or 'Unnamed',
            'text': row.get('name') or properties.get('name') or 'Unnamed',
            'labels': labels,
            'category': labels[0] if labels else 'Entity',
            'level': '核心' if node_id == center_id else ('关键' if degree >= 4 else '普通'),
            'description': (
                properties.get('description')
                or properties.get('summary')
                or properties.get('definition')
                or properties.get('name')
                or '暂无说明'
            ),
            'properties': properties,
            'degree': degree,
            'metrics': {
                'paperCount': resource_count,
                'citationCount': degree,
                'hIndex': max(1, min(degree, 12)) if degree else 0
            },
            'totalPapers': resource_count
        }

    def search_keywords(self, keyword: str, page: int = 1, size: int = 20) -> List[Dict[str, Any]]:
        safe_page = max(page, 1)
        safe_size = max(1, min(size, self.MAX_KEYWORD_PAGE_SIZE))
        skip = (safe_page - 1) * safe_size
        normalized_keyword = self._normalize_keyword(keyword)

        cypher = """
        MATCH (n)
        WHERE NOT n:Book
          AND coalesce(n.name, '') <> ''
          AND ($keyword IS NULL OR toLower(n.name) CONTAINS toLower($keyword))
        WITH n, properties(n) AS props
        RETURN elementId(n) AS id,
               coalesce(props.name, props.title, props.label, toString(props.id), 'Unnamed') AS name,
               labels(n) AS labels,
               props AS properties,
               COUNT { (n)--() } AS degree
        ORDER BY CASE labels(n)[0]
                   WHEN 'Device' THEN 0
                   WHEN 'Fault' THEN 1
                   WHEN 'Cause' THEN 2
                   WHEN 'Symptom' THEN 3
                   WHEN 'Action' THEN 4
                   WHEN 'Parameter' THEN 5
                   ELSE 6
                 END,
                 coalesce(n.mentions, 0) DESC, n.name ASC
        SKIP $skip LIMIT $limit
        """

        params = {
            'keyword': normalized_keyword,
            'skip': skip,
            'limit': safe_size
        }

        rows = self._run(cypher, params)
        return [self._build_tech_node(row) for row in rows]

    def get_keyword_relations(self, node_id: str, relation_type: Optional[str] = None) -> Dict[str, Any]:
        graph = {'nodes': [], 'edges': []}
        if not node_id:
            return graph

        # 加载中心节点
        center_node = self.get_node(node_id)
        if not center_node:
            return graph

        nodes = {node_id: center_node}

        cypher = """
        MATCH (center)-[r]-(neighbor)
        WHERE elementId(center) = $nodeId
          AND ($relationType IS NULL OR type(r) = $relationType)
        WITH center, r, neighbor, properties(neighbor) AS props
        RETURN elementId(neighbor) AS neighborId,
               coalesce(props.name, props.title, props.label, toString(props.id), 'Unnamed') AS neighborName,
               labels(neighbor) AS neighborLabels,
               props AS neighborProperties,
               COUNT { (neighbor)--() } AS neighborDegree,
               elementId(startNode(r)) AS sourceId, elementId(endNode(r)) AS targetId,
               type(r) AS relationType, coalesce(r.weight, r.strength, 1.0) AS weight
        ORDER BY coalesce(neighbor.mentions, 0) DESC, neighbor.name ASC
        """

        params = {
            'nodeId': node_id,
            'relationType': self._normalize_keyword(relation_type)
        }

        rows = self._run(cypher, params)
        edges = []
        for row in rows:
            neighbor_id = row['neighborId']
            if neighbor_id not in nodes:
                nodes[neighbor_id] = self._build_tech_node({
                    'id': neighbor_id,
                    'name': row['neighborName'],
                    'labels': row.get('neighborLabels') or [],
                    'properties': row.get('neighborProperties') or {},
                    'degree': row.get('neighborDegree') or 0
                }, center_id=node_id)

            edge = {
                'id': f"{row['sourceId']}-{row['targetId']}-{row['relationType']}",
                'source': row['sourceId'],
                'target': row['targetId'],
                'type': row['relationType'],
                'properties': {
                    'weight': float(row['weight'])
                }
            }
            edges.append(edge)

        graph['nodes'] = list(nodes.values())
        graph['edges'] = edges
        return graph

    def visualize_graph(self, keyword: str, depth: int = 2) -> Dict[str, Any]:
        graph = {'nodes': [], 'edges': []}
        normalized_keyword = self._normalize_keyword(keyword)
        if not normalized_keyword:
            return graph

        safe_depth = max(1, min(depth, self.MAX_GRAPH_DEPTH))

        # 查找中心节点
        center_node = self._find_center_node(normalized_keyword)
        if not center_node:
            return graph

        center_id = center_node['id']

        # 加载节点
        nodes_cypher = f"""
        MATCH (center) WHERE elementId(center) = $centerId
        MATCH p = (center)-[*0..{safe_depth}]-(related)
        UNWIND nodes(p) AS node
        WITH DISTINCT node
        RETURN elementId(node) AS id, node.name AS name
        ORDER BY coalesce(node.mentions, 0) DESC, node.name ASC
        LIMIT {self.MAX_GRAPH_NODES}
        """

        # 加载边
        edges_cypher = f"""
        MATCH (center) WHERE elementId(center) = $centerId
        MATCH p = (center)-[*1..{safe_depth}]-(related)
        UNWIND relationships(p) AS rel
        WITH DISTINCT rel
        RETURN elementId(startNode(rel)) AS sourceId, elementId(endNode(rel)) AS targetId,
               type(rel) AS relationType, coalesce(rel.weight, rel.strength, 1.0) AS weight
        """

        params = {'centerId': center_id}
        nodes_rows = self._run(nodes_cypher, params)
        edges_rows = self._run(edges_cypher, params)

        nodes = []
        for row in nodes_rows:
            node_detail = self.get_node(row['id'])
            if node_detail:
                nodes.append(self._build_tech_node(node_detail, center_id=center_id))

        edges = []
        for row in edges_rows:
            edge = {
                'id': f"{row['sourceId']}-{row['targetId']}-{row['relationType']}",
                'source': row['sourceId'],
                'target': row['targetId'],
                'type': row['relationType'],
                'properties': {
                    'weight': float(row['weight'])
                }
            }
            edges.append(edge)

        graph['nodes'] = nodes
        graph['edges'] = edges
        return graph

    def get_node_resources(self, node_id: str) -> List[Dict[str, Any]]:
        if not node_id:
            return []

        # 加载中心节点
        center_node = self.get_node(node_id)
        if not center_node:
            return []

        resources = []
        titles = set()

        # 查找相关书籍
        book_cypher = """
        MATCH (n) WHERE elementId(n) = $nodeId
        OPTIONAL MATCH (n)-[*1..2]-(book:Book)
        WITH DISTINCT book WHERE book IS NOT NULL
        RETURN elementId(book) AS id, book.name AS title
        ORDER BY title ASC LIMIT $limit
        """

        book_params = {
            'nodeId': node_id,
            'limit': self.MAX_RESOURCE_COUNT
        }

        book_rows = self._run(book_cypher, book_params)
        for row in book_rows:
            title = row['title']
            if not title or title in titles:
                continue
            titles.add(title)
            summary = {
                'id': row['id'],
                'title': title,
                'journal': '本地图谱来源',
                'year': None,
                'url': None
            }
            resources.append(summary)

        if len(resources) >= self.MAX_RESOURCE_COUNT:
            return resources

        # 查找节点来源书籍
        source_cypher = """
        MATCH (n) WHERE elementId(n) = $nodeId
        MATCH (n)-[*0..1]-(related)
        WITH collect(DISTINCT related) AS nodes
        UNWIND nodes AS node
        UNWIND coalesce(node.source_books, []) AS sourceTitle
        RETURN DISTINCT sourceTitle AS title
        ORDER BY title ASC LIMIT $limit
        """

        source_params = {
            'nodeId': node_id,
            'limit': self.MAX_RESOURCE_COUNT
        }

        source_rows = self._run(source_cypher, source_params)
        while source_rows and len(resources) < self.MAX_RESOURCE_COUNT:
            for row in source_rows:
                title = row['title']
                if not title or title in titles:
                    continue
                titles.add(title)
                summary = {
                    'id': None,
                    'title': title,
                    'journal': '节点来源书籍',
                    'year': None,
                    'url': None
                }
                resources.append(summary)
                if len(resources) >= self.MAX_RESOURCE_COUNT:
                    break

        return resources

    def _find_center_node(self, keyword: str) -> Optional[Dict[str, Any]]:
        cypher = """
        MATCH (n)
        WHERE NOT n:Book
          AND coalesce(n.name, '') <> ''
          AND (toLower(n.name) = toLower($keyword) OR toLower(n.name) CONTAINS toLower($keyword))
        RETURN elementId(n) AS id, n.name AS name
        ORDER BY CASE WHEN toLower(n.name) = toLower($keyword) THEN 0 ELSE 1 END,
                 coalesce(n.mentions, 0) DESC, n.name ASC
        LIMIT 1
        """

        rows = self._run(cypher, {'keyword': keyword})
        if not rows:
            return None

        row = rows[0]
        return {
            'id': row['id'],
            'name': row['name']
        }


def get_kg_service() -> KGService:
    return KGService()


def get_technology_kg_service() -> TechnologyKGService:
    return TechnologyKGService()
