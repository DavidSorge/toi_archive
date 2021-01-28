import os
from zipfile import ZipFile
import subprocess
import pandas as pd
import regex as re
import string
from IPython.display import clear_output, IFrame, display
from urllib.parse import quote
from pathlib import Path
from textwrap import wrap

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


def get_display_list(request_list, output_csv):
    """
    This function takes an input csv,
    an output csv, and outputs a list of articles
    in the input list but not in the output list
    """
    out = Path(output_csv)

    if out.exists():
        completed_articles = [str(x) for x in list(pd.read_csv(out,
                                                               index_col=0)
                                                   .index)]
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
        print('No valid article IDs Recognized!')
    return(wanted_articles)


def unpack_pdfs(request_list):
    print("Unpacking requested pdfs...")

    global TOI_METADATA

    df = TOI_METADATA.loc[request_list]

    basepath = Path(__file__).parent.resolve()

    zips_to_open = (df[df.pdf_zip.notnull()]
                    .pdf_zip
                    .unique()
                    .tolist())

    for zip_file in zips_to_open:

        files_to_extract = (df[df['pdf_zip'] == zip_file]
                            .pdf_file
                            .unique()
                            .tolist())

        zip_path = basepath / 'PDF' / zip_file

        with ZipFile(zip_path) as zf:
            for file in files_to_extract:
                zf.extract(file, path=(basepath / "temp"))

    print("Done!")


def display_article(article, input_function):
    """
    Displays the pdf version of a requested article in a notebook's IFrame
    """
    global TOI_METADATA

    # For some reason I don't quite understand, resolving the symlink
    # causes the IFrame to fail to find the pdf files. Very strange.
    # Particularly weirdly, using the symlink works,
    # while avoiding the symlink fails. (I would have expected
    # the opposite behavior)

    basepath = Path(os.path.dirname(__file__))

    if type(TOI_METADATA.at[article, 'pdf_file']) == str:

        pdf_file = TOI_METADATA.at[article, 'pdf_file']
        pdf_file = basepath / "temp" / pdf_file

        rel_path = os.path.relpath(pdf_file)

        display(IFrame(src=rel_path, width='100%', height='700px'))

    else:
        print("No pdf file found in archive, displaying txt instead:")
        ziparchive = TOI_METADATA.at[article, 'txt_zip']
        txt_file = TOI_METADATA.at[article, 'txt_file']

        with ZipFile(basepath / 'TXT' / ziparchive) as zf:
            text = zf.read(txt_file)

        print(text)

    pub_date = TOI_METADATA.at[article, 'pub_date']
    objecttypes = TOI_METADATA.at[article, 'objecttypes']
    objecttypes = objecttypes.split(';')

    try:
        print(f'Article ID: {article} \t Published {pub_date:%A, %B %d, %Y}')
        print('Object Types:\t', ', '.join(objecttypes))
    except NameError:
        pass

    if callable(input_function):
        feedback = input_function()
    elif input_function is None:
        feedback = input("Press enter to display next article.")
    else:
        raise TypeError('input_function is not a valid function.')

    clear_output()

    return feedback


def binary_input(message=None):

    response = ''

    instructions = [str(message or ''),
                    'For yes, enter y. (t, a, or 1 also acceptable)',
                    'For no,  enter n. (f, z or 0 also acceptable).\n']

    while type(response) != bool:
        # Request input
        response = input('\n'.join(instructions))

        # Handle input
        if response in ['y', 't', 'a', '1']:
            response = True
        elif response in ['n', 'f', 'z', '0']:
            response = False
        else:
            print("I'm not sure how to interpret that.")

    return response


def save_results(output_dict, save_location):
    """
    Saves a CSV with article index and a copy of user input.
    """
    df = pd.DataFrame.from_dict(output_dict,
                                orient='index',
                                columns=['human_input'])

    df.to_csv(save_location)

    print("Progress saved.")


