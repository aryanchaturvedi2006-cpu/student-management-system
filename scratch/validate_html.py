from html.parser import HTMLParser
import re

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.void_elements = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        if tag not in self.void_elements:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack:
            if self.stack[-1] == tag:
                self.stack.pop()
            else:
                print(f"Mismatched end tag at line {self.getpos()[0]}: </{tag}>. Expected: </{self.stack[-1]}>")
                if tag in self.stack:
                    while self.stack[-1] != tag:
                        self.stack.pop()
                    self.stack.pop()
        else:
            print(f"Extra end tag at line {self.getpos()[0]}: </{tag}>")

parser = MyHTMLParser()
with open(r'c:\Users\DELL\Desktop\projects\student-management\templates\index.html', 'r', encoding='utf-8') as f:
    content = f.read()
    
    parser.feed(content)
    if parser.stack:
        print("Unclosed tags:", parser.stack)
    else:
        print("All tags matched perfectly.")
