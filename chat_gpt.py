import openai
import sys
import requests
from PIL import Image
from io import BytesIO
import argparse
import os
import tty
import termios
import tempfile
import subprocess
from parse_markdown import parse_markdown_file, Section, Level

def wait_for_keypress():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        key = sys.stdin.read(1)
        return key
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def delete_lines(lines=1):
    for line in range(lines):
        sys.stdout.write('\x1b[1A')
        sys.stdout.write('\x1b[2K')

def update_history(messages, markdown_info):
    messages[1]['content'] = markdown_info.markdown_family()

def save_result_to_history(markdown_info, prompt, result):
    print('Would you like to add this to an object in the history? Y/n')
    key = wait_for_keypress()
    while key not in ['y', 'n']:
        key = wait_for_keypress()
    if key == 'n':
        return

    # Update the requested item
    item_address = input('What is the family identifier for the object you wish to add to?\n')
    item = markdown_info.get_descendent(item_address)
    if isinstance(result, str):
        newItem = Section(prompt, result, level=Level(item.level.value + 1), parent=item)
        item.children.append(newItem)
    elif isinstance(result, Image.Image):
        # Save the image to the current working directory
        name = 1
        while os.path.exists(f"{name}.PNG"):
            name += 1
        path = f"{os.getcwd()}/{name}.PNG"
        result.save(path, "PNG")
        # Append the image markdown to the text of item
        item.text += f"\n![{prompt}]({path})\n\n"
    else: 
        raise TypeError(f'{type(result)} cannot be currently added to markdown') 

PROMPT = """
What do you need? 
\t't' - Generate a text response to a prompt
\t'p' - Generate a picture based on prompt
"""
DISPLAY_HISTORY = """\t'd' - Display all sections of history file loaded
\t'e' - Edit specified item based on family tree list
\t'i' - Display specified item based on family tree list
\t's' - Save the current history to a file
"""
QUIT_OPTION = """\t'q' - Quit
"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Chat GPT Terminal Interface",
                                     description="Provides a basic terminal interface with OpenAI's Chat GPT")
    parser.add_argument('-hist', '--history')
    args = parser.parse_args()
    openai.api_key = os.environ.get('OPENAI_API_KEY') 
    client = openai.OpenAI()
    messages = [{'role': 'system', 
                 'content': 'You accurately summarize with minimal embellishments.'}]
    markdown_info = None
    if args.history:
        historicalData = ""
        if not os.path.exists(args.history):
            raise ValueError(f'"{args.history}" does not exist')
        with open(args.history, 'r') as history:
            historicalData = history.read()
        messages.append({'role': 'system',
                        'content': historicalData})
        markdown_info = parse_markdown_file(args.history)

    history_options = DISPLAY_HISTORY if markdown_info else ""
    options = PROMPT + history_options + QUIT_OPTION

    endChat = False 
    while not endChat:
        print(options)
        key = wait_for_keypress()
        delete_lines(lines=len(options.split('\n')))
        if key == 'q':
            endChat = True
        elif markdown_info and key == 'd':
            summary = markdown_info.display_family(identify=True)
            print(summary)
        elif markdown_info and key == 'e':
            # User wants to edit a section 
            identity_string = input('What object do you want to edit?\n')
            item = markdown_info.get_descendent(identity_string)
            tempPath = ""
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                temp_file.write(item.markdown())
                tempPath = temp_file.name
            subprocess.Popen(f"xterm -fs 30 -e $EDITOR {tempPath}", shell=True)
            print('Press any key once you have finished editing.')
            wait_for_keypress()
            # Process the new markdown
            temp_root = parse_markdown_file(tempPath)
            # This will be a root item, so the item we want is actually the first child. 
            edited_item = temp_root.children[0]
            edited_item.parent = item.parent 
            item_index = 0
            for sibling in range(len(item.parent.children)):
                if item.parent.children[sibling] == item:
                    item_index = sibling
            # Check to see if item had previous children and append them here 
            for child in item.parent.children[item_index].children:
                child.parent = edited_item
                edited_item.children.append(child)
            # Check to see if more siblings have been added at the same level. 
            for sibling in temp_root.children[1:]:
                sibling.parent = item.parent
                item.parent.children.append(sibling)
            # Replace the item with the edited item in the tree 
            item.parent.children[item_index] = edited_item
            # Reload the historical data used for text prompts 
            update_history(messages, markdown_info)
        elif markdown_info and key == 'i':
            identity_string = input('What object do you want?\n')
            delete_lines(lines=2)
            item = markdown_info.get_descendent(identity_string)
            print(item.markdown())
        elif key == 'p':
            prompt = ""
            if markdown_info: 
                print('Would you like to describe something in the history? Y (Yes)/n (no)')
                key = wait_for_keypress().lower()
                while key not in ['y', 'n']:
                    key = wait_for_keypress().lower()
                if key == 'y':
                    character = input('What would you like depicted?\n')
                    messages.append({'role': 'user',
                                     'content': f"Provide a visual description of '{character}'"})
                    chat = client.chat.completions.create(model='gpt-4-1106-preview', messages=messages)
                    prompt = chat.choices[0].message.content 

            if prompt == "":
                prompt = input('What do you need a picture of?\n')
            response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1)
            image_url = response.data[0].url
            pic = requests.get(image_url).content
            image = Image.open(BytesIO(pic))
            image.show()
            if markdown_info:
                summaryPrompt = f"Summarize the following in one line: '{prompt}'"
                messages.append({'role': 'user',
                                 'content': summaryPrompt})
                chat = client.chat.completions.create(model='gpt-4-1106-preview', messages=messages)
                summary = chat.choices[0].message.content.replace('\n', '')
                save_result_to_history(markdown_info, summary, image)
                update_history(messages, markdown_info)
        elif markdown_info and key == 's':
            fileName = input('What do you want to name the new history?\n(This will be saved to the current working directory)\n')
            if len(fileName) > 3 and fileName[-3:].lower() != '.md':
                fileName += '.md'
            with open(fileName, 'w') as new_history:
                new_history.write(markdown_info.markdown_family())

        elif key == 't':
            message = input('What do you want information about?\n')
            messages.append({'role': 'user', 
                             'content': message})
            chat = client.chat.completions.create(model='gpt-4-1106-preview', messages=messages)

            reply = chat.choices[0].message.content
            print(f'\n{reply}')
            messages.append({'role': 'assistant', 'content': reply})
            if markdown_info:
                save_result_to_history(markdown_info, message, reply)
                update_history(messages, markdown_info)
