import argparse
import easyocr.easyocr as easyocr
import numpy
import json
from PIL import Image


parser = argparse.ArgumentParser(prog = 'ProcessOCR',description = 'process document with ocr')
parser.add_argument('img_path')
args = parser.parse_args()

ocr_reader  = easyocr.Reader(['fr']) 
im0 = Image.open(args.img_name)
t_img_name = "t"+args.img_name+".png"
best_text  = None
best_proba = -1
for rotate in [-90,0,90] : # lets assume the document is not reversed....
    print("rotation",rotate)
    im1 = im0.rotate(rotate, Image.NEAREST, expand = 1)
    im1.save(t_img_name)
    try:
        result = ocr_reader.readtext(t_img_name)

        if not result:
            continue

        proba_total = 0
        text_total  = ''
        num = 0 
        for text , proba in result:
            if proba > 0.3:
                print("text={0} (proba={1})".format(text,proba))
                proba_total += proba
                found_extra_text = True
                text_total += text + '\n'
                num += 1
        if num>0:
            proba_total /= num
        proba_total *= len(text_total) # we gotta reward the fact we recognized more characters
        if proba_total > best_proba:
            best_proba = proba_total
            best_text  = text_total
    except Exception as e:
        print("Error while processing image",t_img_name,e)
        #traceback.print_exc()
json_result = dict()

try:
    os.remove(t_img_name)
except:
    pass

if best_text is not None:
    print("Found text:",best_text)
    json_result['best_text'] = best_text
str_dump = json.dumps(json_result)
hex_dump = str_dump.encode('utf-8').hex()
print("RESULT="+hex_dump)
