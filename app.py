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
from io import BytesIO
from flask_cors import CORS,cross_origin

import argparse


parser = argparse.ArgumentParser()
parser.add_argument(
    "--env",
    choices=["local", "docker"],
    default="local",
)

args = parser.parse_args()
env_runtime = args.env


############# FLASK SETUP
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

###### ENV VARIABLES ######
load_dotenv()
if env_runtime == "local":
    MONGO_URI = "mongodb://localhost:27017/"

else :
    # # Initialize MongoController
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
if env_runtime == "local":
    pdf_url = 'http://localhost:80/'
else : 
    pdf_url = os.getenv("PDF_URL",'http://localhost:80')
model_choice = os.getenv("OPENAI_MODEL_CHOICE")
openai_api_key = os.getenv("OPEN_AI_API_KEY","failed?")

########################

client = OpenAI(
    api_key=openai_api_key
)
system = {
    "model_choice" :  model_choice,
    'system_prompt' : "You are an helpful assistant, you will only use provided informations to answer and will not assume informations. You need to output only relevant information, introduction message are not required"
}
mongo_controller = MongoController(MONGO_URI)
builder = CvBuilder(mongo_controller, client, system,pdf_url)


############################################################


@app.route('/')
def serve_index():
    # Serve the main index.html file for the Vue app
    return send_from_directory(app.template_folder, 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    # Serve static files from the Vue build
    return send_from_directory(app.static_folder, path)


@app.route('/user')
def get_user_info():
    user_data = mongo_controller.retrieve_user_info()
    user_data['_id'] = str(user_data['_id'])
    return jsonify(user_data)

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
            cv['cover_letter'] = cv['cover_letter'].replace('\n','<br>')
            return jsonify(cv)
        else:
            return jsonify({'error': 'CV not found'}), 404
    except Exception:
        return jsonify({'error': 'Invalid CV ID'}), 400


@app.route('/user/<user_id>', methods=['PUT'])
@cross_origin(origin="*", supports_credentials=True)
def update_user(user_id):
    user_data = request.json
    try:
        result = mongo_controller.update_user_info(user_id,user_data)
        if result.matched_count:
            return jsonify({'message': 'CV updated successfully'})
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

@app.route('/cv/<cv_id>', methods=['DELETE'])
@cross_origin(origin="*", supports_credentials=True)
def delete_cv(cv_id):
    try:
        result = mongo_controller.delete_cv(cv_id)
        if result != None:
            return jsonify({'message': 'CV deleted successfully'})
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
    # Load the CV using the provided cv_id
    builder.load(cv_id)
    company_name = builder.company_info['name'].strip()
    user_name = builder.coordinates['full_name'].lower().replace(' ','_')
    file_name = f'cv_{user_name}_X_{company_name.strip()}.pdf'

    output_path = f'output/{file_name}'

    # Generate the CV PDF
    try:
        pdf_content = builder.generate_cv_pdf(output_path)
        pdf_stream = BytesIO(pdf_content)
    except Exception as e:
        # Handle any errors that occur
        return jsonify({"error": str(e)}), 500

    # Send the generated PDF file as a response
    return send_file(
        pdf_stream,
        as_attachment=True,
        download_name=file_name,
        mimetype='application/pdf'
    )

  
@app.route('/generate_cover_letter', methods=['GET'])
def generate_cover_letter():
    # Get cv_id from the query parameters
    cv_id = request.args.get('cv_id')

    if not cv_id:
        return jsonify({"error": "cv_id parameter is required"}), 400
    # Load the CV using the provided cv_id
    builder.load(cv_id)
    company_name = builder.company_info['name']
    user_name = builder.coordinates['full_name'].lower().replace(' ','_')
    file_name = f'cover_letter_{user_name}_X_{company_name.strip()}.pdf'
    output_path = f'output/{file_name}'

    # Generate the CV PDF
    try:
        pdf_content = builder.generate_cover_letter_pdf(output_path)
        pdf_stream = BytesIO(pdf_content)
    except Exception as e:
        # Handle any errors that occur
        return jsonify({"error": str(e)}), 500

    # Send the generated PDF file as a response
    return send_file(
        pdf_stream,
        as_attachment=True,
        download_name=file_name,
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    if env_runtime == "local":
        app.run(debug=True)
    else :
        app.run(debug=True,host="0.0.0.0",port=8000)
