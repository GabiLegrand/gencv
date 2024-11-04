
from openai import OpenAI
import time
import re
import json
import os
from dotenv import load_dotenv
from src.LLM_prompting import *
from src.html_generation import * 
import pdfkit 

import argparse


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--r",
        choices=["local", "openai"],
        default="openai",
        help="runetime should be 'local' for local llm or 'openai' for openai API"
    )
    args = parser.parse_args()

 
    if args.r == "local":
        model_choice = os.getenv("LOCAL_MODEL_CHOICE")
        endpoint = os.getenv("LOCAL_ENDPOINT")

        client = OpenAI(
            api_key="none",
            base_url=endpoint,
        )
    elif args.r == "openai":
        model_choice = os.getenv("OPENAI_MODEL_CHOICE")
        openai_api_key = os.getenv("OPEN_AI_API_KEY")

        client = OpenAI(
            api_key=openai_api_key
        )


    system = {
        "model_choice" :  model_choice,
        'system_prompt' : "You are an helpful assistant, you will only use provided informations to answer and will not assume informations. You need to output only relevant information, introduction message are not required"
    }
    

    with open('./personal_info.json','r') as fd:
        user_data = json.load(fd)

    static_context = user_data['static_context']
    general_info = user_data['general_info'] 
    skills = user_data['skills']
    work_experience = user_data['work_experience']
    work_experience_meta = user_data['work_experience_meta'] 
    education = user_data['education'] 


    with open('job_description.txt','r') as fd:
        job_description = fd.read()

    verbose = True
    job_info = extract_job_info_from_description(client, job_description, system, verbose)
    work_xp_selected = select_work_experience(client, job_info, work_experience, system, verbose)
    work_selected_descriptions = generate_description_for_work_xp_selected(client, work_xp_selected, job_info, system, verbose)
    profile_description = generate_profile_description(client, job_info, work_experience, general_info, skills, system, verbose)
    profile_title = generate_profile_title(client, job_info, work_experience, general_info, skills, system, verbose)
    selected_project = generate_project_set(client, job_info, work_experience, system, verbose)
    CV_skillset = generate_skill_set_list(client, job_info, skills, system, verbose)


    relevant_skillset = [skill for skill in CV_skillset if skill.lower() not in skills.lower()]
    formated_CV_work_xp = format_CV_work_experience(work_selected_descriptions,work_experience_meta)

    html_content = generate_cv_html(static_context,
                    profile_title, profile_description,
                    education, formated_CV_work_xp, selected_project,
                    relevant_skillset)
    

    try:
        pdfkit.from_string(html_content, "./cv_custom.pdf")
        print('CV created!')
    except Exception as e:
        print(f"Error generating PDF: {e}")
