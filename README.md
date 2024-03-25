# CS6111 Adv Database Systems Spring 24 - Project 2
Mar 25, 2024

## Team
Amari Byrd (ab5311) and Lauren Kopac (ljk2148)

## Files in Submission
|File Name| Description|
|---------|------------|
| `ise_main.py`| Main proj2 `.py` file. Imports functions from `relation_extraction.py` and `web_scraping.py` to preform a websearch and iteratively generate tuples|
|`web_scraping.py`| Web scrapping helper functions to fetch text from URLs.|
|`relation_extraction.py`|Processes text gathered from web search and uses either spanBERT or Gemini to interpret text into relations.|
|`spacy_help_functions.py`| Modified version of spacy helper functions provided by the course staff.|
|`gemini_help_functions.py`| Help functions for generating prompts to send to gemini and processing responses. |
|`spanbert.py`| Modified version of spanbert class provided by the course staff.|
|`README.pdf`| PDF version of `README.md` file on Github.|
|`requirements.txt`| Packages required for the program.|
|`spanbert_transcript.pdf`| PDF file of spanbert test case transcript. |
|`gemini_transcript.pdf`| PDF file of spanbert test case transcript.|
|`./pretrained_spanbert/config.json`| JSON config file for pretrained spanbert model. |
|`./pytorch_pretrained_bert/file_utils.py`| Needed `.py` file for spanbert model. |
|`./pytorch_pretrained_bert/modeling.py`| Needed `.py` file for spanbert model. |
|`./pytorch_pretrained_bert/optimization.py`| Needed `.py` file for spanbert model. |
|`./pytorch_pretrained_bert/tokenization.py`| Needed `.py` file for spanbert model. |

## Files NOT in Submission

The following file(s) were originally provided by the course staff, but due to size requirements we were unable to upload with the rest of our submission. To successfully run the program, they need to be added into the marked directories. 

|File Name| Description|
|---------|------------|
|`./pretrained_spanbert/pytorch_model.bin`| Pretrained spanbert model. This file was too big to submit over GradeScope. To run our program, the `pytorch_model.bin` file must be added to the `./pretrained_spanbert/` directory. |


## API Keys
|Key Name | Key|
|---------|------------|
|Google API Key | `AIzaSyBHRHOxxGtFuRU3bfpVkGKc29_R8jN6Gu8`|
|Google Engine ID |`f2d45d63dda814dd6`|
|Google Gemini API| `AIzaSyC-esIaQHAInpTOquQmTPN8-7w_FnIrTvU`|


## How to Use
Navigate to the project's root file and run the following to install needed packages after activating the python virtual environment:

```bash
$ pip install -r requirements.txt
```

To run the program, enter the following into the command line within the Project2 directory:

```bash
$ python3 ise_main.py [-spanbert|-gemini] <google api key> <google engine id> <google gemini api key> <r> <t> <q> <k>
```

### Implementation Parameters
*  `[-spanbert|-gemini]` - either `-spanbert` or `-gemini`, to indicate which relation extraction method to request
* `<google api key>` - Google Custom Search API Key (see API Keys section)
* `<google engine id>` -  Google Custom Search Engine ID (see API Keys section)
* `<google gemini api key>` - Google Gemini API key (see API Keys section)
* `<r>` - integer between 1 and 4 (inclusive), indicating the relation to extract: 
  * 1 - Schools_Attended
  * 2 - Work_For
  * 3 - Live_In
  * 4 - Top_Member_Employees
* `<t>` - real number between 0 and 1 (inclusive), indicating the "extraction confidence threshold," a.k.a, the minimum extraction confidence requested for the tuples in the output
  * **Note:** `t` is ignored if we are specifying `-gemini`, which will assume a confidence threshold of 1.
* `<q>` - seed query, a list of words in double quotes corresponding to a plausible tuple for the relation to extract 
  * **Example:** "bill gates microsoft" for relation Work_For
* `<k>` - integer greater than 0, indicating the number of tuples that we request in the output

## Internal Design

### Phase 1: Retrieval and Parsing of Webpages
For a user inputed seed query (`q`) the program will make an API call to Google's Custom Search Engine and retrieve the top 10 URLs to parse for plain text.

1. The program will first accept a set of parameters from the user. If valid, the program will print back the parameters for the user in the terminal. 
2. An API call will be made to Google's custom search engine to fetch the top-10 search results for `q`. 
3. Using `BeautifulSoup`, the webpages are parsed and plain text is extracted. If the resulting plain text is longer than 10,000 characters, the text is truncated and anything exceeding 10,000 characters is discarded. If any of the top-10 URLs are unretrievable or otherwise not parsable, it will be skipped.
4. Each validly retrieved URL is then processed fully, one at a time, to search for tuples to extract relevant to what the user is searching for

#### Associated Files
 * `ise_main.py`
 * `web_scraping.py`

### Phase 2: Processing of Plain Text, Extract Named Entities
As URLs are retrieved in Phase 1, their plain text is processed using the `spacy` library and its English language model (`"en_core_web_lg"`) to identify and tag entities (i.e. PERSON, ORGANIZATION) for relationship identification.

1. The body of plain text retrieved from a URL passed through spaCy's English language model and is then split into sentences.
2. For each processed sentence, the entites are extracted and compared against what entities are relevant to the user's request (`r`). If there is a match, i.e. the entities contained in the processed sentence match the entities of the desired relation, the sentence will then be passed onto a model (either spanBERT or Gemini as determined by the user) for relation extraction.

