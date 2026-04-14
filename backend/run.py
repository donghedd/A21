#!/usr/bin/env python
"""
SFQA Application Entry Point
"""
import os
from pathlib import Path
import click
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import create_app
from app.extensions import db

# Create application
app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.cli.command('init-db')
def init_db():
    """Initialize the database."""
    with app.app_context():
        db.create_all()
        print('Database tables created successfully!')


@app.cli.command('drop-db')
def drop_db():
    """Drop all database tables."""
    with app.app_context():
        db.drop_all()
        print('Database tables dropped!')


@app.cli.command('init-ship-electrical-kb')
@click.option('--source-dir', default=None, help='Directory containing KB source files.')
@click.option('--name', default='船舶电气知识库', help='Knowledge base display name.')
@click.option('--collection-name', default='kb_ship_electrical_system', help='Chroma collection name.')
@click.option('--rebuild/--no-rebuild', default=False, help='Delete existing imported files and rebuild the KB.')
def init_ship_electrical_kb(source_dir, name, collection_name, rebuild):
    """Create/update the system ship electrical knowledge base from data/KB."""
    from app.models import User, KnowledgeBase, File
    from app.services import get_file_service, get_vector_service, get_rag_service

    project_root = Path(__file__).resolve().parent.parent
    kb_source_dir = Path(source_dir) if source_dir else (project_root / 'data' / 'KB')
    kb_source_dir = kb_source_dir.resolve()

    if not kb_source_dir.exists():
        raise click.ClickException(f"Source directory not found: {kb_source_dir}")

    with app.app_context():
        admin = User.query.filter_by(role='admin').order_by(User.created_at.asc()).first()
        if not admin:
            raise click.ClickException('No admin user found. Initialize admin first.')

            kb = KnowledgeBase.query.filter_by(collection_name=collection_name).first()
            if kb is None:
                kb = KnowledgeBase(
                    user_id=admin.id,
                    name=name,
                    description='系统级船舶电气知识库，内容来自 data/KB',
                    collection_name=collection_name,
                    is_system=True,
                )
            db.session.add(kb)
            db.session.commit()
            click.echo(f"Created knowledge base: {kb.name} ({kb.id})")
        else:
            kb.name = name
            kb.is_system = True
            if not kb.description:
                kb.description = '系统级船舶电气知识库，内容来自 data/KB'
            db.session.commit()
            click.echo(f"Using existing knowledge base: {kb.name} ({kb.id})")

        if rebuild:
            vector_service = get_vector_service()
            vector_service.delete_collection(kb.collection_name)
            rag_service = get_rag_service()
            rag_service.bm25_retriever.invalidate_cache(kb.collection_name)

            for file_record in kb.files.all():
                try:
                    if file_record.filepath and os.path.exists(file_record.filepath):
                        os.remove(file_record.filepath)
                except OSError:
                    pass
                db.session.delete(file_record)
            db.session.commit()
            click.echo('Rebuild requested: cleared existing imported files and vector collection.')

        supported_files = []
        for path in sorted(kb_source_dir.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower().lstrip('.') not in app.config['ALLOWED_EXTENSIONS']:
                continue
            supported_files.append(path)

        if not supported_files:
            raise click.ClickException(f'No supported files found in {kb_source_dir}')

        file_service = get_file_service()
        imported = 0
        skipped = 0
        failed = 0

        for path in supported_files:
            try:
                existing = File.query.filter_by(knowledge_base_id=kb.id, filename=path.name).first()
                if existing:
                    skipped += 1
                    click.echo(f"Skip existing: {path.name}")
                    continue

                file_record = file_service.import_local_file(str(path), kb.id, admin.id)
                file_service.process_file(file_record.id)
                imported += 1
                click.echo(f"Imported: {path.name}")
            except Exception as e:
                failed += 1
                click.echo(f"Failed: {path.name} -> {e}")

        click.echo(
            f"Done. knowledge_base_id={kb.id} imported={imported} skipped={skipped} failed={failed}"
        )


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=app.config['DEBUG']
    )
