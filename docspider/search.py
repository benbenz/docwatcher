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
            old_ids.add(doc.pk)

        results = searcher.perform_search(search_obj)
        print("search done for {0}: {1} result(s)".format(search_obj.params,results.count()))        
        for doc in results:
            new_ids.add(doc.pk)

        print(old_ids,new_ids)

        if old_ids == new_ids:
            print("results for {0} are the same".format(search_obj.params))
        else:
            print("results for {0} have changed".format(search_obj.params))
            hits_add = new_ids.difference(old_ids)
            hits_rmv = old_ids.difference(new_ids)
            print(hits_add,hits_rmv)
            for ha in hits_add:
                search_obj.hits.add(ha)
            for hr in hits_rmv:
                search_obj.hits.remove(hr)
            search_obj.save()


if __name__ == '__main__':
    perform_search()


        
        