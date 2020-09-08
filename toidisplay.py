# Imports
import os, zipfile, pathlib, shutil, subprocess, zipp
import pandas as pd
import regex as re
from IPython.display import clear_output
from IPython.display import IFrame
from urllib.parse import quote
from wand.image import Image as Wimage
from PyPDF2 import PdfFileReader

# tqdm import
def isnotebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter

if isnotebook():
    from tqdm.notebook import tqdm
else:
    from tqdm import tqdm 

# Definitions

def get_display_list(request_list, output_csv='article_output.csv'):
    """
    This function takes an input csv, 
    an output csv, and outputs a list of articles 
    in the input list but not in the output list
    """
    if os.path.exists(output_csv):
        completed_articles = list(pd.read_csv(output_csv,index_col=0).index)
    else:
        completed_articles = []
  
    # read in the categorization done so far
    request_list = list(set(request_list) - set(completed_articles))
    
    return request_list

def input_list(request):
    lookup_list = input(request)
    lookup_list = re.sub(r'[,;](*SKIP)(*FAIL)|\W', '', lookup_list)
    return re.split(r',\s*|;\s*|\s+', lookup_list)

def request_input():
    """
    Requests a list of article IDs to display, and returns a split list.
    """
    
    request_list = input_list("What article IDs shall I look up for you?")
    clear_output()
    return request_list

def sanitize(request_list):
    """
    Takes a raw-text input, returns all members of the list that are
    valid TOI article ids as a list, and prints a notification of any
    members of the list not so recognized.
    """
    TOI_METADATA = load_metadata()
    wanted_articles = []
    unrecognized_articles = []
    
    all_articles = set(TOI_METADATA.index)

    for article in request_list:
        clean_art = int(str(article).strip())
        if clean_art in all_articles:
            wanted_articles.append(clean_art)
        elif clean_art == '':
            pass
        else: 
            unrecognized_articles.append(clean_art)
    
    if len(unrecognized_articles) > 0:
        print("The following entries were not recognized as articles:")
        [print(repr(x)) for x in unrecognized_articles]
    if len(wanted_articles) == 0:
        raise ValueError('No valid article IDs Recognized!')
    return(wanted_articles)

def unpack_pdfs(request_list):
    print("Unpacking requested pdfs...")
    
    global TOI_METADATA
    
    df = TOI_METADATA.loc[request_list]
    zips_to_open = df[df.pdf_zip.notnull()].pdf_zip.unique().tolist()

    for zip_file in zips_to_open:
        
        files_to_extract = df[df['pdf_zip'] == zip_file].pdf_file.unique().tolist()   

        with zipfile.ZipFile(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'PDF', zip_file)) as zf: 

            for file in files_to_extract:
                zf.extract(file, path=os.path.join(os.path.abspath(os.path.dirname(__file__)), "temp"))
    print("Done!")

def display_article(article, input_function):
    """
    Displays the pdf version of a requested article in a notebook's IFrame
    """
    global TOI_METADATA
    
    if type(TOI_METADATA.at[article, 'pdf_file']) == str:

        pdf_file = TOI_METADATA.at[article, 'pdf_file']
        pdf_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), "temp", pdf_file)

        rel_path = os.path.relpath(pdf_file)
        with open(rel_path, 'rb') as f:
            number_of_pages = PdfFileReader(f).getNumPages()
        for page in range(number_of_pages):
            img = Wimage(filename=rel_path+f'[{page}]', resolution=150)
            display(img)
            # display(IFrame(src=rel_path, width='100%', height='700px'))
    
    else:
        print("No pdf file found in archive, displaying txt instead:")
        ziparchive = TOI_METADATA.at[article, 'txt_zip']
        txt_file = TOI_METADATA.at[article, 'txt_file']
        with zipfile.ZipFile(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'TXT', ziparchive)) as zf:
            text = zf.read(txt_file)
        print(text)

    
    pub_date = TOI_METADATA.at[article, 'pub_date']
    objecttypes = TOI_METADATA.at[article, 'objecttypes']
    objecttypes = objecttypes.split(';')
    
    try:
        print(f'Article ID: {article} \t Published: {pub_date}')
        print('Object Types:\t', ', '.join(objecttypes))
    except:
        pass
    
    if callable(input_function):
        feedback = input_function(article)
    elif input_function == None:
        feedback = input("Press enter to display next article.")
    else:
        raise TypeError('input_function is not a valid function.')
        
    clear_output()
    
    return feedback
    
