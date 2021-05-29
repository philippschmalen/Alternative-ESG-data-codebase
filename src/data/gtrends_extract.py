"""
Extract data from Google trends with the pytrends package

methods take one keyword, call pytrends and return raw data 

"""

import pandas as pd
import logging
import os
from datetime import datetime
from pytrends.request import TrendReq



def create_pytrends_session():
    """Create pytrends TrendReq() session on which .build_payload() can be called """
    pytrends_session = TrendReq() 

    return pytrends_session

# ----------------------------------------------------------
# Google trends: related queries
# ----------------------------------------------------------

def get_related_queries(pytrends_session, keyword_list, cat=0, geo=''):
    """Returns a dictionary with a dataframe for each keyword 
    Calls pytrend's related_queries()
    
    Args:
        pytrends_session (object): TrendReq() session of pytrend
        keyword_list (list): Used as input for query and passed to TrendReq().build_payload() 
        cat (int): see https://github.com/pat310/google-trends-api/wiki/Google-Trends-Categories
        geo (str): Geolocation like US, UK

    Returns:
        Dictionary: Dict with dataframes with related query results 
    """    
    assert isinstance(keyword_list, list), f"keyword_list should be string. Instead of type {type(keyword_list)}"

    df_related_queries = pd.DataFrame()

    try:
        pytrends_session.build_payload(keyword_list, cat=cat, geo=geo)
        df_related_queries = pytrends_session.related_queries()
        logging.info(f"Query succeeded for {*keyword_list ,}")

    except Exception as e:
        logging.error(f"Query not unsuccessful due to {e}. Return empty DataFrame.")

    return df_related_queries

def process_related_query_response(response, kw, geo, ranking):
    """ Helper function for unpack_related_queries_response() """
    try:
        df = response[kw][ranking]
        df[['keyword', 'ranking', 'geo', 'query_timestamp']] = [
            kw, ranking, geo, datetime.now()]
    except:
        logging.info(f"Append empty dataframe for {ranking}: {kw}")
        return pd.DataFrame(columns=['query', 'value', 'keyword', 'ranking', 'geo', 'query_timestamp'])

    return df

def unpack_related_queries_response(response):
    """Unpack response from dictionary and create one dataframe for each ranking and each keyword """
    assert isinstance(response, dict), "Empty response. Try again."

    ranking = [*response[[*response][0]]]
    keywords = [*response]

    return response, ranking, keywords

def create_related_queries_dataframe(response, rankings, keywords, geo_description='global'):
    """Returns a single dataframe of related queries for a list of keywords
    and each ranking (either 'top' or 'rising')
    """
    df_list = []
    for r in rankings:
        for kw in keywords:
            df_list.append(process_related_query_response(
                response, kw=kw, ranking=r, geo=geo_description))

    return pd.concat(df_list)

def get_related_queries_pipeline(pytrends_session, keyword_list, cat=0, geo='', geo_description='global'): 
    """Returns all response data for pytrend's .related_queries() in a single dataframe
    
    Example usage:

        pytrends_session = create_pytrends_session()
        df = get_related_queries_pipeline(pytrends_session, keyword_list=['pizza', 'lufthansa'])
    """
    response = get_related_queries(pytrends_session=pytrends_session, keyword_list=keyword_list, cat=cat, geo=geo) # 
    response, rankings, keywords  = unpack_related_queries_response(response=response)
    df_trends = create_related_queries_dataframe(
        response=response, 
        rankings=rankings, 
        keywords=keywords, 
        geo_description=geo_description)
    
    return df_trends




# ----------------------------------------------------------
# Google trends: Interest over time
# ----------------------------------------------------------


import os
import sys
from time import sleep
from random import randint 

def handle_query_results(df_query_result, keywords, date_index=None, query_length=261):
    """Process query results: 
            (i) check for empty response --> create df with 0s if empty
            (ii) drop isPartial rows and column
            (iii) transpose dataframe to wide format (keywords//search interest)

    Args:
        df_query_result (pd.DataFrame): dataframe containing query result (could be empty)
        date_index (pd.Series): series with date form a basic query to construct df for empty reponses 
        
    Returns:
        Dataframe: contains query results in long format 
        (rows: keywords, columns: search interest over time)
    """
    # non-empty df
    if df_query_result.shape[0] != 0:
        # reset_index to preserve date information, drop isPartial column
        df_query_result_processed = df_query_result.reset_index()\
            .drop(['isPartial'], axis=1)

        df_query_result_long = pd.melt(df_query_result_processed, id_vars=['date'], var_name='keyword', value_name='search_interest')

        # long format (date, keyword, search interest)
        return df_query_result_long

    # empty df: no search result for any keyword
    else:        
        # create empty df with 0s
        query_length = len(date_index) if date_index is not None else query_length

        df_zeros = pd.DataFrame(np.zeros((query_length*len(keywords), 3)), columns=['date','keyword', 'search_interest'])
        # replace 0s with dates
        df_zeros['date'] = pd.concat([date_index for i in range(len(keywords))], axis=0).reset_index(drop=True) if date_index is not None else 0
        # replace 0s with keywords 
        df_zeros['keyword'] = np.repeat(keywords, query_length)


        return df_zeros



