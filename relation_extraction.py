"""
This file initiates the entity extraction process and diverts scraped text to either the spanBERT or Gemini models
    for relationship prediction and transcript read-out. 
"""

import spacy
import google.generativeai as genai

# Used to handle results returned by Gemini
import ast

# Load pre-trained SpanBERT model
from spanbert import SpanBERT 
from spacy_help_functions import *
spanbert = SpanBERT("./pretrained_spanbert")  

# Load helper functions for gemini extraction
from gemini_help_functions import *

# Load the spaCy English language model
nlp = spacy.load("en_core_web_lg")

def spanbert_relation_extraction(text, desired_type, conf):
    """
    Helper function to handle text when -spanbert is selected.
    Input: Raw Text, a list of entities belonging to desired relation, confidence threshold.
    Output: Returns a dictionary of relations to be handled and printed out for the user.
    """

    # Tag named entities of raw text using spaCy
    doc = extract_entities(text)

    # Get the desired entity types and entity relationship from user input
    entity_type, relation_type = get_entity_type(desired_type)

    # Use SpanBERT to return the relations between desired entity types and their confidence
    relations = extract_relations(doc, spanbert, conf, entity_type, relation_type)

    return dict(relations)

def gemini_relation_extraction(text, gemini_api_key, desired_type, model_name='gemini-1.0-pro', max_tokens=2048,
                               temperature=0.9, top_p=1, top_k=1):
    """
    Method to handle text when Gemini is selected as the model.

    Input: plain text, Gemini API key, desired relationship between entities, Gemini model parameters
    Output: 
    """

    # Apply Gemini API Key
    GEMINI_API_KEY = gemini_api_key 
    genai.configure(api_key=GEMINI_API_KEY)

    # Initialize a generative model
    model = genai.GenerativeModel(model_name)

    # Configure the model
    ## Defaults set, but can be tuned here
    generation_config = {
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "max_output_tokens": max_tokens,
    }
    
    # Return an implicit exmaple for prompt based on the user selected desired relationship type
    implicit_example = gemini_relation_implicit_example(desired_type)

    # Return the relationship type in plain text for the prompt
    relation_type = gemini_relation_description(desired_type)

    # Return the desired relationship format for the prompt
    relation_format = gemini_relation_example(desired_type)[0]

    # Return an example in the desired format
    relation_example = gemini_relation_example(desired_type)[1]
    
    # Prompt to be passed to Gemini before presenting the sentence for evaluation
    ## Relies on variables defined above for "few-shot" prompt engineering.
    few_shot = f"""
    Given a sentence, can you find any {relation_type} entity relations? If no explicit relations found then
    pay attention to any implied connections in the sentence , such as
    {implicit_example} as these also count as a relation.
    Please respond in this format only: "\n{relation_format}\n" , for each relation found, there may be more than one per sentence.
    
    Here is a example of a {relation_type} relation: 
    {relation_example}

    If there is no mention of subject or object then only return the format as "["Unknown","Unknown"]".
    Sentence:
    """
   
    # Initialize list to store extracted tuples
    extracted_tuples = []

    # Parse the document into sentences
    sentences = list(extract_entities(text).sents)

    num_sentences = len(sentences)

    print(f"        Extracted {num_sentences} sentences. Processing each sentence one by one to check for presence of right pair of named entity types; if so, will run the second pipeline ...")
    # initialize sentence processed counter
    processed_sentence_counter = 0

    # initialize number of annotations sentences counter
    num_annotated_sentences = 0

    # initialize number of relations counter
    num_relations_from_website = 0

    # Process each sentence
    for sentence in sentences:
        # check if the sentence has been annotated or not
        have_annotate_sentence = False
        processed_sentence_counter += 1 
        if processed_sentence_counter % 5 == 0:
                print(f"        Processed {min(processed_sentence_counter, num_sentences)} / {num_sentences} sentences")

        # Process the sentence for entity types
        entities = get_entities(sentence,get_entity_type(desired_type)[0])

        # Check if the sentence contains the named entity pairs required for the relation of interest
        if contains_entities(sentence, desired_type) and len(entities) != 0:
            entity_pairs = []
            # Generate a response only if sentence contains desired entity
            ## Combine the sentence with a few-shot prompt for Gemini
            prompt = f"""
            {few_shot} \n "{sentence.text}"\n
            , strictly limiting the extraction to connections 
            between entities specifically mentioned in the sentence without making any inferences or assumptions
            """
            # Save the response generated by Gemini from the prompt
            response = model.generate_content([prompt], generation_config=generation_config)
            # Make sure the repsonse is in the needed structure to parse for Subjects and Objects
            ## Sometimes Gemini would response in a sentence, letting the user know no relation was found. This avoids that type error.
            if check_response_structure(response.text, desired_type):
                try:
                    # Append the extracted_tuples list with the response from Gemini
                    entity_pairs.append(response.text)
                    results = [item for sublist in [x.split('\n') if '\n' in x else [x] for x in entity_pairs] for item in sublist]
                    list_of_lists = [ast.literal_eval(item) for item in results]
                 
                    # Iterate through all the lists of lists returned by Gemini from the processed sentence
                    for ep in list_of_lists:

                        subj = ep[0]
                        obj = ep[2]

                        print("\n\t\t=== Extracted Relation ===")
                        print("\t\tSentence: {}\n".format(sentence.text))
                        print("\t\tSubject: {} ; Object: {} ;".format(subj, obj))
                        # If this is a unique tuple, add it to extracted_tuples
                        if {"subj": subj, "obj": obj} not in extracted_tuples:
                            extracted_tuples.append({"subj": subj, "obj": obj})
                            print("\t\tAdding to set of extracted relations")
                        # If this is a duplicate tuple, do nothing and inform the user
                        else:
                            print("\t\tDuplicate. Ignoring this.")

                        have_annotate_sentence = True 
                        num_relations_from_website += 1
                            
                        print("\t\t==========")
                except:
                    pass

        # if we have extracted any annotations from a current sentence then add 1 to the number of annotated sentences out all the sentences
        if have_annotate_sentence:
            num_annotated_sentences += 1

    # print the annotated and relation results
    print(f"\n        Extracted annotations for  {num_annotated_sentences}  out of total  {num_sentences}  sentences")
    print(f"        Relations extracted from this website: {len(extracted_tuples)} (Overall: {num_relations_from_website})\n")
    
    # Return final results
    return extracted_tuples

