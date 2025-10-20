from flask import jsonify, request
import os
import time

def handler(request):
    """性能指标端点 - Vercel Serverless Function"""
    # 简单的性能指标
    metrics = {
        'timestamp': int(time.time()),
        'environment': 'production' if os.environ.get('VERCEL') else 'development',
        'region': os.environ.get('VERCEL_REGION', 'local'),
        'uptime': int(time.time()) - int(os.environ.get('VERCEL_DEPLOYMENT_CREATED_AT', time.time())),
        'requests_served': 0  # 可以扩展为实际计数
    }
    
    return jsonify(metrics), 200