def query_googletrends(keywords, date_index=None, timeframe='today 5-y'):
    """Forward keywords to Google Trends API and process results into long format

    Args
        keywords: list of keywords, with maximum length 5

    Return
        DataFrame with search interest per keyword, preprocessed by handle_query_results()

    """
    # initialize pytrends
    pt = create_pytrends_session()

    # pass keywords to api
    pt.build_payload(kw_list=keywords, timeframe=timeframe) 

    # retrieve query results: search interest over time
    df_query_result_raw = pt.interest_over_time()

    # preprocess query results
    df_query_result_processed = handle_query_results(df_query_result_raw, keywords, date_index)

    return df_query_result_processed


def get_query_date_index(timeframe='today 5-y'):
    """Queries Google trends to have a valid index for query results that returned an empty dataframe

    Returns:
        pd.Series: date index of Google trend's interest_over_time()
    """
    
    # init pytrends with query that ALWAYS works
    pt = create_pytrends_session()
    pt.build_payload(kw_list=['pizza', 'lufthansa'], timeframe=timeframe)
    df = pt.interest_over_time()

    # set date as column
    df = df.rename_axis('date').reset_index()


    return df.date

#---------------------------------------------------
# -- UTILITIES
# 
# list_flatten: flatten list
# n_batch: generator for n-sized list batches
# list_batch: get n-sized chunks from n_batch generator
# df_to_csv: write csv
# timestamp_now: get string  
# sleep_countdown(): countdown in console
# 
#---------------------------------------------------

def list_flatten(nested_list):
    """Flattens nested list"""
    return [element for sublist in nested_list for element in sublist]

def n_batch(lst, n=5):
    """Yield successive n-sized chunks from list lst
    
    Args
        lst: list 
        n: selected batch size
        
    Returns 
        List: lst divided into batches of len(lst)/n lists
    """
    
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def list_batch(lst, n=5):
    """"Divides a list into a list of lists with n-sized length"""
    return list(n_batch(lst=lst, n=n))


def df_to_csv(df, filepath):
    """Export df to CSV. If it exists already, append data."""
    # file does not exist --> write header
    if not os.path.isfile(f'{filepath}'):
        df.to_csv(f'{filepath}', index=False)
    # file exists --> append data without header
    else:
        df.to_csv(f'{filepath}', index=False, header=False, mode='a')

def timestamp_now():
    """Create timestamp string in format: yyyy/mm/dd-hh/mm/ss"""
    
    timestr = strftime("%Y%m%d-%H%M%S")
    timestamp = '{}'.format(timestr)  
    
    return timestamp

def sleep_countdown(duration, print_step=2):
    """Sleep for certain duration and print remaining time in steps of print_step
    
    Input
        duration: duration of timeout (int)
        print_step: steps to print countdown (int)

    Return 
        None
    """
    for i in range(duration,0,-print_step):
        sleep(print_step)
        sys.stdout.write(str(i-print_step)+' ')
        sys.stdout.flush()

#--------------------------------------------------- 
# main function
#---------------------------------------------------

def get_interest_over_time(keyword_list, filepath, filepath_unsuccessful, timeframe='today 5-y', max_retries=3, timeout=20):
    """  
    Args:
        TODO: add docs
        max_retries: number of maximum retries
    Returns:
        None: Writes dataframe to csv
    """
    # get basic date index for empty responses
    date_index = get_query_date_index(timeframe=timeframe)

    # keywords in batches of 5
    kw_batches = list_batch(lst=keyword_list, n=5)


    for kw_batch in kw_batches: 
        # retry until max_retries reached
        for attempt in range(max_retries): 

            # random int from range around timeout 
            timeout_randomized = randint(timeout-3,timeout+3)
            try:
                df = query_googletrends(kw_batch, date_index=date_index)
            
            # query unsuccessful
            except Exception as e:
                timeout += 3 # increase timetout to be safe
                sleep_countdown(timeout_randomized, print_step=2)
            

            # query was successful: store results, sleep 
            else:
                df_to_csv(df, filepath=filepath)
                sleep_countdown(timeout_randomized)
                break

        # max_retries reached: store index of unsuccessful query
        else:
            df_to_csv(pd.DataFrame(kw_batch), filepath=filepath_unsuccessful)
            logging.warning(f"{kw_batch} appended to unsuccessful_queries")
