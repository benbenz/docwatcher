import argparse
import easyocr.easyocr as easyocr
import numpy
from io import BytesIO


def nullable_string(val):
    if not val:
        return None
    return val

parser = argparse.ArgumentParser(prog = 'ProcessOCR',description = 'process document with ocr')
parser.add_argument('img_path')
args = parser.parse_args()

ocr_reader  = easyocr.Reader(['fr']) 
result      = ocr_reader.readtext(args.img_path)
bytes_out   = BytesIO()
numpy.save(bytes_out,result,allow_pickle=False)
#print(bytes_out.getvalue())
print("RESULT=",bytes_out.getvalue())