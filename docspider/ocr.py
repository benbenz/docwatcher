import argparse
import json
import easyocr.easyocr as easyocr
import numpy as np

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        # elif isinstance(item, tuple):
        #     return {'__tuple__': True, 'items': item}
        # elif isinstance(item, list):
        #     return [hint_tuples(e) for e in item]
        # elif isinstance(item, dict):
        #     return {key: hint_tuples(value) for key, value in item.items()}
        return super(NpEncoder, self).default(obj)

def nullable_string(val):
    if not val:
        return None
    return val

parser = argparse.ArgumentParser(prog = 'ProcessOCR',description = 'process document with ocr')
parser.add_argument('img_path')
args = parser.parse_args()

ocr_reader  = easyocr.Reader(['fr']) 
result      = ocr_reader.readtext(args.img_path)
json_result = []
for position , text , proba in result:
    json_result.append({
        'proba' : proba,
        'position' : position ,
        'text' : text
    })
print("RESULT="+json.dumps({'result':json_result},cls=NpEncoder))


