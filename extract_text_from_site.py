from urllib.request import urlopen
from bs4 import BeautifulSoup


def get_text_in_url(url):

    html = urlopen(url).read()
    soup = BeautifulSoup(html, features="html.parser")
    
    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()    # rip it out
    
    # get text
    text = soup.get_text()
    
    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text
    

def main():
    text = get_text_in_url(url="https://www.linkedin.com/jobs/view/principal-scientist-process-sciences-at-randstad-life-sciences-us-3360772282")  
    print(text)
    return None

# main()
    
