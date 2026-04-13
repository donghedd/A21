// Typed knowledge graph import for Neo4j
// Put all *_neo4j.csv files in the database import directory before running.

CREATE CONSTRAINT book_id_unique IF NOT EXISTS FOR (n:Book) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT device_id_unique IF NOT EXISTS FOR (n:Device) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT fault_id_unique IF NOT EXISTS FOR (n:Fault) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT cause_id_unique IF NOT EXISTS FOR (n:Cause) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT symptom_id_unique IF NOT EXISTS FOR (n:Symptom) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT action_id_unique IF NOT EXISTS FOR (n:Action) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT parameter_id_unique IF NOT EXISTS FOR (n:Parameter) REQUIRE n.id IS UNIQUE;

LOAD CSV WITH HEADERS FROM 'file:///nodes_book_neo4j.csv' AS row
MERGE (n:Book {id: row.id})
SET n.name = row.name,
    n.mentions = toInteger(row.mentions),
    n.source_books = CASE WHEN row.source_books IS NULL OR trim(row.source_books) = '' THEN [] ELSE split(row.source_books, '|') END;

LOAD CSV WITH HEADERS FROM 'file:///nodes_device_neo4j.csv' AS row
MERGE (n:Device {id: row.id})
SET n.name = row.name,
    n.mentions = toInteger(row.mentions),
    n.source_books = CASE WHEN row.source_books IS NULL OR trim(row.source_books) = '' THEN [] ELSE split(row.source_books, '|') END;

LOAD CSV WITH HEADERS FROM 'file:///nodes_fault_neo4j.csv' AS row
MERGE (n:Fault {id: row.id})
SET n.name = row.name,
    n.mentions = toInteger(row.mentions),
    n.source_books = CASE WHEN row.source_books IS NULL OR trim(row.source_books) = '' THEN [] ELSE split(row.source_books, '|') END;

LOAD CSV WITH HEADERS FROM 'file:///nodes_cause_neo4j.csv' AS row
MERGE (n:Cause {id: row.id})
SET n.name = row.name,
    n.mentions = toInteger(row.mentions),
    n.source_books = CASE WHEN row.source_books IS NULL OR trim(row.source_books) = '' THEN [] ELSE split(row.source_books, '|') END;

LOAD CSV WITH HEADERS FROM 'file:///nodes_symptom_neo4j.csv' AS row
MERGE (n:Symptom {id: row.id})
SET n.name = row.name,
    n.mentions = toInteger(row.mentions),
    n.source_books = CASE WHEN row.source_books IS NULL OR trim(row.source_books) = '' THEN [] ELSE split(row.source_books, '|') END;

LOAD CSV WITH HEADERS FROM 'file:///nodes_action_neo4j.csv' AS row
MERGE (n:Action {id: row.id})
SET n.name = row.name,
    n.mentions = toInteger(row.mentions),
    n.source_books = CASE WHEN row.source_books IS NULL OR trim(row.source_books) = '' THEN [] ELSE split(row.source_books, '|') END;

LOAD CSV WITH HEADERS FROM 'file:///nodes_parameter_neo4j.csv' AS row
MERGE (n:Parameter {id: row.id})
SET n.name = row.name,
    n.mentions = toInteger(row.mentions),
    n.source_books = CASE WHEN row.source_books IS NULL OR trim(row.source_books) = '' THEN [] ELSE split(row.source_books, '|') END;

LOAD CSV WITH HEADERS FROM 'file:///rels_covers_neo4j.csv' AS row
MATCH (s:Book {id: row.source_id})
MATCH (t {id: row.target_id})
MERGE (s)-[r:COVERS]->(t)
SET r.weight = toInteger(row.weight),
    r.source_book = row.source_book,
    r.page = CASE WHEN row.page IS NULL OR trim(row.page) = '' THEN null ELSE toInteger(row.page) END,
    r.evidence = row.evidence;

