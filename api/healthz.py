from flask import jsonify
import os

def handler(request):
    """健康检查端点 - Vercel Serverless Function"""
    return jsonify({
        'status': 'healthy',
        'environment': 'production' if os.environ.get('VERCEL') else 'development',
        'timestamp': os.environ.get('VERCEL_REGION', 'local')
    }), 200