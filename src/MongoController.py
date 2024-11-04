from pymongo import MongoClient
from pymongo.errors import PyMongoError
import datetime

class MongoController:
    # For local usage only, so we don't need to have complexe db connection
    def __init__(self,local_db_path="mongodb://localhost:27017/"):
        try : 
            self.mongo_client = MongoClient(local_db_path)
            self.mongo_db = self.mongo_client['cvBuilder']
            self.mongo_user_coll = self.mongo_db['user']
            self.mongo_cv_coll = self.mongo_db['cv']

        except PyMongoError as e:
            print("Connection to MongoDB failed. Cause: %s" % (e))
    def save_user_info(self, user_info):
        user_info['creation_date'] = datetime.datetime.now()
        insert_obj = self.mongo_user_coll.insert_one(user_info)

        # if insert_obj.inserted_id :
        #     raise Exception("Controller didn't managed to add user info to database")
        return insert_obj
    def retrieve_user_info(self, query=None):
        """
        retrieve user info based on query, if no query is provided, return the last user_info created
        user is responsible for the query quality
        """
        if query :
            return self.mongo_user_coll.find_one(query, sort=[("creation_date" , -1)])
        else :
            return self.mongo_user_coll.find_one(sort=[("creation_date" , -1)])
        
    def save_user_cv(self, user_id, cv_info):
        cv_info['creation_date'] = datetime.datetime.now()
        cv_info['user_id'] = user_id

        insert = self.mongo_cv_coll.insert_one(cv_info)
        # if insert.inserted_id :
        #     raise Exception("Controller didn't managed to add cv info to database")
        return insert

    def retrieve_cv_info(self, query=None):
        """
        retrieve cv info based on query, if no query is provided, return the last cv_info created
        user is responsible for the query quality
        """
        if query :
            return self.mongo_cv_coll.find_one(query, sort=[("creation_date" , -1)])
        else :
            return self.mongo_cv_coll.find_one(sort=[("creation_date" , -1)])