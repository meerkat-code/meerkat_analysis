import requests
import os
import csv
import json
import time

def name_id(name=None, var_id=None, variables=None):
    """
    Returns the id of the variable

    Args: 
        var_id: variable_id
        name: Variable name
        variables
    """

    if var_id is not None:
        return var_id
    elif name is not None:
        if variables is None:
            raise KeyError("Need to provide variables")
        return variables.get_id(name)
    else:
        raise KeyError("Need to provide either name or id")

    
def download_file(url, filename, params=None, cookies=None):
    """
    Download an url and saves it as file

    Args: 
        url: url to be downloaded
        filename: filename
        parmas: any get parameters
    Returns: 
       None
    Raises:
       IOError: if not status_code is 200

    """
    req = requests.get(url, params=params, cookies=cookies)
    if req.status_code == 200:
        with open(filename, "wb") as f:
            for line in req:
                f.write(line)
    else:
        raise IOError("Could not download url {url}, "
                      "got stats_code {code}".format(url=url,
                                                     code=req.status_code))

    
def load_from_json_file(filename):
    """ Loads variables from json file
    
    Args: 
        filename: name of file
    """
    with open(filename, "r") as f:
        dictionary = json.loads(f.read())
    return dictionary
    
class Variables:
    """
    A class to deal with variable definitions

    """

    def __init__(self, variables):
        """
        Initialises the class from a python dictionary with variabled_id: variable

        Args: 
            variables: variables
        """
        self.variables = variables
        groups = {}

        for variable in self.variables.values():
            if variable["category"]:
                for group in variable["category"]:
                    groups.setdefault(group, [])
                    groups[group].append(variable["id"])
        self.groups = groups

    @classmethod
    def from_url(cls, live_downloader, filename):
        """
        Will download variables from the live_downloade and initialise the class with those. Filename stores the variabels

        Args: 
            live_downloader: live downloader class
            filename: filename to store the variables
        """
        live_downloader.download_variables(filename)
        return cls(load_from_json_file(filename))

    @classmethod
    def from_json_file(cls, filename):
        """ Initilises the class from a json file
        Args:
           filename: name of file
        """
        return cls(load_from_json_file(filename))

    @classmethod
    def from_csv_file(cls, filename):
        """ Initialsing the class from a csv file.

        Args:
            filename: name of file
        """
        variables = {}
        with open(filename, "r", encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["category"]:
                    if ";" in row["category"]:
                        row["category"] = row["category"].split(";")
                    else:
                        row["category"] = row["category"].split(",")
                variables[row["id"]] = dict(row)
        return cls(variables)

    def name(self, variable_id):
        """ Return the name of the variable
        
        Args: 
            variable_id
        """
        if variable_id in self.variables:
            return self.variables[variable_id]["name"]
        else:
            return None

    def get_id(self, name):
        """ Get variable id by name
        
        Args:
            name: name of variable
        """
        ret = []
        for v in self.variables.values():
            if name == v["name"]:
                ret.append(v["id"])
        if len(ret) == 1:
            return ret[0]
        else:
            return None

class Locations:
    """
    A class to keep location data

    """
    def __init__(self, locations):
        self.locations = locations
    @classmethod
    def from_json_file(cls, filename):
        """ Initilises the class from a json file
        Args:
           filename: name of file
        """
        return cls(load_from_json_file(filename))
    
    @classmethod
    def from_url(cls, live_downloader, filename):
        """
        Will download variables from the live_downloade and initialise the class with those. Filename stores the variabels

        Args: 
            live_downloader: live downloader class
            filename: filename to store the variables
        """
        live_downloader.download_locations(filename)
        return cls(load_from_json_file(filename))

    def population(self, loc_id):
        """
        Returns the population
        """
        ret = 0
        if loc_id in self.locations:
            ret = self.locations[loc_id]["population"]
        elif str(loc_id) in self.locations:
            ret = self.locations[str(loc_id)]["population"]
        return ret

    def loc_id_from_name(self, name, district):
        """ 
        Returns a location id from a name and district
        """
        for l in self.locations.values():
            if l["name"] == name and l["district"] == district:
                return l["id"]
        return None
    def name(self, loc_id):
        """
        Returns the name of the location
        """
        ret = None
        if loc_id in self.locations:
            ret = self.locations[loc_id]["name"]
        elif str(loc_id) in self.locations:
            ret = self.locations[str(loc_id)]["name"]
        return ret

    def populations(self, level):
        """
        Returns the populations for the given level

        """


        locs = self.get_level(level)
        ret = {}
        for l in locs:
            ret[l] = self.population(l)
        return ret
        
        
    def get_level(self, level, only_case_report=True):
        """
        Returns all the locations with the correct level
        """
        ret = []
        if level != "clinic" or not only_case_report:
            for l in self.locations:
                if self.locations[l]["level"] == level:
                    ret.append(l)
        else:
            for l in self.locations:
                if self.locations[l]["level"] == "clinic" and self.locations[l]["case_report"] == 1:
                    ret.append(l)
            
        return ret
    def get_clinics(self, loc_id):
        """
        Returns the clincs that are sublocations to the given location
        """
        clinics = []
        for l in self.locations.values():
            if l["level"] == "clinic" and self.is_child(loc_id, l["id"]):
                clinics.append(str(l["id"]))
        return clinics
                    
    def is_child(self, parent, child):
        """
        Determines if child is child of parent
        
        Args:
          parent: parent_id
          child: child_id

       Returns:
          is_child(Boolean): True if child is child of parent
        """
        parent = str(parent)
        child = str(child)
        if child == parent or parent == "1":
            return True
        loc_id = child
        while loc_id != "1":
            loc_id = str(self.locations[loc_id]["parent_location"])
            if loc_id == parent:
                return True
        return False

        
class LiveDownloader:
    """
    A class to download data from the live site

    """

    def __init__(self, url, username=None, password=None):
        """
        Initialse the class with the url for the site and the api_key

        Args: 
            url: url to site
            api_key: api_key to access the api
        """
        self.base_url = url
        if username is None or password is None:
            raise KeyError("No username/password proived")
        else:
            if "localhost" in url:
                auth_url = "http://localhost/auth/api/login"
            else:
                auth_url = "https://auth.emro.info/api/login"
        auth_response = requests.post(auth_url, json={"password": password,
                                                      "username": username
                                                      })
        print(auth_response)
        if auth_response.status_code == 200:
            self.cookies = auth_response.cookies
        else:
            raise IOError("Could not authorise with that username/password")

    def download_structured_data(self, filename):
        """ Download stucutred data from url and saves it as a csv file
        
        Args:
            filename: name of file
        """
        url = self.base_url + "/api/export/data/1"
        req = requests.get(url, cookies=self.cookies)
        if req.status_code == 200:
            uid = req.text[1:-2]
            status = 0
            while status == 0:
                time.sleep(10)
                req = requests.get(self.base_url + "/api/export/get_status/" + uid,
                                   cookies=self.cookies)
                res = json.loads(req.text)

                status = res["status"]
            if res["success"]:
                download_file(self.base_url + "/api/export/getcsv/" + uid,
                              filename, cookies=self.cookies)
            else:
                print("Not successfull")
        
    def download_alerts(self, filename):
        """ Download alerts from url and saves it as a json file
        
        Args:
            filename: name of file
        """
        url = self.base_url + "/api/export/alerts"
        download_file(url, filename, cookies=self.cookies)
        
    def download_variables(self, filename):
        """ Download variables from url and saves it as a json file
        
        Args:
            filename: name of file
        """

        url = self.base_url + "/api/variables/all"
        download_file(url, filename, cookies=self.cookies)
         
    def download_locations(self, filename):
        """ Download location data from url and saves it as a json file
        
        Args:
            filename: name of file
        """
        
        url = self.base_url + "/api/locations"
        download_file(url, filename, cookies=self.cookies)