def display_article_chunk(request_list,
                          chunk_number,
                          chunk_size,
                          input_function,
                          output_dict,
                          save_location):
    global TOI_METADATA

    number_of_chunks = (len(request_list)//chunk_size
                        + (len(request_list) % chunk_size > 0))

    n = 0

    if len(request_list) >= chunk_size*chunk_number+1:
        this_chunk = request_list[chunk_size*chunk_number:
                                  chunk_size*(chunk_number+1)]
    else:
        this_chunk = request_list[chunk_size*chunk_number:]

    for article in this_chunk:
        n += 1

        a = len(this_chunk)
        b = chunk_number+1
        c = number_of_chunks

        print(f"Here's article {n} of {a}, in set {b} of {c}:")
        feedback = display_article(article, input_function)
        output_dict.update({article: feedback})
        save_results(output_dict, save_location)

    return output_dict


def sort_chronological(article_list):
    TOI_METADATA = load_metadata()
    arts = [int(art) for art in article_list]
    return (TOI_METADATA.loc[arts, :]
                        .sort_values('start_page')
                        .sort_values('pub_date')
                        .index
                        .to_list())


def sort_reverse_chronological(article_list):
    TOI_METADATA = load_metadata()
    arts = [int(art) for art in article_list]
    return (TOI_METADATA.loc[arts, :]
                        .sort_values('start_page')
                        .sort_values('pub_date', ascending=False)
                        .index
                        .to_list())


def display_requested_articles(display_list=None,
                               input_function=None,
                               chunk_size=15,
                               append_mode=True,
                               display_order='chronological',
                               save_location='article_output.csv',
                               output=False):
    global TOI_METADATA

    TOI_METADATA = load_metadata()

    # if no display_list given, prompt for display_list.
    if display_list is None:
        request_list = request_input()
    else:
        request_list = display_list

    # check and make sure that the listed ids are valid article ids.

    if append_mode:
        request_list = sanitize(get_display_list(request_list,
                                                 output_csv=save_location))
    else:
        request_list = sanitize(request_list)

    if len(request_list) == 0:
        return

    # unzip the pdfs into temp folder for display
    unpack_pdfs(request_list)

    # Set up periodic option to discontinue, and output_dict
    global continue_indicator
    continue_indicator = 1

    if Path(save_location).exists():
        old = pd.read_csv(save_location, index_col=0)
        output_dict = old.human_input.to_dict()
    else:
        output_dict = {}

    # sort presentation order for articles in request_list

    if display_order == 'chronological':
        request_list = sort_chronological(request_list)
    elif display_order == 'reverse':
        request_list = sort_reverse_chronological(request_list)

    # Calculate number of chunks, based on chunk_size and request_list
    number_of_chunks = (len(request_list) // chunk_size +
                        int(len(request_list) % chunk_size > 0))

    for chunk_number in range(number_of_chunks):
        if int(continue_indicator) == 1:
            output_dict = display_article_chunk(request_list,
                                                chunk_number,
                                                chunk_size,
                                                input_function,
                                                output_dict,
                                                save_location)
            if chunk_number + 1 != number_of_chunks:
                continue_indicator = \
                    int(binary_input('Would you like to continue?'))

            elif chunk_number + 1 == number_of_chunks:
                print("All requested articles displayed!")
        elif int(continue_indicator) == 0:
            pass

    basepath = Path(__file__).parent.resolve()

    empty(basepath / "temp")

    if output:
        return output_dict


def load_metadata():
    if 'TOI_METADATA' not in globals():
        global TOI_METADATA

        print('Loading TOI metadata...')
        df_list = []

        basepath = Path(__file__).parent.resolve()

        with ZipFile(basepath / 'TOI_metadata.zip') as zf:
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


