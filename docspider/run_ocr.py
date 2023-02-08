from docspider.handlers import AllInOneHandler
import json
from docs.models import Document

output_dir = "download"

def perform_ocr():

    handler = AllInOneHandler(directory=output_dir, subdirectory=None)

    if not handler.using_ocr:
        print("Not using OCR >> exiting")
        return

    docs = handler.get_documents(doc_types=[Document.DocumentType.PDF],for_ocr=True)
    num = docs.count()

    # we only perform OCR on PDF for now
    i = 1 
    for doc in docs:
        print("document {0}/{1}".format(i,num))
        # re-perform OCR 
        handler.update_document(doc)
        i+=1


if __name__ == '__main__':
    perform_ocr()


        
        