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
numpy.save(bytes_out,result,allow_pickle=True)
#print(bytes_out.getvalue())
print("RESULT=")
print(bytes_out.getbuffer().decode('latin-1')) # NUMPY v1 or v2 are in latin-1
print("/RESULT")