LOAD CSV WITH HEADERS FROM 'file:///rels_has_fault_neo4j.csv' AS row
MATCH (s:Device {id: row.source_id})
MATCH (t:Fault {id: row.target_id})
MERGE (s)-[r:HAS_FAULT]->(t)
SET r.weight = toInteger(row.weight),
    r.source_book = row.source_book,
    r.page = CASE WHEN row.page IS NULL OR trim(row.page) = '' THEN null ELSE toInteger(row.page) END,
    r.evidence = row.evidence;

LOAD CSV WITH HEADERS FROM 'file:///rels_caused_by_neo4j.csv' AS row
MATCH (s:Fault {id: row.source_id})
MATCH (t:Cause {id: row.target_id})
MERGE (s)-[r:CAUSED_BY]->(t)
SET r.weight = toInteger(row.weight),
    r.source_book = row.source_book,
    r.page = CASE WHEN row.page IS NULL OR trim(row.page) = '' THEN null ELSE toInteger(row.page) END,
    r.evidence = row.evidence;

LOAD CSV WITH HEADERS FROM 'file:///rels_has_symptom_neo4j.csv' AS row
MATCH (s:Fault {id: row.source_id})
MATCH (t:Symptom {id: row.target_id})
MERGE (s)-[r:HAS_SYMPTOM]->(t)
SET r.weight = toInteger(row.weight),
    r.source_book = row.source_book,
    r.page = CASE WHEN row.page IS NULL OR trim(row.page) = '' THEN null ELSE toInteger(row.page) END,
    r.evidence = row.evidence;

LOAD CSV WITH HEADERS FROM 'file:///rels_resolved_by_neo4j.csv' AS row
MATCH (s:Fault {id: row.source_id})
MATCH (t:Action {id: row.target_id})
MERGE (s)-[r:RESOLVED_BY]->(t)
SET r.weight = toInteger(row.weight),
    r.source_book = row.source_book,
    r.page = CASE WHEN row.page IS NULL OR trim(row.page) = '' THEN null ELSE toInteger(row.page) END,
    r.evidence = row.evidence;

LOAD CSV WITH HEADERS FROM 'file:///rels_targets_neo4j.csv' AS row
MATCH (s:Action {id: row.source_id})
MATCH (t {id: row.target_id})
MERGE (s)-[r:TARGETS]->(t)
SET r.weight = toInteger(row.weight),
    r.source_book = row.source_book,
    r.page = CASE WHEN row.page IS NULL OR trim(row.page) = '' THEN null ELSE toInteger(row.page) END,
    r.evidence = row.evidence;

LOAD CSV WITH HEADERS FROM 'file:///rels_affects_parameter_neo4j.csv' AS row
MATCH (s:Fault {id: row.source_id})
MATCH (t:Parameter {id: row.target_id})
MERGE (s)-[r:AFFECTS_PARAMETER]->(t)
SET r.weight = toInteger(row.weight),
    r.source_book = row.source_book,
    r.page = CASE WHEN row.page IS NULL OR trim(row.page) = '' THEN null ELSE toInteger(row.page) END,
    r.evidence = row.evidence;

LOAD CSV WITH HEADERS FROM 'file:///rels_shows_as_neo4j.csv' AS row
MATCH (s:Parameter {id: row.source_id})
MATCH (t:Symptom {id: row.target_id})
MERGE (s)-[r:SHOWS_AS]->(t)
SET r.weight = toInteger(row.weight),
    r.source_book = row.source_book,
    r.page = CASE WHEN row.page IS NULL OR trim(row.page) = '' THEN null ELSE toInteger(row.page) END,
    r.evidence = row.evidence;

LOAD CSV WITH HEADERS FROM 'file:///rels_has_component_neo4j.csv' AS row
MATCH (s:Device {id: row.source_id})
MATCH (t:Device {id: row.target_id})
MERGE (s)-[r:HAS_COMPONENT]->(t)
SET r.weight = toInteger(row.weight),
    r.source_book = row.source_book,
    r.page = CASE WHEN row.page IS NULL OR trim(row.page) = '' THEN null ELSE toInteger(row.page) END,
    r.evidence = row.evidence;

// Verification
MATCH (n) RETURN labels(n) AS labels, count(*) AS cnt ORDER BY cnt DESC;
MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt ORDER BY cnt DESC;