def binary_categorize(article):
    
    category_judgment = ''
    while type(category_judgment) != bool:
        category_judgment = input(f"enter (y or 1 = Yes, n or 0 = No)")
        if category_judgment == 'y' or category_judgment == '1':
            category_judgment = True
        elif category_judgment == 'n' or category_judgment == '0':
            category_judgment = False
        else:
            print("I'm not sure how to interpret that.")
    
    return category_judgment

def save_results(output_dict, save_location):
    """
    Saves a CSV with article index and a copy of user input.
    """
    if os.path.exists(save_location):
        old = pd.read_csv(save_location, index_col=0)
        new = pd.DataFrame.from_dict(output_dict, orient='index', columns=['human_input'])
        df = old.append(new)
    else:
        df = pd.DataFrame.from_dict(output_dict, orient='index', columns=['human_input'])

    df.to_csv(save_location)

    print("Progress saved.")

def display_article_chunk(request_list, chunk_number, chunk_size, input_function, output_dict, save_location):
    global TOI_METADATA
    
    number_of_chunks = len(request_list)//chunk_size + (len(request_list) % chunk_size > 0)
    
    n = 0

    if len(request_list) >= chunk_size*chunk_number+1:
        this_chunk = request_list[chunk_size*chunk_number:chunk_size*(chunk_number+1)]
    else:
        this_chunk = request_list[chunk_size*chunk_number:]
        
    
    for article in this_chunk:
        n+=1
        print(f"Here's article {n} of {len(this_chunk)}, in set {chunk_number+1} of {number_of_chunks}:")
        feedback = display_article(article, input_function)
        output_dict.update({article:feedback})
        
    save_results(output_dict, save_location)
    
    return output_dict
    
def display_requested_articles(display_list=None, input_function=None, chunk_size=15, append_mode=True, save_location='article_output.csv'):
    global TOI_METADATA

    TOI_METADATA = load_metadata()

    if display_list == None:
        request_list = request_input()
    elif callable(display_list):
        request_list = display_list()
    elif type(display_list) == list:
        request_list = display_list
    
    if type(request_list) != list:
        raise TypeError('Please make sure display_list is either a list of IDs or a function returning a list of article IDs.')
    
    if append_mode == True:
        request_list = sanitize(get_display_list(request_list, output_csv=save_location))
    else:
        request_list = sanitize(request_list)
    
    unpack_pdfs(request_list)
    
    number_of_chunks = len(request_list)//chunk_size + (len(request_list) % chunk_size > 0)
    
    global continue_indicator
    
    continue_indicator = 1
    
    output_dict = {}
    
    for chunk_number in range(number_of_chunks):
        if int(continue_indicator) == 1:
            output_dict = display_article_chunk(request_list, chunk_number, chunk_size, input_function, output_dict, save_location)
            if chunk_number + 1 != number_of_chunks:
                continue_indicator = ask_whether_to_continue()
            if chunk_number + 1 == number_of_chunks:
                print("All requested articles displayed!")
        elif int(continue_indicator) == 0:
            pass
               
    empty(os.path.join(os.path.abspath(os.path.dirname(__file__)), "temp"))

def ask_whether_to_continue():
    continue_indicator = input('Enter 1 to continue, or 0 to exit:')
    while continue_indicator not in set(['1', '0']):
        continue_indicator = input('Enter 1 to continue, or 0 to exit:')
    return continue_indicator

# Import Data Index

def load_metadata():
    if 'TOI_METADATA' not in globals():
        global TOI_METADATA 
    
    
        print('Loading TOI metadata...')
        df_list = []
        with zipfile.ZipFile(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'TOI_metadata.zip')) as zf:
            with zf.open('TOI_metadata.csv') as file:
                for df_chunk in tqdm(pd.read_csv(file, 
                                                 index_col='record_id', 
                                                 dtype='object', 
                                                 engine='c',
                                                 chunksize=7240),
                                     total=1000):
                    df_list.append(df_chunk)
        TOI_METADATA = pd.concat(df_list)
        TOI_METADATA['pub_date'] = pd.to_datetime(TOI_METADATA.pub_date)
        clear_output
        print('done \n')
    
    return TOI_METADATA

def read_text(zipfile_object,fn):
    with zipfile_object.open(fn) as txt:
        txt_string = txt.read()
    txt_string = txt_string.decode()
    return(txt_string)

def punctuate(text):
    
    """
    This function makes use of Ottokar Tilk's Punctuator2,
    online at <https://github.com/ottokart/punctuator2>, and
    described in 
    @inproceedings{tilk2016,
                  author    = {Ottokar Tilk and Tanel Alum{\"a}e},
                  title     = {Bidirectional Recurrent Neural Network with Attention Mechanism for Punctuation Restoration},
                  booktitle = {Interspeech 2016},
                  year      = {2016}
                  }
    """
    
    proc = subprocess.Popen(["curl", "-d", f"text={quote(text)}", "http://bark.phon.ioc.ee/punctuator"], stdout=subprocess.PIPE)
    out = proc.communicate()[0]
    return out.decode("utf-8")