def read_text(zipfile_object, fn):
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
                  title     = {Bidirectional Recurrent Neural Network with
                               Attention Mechanism for Punctuation
                               Restoration},
                  booktitle = {Interspeech 2016},
                  year      = {2016}
                  }
    """
    text = text.translate(str.maketrans('', '', string.punctuation))
    texts = wrap(text, 15000)

    punc_text = ""
    for text in texts:
        proc = subprocess.Popen(["curl",
                                 "-d",
                                 f"text={quote(text)}",
                                 "http://bark.phon.ioc.ee/punctuator"],
                                stdout=subprocess.PIPE)
        out = proc.communicate()[0]
        punc_text = punc_text + (out.decode("utf-8"))

    return punc_text


def get_text_df(request_list):
    TOI_METADATA = load_metadata()

    print("Reading in article contents")

    if type(request_list) != list:
        raise TypeError('Please make sure display_list is a list of IDs.')

    request_list = sanitize(request_list)

    working_set = TOI_METADATA.loc[request_list]

    article_texts = pd.Series(dtype='object')

    for zip_file in tqdm(working_set.txt_zip.unique()):

        basepath = Path(__file__).parent.resolve()

        path = basepath / 'TXT' / zip_file
        files = working_set[working_set.txt_zip == zip_file]

        with ZipFile(path) as z:
            text_series = files.txt_file.apply(lambda x: read_text(z, x))
            article_texts = article_texts.append(text_series)

    print('Done')

    return pd.DataFrame({"article_text": article_texts})


def drop_by_objecttype(metadata,
                       news=True,
                       opinion=False,
                       images=False,
                       life_transitions=False,
                       notices=False,
                       ads=False,
                       toc=False,
                       other=True):

    print('Filtering out non-news articles by type')
    before = len(metadata)

    # Drop based on object type

    objecttypes = {'news': ['feature;article',
                            'news',
                            'news;military/war news',
                            'general information',
                            'front page/cover story',
                            'article;feature',
                            'military/war news;news'],
                   'opinion': ['editorial;commentary',
                               'commentary;editorial',
                               'letter to the editor;correspondence',
                               'correspondence;letter to the editor',
                               'review'],
                   'images': ['image/photograph',
                              'illustration',
                              'editorial cartoon/comic'],
                   'life_transitions': ['obituary',
                                        'birth notice',
                                        'news;marriage announcement',
                                        'marriage announcement;news'],
                   'notices': ['stock quote',
                               'credit/acknowledgement',
                               'news;legal notice'],
                   'ads': ['classified advertisement;advertisement',
                           'advertisement',
                           'advertisement;classified advertisement'],
                   'toc': ['table of contents;front matter',
                           'front matter;table of contents'],
                   'other': ['undefined']}

    wanted = []
    if news:
        wanted.extend(objecttypes['news'])

    if opinion:
        wanted.extend(objecttypes['opinion'])

    if images:
        wanted.extend(objecttypes['images'])

    if life_transitions:
        wanted.extend(objecttypes['life_transitions'])

    if notices:
        wanted.extend(objecttypes['notices'])

    if ads:
        wanted.extend(objecttypes['ads'])

    if toc:
        wanted.extend(objecttypes['toc'])

    if other:
        wanted.extend(objecttypes['other'])

    if len(wanted) == 0:
        print("No records trimmed based on objecttype.")
        return metadata

    metadata = metadata[metadata.objecttypes.isin(wanted)]

    trimmed = before - len(metadata)
    print(f"{trimmed:n} records trimmed. {len(metadata):n} records remain.")

    return metadata


def drop_by_note(metadata):
    print('Filtering out articles with no text')
    before = len(metadata)

    # Drop if article has no text
    # (the 'note' column is either null, or contains the string 'No text')

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
    For a list of articles, creates a dataframe containing the article id,
    text,and punctuated text. Saves this dataframe as a CSV file.
    """

    if Path(save_as).exists():

        print('Loading text dataframe...')
        texts = pd.read_csv(save_as, index_col=0)
        print('Done!')
        return texts

    else:

        # Reading in article texts:
        print("Reading in article text...")
        texts = get_text_df(article_list)

        # Punctuating the article texts:
        print("Inferring text punctuation...")
        texts['punctuated_text'] = texts.article_text.progress_apply(punctuate)

        # Saving, because this is really time-consuming
        print("Saving texts...")
        texts.to_csv(save_as)

        print('Done!')
        return texts


def empty(pth):
    """
    Deletes all files, directories, or links in a folder.
    """
    pth = Path(pth)
    for child in pth.glob('*'):
        if child.is_file():
            child.unlink()
        else:
            empty(child)
    pth.rmdir()
