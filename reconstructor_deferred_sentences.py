#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import base64
import html5lib
from lxml import etree
from xml.etree import ElementTree
import argparse
import mmh3

def get_sentence(standoff,document):
    """Returns the text string from the XHTML/XML document that is pointed by the standoff annotation

    Retrieves the original content from a XHTML/XML html5lib parsed document pointed by a standoff annotation
    """
    reconstructedsentence = []
    for wordstandoff in standoff.split(';'):    #Split by standoff separator ';'
        wordstandoffsegments = wordstandoff.split('+')  #Split by '+' in case of glued annotations
        for wordstandoffseg in wordstandoffsegments:
            if wordstandoffseg == "":
                continue
            wordstandoffparts = wordstandoffseg.split(':')  #Obtain path and length range/limits
            wordstandofflimits = wordstandoffparts[1].split('-')
            element = document.find(wordstandoffparts[0])   #Get lxml element from path
            if element.text is None:
                element.text = ""
            if int(wordstandofflimits[1]) < len(element.text):  #Search word in element.text or in children tail depending on the limits
                if wordstandoffseg == wordstandoffsegments[0]:  #Create new annotation or add to previous word reconstruction if glued annotation
                    reconstructedsentence.append(element.text[int(wordstandofflimits[0]):int(wordstandofflimits[1])+1])
                else:
                    reconstructedsentence[-1] = reconstructedsentence[-1] + element.text[int(wordstandofflimits[0]):int(wordstandofflimits[1])+1]
            else:
                tail = element.text
                for child in element:
                    if child.tail is not None:
                        tail = tail + child.tail
                    if len(tail) > int(wordstandofflimits[1]):
                        if wordstandoffseg == wordstandoffsegments[0]:
                            reconstructedsentence.append(tail[int(wordstandofflimits[0]):int(wordstandofflimits[1])+1])
                        else:
                            reconstructedsentence[-1] = reconstructedsentence[-1] + tail[int(wordstandofflimits[0]):int(wordstandofflimits[1])+1]
                        break
    return " ".join(reconstructedsentence)

parser = argparse.ArgumentParser(description='Given Bitextor DOCALG file with deferred segments (stdin) and a Bitextor crawl file (positional argument), returns reconstructed segments in DOCALG format (stdout)')
parser.add_argument('crawl_path', help='path of crawl file')
parser.add_argument('--tmx', dest='tmx', action='store_true')

args = parser.parse_args()


#Argument input: path of original Bitextor formatted crawl file
document_standoff = dict()
with open(args.crawl_path,'r') as reader:
    for line in reader:
        fields=line.split('\t')
        fields = list(map(str.strip, fields)) #Strip all elements
        #We use lxml treebuilder because of getelementpath function and iteration through elements
        document_standoff[fields[1]] = html5lib.parse(base64.b64decode(fields[0]),treebuilder="lxml",namespaceHTMLElements=False) #Store url:html5lib_tree for easy path search

#Input (stdin): Bitextor DOCALG file (deferred):
#url1 url2 deferred_clean_text1 deferred_clean_text2

#Output (stdout): Bitextor DOCALG file reconstructed:
#url1 url2 clean_text1 clean_text2
if args.tmx:
    tree = etree.parse(sys.stdin)
    root = tree.getroot()
    for tu in root.findall('body')[0]:
        for tuv in tu.findall('tuv'):
            url=""
            annotation=""
            checksum=""
            for prop in tuv.findall('prop'):
                if prop.attrib['type'] == "source-document":
                    url=prop.text
                elif prop.attrib['type'] == "deferred-seg":
                    annotation=prop.text
                elif prop.attrib['type'] == "checksum-seg":
                    checksum=prop.text
            tuv.findall('seg')[0].text = get_sentence(annotation,document_standoff[url])
            if str(mmh3.hash(tuv.findall('seg')[0].text)) != checksum:
                tuv.append(etree.Element('prop'))
                tuv[-1].attrib['type']='info'
                tuv[-1].text = "Reconstructed segment murmurhash checksum does not match"
    print(etree.tostring(root, pretty_print=True).decode())
else:
    for line in sys.stdin:
        fields = line.split('\t')
        fields = list(map(str.strip, fields))
        newfields = [fields[0],fields[1]]
        for pair in [(fields[2],fields[0]),(fields[4],fields[1])]:
            annotation,url = pair
            if annotation != "":
                newfields.append(get_sentence(annotation,document_standoff[url]))
            else:
                newfields.append("")
        newfields.append(fields[3])
        newfields.append(fields[5])
        if len(fields) > 6:
            newfields = newfields + fields[6:]
        print("\t".join(newfields))


