from docspider.searchers import DocumentSearcher
import json

def perform_search():

    search_handler = DocSearchHandler()
    
    with open('config.json','r') as jsonfile:
        cfg = json.load(jsonfile)
    
    for search in cfg.get('searches') or []:
        search_obj = search_handler.get_search(search)
        if not search_obj:
            search_obj = search_handler.save_search(search)
        
        