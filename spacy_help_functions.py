"""
This file contains spacy help functions to process plain text. 

It also contains functions to execute the spanBERT model if selected by the user.

This file was largely provided by the course staff, with minor modifications outlined in README.md
"""

# Environment Set Up
import spacy
from collections import defaultdict

spacy2bert = { 
        "ORG": "ORGANIZATION",
        "PERSON": "PERSON",
        "GPE": "LOCATION", 
        "LOC": "LOCATION",
        "DATE": "DATE"
        }

bert2spacy = {
        "ORGANIZATION": "ORG",
        "PERSON": "PERSON",
        "LOCATION": "LOC",
        "CITY": "GPE",
        "COUNTRY": "GPE",
        "STATE_OR_PROVINCE": "GPE",
        "DATE": "DATE"
        }


def get_entities(sentence, entities_of_interest):
    """
    Get entities of interest from a spacy processed sentence. Use spacy2bert to map entity naming conventions

    Input: A spacy processed setnence and a list of entities of interest
    Output: A list of entities of interest contained in the processed sentence
    """
    return [spacy2bert.get(e.label_,"OTHER") for e in sentence.ents if spacy2bert.get(e.label_,"OTHER") in entities_of_interest]

def extract_relations(doc, spanbert, conf, entities_of_interest=None,relations_of_interest=None):
    """
    Preforms the relation extraction for the spanBERT model. As the program iterates through sentences, it will print to the terminal to keep the user updated on progress.

    Input: A spacy processed document (in our case, processed plain text scrapped from websites)
    Output: Relationship Tuples
    """
    num_sentences = len([s for s in doc.sents])
    print(f"        Extracted {num_sentences} sentences. Processing each sentence one by one to check for presence of right pair of named entity types; if so, will run the second pipeline ...")

    # initialize sentence processed counter
    processed_sentence_counter = 0

    # initialize number of annotations sentences counter
    num_annotated_sentences = 0

    # initialize number of relations counter
    num_relations_from_website = 0

    res = defaultdict(int)
    
    for sentence in doc.sents:
        # check if the sentence has been annotated or not
        have_annotate_sentence = False
        processed_sentence_counter += 1 
        if processed_sentence_counter % 5 == 0:
                print(f"        Processed {min(processed_sentence_counter, num_sentences)} / {num_sentences} sentences")

       
        entity_pairs = create_entity_pairs(sentence, entities_of_interest)

        examples = []
        for ep in entity_pairs:
            examples.append({"tokens": ep[0], "subj": ep[1], "obj": ep[2]})
            examples.append({"tokens": ep[0], "subj": ep[2], "obj": ep[1]})

        # remove non required entities
        examples = [ex for ex in examples if ex['subj'][1] == entities_of_interest[0] and ex['obj'][1] == entities_of_interest[1]]
        
        # check if there is any entity pairs, if not then continue to next sentence
        if not examples:      
            continue

        preds = spanbert.predict(examples)
        for ex, pred in list(zip(examples, preds)):
            relation = pred[0]
            if relation == 'no_relation':
                continue
            
            if relation in relations_of_interest:
                    print("\n\t\t=== Extracted Relation ===")
                    tokens = ex["tokens"]
                    print("\t\tInput tokens: {}\n".format(tokens))
                    subj = ex["subj"][0]
                    obj = ex["obj"][0]
                    confidence = pred[1]
                    print("Output Confidence: ", confidence, "; Subject: {} ; Object: {} ;".format(subj, obj))
                    if confidence > conf:
                        if res[(subj, obj)] < confidence:
                            res[(subj,obj)] = confidence 
                            print("\t\tAdding to set of extracted relations")
                        else:
                            print("\t\tDuplicate with lower confidence than existing record. Ignoring this.")
                    else:
                        print("\t\tConfidence is lower than threshold confidence. Ignoring this.")
                    have_annotate_sentence = True 
                    num_relations_from_website += 1
        
                    print("\t\t==========")
        # if we have extracted any annotations from a current sentence then add 1 to the number of annotated sentences out all the sentences
        if have_annotate_sentence:
            num_annotated_sentences += 1

    # print the annotated and relation results
    print(f"\n        Extracted annotations for  {num_annotated_sentences}  out of total  {num_sentences}  sentences")
    print(f"        Relations extracted from this website: {len(res)} (Overall: {num_relations_from_website})\n")
    
    # return all relations
    return res


def create_entity_pairs(sents_doc, entities_of_interest, window_size=40):
    """
    Create entity pairs from a spacy processed sentence using entities of interest over a given window size

    Input: a spaCy Sentence object and a list of entities of interest, window size defaulted to 40
    Output: list of extracted entity pairs: (text, entity1, entity2)
    """

    if entities_of_interest is not None:
        entities_of_interest = {bert2spacy[b] for b in entities_of_interest}
    ents = sents_doc.ents # get entities for given sentence

    length_doc = len(sents_doc)
    entity_pairs = []
    for i in range(len(ents)):
        e1 = ents[i]
        if entities_of_interest is not None and e1.label_ not in entities_of_interest:
            continue

        for j in range(1, len(ents) - i):
            e2 = ents[i + j]
            if entities_of_interest is not None and e2.label_ not in entities_of_interest:
                continue
            if e1.text.lower() == e2.text.lower(): # make sure e1 != e2
                continue

            if (1 <= (e2.start - e1.end) <= window_size):

                punc_token = False
                start = e1.start - 1 - sents_doc.start
                if start > 0:
                    while not punc_token:
                        punc_token = sents_doc[start].is_punct
                        start -= 1
                        if start < 0:
                            break
                    left_r = start + 2 if start > 0 else 0
                else:
                    left_r = 0

                # Find end of sentence
                punc_token = False
                start = e2.end - sents_doc.start
                if start < length_doc:
                    while not punc_token:
                        punc_token = sents_doc[start].is_punct
                        start += 1
                        if start == length_doc:
                            break
                    right_r = start if start < length_doc else length_doc
                else:
                    right_r = length_doc

                if (right_r - left_r) > window_size: # sentence should not be longer than window_size
                    continue

                x = [token.text for token in sents_doc[left_r:right_r]]
                gap = sents_doc.start + left_r
                e1_info = (e1.text, spacy2bert[e1.label_], (e1.start - gap, e1.end - gap - 1))
                e2_info = (e2.text, spacy2bert[e2.label_], (e2.start - gap, e2.end - gap - 1))
                if e1.start == e1.end:
                    assert x[e1.start-gap] == e1.text, "{}, {}".format(e1_info, x)
                if e2.start == e2.end:
                    assert x[e2.start-gap] == e2.text, "{}, {}".format(e2_info, x)
                entity_pairs.append((x, e1_info, e2_info))

    return entity_pairs