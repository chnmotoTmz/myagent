from flask import Blueprint, request, jsonify

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/receive_message', methods=['POST'])
def receive_message():
    try:
        data = request.get_json()
        # Add your message handling logic here
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
