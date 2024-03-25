
"""
This is the main .py file for Proj2. It takes the user input and executes the rest of the program
"""
# Environment Set Up
import requests
import sys
import string
import re

# Import all functions from other files for Annotation and relation extraction 
from relation_extraction import *
from web_scraping import *

# Global variables from command line
seed_query = ""
num_tuples = 0
confidence_threshold = 0
extraction_method = ""
google_api_key = ""
gemini_api_key = ""
cx = ""
extraction_type = 0

# Used urls
seen_urls = set()

# Used queries
used_queries = set()

# Relations_type mapping from cmd input
relations = {
    1: 'Schools_Attended',
    2: 'Work_For',
    3: 'Live_In',
    4: 'Top_Member_Employees'}


def remove_tuple_duplicates(X):
    """
    Function to remove duplicates from returned relations

    Input: Tuples collected from relationship extraction
    Output: Two data structures (list and set) containing unique tuples
    """

    # Convert set X to list
    dup_X = list(X)

    # Sort the list of tuples by extraction confidence in decreasing order
    dup_X.sort(key=lambda x: x[-1], reverse=True)

    # Initialize a dictionary to store unique tuples with the highest confidence score
    non_dup_tuples = {}

    # Iterate over each tuple in the sorted list
    for tuple_item in dup_X:
         # Check if at least 3 elements are present, can contain subj, obj,confidence (-spanbert)
        if len(tuple_item) >= 3: 
             subj, obj, _ = tuple_item
        # Else, can only contain subj, obj (-gemini)
        else:
            subj, obj = tuple_item

        # Create a key tuple with the subject and object
        key = (subj, obj)
        # Check if the key exists in the tuple dict
        if key not in non_dup_tuples:
            non_dup_tuples[key] = tuple_item


    # Convert dictionary back to set to be the current X set and return that and list to be used to print final result
    return list(non_dup_tuples.values()), set(non_dup_tuples.values())


def print_results(result_X):
    """
    Print the final results to the terminal for the user. 
    If spanbert was selected, only the top X results will print. If gemini was selected, all results will be printed.

    Input: Tuples extracted (top results for spanBERT, all results for Gemini)
    Output: A print out to the terminal detailing the results of the extraction
    """
    # Print header to the terminal with desired relation type and total number results printed
    print(f"================== ALL RELATIONS for {relations.get(extraction_type, 'INVALID')} ( {len(result_X)} ) =================")
    
    if extraction_method == 'spanbert':
        # iterate over each top tuple in the result X (top tuples only) and print the result
        for tuple_item in result_X:
            subject, obj, confidence = tuple_item
            print("Confidence: \t",confidence, "| Subject: {}\t| Object: {}".format(subject, obj))
    elif extraction_method == 'gemini':
        # iterate over each tuple in the result X and print the result
        for tuple_item in result_X:
            subject, obj = tuple_item
            print("Subject: {}\t| Object: {}".format(subject, obj))

def get_next_query(sorted_X):
   """
   Generate a new query if the desired number of tuples has not been reached after processing all URLs in iteration.

   Input: Sorted Tuples (by confidence if SpanBERT, arbitrary if Gemini)
   Output: A new query from the top tuple collected so far. If no top tuple was found, return None to exit the program
   """
   # get the current used queries
   global used_queries

   # initialize variables for top selected tuple and max confidence
   top_selected_tuple = None
   max_confidence = -1

   # iterate over each tuple in the sorted X
   for tuple_item in sorted_X:
       # get the subject and object from the tuple
       subj, obj = tuple_item[:2]
       # check if the tuple has already been used
       if (subj, obj) not in used_queries:
           # if not, update the top tuple based on the extraction method  
           if extraction_method == 'spanbert':
            # get the confidence from the tuple
            confidence = tuple_item[-1] 
            # check if the confidence is greater than the max confidence
            if confidence > max_confidence:
                # update the max confidence and the top selected tuple
                max_confidence = confidence
                top_selected_tuple = (subj, obj)
           # if not, return the top selected tuple (-gemini)
           else:
                top_selected_tuple = (subj, obj)
                break  # Early exit for Gemini
    
   # if top_selected_tuple is not None, create a new query with the selected tuple
   if top_selected_tuple is not None:
        # create a new query with the selected tuple
        new_query =  " ".join(top_selected_tuple)

        # add selected tuple to used_queries
        used_queries.add(top_selected_tuple)

        # return new query
        return new_query
               
   # if no top tuple is found, return None
   return None

