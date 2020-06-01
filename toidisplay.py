# Imports
import os, zipfile, pathlib, shutil
import pandas as pd
import regex as re
from IPython.display import clear_output
from IPython.display import IFrame
import zipp

# Definitions

def empty(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

def sanitize(request_list):
    wanted_articles = []
    unrecognized_articles = []
    
    all_articles = set(metadata.index)

    for article in request_list:
        clean_art = str(article).strip()
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

def request_input():
    request = input("What article IDs shall I look up for you?")
    request_list = re.split(",|;| ", request)
    clear_output()
    return request_list

def unpack_pdfs(archive_location, request_list):
    print("Unpacking requested pdfs...")
    
    global metadata
    
    df = metadata.loc[request_list]
    zips_to_open = df.pdf_zip.unique().tolist()

    for zip_file in zips_to_open:

        files_to_extract = df[df['pdf_zip'] == zip_file].pdf_file.unique().tolist()   

        with zipfile.ZipFile(os.path.join(archive_location, 'PDF', zip_file)) as zf: 

            for file in files_to_extract:
                zf.extract(file, path=os.path.join(archive_location, "temp"))
    print("Done!")

def display_article(article, linked_function):
    
    global metadata
    
    pdf_file = metadata.at[article, 'pdf_file']
    pdf_file = os.path.join("temp", pdf_file)
    
    display(IFrame(src=pdf_file, width='100%', height='700px'))
    
    pub_date = metadata.at[article, 'pub_date']
    objecttypes = metadata.at[article, 'objecttypes']
    objecttypes = objecttypes.split(';')
    
    txt_zip = metadata.at[article, 'txt_zip']
    txt_file = metadata.at[article, 'txt_file']
    
    txt_zip = os.path.join('TXT', txt_zip)
    
    with zipfile.ZipFile(txt_zip) as zf:
        with zf.open(txt_file) as f:
            text = f.read()
    
    print(f'Article ID: {article} \t Published: {pub_date}')
    print('Object Types:\t', ', '.join(objecttypes))
    
    
#     print('Article text:', '\n\n', text, '\n')
    if callable(linked_function):
        linked_function(article)
    elif linked_function == None:
        foo = input("Press enter to display next article.")
    else:
        raise TypeError('linked_function is not a valid function.')
        
    
    clear_output()
    
# Next step is to introduce the choice to save and end or save and continue.

def save_results(save_function):
    if callable(save_function):
        save_function()
        save_indicator = 1
    elif save_function == None:
        save_indicator = 0
    else:
        raise TypeError("save_function is not a valid function")
    
    if save_indicator == 1:
        print('changes saved!')
    else:
        print('no save function detected; changes not saved.')
    


def display_article_chunk(request_list, chunk_number, chunk_size, linked_function, save_function):
    global metadata
       
    number_of_chunks = len(request_list)//chunk_size + (len(request_list) % chunk_size > 0)
    
    n = 0
    save_indicator = 0

    if len(request_list) >= chunk_size*chunk_number+1:
        this_chunk = request_list[chunk_size*chunk_number:chunk_size*(chunk_number+1)]
    else:
        this_chunk = request_list[chunk_size*chunk_number:]

    for article in this_chunk:
        n+=1
        print(f"Here's article {n} of {len(this_chunk)}, in set {chunk_number+1} of {number_of_chunks}:")
        display_article(article, linked_function)
        
    save_results(save_function)
    
def display_requested_articles(display_list=None, linked_function=None, save_function=None, archive_location='.', chunk_size=15):
    if 'metadata' not in globals():
        global metadata
        metadata = load_metadata(archive_location)
        
    if display_list == None:
        request_list = request_input()
    elif callable(display_list):
        request_list = display_list()
    elif type(display_list) == list:
        request_list = display_list
    
    if type(request_list) != list:
        raise TypeError('Please make sure display_list is either a list of IDs or a function returning a list of article IDs.')
    
    request_list = sanitize(request_list)
    
    unpack_pdfs(archive_location, request_list)
    
    number_of_chunks = len(request_list)//chunk_size + (len(request_list) % chunk_size > 0)
    
    global continue_indicator
    
    continue_indicator = 1
    
    for chunk_number in range(number_of_chunks):
        if int(continue_indicator) == 1:
            display_article_chunk(request_list, chunk_number, chunk_size, linked_function, save_function)
            if chunk_number + 1 != number_of_chunks:
                continue_indicator = ask_whether_to_continue()
            if chunk_number + 1 == number_of_chunks:
                print("All requested articles displayed!")
        elif int(continue_indicator) == 0:
            pass
               
    empty(os.path.join(archive_location, "temp"))

def ask_whether_to_continue():
    continue_indicator = input('Enter 1 to continue, or 0 to exit:')
    while continue_indicator not in set(['1', '0']):
        continue_indicator = input('Enter 1 to continue, or 0 to exit:')
    return continue_indicator

# Import Data Index

def load_metadata(archive_location='.'):
    print('Loading metadata...')
    with zipfile.ZipFile(os.path.join(archive_location, 'TOI_metadata.zip')) as zf:
        with zf.open('TOI_metadata.csv') as file:
            metadata = pd.read_csv(file, usecols=['record_id', 
                                                  'pub_date', 
                                                  'txt_zip', 
                                                  'txt_file',
                                                  'pdf_zip',
                                                  'pdf_file',
                                                  'objecttypes'], dtype='object').set_index('record_id')

    print('done \n')
    return metadata