#### Associated Files
* `relation_extraction.py`
* `spacy_help_functions.py`

### Phase 3: Model Prediction of Relationship
Based on user input (`[-spanbert|-gemini]`), processed sentences from Phase 2 will be sent to either the SpanBERT pretrained model (provided by course staff) or Google Gemini's LLM for relationship predictions.

#### SpanBERT
If the user indicated `-spanbert` when initiating the program, the process of extracting tuples with the pretrained SpanBERT model will begin.

1. One at a time, valid processed sentences from Phase 2 will be passed to the spanBERT model for relationship prediction.
2. Entity pairs are created for relationship assessment with `create_entity_pairs(sentence, entities_of_interest)`
3. If spanBERT can determine a relationship between entity pairs created, the relationship will be checked against the desired relationship entered by the user. If no relationship is found, no tuples will be added. If the relationship is as desired, the tuple will be assessed for viability.
4. If a relationship is found in the previous step, the model will assign the relationship a confidence value. For the candidate tuple to be successfully extracted, its confidence value must be greater than or equal to the threshold set by the user. If it is lower, the tuple is skipped. If it passes the threshold, it will assessed agaisnt existing tuples.
5. If a newly extracted tuple is identical to an existing one, the confidence values will be compared, keeping the higher of the two and discarding the lower.
6. This process repeats until all 10 URLs are processed.
7. Following the processing of the original 10 URLs, the program checks to see if it has succcessfully collected the `k` number of tuples requested by the user. If not, the program will reiterate from Phase 1, using the top collected tuple to construct a new query and search for new URLs to scrape.

While the SpanBERT extaction process runs, the user receives output to the terminal of the progress made processing URLs and extracting tuples. At the conclusion of the program, the user will recieve a final output detailing the top `k` tuples collected from the URLs. Top `k` is defined as the `k` number of tuples with highest confidence values, where `k` is set by the user at initialization.

#### Gemini
If the user indicated `gemini` when initiating the program, the process of extracting tuples through Gemini will begin.

1. One at a time, valid processed sentences from Phase 2 will be passed to Google's Gemini LLM for relationship predicition. 
2. Depending on the user selected relation, a prompt will be generated translating the `r` parameter (an int between 1 and 4) into a plain english explanation. The prompt will include an implicit example for gemini for the given relationship, and a desired structured output for Gemini to give a response.
3. Reponses from Gemini are then checked to confirm the type of relationship extracted matches the user's desired input. The responses are also checked for structure as tuples are extracted and saved.
4. Gemini does not assign a confidence to relations provided, but as the program iterates through sentences, it checks for duplicates. If a duplicate relation is extracted, the duplicate is ignored and the program moves onto the next sentence.
5. This process repeates until all 10 URLs are processed.
6. Following the processing of the original 10 URLs, the program checks to see if it has succcessfully collected the `k` number of tuples requested by the user. If not, the program will reiterate from Phase 1, using the first collected tuple to construct a new query and search for new URLs to scrape.

While the Gemini extraction process runs, the user receives output to the terminal of the progress made processing URLs and extracting tuples. At the conclusion of the program, the user will recieve a final output detailing all tuples collected from the URLs. This is different than the spanBERT method that only returns the top `k`. 

#### Associated Files
* `relation_extraction.py`
* `spacy_help_functions.py`
* `spanbert.py`
* `gemini_help_functions.py`
* `ise_main.py`

#### Modifications to `spacy_help_functions.py`

To better serve our specific program, we made modifications to the helper functions provided by the course staff. 

* When using the SpanBERT model, we pass the spaCy processed sentences through `extract_relations()` from `spacy_help_functions.py`.
  * **Modifications:** Added `relations_of_interest` parameter that is passed when calling the method. Makes sure that only the relationships we are interested in ar returned. Executed with a nested `if` statement that checks to see if the parameter has been passed and assesses each entity pairs relationship 
    ```python
    if relation == 'no_relation':
      continue
    if relations_of_interest is not None:
      if relation in relations_of_interest:
          # Code that assesses the entity pair and decides 
          #  whether or not to add it to set of extracted relations.
      else:
    ```

#### Fixed Values and Parameters

For the Google Gemini model, we elected to use the following parameters [^1]:

* `model_name` = 'gemini-1.0-pro'
* `max_tokens` = 2048
* `temperature` = 0.9
* `top_p` = 1
* `top_k` = 1

They are set by default when calling `gemini_relation_extraction`.


## External Libraries
Our programs relies on the following Python frameworks:

|Library | Use |
|---------|------------|
|`requests`| Used in the `fetch_website()` method to make a call Google's custom search engine API. Responses converted to JSON for processing.|
| `bs4` | Using `BeautifulSoup` and `Comment` to parse html content of URLs in `extract_plain_text()` method.|
|`spacy`| Using to process natural language text, tag entities, and allow models (SpanBERT/gemini) to predict relations. |
|`google.generativeai`| Using to make an API call to Google's Gemini LLM. |
|`ast`| Using to process Gemini's reponses into easily manipulated data structures. | 
|`re`| Using to evaluate the structure of Gemini's responses. Helping to pick out subjects and objects of outputs. |
|`collections`| Using in `spacy_help_functions.py` to handle collected tuples from the spanBERT extraction process. |


## External References
[^1] “Gemini API  |  Generative AI on Vertex AI  |  Google Cloud.” Google, Google, cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini. Accessed 21 Mar. 2024. 
