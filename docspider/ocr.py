import argparse
import easyocr.easyocr as easyocr
import numpy
from io import StringIO


def nullable_string(val):
    if not val:
        return None
    return val

parser = argparse.ArgumentParser(prog = 'ProcessOCR',description = 'process document with ocr')
parser.add_argument('img_path')
args = parser.parse_args()

ocr_reader  = easyocr.Reader(['fr']) 
result      = ocr_reader.readtext(args.img_path)
fileout     = StringIO()
numpy.save(fileout,result,allow_pickle=True)
#print(bytes_out.getvalue())
print("RESULT="+fileout.getvalue().decode())