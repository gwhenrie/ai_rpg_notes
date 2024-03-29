#!/home/gwhenrie/Dropbox/Pathfinder/MafiaGame/.venv/bin/python3
from enum import Enum
import argparse
import os
import re

class Level(Enum):
    root=0
    level_1 = 1
    level_2 = 2
    level_3 = 3
    level_4 = 4
    level_5 = 5
    level_6 = 6

class Section:
    @property
    def level(self)->Level:
        return self._level

    @level.setter
    def level(self, value: Level):
        if not isinstance(value, Level):
            raise TypeError(f"level must be of type 'Level'")
        self._level = value

    @property 
    def title(self)->str:
        return self._title

    @title.setter
    def title(self, value:str):
        if not isinstance(value, str):
            raise TypeError('title must be a string.')
        self._title = value

    @property 
    def text(self)->str:
        return self._text 

    @text.setter
    def text(self, value:str):
        if not isinstance(value, str):
            raise TypeError('value must be a string.')
        self._text = value

    @property 
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        if value != None:
            if not isinstance(value, Section):
                raise TypeError('parent must be of type Section')
            self._parent = value
        else:
            self._parent = None

    @property 
    def children(self) -> list:
        return self._children

    def display(self, identify=False) -> str:
        level_indication = '\t'*self.level.value
        display_title = self.title if self.parent != None else ''
        identify = ''
        if self.parent != None:
            for i in range(len(self.parent.children)):
                if self.parent.children[i] == self:
                    identify = f"{i}| "
        text = f"{level_indication}{identify}{display_title}\n"
        return text

    def display_family(self, identify=False) -> str:
        text = self.display()
        for child in self.children:
            text += child.display_family(identify)
        return text

    def get_descendent(self, identity_string:str):
        identity_string = identity_string.replace(' ', '')
        identity = identity_string.split(',')
        current = int(identity[0])
        # Get the child item identified 
        try:
            item = self.children[current]
        except IndexError:
            raise ValueError(f"{self.display} does not have child {current}")
        if len(identity) == 1:
            return item
        else:
            # Create new identity_string 
            return self.children[current].get_descendent(','.join(identity[1:]))

    def markdown(self) -> str:
        level_indication = '#'*self.level.value
        display_title = self.title if self.parent != None else ''
        return f"{level_indication} {display_title}\n{self.text}"

    def markdown_family(self) -> str:
        text = self.markdown()
        for child in self.children:
            text += child.markdown_family()
        return text

    def __init__(self, 
                 title:str,
                 text:str,
                 level: Level=Level.root, 
                 parent=None):
       self.level = level 
       self.title = title
       self.text = text
       self._children = list()
       self.parent = parent
       if self.parent != None:
           self.parent.children.append(self)

def _parse_text(start: int, end: int, text: list):
    final_text = ''
    if end > start:
        for i in range(start, end):
            final_text += f'{text[i]}\n'
    return final_text

def _parse_title(line: str):
    spaces = re.compile(r'^ +')
    match = spaces.search(line)
    line = line.replace('\n', '')
    if match != None:
        return line[match.span()[1]:]
    else:
        return line

def parse_markdown_file(markdown_file:str):
    if not isinstance(markdown_file, str):
        raise TypeError('markdown_file must be a string')
    if not os.path.exists(markdown_file):
        raise ValueError('markdown_file did not refer to a valid path to a file.')
    full_text = list()
    with open(markdown_file, 'r') as filedata:
        full_text = list(filter(lambda x: x.strip(), filedata.readlines()))

    # Begin parseing 
    short_file_name = markdown_file.split('/')[-1].lower().replace('.md', '')

    # Identify all headers
    headers = list()
    for i in range(len(full_text)):
        if full_text[i][0] == "#":
            headers.append(i)

    unbound_text = ''
    # Check to see if the first line including a header is not the first line in the file
    if len(headers) > 1 and headers[0] != 0:
        unbound_text = _parse_text(0, headers[0], full_text)
    elif len(headers) == 0:
        unbound_text = _parse_text(0, len(full_text), full_text)

    root = Section(short_file_name, unbound_text)
    prev = root
    for hline in range(len(headers)):
        line = headers[hline]
        header_symbol = re.compile(r'^#+')
        match = header_symbol.search(full_text[line])
        level = match.span()[1]
        title = _parse_title(full_text[line][level:])
        start = line + 1
        emptyText = False
        try:
            end = headers[hline+1]
        except IndexError:
            end = len(full_text)
        emptyText = (start == end)
        text = "" if emptyText else _parse_text(start, end, full_text) 

        if level > prev.level.value:
            # This is a child of the previous
            newSection = Section(title, text, Level(level), prev)            
        elif level == prev.level.value:
            # This is a sibling of the previous
            newSection = Section(title, text, Level(level), prev.parent)
        elif level < prev.level.value:
            # This is a sibling of one of the previous's ancestors 
            # Find the ancestor that could be its parent 
            curParent = prev
            while level < curParent.level.value:
                curParent = curParent.parent
            newSection = Section(title, text, Level(level), curParent.parent)
        prev = newSection
    return root

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="markparse",
                                     description="Is capable of reading in a Markdown file and returning a tree view of the file as separated by Header sections")
    parser.add_argument('markdown_file', help="Path to markdown file to be parsed")
    args = parser.parse_args()
    results = parse_markdown_file(args.markdown_file)
    print(results.display_family())
