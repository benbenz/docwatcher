from docspider.handlers import AllInOneHandler
import json
from docs.models import Document
import signal
import argparse
from datetime import datetime, timedelta
import logging
import os
logger = logging.getLogger("DocCrawler")


output_dir = "download"

handler = AllInOneHandler(directory=output_dir, subdirectory=None)

ids_in_process    = list()
blacklistfilename = 'ocr-blacklist.json'
blacklist         = list()

def perform_ocr(expiration):
    global blacklist
    if os.path.isfile(blacklistfilename):
        try:
            with open(blacklistfilename,'r') as f:
                blacklist = json.load(f)
        except:
            pass

    if expiration is not None:
        time0            = datetime.now()
        expiration_delta = timedelta(minutes=expiration)
    else:
        time0 = expiration_delta = None

    logger.setLevel(logging.DEBUG)
    for h in logger.handlers:
        h.setLevel(logging.DEBUG)

    if not handler.using_ocr:
        print("Not using OCR >> exiting")
        return

    docs = handler.get_documents(doc_types=[Document.DocumentType.PDF],for_ocr=True)
    num = docs.count()

    # we only perform OCR on PDF for now
    i = 1 
    for doc in docs:
        if doc.id in blacklist:
            continue
        ids_in_process.append(doc.id)
        if time0 is not None:
            datetime_now = datetime.today()
            if datetime_now - time0 > expiration_delta:
                logger.warning("Exiting due to expiration")
                return
        print("document {0}/{1}".format(i,num))
        # re-perform OCR 
        handler.update_document(doc)
        i+=1


def exit_gracefully(signum,frame):
    logger.warning("RECEIVED SIGNAL {0}".format(signum))
    signame = signal.Signals(signum).name
    logger.info(f'exit_gracefully() called with signal {signame} ({signum})')  
    # we could only process one document ... let's discard this one for now ...
    if len(ids_in_process)==1:
        blacklist.append(ids_in_process[0])
        try:
            with open(blacklistfilename,'w') as f:
                json.dump(blacklist,f)
        except:
            pass
    handler.stop()

if __name__ == '__main__':

    signal.signal(signal.SIGINT , exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)   

    parser = argparse.ArgumentParser(prog = 'DocWatcher OCR',description = 'Perform OCR on documents',epilog = '=)')
    parser.add_argument('-e','--expiration',type=int,help="Add an expiration time to the runtime")
    args = parser.parse_args()    

    perform_ocr(args.expiration)


        
        