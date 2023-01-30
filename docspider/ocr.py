import argparse
import json
import easyocr.easyocr as easyocr

def nullable_string(val):
    if not val:
        return None
    return val

parser = argparse.ArgumentParser(prog = 'ProcessOCR',description = 'process document with ocr')
parser.add_argument('img_path')
args = parser.parse_args()

ocr_reader = easyocr.Reader(['fr']) 
result     = ocr_reader.readtext(args.img_path)

print(json.dumps(result))


