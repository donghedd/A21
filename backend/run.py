#!/usr/bin/env python
"""
SFQA Application Entry Point
"""
import os
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


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=app.config['DEBUG']
    )
