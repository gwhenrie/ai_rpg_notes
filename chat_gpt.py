import openai
import sys
import requests
from PIL import Image
from io import BytesIO
import argparse
import os
import tty
import termios

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

PROMPT = """
What do you need? 
\t't' - Generate an answer to a question based on a prompt
\t'p' - Generate a picture based on prompt
\t'q' - Quit
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
    if args.history:
        historicalData = ""
        if not os.path.exists(args.history):
            raise ValueError(f'"{args.history}" does not exist')
        with open(args.history, 'r') as history:
            historicalData = history.read()
        messages.append({'role': 'system',
                        'content': historicalData})
    endChat = False 
    while not endChat:
        print(PROMPT)
        key = wait_for_keypress()
        delete_lines(lines=len(PROMPT.split('\n')))
        if key == 'q':
            endChat = True
        elif key == 'p':
            response = client.images.generate(
                    model="dall-e-3",
                    prompt=input('What do you need a picture of?\n'),
                    size="1024x1024",
                    quality="standard",
                    n=1)
            image_url = response.data[0].url
            pic = requests.get(image_url).content
            image = Image.open(BytesIO(pic))
            image.show()
        elif key == 't':
            message = input('What do you want information about?\n')
            messages.append({'role': 'user', 
                             'content': message})
            chat = client.chat.completions.create(model='gpt-3.5-turbo-1106', messages=messages)

            reply = chat.choices[0].message.content
            print(f'\n{reply}')
            messages.append({'role': 'assistant', 'content': reply})