def get_text_df(request_list):
    TOI_METADATA = load_metadata()

    print("Reading in article contents")
    
    if type(request_list) != list:
        raise TypeError('Please make sure display_list is a list of IDs.')
    
    request_list = sanitize(request_list)
    
    working_set = TOI_METADATA.loc[request_list]
    
    article_texts = pd.Series(dtype='object')
    
    for zip_file in tqdm(working_set.txt_zip.unique()):
        path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'TXT', zip_file)
        files = working_set[working_set.txt_zip == zip_file]
        with zipfile.ZipFile(path) as z:
            text_series = files.txt_file.apply(lambda x: read_text(z,x))
            article_texts = article_texts.append(text_series)
            
    clear_output
    
    return pd.DataFrame({"article_text":article_texts})

def drop_by_objecttype(metadata):
    print('Filtering out non-news articles by type')
    before = len(metadata)

    # Drop based on object type

    unwanted = ["classified advertisement;advertisement",
                "advertisement",
                "credit/acknowledgement",
                "letter to the editor;correspondence",
                "stock quote",
                "image/photograph",
                "illustration",
                "obituary",
                "review",
                "birth notice",
                "news;marriage announcement",
                "table of contents;front matter",
                "editorial cartoon/comic",
                "advertisement;classified advertisement",
                "front matter;table of contents",
                "correspondence;letter to the editor",
                "news;legal notice",
                "undefined",
                "marriage announcement;news"]

    wanted = ['feature;article',
              'news',
              'editorial;commentary',
              'news;military/war news',
              'general information',
              'front page/cover story',
              'article;feature',
              'commentary;editorial',
              'military/war news;news']
    # (This is the complement of the "unwanted" set; for confirmation, 
    # uncomment and run the following 2 lines:

    # print(set(metadata[metadata.objecttypes.isin(wanted)].record_id.tolist()) == 
    #       set(metadata[~metadata.objecttypes.isin(unwanted)].record_id.tolist()))

    metadata = metadata[~metadata.objecttypes.isin(unwanted)]

    trimmed = before - len(metadata)
    print(f"{trimmed:n} records trimmed. {len(metadata):n} records remain.")
    
    return metadata

def drop_by_note(metadata):
    print('Filtering out articles with no text')
    before = len(metadata)

    # Drop if article has no text ('note' is either null, or contains 'No text')
    metadata = metadata[metadata.note.isnull()]

    trimmed = before - len(metadata)
    print(f"{trimmed:n} records trimmed. {len(metadata):n} records remain.")
    
    return metadata

def drop_by_title(metadata):
    print('Filtering out non-news documents identifiable by title')

    before = len(metadata)

    # Drop based on title
    unwanted_titles = ['weather', 
                       'current_topics', 
                       'city_lights', 
                       'radio.txt', 
                       'telefilm',
                       'engagements', 
                       'greetings', 
                       'television.txt', 
                       'acknowledgement.txt']

    unwanted_titles = '|'.join(unwanted_titles)

    metadata = metadata[~metadata.txt_file.str.contains(unwanted_titles)]

    trimmed = before - len(metadata)
    print(f"{trimmed:n} records trimmed. {len(metadata):n} records remain.")
    return(metadata)

def filter_non_news_articles(metadata):
    metadata = drop_by_objecttype(metadata)
    metadata = drop_by_note(metadata)
    metadata = drop_by_title(metadata)
    return metadata

def get_punctuated_text_df(article_list, save_as):
    """
    For a list of articles, creates a dataframe containing the article id, text, 
    and punctuated text. Saves this dataframe as a CSV file.
    """
    
    if os.path.exists(save_as):
        
        print('Loading text dataframe...')
        texts = pd.read_csv(save_as, index_col=0)
        clear_output
        
        print('Done!')
        return texts
    
    else:
        
        # Reading in article texts:
        print("Reading in article text...")
        texts = get_text_df(article_list)
        clear_output()

        # Punctuating the article texts:
        print("Inferring text punctuation...")
        texts['punctuated_text'] = texts.article_text.progress_apply(punctuate)
        clear_output()

        # Saving, because this is really time-consuming
        print("Saving texts...")
        texts.to_csv(save_as)
        clear_output()

        print('Done!')
        return texts

def empty(folder):
    """
    Deletes all files, directories, or links in a folder.
    """
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))