def search():
    """
    API call to JSON API for Google Search results for user inputed query

    INPUT: user inputed API_Key, CS, seed_query(query) via globals
    OUTPUT: Query url results for tuple extraction
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
            "q": seed_query,
            "key": google_api_key,
            "cx": cx,
            "num": 10
    }

    # Perform a Google search using the requests package
    response = requests.get(url, params=params)
    json = response.json()

    urls = [] # List of URLs found in the search results
    if 'items' in json:
       for i, result in enumerate(json['items'], 1):
            # Return only HTML results for user
            if ((result.get('fileFormat') is None) | ('fileFormat' not in json)):
                urls.append(result['link'])
    
    return urls


def run_ise_algorithm():
    """
    Main loop of program. This will run until a desired number of tuples is reached, or (if there is no new query to be generated from the results) the programed is halted.

    Input: N/A
    Output: Initates URL scraping for results generated by user query. From there text is processed for relationship tuples. 
    """
    global seed_query, seen_urls

    X = set()
    iteration = 0

    # Display search parameters lines to user
    query_print_cmd(iteration,extraction_method)

    # loop until we have enough extracted tuples in X
    while len(X) < num_tuples:
        # print current iteration and query to user
        print(f"=========== Iteration: {iteration} - Query: {seed_query} ===========\n")

        # perform google api search for 10 urls based on seed query
        url_results = search()

        # remove urls that have already been seen
        url_results = [url for url in url_results if url not in seen_urls]

        if not url_results:
            print("All the urls have already been seen.. Stopping Program.")
            sys.exit(0)

        # loop through the results and perform 
        for i, url in enumerate(url_results):
            # add url to seen_urls
            seen_urls.add(url)
            
            # print current url to user
            print(f"URL ( {i + 1} / {len(url_results)}): ", url)

            # fetch the website from the url
            html = fetch_website(url)

            #check if html is None (website not found i.e timeout)
            if html is None:
                continue

            # extract plain text from html
            plain_text = extract_plain_text(html)

            print(f"        Webpage length (num characters): {len(plain_text)}")

            # perform Annotation and Information Extraction using spaCy(relation_extraction.py)
            print(f"        Annotating the webpage using spacy...")
        
            # extract relations extractions by using gemini or spanbert(relation_extraction.py)
            if extraction_method == "spanbert" :
                relations = spanbert_relation_extraction(plain_text,extraction_type,confidence_threshold)

                # add individual tuples to the set X
                for key, value in relations.items():
                    subject, obj = key
                    confidence = value
                    X.add((subject, obj, confidence))
            
            elif extraction_method == "gemini":
                relations = gemini_relation_extraction(plain_text, gemini_api_key, extraction_type)

                # add individual tuples to the set X
                for relation in relations:
                    subject = relation["subj"]
                    obj = relation["obj"]
                    X.add((subject, obj))

        # remove duplicates from X (get both the list and set of X , easy to print final result)
        X_list, X = remove_tuple_duplicates(X)

        # initialize top_X_result used to print final result of current interaction to user
        top_X_result = None

        try:
            # sort in decreasing order of confidence number
            sorted_X = sorted(X_list,key=lambda x: x[3], reverse=True)
    
        except:
            # if no confidence numbers (using -gemini), just return X_list
            sorted_X = X_list

          # If X contains at least k tuples, return the top-k such tuples, print result and stop program
        if len(X) >= num_tuples:
            # set top_x_result depending on method, for spanbert only return the top K , while gemini return all
            if extraction_method == 'spanbert':
                top_X_result = sorted_X[:num_tuples]
            elif extraction_method == "gemini":
                top_X_result = sorted_X

            # print top k relations results to user
            print_results(top_X_result) 
            print(f"Total # of iterations = {iteration + 1}")
            sys.exit(0)
            
        # make new query if X < num_tuples
        else:
            # print top k relations results to user
            print_results(sorted_X)
            seed_query = get_next_query(sorted_X)
            if not seed_query:
                print("There are no new queries to be made. Stopping program.")
                sys.exit(0)

        iteration += 1

    
def cmd_line():
    """
    Gather needed input from the user to run the program. If the structure is not correct, exit and give example usage. 

    Input: Command line input from user python project2.py [-spanbert|-gemini] <google api key> <google engine id> <google gemini api key> <r> <t> <q> <k>
    Output: Either exit and explain proper usage or continue to execute the program
    """

    # Declare global variables to be used across program
    global google_api_key, gemini_api_key, cx, seed_query, num_tuples, confidence_threshold, extraction_method, extraction_type

    # If too few or too many args passed, exit and explain
    if len(sys.argv) != 9:
        print("Usage: python project2.py [-spanbert|-gemini] <google api key> <google engine id> <google gemini api key> <r> <t> <q> <k>")
        exit(1)

    # Extract command line arguments: google api key, google engine key, gemini api key, extraction type, confidence threshold, seed query, number of tuples
    try:
        # Extraction method selection (SpanBERT or Gemini)
        command_extraction = sys.argv[1]
        if command_extraction != "-spanbert" and command_extraction != "-gemini":
            raise ValueError(" Extraction Relation Method must use either be -spanbert or -gemini")

        # Trim text
        extraction_method = "gemini" if command_extraction == "-gemini" else "spanbert"

        # API keys
        google_api_key = sys.argv[2]
        cx = sys.argv[3]
        gemini_api_key = sys.argv[4]

        # Desired relationship extraction type
        extraction_type = int(sys.argv[5])

        if extraction_type not in range(1, 5):
            print(extraction_type)
            raise ValueError("Extraction Type must be an integer between 1 and 4.")

        # Confidence threshold (spanBERT only, gemini is unaltered by this value)
        confidence_threshold = float(sys.argv[6])

        # Confidence threshold validation
        if extraction_method == "spanbert" and not (0 < confidence_threshold <= 1):
            raise ValueError("Confidence Threshold must be a number greater than 0 and less than/equal to 1.")

        # Original seed query
        seed_query = sys.argv[7]

        if not seed_query:
            raise ValueError("Seed Query cannot be empty.")

        # Desired number of tuples...
        num_tuples = int(sys.argv[8])

        # ...cannot be 0 or less
        if num_tuples <= 0:
            raise ValueError("Number of Tuples must be greater than 0.")

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

   
def query_print_cmd(iteration, extraction_method):
    """
    Display keys and current query to user (parameters and result line to be displayed before each search)

    Input: Number iteration (starting with 0 for initial search), and desired relation description
    Output: A terminal print out for the user summarizing their inputed args
    """

    print("____")
    print('Parameters:')
    print(f"Client key = {google_api_key}")
    print(f"Engine key = {cx}")
    print(f"Gemini key = {gemini_api_key}")
    print(f"Method     = {extraction_method}")
    print(f"Relation   = {relations[extraction_type]}")
    print(f"Threshold  = {confidence_threshold}")
    print(f"Query      = {seed_query}")
    print(f"# of Tuples  = {num_tuples}")
    print("Loading necessary libraries; This should take a minute or so ...")

# Main function - start of the information extraction process
def main():
    # Read in the required keys, seed query, relation method and type, number of tuples from command-line
    cmd_line()

    # Initiate information extraction with user input
    run_ise_algorithm()

if __name__ == "__main__":
    main()