import requests
import json
import pandas as pd
from tqdm import tqdm

######Global Params#######
graph_url = 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2'

col_data_types = {'amount0': float, 'amount1': float, 'logIndex': int, 'liquidity': float,
                  'amount0In': float, 'amount0Out': float, 'amount1In': float, 'amount1Out': float}
#########################

def process_query(query, data_field, graph_url):
    """
    Helper function to take a query and retrieve the data.
    query (str): The query to be executed
    data_field (str): The data field to be pulled out
    graph_url (str): The url of the subgraph
    """
    
    #Make the request
    request = requests.post(graph_url, json={'query': query})
    
    #Pull the json out from the text
    data = json.loads(request.text)
    
    #Pull out the relevant data field
    data = data['data'][data_field]
    
    return data

def convert_where_clause(clause):
    out = "{"
    for key in clause.keys():
        out += "{}: ".format(key)
        out += '"{}"'.format(clause[key])
        out += ","
    out += "}"
    return out

def query_builder(main, fields,
                  where_clause=None, first=None, skip=None,
                 order_by=None, order_direction=None):
    """
    main (str): The main query that is being run
    fields (list[str]): A list of strings representing each field we want to pull
    where_clause (dict): A dictionary of clauses for filtering with the where statement
    first (int): Number of records to grab (maximum 1000)
    skip (int): Number of records to skip (maximum 5000)
    order_by (str): Field to order by
    order_direction (str): The direction of ordering for the field
    """
    #Convert the where clause
    where_clause = convert_where_clause(where_clause)
    
    #Clauses for the main function
    main_clauses = []
    if first:
        main_clauses.append("first: {}".format(first))
    if skip:
        main_clauses.append("skip: {}".format(skip))
    if order_by:
        main_clauses.append("orderBy: {}".format(order_by))
    if order_direction:
        main_clauses.append("orderDirection: {}".format(order_direction))
    if where_clause:
        main_clauses.append("where: {}".format(where_clause))
    
    #Convert clauses to a string
    main_clauses = ", ".join(main_clauses)
    
    #Convert fields to a string
    fields = ", ".join(fields)
    
    


    query = """query{{
    {}({}){{
    {}
    }}
    }}""".format(main, main_clauses, fields)
    return query

def pull_data(query_function, field):
    """
    Function to pull 6000 rows of data
    """
    
    #Iterate over the chunks
    data = []
    for i in tqdm(range(0, 6000, 1000)):
        #Build query
        query = query_function(i)
        
        #Extract data
        data.extend(process_query(query, field, graph_url))
        
    #Convert to dataframe
    data = pd.DataFrame(data)
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit = 's')
    data['event'] = field
    
    #Create mapping of column data types
    cdt = {}
    for col in data.columns:
        if col in col_data_types.keys():
            cdt[col] = col_data_types[col]
            
    #Map the data types
    data = data.astype(cdt)
    
    return data



def find_data_overlap(data):
    """
    Function to find the earliest date that ensures data overlap.
    """
    return max([df['timestamp'].min() for df in data])

def process_amount(df):
    if df['event'].iloc[0] == 'mints':
        pass
    elif df['event'].iloc[0] == 'burns':
        df[['amount0', 'amount1', 'liquidity']] *= -1
    elif df['event'].iloc[0] == 'swaps':
        df['amount0'] = df['amount0Out'] - df['amount0In']
        df['amount1'] = df['amount1Out'] - df['amount1In']
        df['liquidity'] = 0
        df.drop(columns=['amount0Out', 'amount0In', 'amount1Out', 'amount1In'], inplace=True)
        
def process_events(df):
    if df['event'].iloc[0] == 'mints':
        df['event'] = 'mint'
    elif df['event'].iloc[0] == 'burns':
        df['event'] = 'burn'
    elif df['event'].iloc[0] == 'swaps':
        df['event'] = (df['amount0'] > 0).map({True: 'ethPurchase', False: 'tokenPurchase'})

def process_data(data, lim_date=False):
    #Do all data processing
    for df in data:
        process_amount(df)
        process_events(df)
    
    #Consider only overlapping data
    if lim_date:
        overlap_date = find_data_overlap(data)
        data = [df[df['timestamp'] >= overlap_date] for df in data]
    
    #Concat
    data = pd.concat(data)
    
    #Rename columns
    data = data.rename(columns={'amount0': 'token_delta', 'amount1': 'eth_delta', 'liquidity': 'UNI_delta'})
    
    #Indexing
    data = data.sort_values(['timestamp', 'logIndex'])
    data.reset_index(inplace = True, drop = True)
    
    #Find balances over time
    for col1, col2 in zip(['token_balance', 'eth_balance', 'UNI_supply'], ['token_delta', 'eth_delta', 'UNI_delta']):
        data[col1] = data[col2].cumsum()
    
    print("TODO: ADD IN GENESIS STATE")
    
    return data

def create_data():
    mint_query = lambda i: query_builder("mints",
                      ["timestamp", "amount0", "amount1", "logIndex", "liquidity"],
                     first=1000, skip=i, order_by="timestamp", order_direction="desc",
                             where_clause={"pair": "0x8ae720a71622e824f576b4a8c03031066548a3b1"})
    
    burns_query = lambda i: query_builder("burns",
                      ["timestamp", "amount0", "amount1", "logIndex", "liquidity"],
                     first=1000, skip=i, order_by="timestamp", order_direction="desc",
                             where_clause={"pair": "0x8ae720a71622e824f576b4a8c03031066548a3b1"})
    
    swaps_query = lambda i: query_builder("swaps",
                      ["timestamp", "amount0In", "amount1In", "amount0Out", "amount1Out","logIndex"],
                     first=1000, skip=i, order_by="timestamp", order_direction="desc",
                             where_clause={"pair": "0x8ae720a71622e824f576b4a8c03031066548a3b1"})
    
    queries = [mint_query, burns_query, swaps_query]
    fields = ["mints", "burns", "swaps"]
    data = [pull_data(q, f) for q, f in zip(queries, fields)]
    data = process_data(data, lim_date=True)
    return data