def extract_entities(text):
    """
    Tag named entites with spaCy.

    Input: plain text
    Output: text processed by the spaCy library for named entities
    """
    # Extract named entities using spaCy that meet the user selected extraction type
    doc = nlp(text)
    
    return doc
    

def get_entity_type(desired_type):
    """
    Mapping function that takes the user imputted extraction type  and transforms it into the
    text associated with the desired extraction type and relation type.

    Input: int (1-4 inclusive)
    Output: A list of relevant entites, relationship that can be processed by spanBERT. For numbers outside of 1-4, return 'INVALID'.
    """ 
    entities = {
        1: ['PERSON','ORGANIZATION'],
        2: ['PERSON','ORGANIZATION'],
        3: ['PERSON','LOCATION','CITY','STATE_OR_PROVINCE','COUNTRY'],
        4: ['ORGANIZATION','PERSON']
        }
    
    relations = {
        1: ['per:schools_attended'],
        2: ['per:employee_of'],
        3: ['per:countries_of_residence','per:cities_of_residence','per:stateorprovinces_of_residence'],
        4: ['org:top_members/employees']
        }
    
    return entities.get(desired_type, 'INVALID'), relations.get(desired_type, 'INVALID')

def contains_entities(processed_sentence, desired_type):
    """
    This method will check to make sure a sentence processed by spaCy contains all of the entity types required of the desired relationship.
    In the event that the user is looking for the Lived_In relationship, the method will accept any subset of LOCATION, CITY, STATE_OR_PROVINCE, or COUNTRY.

    Input: a spaCy processed sentence.
    Output: Boolean value to say "Yes, predict a relationship from this sentence" or "No, do not evaluate this sentence with the model."
    """

    # spaCy to spanBERT mappings
    ## spanBERT entities names used in gemini model as well for easier readability
    spacy2bert = { 
        "ORG": "ORGANIZATION",
        "PERSON": "PERSON",
        "GPE": "LOCATION", 
        "LOC": "LOCATION",
        "DATE": "DATE"
        }

    # Determine entity types of interest from user inputed desired relationship
    entity_types = get_entity_type(desired_type)[0]

    # Flag to check if any location-related entity is found
    location_found = False

    # Initialize flags for each entity type
    entity_found = {ent_type: False for ent_type in entity_types}

    # Iterate over entities in the processed sentence
    for ent in processed_sentence.ents:
        # Get the mapped entity name
        ## If no mapping exists in our dict, call it OTHER
        mapped_entity_type = spacy2bert.get(ent.label_,"OTHER")
        if mapped_entity_type in entity_types:
            # If the mapped entity type is LOCATION, set location_found to True
            if mapped_entity_type == "LOCATION":
                if spacy2bert.get(ent.label_,"OTHER") in ['LOCATION','CITY','STATE_OR_PROVINCE','COUNTRY']:
                    location_found = True
            else:
                entity_found[mapped_entity_type] = True

    # If any location-related entity is found, set all location-related entity flags to True
    if location_found:
        for location_type in ["LOCATION", "CITY", "STATE_OR_PROVINCE", "COUNTRY"]:
            entity_found[location_type] = True

    # Check if all specified entity types are found. If yes, return True to process the sentence with the model
    return all(entity_found.values())