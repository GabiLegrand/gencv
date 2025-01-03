from openai import OpenAI
import time
import re
import json
import uuid
import os
from jinja2 import Template

def save_prompt(folder_name: str, content: str):
    # Create the folder if it doesn't exist
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    
    # Generate a unique UUID for the filename
    file_name = f"{uuid.uuid4()}.txt"
    file_path = os.path.join(folder_name, file_name)
    
    # Write the content to the file
    with open(file_path, 'w') as file:
        file.write(content)

def prompt_llm(client, prompt, system, verbose=True):
    # if verbose:
    #     save_prompt('debug',prompt)
    
    response = client.chat.completions.create(
        model=system['model_choice'],
        messages=[
            {"role": "system", "content": system['system_prompt']},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        stream=True
    )
    answer = ""
    for chunk in response:
        text = chunk.choices[0].delta.content
        if text != None :
            answer += text
            if verbose:
                print(text,end='')
    if verbose:
        print()
    return answer 




def format_CV_work_experience(descriptions,work_experience_meta):
    descriptions_splited = re.findall(".*\\n\[DESC\].*\[/DESC\]",descriptions)
    work_info_wt_description = []
    for d in descriptions_splited:

        match_company_name = re.search(r"(.*?) -", d)
        company_name = match_company_name.group(1) if match_company_name else None
        match_description = re.search(r"\[DESC\](.*?)\[/DESC\]", d)
        description = match_description.group(1) if match_description else None

        if company_name.lower() in work_experience_meta.keys():
            info = work_experience_meta[company_name.lower()].copy()
            info["company"] = company_name
            info["description"] = description
            work_info_wt_description.append(info)
    return work_info_wt_description


def skills_context_to_text(skills_context):
    return '\n'.join(f"- **{k}** : " +  ', '.join(skills_context[k]) for k in skills_context.keys())
    
def work_context_to_text(position_context):
    template_work_experience = """# {{company_name}} - {{position_title}}
**Date : {{start_date}} - {{end_date}}
**Employment Type**: {{employment_type}}
**Responsibilities**:
{{responsibilities}}**Skills and Tools Used**: {{skill_list}}"""


    responsibilities = ''.join(f' - {r}\n' for r in position_context['responsibilities'])
    skills = ', '.join(position_context['skills'])

    context = {
        "company_name" : position_context['company_name'],
        "position_title" : position_context["title"],
        "start_date" : position_context['start_date'],
        "end_date" : position_context['end_date'],
        "employment_type" : position_context['employment_type'],
        "responsibilities" :  responsibilities,
        "skill_list" : skills
    }

    template = Template(template_work_experience)
    output = template.render(context)
    return output


#################

def extract_company_info_from_description(client, job_description, system, verbose=True):
    prompt= f"""Given the job description below, identify the company name, the position title, and write a brief, compelling description of the company. Use the following format to structure the output:

[CNAME] company name [/CNAME]
[CDESC] company description [/CDESC]
[PNAME] position title [/PNAME]

Job Description:
[Paste the job description here]

The company name should feel appropriate to the industry and the nature of the job, and the description should convey the company's mission, values, and area of expertise in a way that aligns with the job role.
{job_description}
    """

    company_info_raw = prompt_llm(client, prompt,system,verbose)

    pattern = r"\[CDESC\](.*?)\[/CDESC\]"
    match = re.search(pattern, company_info_raw, re.DOTALL)
    company_desc = match.group(1) if match else None

    pattern = r"\[CNAME\](.*?)\[/CNAME\]"
    match = re.search(pattern, company_info_raw, re.DOTALL)
    company_name = match.group(1) if match else None

    
    pattern = r"\[PNAME\](.*?)\[/PNAME\]"
    match = re.search(pattern, company_info_raw, re.DOTALL)
    position_title = match.group(1) if match else None

    company_info = {"name" : company_name, "description" : company_desc, "position_title" : position_title}
    return company_info

def extract_job_info_from_description(client, job_description, system, verbose=True):
   prompt= f"""Extract the following information from the job description provided, follow this template:

Expected format:

```[DESC]1. **General Description**: A brief summary of the overall purpose of the job.
   - **Keywords**: List of keywords  that capture the essence of the job role.

2. **Job Responsibilities**: A list of key responsibilities or duties expected in the role.
   - **Keywords**: List of keywords  that are essential to the job responsibilities.

3. **Requirements**: A list of required skills, qualifications, or experience needed for the role.
   - **Keywords**: List of keywords  that are crucial to the job requirements.[/DESC]```


Here is the job description:

{job_description}
"""

   job_info = prompt_llm(client, prompt,system,verbose)
   pattern = r"\[DESC\](.*?)\[/DESC\]"
   match = re.search(pattern, job_info, re.DOTALL)
   description = match.group(1) if match else None

   return description



def generate_cover_letter(client, company_info, job_info, 
                          user_coordinates, user_general_info, user_work_experience, user_skills, 
                          user_education, system, verbose=True):
    job_info_full = f"""```
    **Company name** : {company_info['name']}
    **Company description** : {company_info['description']}

    {job_info}```
    """

    prompt = f"""Write a personalized cover letter based on the following information, designed to align closely with the job and company requirements. 
    Make the letter as keyword-rich as possible, reflecting the skills, values, and experience that match the job role of {company_info['position_title']}. 

    Enclose the body of the coverletter with this format:
    ```
    [CLETTER]
    Hello ..

    body of the cover letter 
    Best regards,
    candidate name

    Candidate coordinates
    [/CLETTER]
    ```"

    ##Job and Company Information:
    {job_info_full}
    ##Candidate Experience:
    {user_general_info}

    {user_work_experience}

    {user_education}

    {user_skills}

    ## Candidate coordinates
    {user_coordinates}
    The cover letter should be engaging and polished, showing how the candidate's background uniquely qualifies them for the role and how their experience aligns with the company’s mission, values, and goals
    """

    cover_letter_raw = prompt_llm(client, prompt,system,verbose)
    pattern = r"\[CLETTER\](.*?)\[/CLETTER\]"
    match = re.search(pattern, cover_letter_raw, re.DOTALL)
    cover_letter = match.group(1) if match else None

    return cover_letter



def select_work_experience(client, job_info, user_work_experience, system, verbose=True):
    prompt = f"""Based on the following job description details, select the most relevant experience from my work history and provide a curated list of experiences that best match the job requirements.  

### Job Description Summary
{job_info}

### My Work History
{user_work_experience}

Select experiences that match:
1. **Responsibilities**: Identify roles with similar responsibilities.
2. **Skills and Tools**: Match required skills and technologies to those used in my work history.
3. **Relevant Projects**: Highlight projects or achievements that align with the job's focus.

Provide a list of the top 3 most relevant experiences in the order of highest relevance to lowest, and explain why each experience aligns with the job description.

Expected output format :

```[JOBS]1. **COMPANY_1_NAME - POSITION_1_NAME**: 
JUSTIFICATIONS WITH KEYWORDS FOR POSITION 1

2. **COMPANY_2_NAME - POSITION_2_NAME**: 
JUSTIFICATIONS WITH KEYWORDS FOR POSITION 2

3. **COMPANY_3_NAME - POSITION_3_NAME**: 
JUSTIFICATIONS WITH KEYWORDS FOR POSITION 3[/JOBS]```


Remember to enclose your answer with the tags [JOBS] [/JOBS]"""
    exp_selected = prompt_llm(client, prompt, system, verbose)

    pattern = r"\[JOBS\](.*?)\[/JOBS\]"
    match = re.search(pattern, exp_selected, re.DOTALL)
    exp_selected_text = match.group(1) if match else None

    return exp_selected_text


def generate_description_for_work_xp_selected(client, work_xp_selected, job_info, system, verbose=True):
    prompt = f"""Using the job descriptions and selected work experiences provided, create concise, keyword-rich descriptions for each work experience. Each description should:

- Be no longer than 2-3 sentences.
- Focus on showcasing relevant skills and responsibilities.
- Use as many keywords as possible from the job descriptions and work experience details.
- Be formatted for a CV and maintain a professional tone.    
Here is the information to use:

**Job Descriptions (Keywords included for reference):**
{job_info}

**Work Experiences:**
{work_xp_selected}

Expected format:

Company - Position
[DESC]description[/DESC]

Remember to add the tags [DESC][/DESC].


Enclose the relevant answer with [DATA][/DATA]
Now, please generate descriptions for each work experience.
**Do not include any introductory or concluding messages—only provide the selected information.**
"""

    descriptions = prompt_llm(client, prompt, system, verbose)

    pattern = r"\[DATA\](.*?)\[/DATA\]"
    match = re.search(pattern, descriptions, re.DOTALL)
    descriptions_text = match.group(1) if match else None
    return descriptions_text


def generate_profile_description(client, job_info, work_experience, general_info, user_skills, system, verbose=True):
    prompt = f"""Using the provided job description summary and the candidate's informations, provide a short description of the candidate that match as much as possible the description.

The description should:
- Be highly relevant to the job description.
- Incorporate skills and keywords from the job description.
- Only include items that the candidate possesses or that align with the job requirements.
- Be short, only 3 or 4 sentences.
- Be at the first personne, write the description as if you were the candidate

**Job Description Summary:**
{job_info}

**Candidate’s Skills and Tech Stack:**
{user_skills}

**Candidate's previous work experience:**
{work_experience}

**Candidate's general informations:**
{general_info}


Expected format:
`[DESC]Candidate description[/DESC]`

Generate the best description for the candidate.
Remember to enclose the description with [DESC][/DESC]
**Do not include any introductory, additionnal, notes or concluding messages. only provide the selected information.**
"""

    description_raw = prompt_llm(client, prompt,system,verbose)
    
    pattern = r"\[DESC\](.*?)\[/DESC\]"
    match = re.search(pattern, description_raw, re.DOTALL)
    description = match.group(1) if match else None

    return description


def generate_profile_title(client, job_info, work_experience, general_info, user_skills, system, verbose=True):
    prompt = f"""Using the provided job description summary and the candidate's informations, provide a profession title for the candidate.

The description should:
- Be highly relevant to the job description.
- Be short
- Only include items that the candidate possesses or that align with the job requirements.

**Job Description Summary:**
{job_info}

**Candidate’s Skills and Tech Stack:**
{user_skills}

**Candidate's previous work experience:**
{work_experience}

**Candidate's general informations:**
{general_info}


Expected format:
`[DESC]Candidate job title[/DESC]`

Generate the best job title for the candidate.
Remember to enclose the job title with [DESC][/DESC]
**Do not include any introductory, additionnal, notes or concluding messages. only provide the selected information.**
"""

    description_raw = prompt_llm(client, prompt,system,verbose)
    
    pattern = r"\[DESC\](.*?)\[/DESC\]"
    match = re.search(pattern, description_raw, re.DOTALL)
    description = match.group(1) if match else None

    return description


def generate_skill_set_list(client, job_info, user_skills, system, verbose=True):
    prompt = f"""Using the provided job description summary and the candidate’s skills list, generate a consolidated list of skills that best align with the job requirements.

Each item in the list should:
- Be highly relevant to the job description.
- Incorporate skills and keywords from the job description.
- Only include items that the candidate possesses or that align with the job requirements.

**Job Description Summary:**
{job_info}

**Candidate’s Skills and Tech Stack:**
{user_skills}

Format the output as a single list of skills and tech stack items. 

Expected format:
`[LIST]skill1;skill2;skill3;...[/LIST]`

Generate the best-matching skills and tech stack as one list based on the information provided.
Remember to enclose the list with [LIST][/LIST]
**Do not include any introductory, additionnal, notes or concluding messages. only provide the selected information.**
"""

    skill_list_raw = prompt_llm(client, prompt,system,verbose)
    
    pattern = r"\[LIST\](.*?)\[/LIST\]"
    match = re.search(pattern, skill_list_raw, re.DOTALL)
    skill_list = match.group(1) if match else None

    skill_list = skill_list.split(';')
    return skill_list




def generate_project_set(client, job_info, work_experience, system, verbose=True):
    prompt = f"""Based on the provided job description and the candidate's work experience, select 4 relevant projects from the work experience that most closely align with the job responsibilities and requirements. Ensure each project highlights the candidate's skills, technologies used, and accomplishments directly relevant to the position.

Each selected project should:

- Emphasize key skills and tools from the job description, such as relevant programming languages, frameworks, tools, and domain knowledge.
- Include a one-sentence description for each project, using as many relevant keywords from the job description as possible.


**Job Description Summary:**
{job_info}

**Candidate’s work history:**
{work_experience}

Expected format
[EXP]PR_NAME: name for the project
PR_DESCRIPTION: Description for the project[/EXP]

Generate the best-matching list of projects based on the information provided.
Remember to enclose each project with [EXP][/EXP]
PR_NAME and PR_DESCRIPTION are keyword, include them in the formating

**Do not include any introductory, additionnal, notes or concluding messages. only provide the selected information.**
"""

    projects_selected_raw = prompt_llm(client, prompt,system,verbose)
    
    # Regex pattern to match the structure of each experience block
    pattern = r"\[EXP\]PR_NAME[ ]?:\s*(.+?)\nPR_DESCRIPTION[ ]?:\s*(.+?)\[/EXP\]"
    
    # Find all matches in the input string
    matches = re.findall(pattern, projects_selected_raw, re.DOTALL)
    print(matches)
    # Convert matches to a structured format (list of dictionaries)
    experiences = []
    for match in matches:
        experience = {
            "name": match[0].strip(),
            "description": match[1].strip()
        }
        experiences.append(experience)
    return experiences
