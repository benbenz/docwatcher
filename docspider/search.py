from docspider.searchers import DocumentSearcher
import json
import logging
logger = logging.getLogger("DocCrawler")

def perform_search():

    searcher = DocumentSearcher()
    
    with open('config.json','r') as jsonfile:
        cfg = json.load(jsonfile)

    add_objs = dict()
    rmv_objs = dict()
    highlights = dict()
    
    for search in cfg.get('searches') or []:
        search_obj = searcher.get_search(search)
        if not search_obj:
            search_obj = searcher.save_search(search)

        if not search_obj:
            continue

        search_name = search_obj.params.get('name')
        
        old_ids = set()
        new_ids = set()
        for doc in search_obj.hits.all():
            old_ids.add(doc.pk)

        results = searcher.perform_search(search_obj)
        logger.info("search done for {0}: {1} result(s)".format(search_obj.params,results.count()))        
        highlights[search_name] = dict()
        for doc in results:
            docid = int(doc.pk)
            new_ids.add(docid) # not sure why QuerySearchResult returns IDs as strings...
            highlights[search_name][docid]=doc.highlighted['text'][0] if doc.highlighted and len(doc.highlighted.get('text',[]))>0 else None
        
        if old_ids == new_ids:
            logger.info("results are the same".format(search_obj.params))
        else:
            logger.info("results have changed".format(search_obj.params))
            hits_add = new_ids.difference(old_ids)
            hits_rmv = old_ids.difference(new_ids)
            add_objs[search_name] = set()
            rmv_objs[search_name] = set()
            for ha in hits_add:
                search_obj.hits.add(ha)
                add_objs[search_name].add(searcher.get_document(ha))
            for hr in hits_rmv:
                search_obj.hits.remove(hr)
                rmv_objs[search_name].add(searcher.get_document(hr))
            searcher.mark_of_interest(add_objs[search_name])
            search_obj.save()

    # compose the add/remove lists of objects
    searcher.mail(add_objs,rmv_objs,highlights)


if __name__ == '__main__':
    perform_search()


        
        