"""File Processing API Routes
"""
from flask import request, Response, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
import threading
from . import file_bp
from ..utils.response import success_response, error_response
from ..services import get_file_service
from ..models import File
from ..extensions import db


@file_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """Upload a file to a knowledge base"""
    user_id = get_jwt_identity()
    
    if 'file' not in request.files:
        return error_response(400, 'No file provided')
    
    file = request.files['file']
    knowledge_base_id = request.form.get('knowledge_base_id')
    
    if not knowledge_base_id:
        return error_response(400, 'knowledge_base_id is required')
    
    if not file.filename:
        return error_response(400, 'No file selected')
    
    try:
        file_service = get_file_service()
        file_record = file_service.save_uploaded_file(
            file=file,
            knowledge_base_id=knowledge_base_id,
            user_id=user_id
        )
        
        # Start async processing with current app (avoid creating new app)
        app = current_app._get_current_object()
        
        def process_async(file_id):
            with app.app_context():
                try:
                    file_service = get_file_service()
                    file_service.process_file(file_id)
                except Exception as e:
                    # Ensure file status is updated to 'failed' even if process_file didn't
                    try:
                        db.session.rollback()
                        f = File.query.get(file_id)
                        if f and f.status != 'failed':
                            f.status = 'failed'
                            f.error_message = str(e)[:500]
                            db.session.commit()
                    except Exception:
                        pass
                    print(f"Async processing failed: {e}")
                finally:
                    db.session.remove()
        
        thread = threading.Thread(
            target=process_async,
            args=(file_record.id,)
        )
        thread.daemon = True
        thread.start()
        
        return success_response(
            data=file_record.to_dict(),
            message='File uploaded, processing started',
            code=201
        )
    except ValueError as e:
        return error_response(400, str(e))
    except Exception as e:
        return error_response(500, str(e))


@file_bp.route('/<file_id>/status', methods=['GET'])
@jwt_required()
def get_file_status(file_id):
    """Get file processing status"""
    user_id = get_jwt_identity()
    
    file_record = File.query.filter_by(id=file_id, user_id=user_id).first()
    if not file_record:
        return error_response(404, 'File not found')
    
    return success_response(data=file_record.to_dict())


@file_bp.route('/<file_id>/status/stream', methods=['GET'])
@jwt_required()
def stream_file_status(file_id):
    """Stream file processing status (SSE)"""
    user_id = get_jwt_identity()
    
    file_record = File.query.filter_by(id=file_id, user_id=user_id).first()
    if not file_record:
        return Response(
            f"data: {json.dumps({'error': 'File not found'})}\n\n",
            mimetype='text/event-stream'
        )
    
    app = current_app._get_current_object()
    
    def generate():
        import time
        
        last_status = None
        
        while True:
            with app.app_context():
                # Expire all cached objects to get fresh data from DB
                db.session.expire_all()
                file_record = File.query.get(file_id)
                if not file_record:
                    yield f"data: {json.dumps({'error': 'File not found'})}\n\n"
                    break
                
                status = file_record.status
                
                if status != last_status:
                    yield f"data: {json.dumps(file_record.to_dict())}\n\n"
                    last_status = status
                
                if status in ['completed', 'failed']:
                    break
            
            time.sleep(1)
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )


@file_bp.route('/<file_id>', methods=['DELETE'])
@jwt_required()
def delete_file(file_id):
    """Delete a file"""
    user_id = get_jwt_identity()
    
    try:
        file_service = get_file_service()
        file_service.delete_file(file_id, user_id)
        return success_response(message='File deleted')
    except ValueError as e:
        return error_response(400, str(e))
    except Exception as e:
        return error_response(500, str(e))


@file_bp.route('/<file_id>/reprocess', methods=['POST'])
@jwt_required()
def reprocess_file(file_id):
    """Reprocess a file"""
    user_id = get_jwt_identity()
    
    file_record = File.query.filter_by(id=file_id, user_id=user_id).first()
    if not file_record:
        return error_response(404, 'File not found')
    
    try:
        # Start async processing with current app
        app = current_app._get_current_object()
        
        def process_async(fid):
            with app.app_context():
                try:
                    file_service = get_file_service()
                    file_service.process_file(fid)
                except Exception as e:
                    try:
                        db.session.rollback()
                        f = File.query.get(fid)
                        if f and f.status != 'failed':
                            f.status = 'failed'
                            f.error_message = str(e)[:500]
                            db.session.commit()
                    except Exception:
                        pass
                    print(f"Reprocess failed: {e}")
                finally:
                    db.session.remove()
        
        thread = threading.Thread(
            target=process_async,
            args=(file_id,)
        )
        thread.daemon = True
        thread.start()
        
        return success_response(message='Reprocessing started')
    except Exception as e:
        return error_response(500, str(e))
