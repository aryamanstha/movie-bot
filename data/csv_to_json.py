import pandas as pd
import json

data=pd.read_csv('imdb.csv')

json_data = data.to_json('imdb.json',orient='records',indent=4)


