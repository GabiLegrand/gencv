#!./env/Scripts/python.exe

from openai import OpenAI
import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file, send_from_directory
from src.CvBuilder import CvBuilder
from src.MongoController import MongoController
import argparse
import sys 
from bson import ObjectId
import json
from flask_cors import CORS,cross_origin


#############
app = Flask(__name__,static_folder='static/dist', template_folder='static/dist')
CORS(app)


# Custom JSON Encoder to handle ObjectId and datetime objects
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

app.json_encoder = JSONEncoder

################



# Initialize MongoController
mongo_controller = MongoController()

model_choice = os.getenv("OPENAI_MODEL_CHOICE")
openai_api_key = os.getenv("OPEN_AI_API_KEY")

client = OpenAI(
    api_key=openai_api_key
)
system = {
    "model_choice" :  model_choice,
    'system_prompt' : "You are an helpful assistant, you will only use provided informations to answer and will not assume informations. You need to output only relevant information, introduction message are not required"
}
builder = CvBuilder(mongo_controller, client, system)


############################################################


@app.route('/')
def serve_index():
    # Serve the main index.html file for the Vue app
    return send_from_directory(app.template_folder, 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    # Serve static files from the Vue build
    return send_from_directory(app.static_folder, path)



# Route to fetch all CV meta data
@app.route('/cv', methods=['GET'])
@cross_origin(origin="*", supports_credentials=True)
def get_all_cvs():
    cvs = []
    cv_cursor = mongo_controller.get_all_cvs_meta()
    for cv in cv_cursor:
        cv['_id'] = str(cv['_id'])  # Convert ObjectId to string
        cv['creation_date'] = cv['creation_date'].isoformat()  # Convert datetime to string
        cvs.append(cv)
    return jsonify(cvs)

# Route to fetch one CV based on _id
@app.route('/cv/<cv_id>', methods=['GET'])
@cross_origin(origin="*", supports_credentials=True)
def get_cv(cv_id):
    try:
        cv = mongo_controller.retrieve_cv_info({'_id': {'$eq' : ObjectId(cv_id)}})
        if cv:
            cv['_id'] = str(cv['_id'])  # Convert ObjectId to string
            cv['user_id'] = str(cv['user_id'])  # Convert ObjectId to string
            return jsonify(cv)
        else:
            return jsonify({'error': 'CV not found'}), 404
    except Exception:
        return jsonify({'error': 'Invalid CV ID'}), 400

# Route to update a CV based on _id
@app.route('/cv/<cv_id>', methods=['PUT'])
@cross_origin(origin="*", supports_credentials=True)
def update_cv(cv_id):
    cv_data = request.json
    try:
        result = mongo_controller.update_cv(cv_id, cv_data)
        if result.matched_count:
            return jsonify({'message': 'CV updated successfully'})
        else:
            return jsonify({'error': 'CV not found'}), 404
    except Exception:
        return jsonify({'error': 'Invalid CV ID'}), 400


@app.route('/generate_cv', methods=['POST'])
@cross_origin(origin="*", supports_credentials=True)
def generate_cv_route():
    data = request.get_json()
    job_description = data.get('job_description')
    if not job_description:
        return jsonify({'error': 'job_description is required'}), 400
    try :

        # with open('./job_description.txt','w') as fd:
        #     fd.write(job_description)
        builder.generate_cv_from_job_description(job_description)

        return jsonify({'message': 'CV generated successfully'}), 200
    except Exception as e:
        # Log the exception for debugging
        print(f"Exception during CV generation: {e}")
        return jsonify({'error': 'An error occurred during CV generation', 'details': str(e)}), 500
    
@app.route('/generate_cv', methods=['GET'])
def generate_cv():
    # Get cv_id from the query parameters
    cv_id = request.args.get('cv_id')

    if not cv_id:
        return jsonify({"error": "cv_id parameter is required"}), 400
    output_path = './output/cv.pdf'
    # Load the CV using the provided cv_id
    builder.load(cv_id)
    # Generate the CV PDF
    builder.generate_cv_pdf(output_path)
    # try:
    # except Exception as e:
    #     # Handle any errors that occur
    #     return jsonify({"error": str(e)}), 500

    # Send the generated PDF file as a response
    return send_file(output_path, as_attachment=True, download_name="cv.pdf", mimetype='application/pdf')
if __name__ == '__main__':
    app.run(debug=True)
