from docspider.handlers import AllInOneHandler
import json
from docs.models import Document

output_dir = "download"

def perform_ocr():

    handler = AllInOneHandler(directory=output_dir, subdirectory=None)

    if not handler.using_ocr:
        print("Not using OCR >> exiting")
        return

    # we only perform OCR on PDF for now
    for doc in handler.get_documents(doc_types=[Document.DocumentType.PDF],for_ocr=True):
        # re-perform OCR 
        handler.update_document(doc)


if __name__ == '__main__':
    perform_ocr()


        
        