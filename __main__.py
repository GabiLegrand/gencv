#!/env/Scripts/python.exe

from openai import OpenAI
import os
from dotenv import load_dotenv

from src.CvBuilder import CvBuilder
from src.MongoController import MongoController
import argparse
import sys 

if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--r",
        choices=["local", "openai"],
        default="openai",
        help="runetime should be 'local' for local llm or 'openai' for openai API"
    )
    parser.add_argument(
        "--generate",
        choices=["all", "title", "description", "project", "work", "skills", "pdf"],
        default="all",
        help="Generate allow you to generate a cv or regenerate part of the current CV based on the argument :" + \
            "\n\t`all` : generate all the cv" +  
            "\n\t`title` : re-generate the title of the current CV" + 
            "\n\t`description` : re-generate the description of the current CV" + 
            "\n\t`project` : select a new set of projects for the current CV" + 
            "\n\t`work` : select a new set of work experience for the current CV " + 
            "\n\t`skills` : select a new set of relevant skills for the current CV"
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
    

    mongo_controller = MongoController()
    builder = CvBuilder(mongo_controller, client, system)

    with open('job_description.txt','r') as fd:
        job_description = fd.read()

    if args.generate == "all" :
        builder.generate_cv_from_job_description(job_description)
        sys.exit()

    elif args.generate == "title":
        builder.generate_profile_title()
    elif args.generate == "description":
        builder.generate_profile_description()
    elif args.generate == "project":
        builder.select_projects()
    elif args.generate == "work":
        builder.select_work_experience()
    elif args.generate == "skills":
        builder.generate_relevant_skillset()

    builder.save()
    builder.generate_cv_pdf('./output/cv.pdf')
