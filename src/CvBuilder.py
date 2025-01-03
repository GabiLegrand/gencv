import json
import os
from dotenv import load_dotenv
from src.LLM_prompting import *
from src.html_generation import * 
import pdfkit 
from bson import ObjectId

class CvBuilder:
    def __init__(self, mongo_controller,  llm_client, llm_system, pdf_url, verbose=True, user_id=None):
        if not os.path.exists('./output/'):
            os.makedirs('./output/')
        self.pdf_url = pdf_url
        self.llm_system = llm_system
        self.llm_client = llm_client
        self.mongo_controller = mongo_controller

        if user_id :
            mongo_controller.retrieve_user_info({'_id':user_id})
        else :
            user_data = mongo_controller.retrieve_user_info()


        self.coordinates = user_data['coordinates']
        self.general_info = user_data['general_info'] 
        
        self.skills = skills_context_to_text(user_data['skills'])
        self.work_experience = '\n\n'.join(work_context_to_text(v) for v in user_data['work_experience'].values())
        
        self.work_experience_meta = user_data['work_experience'] 
        self.education_context = user_data['education'] 

        self.coordinates = user_data['coordinates']
        self.user_id = user_data['_id']
        
        self.verbose = verbose
        self.reset_state()
   
    def save(self):
        """Save the entire object to a file using json."""       

        state = {
            'job_infos': self.job_infos,
            'work_context': self.work_context,
            'project_context': self.project_context,
            'relevant_skillset': self.relevant_skillset,
            'profile_description': self.profile_description,
            'profile_title': self.profile_title,
            'job_description' : self.job_description,
            'company_info' : self.company_info,
            'cover_letter' : self.cover_letter
        }

        r = self.mongo_controller.save_user_cv(self.user_id,self.coordinates, state)
        self.state_id = r.inserted_id
        print(f"State saved {r}")

    def update_current(self):
        state = {
            'job_infos': self.job_infos,
            'work_context': self.work_context,
            'project_context': self.project_context,
            'relevant_skillset': self.relevant_skillset,
            'profile_description': self.profile_description,
            'profile_title': self.profile_title,
            'job_description' : self.job_description,
            'company_info' : self.company_info,
            'cover_letter' : self.cover_letter
        }
        self.mongo_controller.update_cv(self.state_id,state)
        


    def load(self, cv_id:str = None):
        """Load the entire object from a mongo"""
        if cv_id:
            print(cv_id)
            state = self.mongo_controller.retrieve_cv_info({"_id": ObjectId(cv_id)})
        else :
            state = self.mongo_controller.retrieve_cv_info({'user_id': self.user_id})

        if state :
            self.job_infos = state['job_infos']
            self.work_context = state['work_context']
            self.project_context = state['project_context']
            self.relevant_skillset = state['relevant_skillset']
            self.profile_description = state['profile_description']
            self.profile_title = state['profile_title']
            self.job_description = state['job_description']
            self.company_info = state.get('company_info', {'name' : 'Unknown', 'description': 'Unknown'})
            self.cover_letter = state.get('cover_letter', '')
            self.state_id = state['_id']
            print(f"State {self.state_id} loaded for user {self.user_id}")
        else :
            raise Exception("Error, couldn't load last user CV")

    def reset_state(self):
        self.job_infos = None
        self.work_context = None 
        self.project_context = None 
        self.relevant_skillset = None 
        self.profile_description = None 
        self.profile_title = None
        self.job_description = None 
        self.company_info = None
        self.cover_letter = None 
        self.state_id = None

    def generate_cv_from_job_description(self,job_description):
        self.job_description = job_description
        self.extract_job_infos(job_description)
        self.select_work_experience()
        self.select_projects()
        self.generate_relevant_skillset()
        self.generate_profile_description()
        self.generate_profile_title()
        self.generate_cover_letter()
        
        # Save CV build
        self.save()
        self.generate_cv_pdf("output/cv.pdf")

    def generate_cover_letter_pdf(self,output_file):
        
        if  self.work_context != None and \
                self.project_context != None and \
                self.relevant_skillset != None and \
                self.profile_description != None and \
                self.profile_title != None :
            html_content = generate_cover_letter_html(self.company_info['name'],
                                       self.company_info['position_title'],
                                       self.coordinates['full_name'],
                                       self.cover_letter)
            
            try:
                
                pdf_content = convet_html_to_pdf(self.pdf_url, html_content,output_file)
                # pdfkit.from_string(html_content, output_file)
                print('Cover letter created!')
                return pdf_content
            except Exception as e:
                print(f"Error generating PDF: {e}")

    
    def generate_cv_pdf(self,output_file):
        if  self.work_context != None and \
                self.project_context != None and \
                self.relevant_skillset != None and \
                self.profile_description != None and \
                self.profile_title != None :
            
            html_content = generate_cv_html(self.coordinates, self.profile_title, 
                                            self.profile_description, self.education_context, 
                                            self.work_context, self.project_context,
                                            self.relevant_skillset)
            
            try:
                pdf_content = convet_html_to_pdf(self.pdf_url, html_content,output_file)
                # pdfkit.from_string(html_content, output_file)
                print('CV created!')
                return pdf_content

            except Exception as e:
                print(f"Error generating PDF: {e}")


    def extract_company_info(self,job_description):
        self.company_info = extract_company_info_from_description(self.llm_client, job_description, 
                                              self.llm_system, self.verbose)

    def extract_job_infos(self,job_description):
        """
        Extract the job informations and keywords from the job description, the informations 
        are the job summary, requirements and responsabilities.

        return 
        ------
            String : a summary of the job, requirements and responsabilities
        """
        self.reset_state()
        self.extract_company_info(job_description)
        self.job_infos = extract_job_info_from_description(self.llm_client, 
                                                           job_description, 
                                                           self.llm_system, 
                                                           self.verbose)
    def generate_cover_letter(self):
        self.cover_letter = generate_cover_letter(self.llm_client, self.company_info, self.job_infos, 
                            self.coordinates, self.general_info, self.work_experience, self.skills, 
                            self.education_context, self.llm_system, verbose=True)

    def select_work_experience(self):
        """
        Select a set of work experience from the user info, add a description with keywords for
        each and format in a context manner
        
        return 
        ------
            Dictionary : A dictionary of the work experience
        """
        if self.job_infos != None :
            work_xp_selected = select_work_experience(self.llm_client, self.job_infos, 
                                                      self.work_experience, self.llm_system, 
                                                      self.verbose)
            work_selected_descriptions = generate_description_for_work_xp_selected(self.llm_client, 
                                                                                   work_xp_selected, 
                                                                                   self.job_infos, 
                                                                                   self.llm_system, 
                                                                                   self.verbose)

            self.work_context = format_CV_work_experience(work_selected_descriptions,
                                                          self.work_experience_meta)
            return self.work_context
        else : 
            raise Exception('Error, cannot extract work experience without job description')
    def select_projects(self):
        """
        Select a set of project to showcase user experience. Add a description with keywords
        
        return 
        ------
            Dictionary : A dictionary of the projects selected
        """
        if self.job_infos != None :
            self.project_context = generate_project_set(self.llm_client, self.job_infos, 
                                                    self.work_experience, 
                                                    self.llm_system, self.verbose)
            return self.project_context
        else : 
            raise Exception('Error, cannot extract work experience without job description')
    def generate_relevant_skillset(self):   
        """
        Identify what skills/keyword should be added to the CV
        
        return 
        ------
            List of string : List of relevant skills to add at the end of the CV, may include keywords
        """     
        if self.job_infos != None :
            all_skillset = generate_skill_set_list(self.llm_client, self.job_infos, self.skills, 
                                                  self.llm_system, self.verbose)
            self.relevant_skillset = [skill for skill in all_skillset if skill.lower() not in self.skills.lower()]
            return self.relevant_skillset
        else : 
            raise Exception('Error, cannot extract work experience without job description')

    def generate_profile_description(self):
        """
        Generate a relevant profile description to match job position
        
        return 
        ------
            String : the generated description
        """
        if self.job_infos != None :
            self.profile_description = generate_profile_description(self.llm_client, self.job_infos, 
                                                               self.work_experience, self.general_info, 
                                                               self.skills, self.llm_system, self.verbose)
            return self.profile_description
        else : 
            raise Exception('Error, cannot extract work experience without job description')

    def generate_profile_title(self):  
        """
        generate a job title relevant to the position applied
        
        return 
        ------
            String : The generated job title
        """      
        if self.job_infos != None :
            self.profile_title = generate_profile_title(self.llm_client, self.job_infos, self.work_experience, 
                                                   self.general_info, self.skills, self.llm_system, self.verbose)
            return self.profile_title
        else : 
            raise Exception('Error, cannot extract work experience without job description')
        