from jinja2 import Environment, FileSystemLoader


def generate_education_html(template_env,education_context):
    education_template = template_env.get_template('templates/education_template.html')

    education_rendered = ""
    for context in education_context:
        education_rendered +=  education_template.render(context) + '\n'
    return education_rendered


def generate_work_experience_html(template_env,work_experience):
    work_template = template_env.get_template('templates/work_template.html')

    work_rendered = ""
    for context in work_experience:
        work_rendered +=  work_template.render(context) + '\n'
    return work_rendered

def generate_project_html(template_env,project_context):
    work_template = template_env.get_template('templates/project_template.html')

    work_rendered = ""
    for context in project_context:
        work_rendered +=  work_template.render(context) + '\n'
    return work_rendered



def generate_cv_html(static_context,
                    profile_title, profile_description,
                    education_context, work_context, project_context,
                    relevant_skillset):
    template_env = Environment(loader=FileSystemLoader('.'))
    cv_template = template_env.get_template('templates/cv_template.html')

    education_rendered = generate_education_html(template_env,education_context)
    work_rendered = generate_work_experience_html(template_env,work_context)
    project_rendered = generate_project_html(template_env,project_context)
    relevant_skillset_str = str(relevant_skillset).replace("'",'').replace('[','').replace(']','')

    context = {
        "job_title" : profile_title,

        "full_name" : static_context["full_name"],
        "location" : static_context["location"],
        "email" : static_context["email"],
        "phone" : static_context["phone"],
        "portfolio_link" : static_context["portfolio_link"],


        "profile_description" : profile_description,
        "work_experience" : work_rendered,
        "projects" : project_rendered,
        "educations" : education_rendered,
        "skills_list" : relevant_skillset_str,
    }

    # Render the template with the context
    cv_html = cv_template.render(context)
    return cv_html