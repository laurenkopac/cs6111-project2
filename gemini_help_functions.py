"""
This file contains help functions for the gemini relation extraction process
"""

# Used to check for a valid response structure from gemini
import re

def check_response_structure(response_text, desired_type):
    """
    Helper function to determine if Gemini returned a valid response to process.
    Uses regex to check for structure. 

    Input: Response from Gemini
    Output: True or False
    """

    # Mapping of possible relations from user
    relations = {
    1: 'Schools_Attended',
    2: 'Work_For',
    3: 'Live_In',
    4: 'Top_Member_Employees'}
    
    # Pattern Gemini was trained to respond in from our few shot prompt
    pattern = r'\["[^"]*"(?:, ?"[^"]*")*\]'

    if re.findall(pattern, response_text):
        # If Gemini's response contains "UNKOWN", return false
        if "unknown" in response_text.lower():
            return False
        # Check for the desired relationship. If any other relation found, return false
        elif (relations[desired_type]) not in response_text:
            return False
        else:
            return True
    # If not matching pattern at all, return false
    ## Sometimes gemini would return a sentence explaining that no relationships were found despite training
    else:
        return False


def gemini_relation_description(desired_relation):
    """
    Translate the desired relation from user input into more "readable" english for Gemini to understand.

    Input: int (1-4 inclusive) from user input
    Output: a simple string description of desired relation.
    """

    # Mapping of possible relations and simple english descriptions
    relation = {
        1: "schools attended",
        2: "companies worked for",
        3: "places lived in", 
        4: "top member employees"
    }
    
    # Return the text description of the relation
    ## if somehow the user was able to pass a number other than 1-4 inclusive, function will return INVALID
    return relation.get(desired_relation, 'INVALID')

def gemini_relation_implicit_example(desired_relation):
    """
    Generate an implicit example for Gemini as a prompt. Example is dependent on desired relationship by user.

    Input: int (1-4 inclusive) from user input
    Output: A text based implicit example of the desired relationship to help Gemini interpret text
    """

    # Mapping of desired relationship to english sentence describing the relationship
    example = {
        1: "obtaining degrees, academic positions, or other educational affiliations, either at the school or department within the school (i.e. Department of Management Science and Engineering)",
        2: "indications of employment or professional involvement with organizations or other affiliations",
        3: "indicating the subject's place of residence or any other locations",
        4: "indications of leadership or any other significant involvement "
    }

    # Return the text description of the relation
    ## if somehow the user was able to pass a number other than 1-4 inclusive, function will return INVALID
    return example.get(desired_relation, 'INVALID')

def gemini_relation_example(desired_relation):
    """
    Translate the desired relation from user input into an example of list based data structure that can be reliably parsed.

    Input: int (1-4 inclusive) from user input
    Output: Data structures as an example for Gemini to mimic. One general and one specific example.
    """

    # Mapping of desired relationship to english sentence describing the relationship
    example = {
        1: ('["Person", "Schools_Attended", "School Name"]', '["Jeff Bezos", "Schools_Attended", "Princeton University"]'),
        2: ('["Employee Name", "Work_For", "Company"]', '["Alec Radford", "Work_For", "OpenAI"]'),
        3: ('["Person", "Live_In", "City, State, or Country"]','["Mariah Carey", "Live_In", "New York City"]'),
        4: ('["Company", "Top_Member_Employees", "Employee Name"]','["Nvidia", "Top_Member_Employees", "Jensen Huang"]')
    }

    # Return the text description of the relation
    ## if somehow the user was able to pass a number other than 1-4 inclusive, function will return INVALID
    return example.get(desired_relation, 'INVALID')
