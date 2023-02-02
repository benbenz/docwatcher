from docspider.handlers import AllInOneHandler
import json
from docs.models import Document

output_dir = "download"

def perform_ocr():

    handler = AllInOneHandler(directory=output_dir, subdirectory=None)

    for doc in handler.get_documents(doc_types_exclude=[Document.DocumentType.HTML]):
        # re-perform OCR 
        handler.update_document(doc)


if __name__ == '__main__':
    perform_ocr()


        
        