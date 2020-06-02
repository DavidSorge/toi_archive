# toi_archive

This is a container for the Times of India archive from ProQuest, with a utility module to ease lookup of toi articles. The underlying data is not posted online for copyright reasons.

The lookup utility is 'toidisplay.py'

## Load TOI metadata in one line

``` load_metadata(archive_location='.') ```

Arguments:

* archive_location: dtype = string. When loading the TOI metadata in any other folder, pass the name of the main toi_archive folder as archive_location

![Screenshot of load_metadata in action](.images/load_metadata.png)

## Display articles, tag them, and save the list of tags

![Screenshot of display_requested_articles in action](.images/display_requested_articles.png)


```
display_requested_articles(display_list=None, 
                           linked_function=None, 
                           save_function=None, 
                           archive_location='.', 
                           chunk_size=15)
```

Arguments:

* display_list: dtype = list/function/None. Takes a list of article IDs to display or a function generating a list of article IDs. If no list or function is passed, the program will prompt for manual entry, which can include multiple IDs using space, comma, or semicolon separators.

* linked_function: dtype = function. A function to be performed after every article is displayed. A tagging-like task was initially in view.

* save_function: dtype = function. A function to be performed after data entry, to save data to a preferred location.

* archive_location: dtype = string. When displaying articles in a notebook in any other folder, pass the name of the main toi_archive folder as archive_location

* chunk_size: dtype = int. The number of articles to display in each chunk. After every chunk, the save_function will be implemented, and the program will prompt to continue or quit.
