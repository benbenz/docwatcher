import argparse
from docspider.handlers import AllInOneHandler

def nullable_string(val):
    if not val:
        return None
    return val

parser = argparse.ArgumentParser(prog = 'ProcessOCR',description = 'process document with ocr')
parser.add_argument('directory',type=nullable_string)
parser.add_argument('subdirectory',type=nullable_string)
parser.add_argument('path')
parser.add_argument('page_count',type=int)
args = parser.parse_args()

print(args)

handler = AllInOneHandler(args.directory,args.subdirectory)