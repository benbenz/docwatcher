import argparse
import easyocr.easyocr as easyocr
import numpy
import json

parser = argparse.ArgumentParser(prog = 'ProcessOCR',description = 'process document with ocr')
parser.add_argument('img_path')
args = parser.parse_args()

ocr_reader  = easyocr.Reader(['fr']) 
result      = ocr_reader.readtext(args.img_path)
json_result = []
for position,text,proba in result:
    json_result.append({'text':str(text),'proba':float(proba)})
print("RESULT="+json.dumps(json_result).encode())
