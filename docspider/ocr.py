import argparse
from docspider.handlers import AllInOneHandler

parser = argparse.ArgumentParser(prog = 'ProcessOCR',description = 'process document with ocr')
parser.add_argument('directory',default=None, type=str)
parser.add_argument('subdirectory',default=None, type=str)
parser.add_argument('path')
parser.add_argument('page_count',type=int)
args = parser.parse_args()

print(args)

handler = AllInOneHandler(args.directory,args.subdirectory)