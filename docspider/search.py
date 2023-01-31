from docspider.searchers import DocumentSearcher
import json

def perform_search():

    searcher = DocumentSearcher()
    
    with open('config.json','r') as jsonfile:
        cfg = json.load(jsonfile)
    
    for search in cfg.get('searches') or []:
        search_obj = searcher.get_search(search)
        if not search_obj:
            search_obj = searcher.save_search(search)

        if not search_obj:
            continue

        old_ids = set()
        new_ids = set()
        for doc in search_obj.hits.all():
            old_ids.add(doc.id)

        results = searcher.perform_search(search_obj)
        for doc in results:
            new_ids.add(doc.id)

        if old_ids == new_ids:
            print("list is the same")
        else:
            print("list has changed")


if __name__ == '__main__':
    perform_search()


        
        