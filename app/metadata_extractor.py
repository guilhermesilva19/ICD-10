from bs4 import BeautifulSoup

def extract_embedded_metadata(file_content, clean_filename):
    gender, unique_name = '', ''
    if not clean_filename.endswith('.html'):
        return gender, unique_name

    soup = BeautifulSoup(file_content, 'html.parser')
    meta_tag = soup.find('meta', attrs={'name': 'Unique'})
    if meta_tag and 'content' in meta_tag.attrs:
        unique_name = meta_tag['content']
    meta_tag = soup.find('meta', attrs={'name': 'Gender'})
    if meta_tag and 'content' in meta_tag.attrs:
        gender = meta_tag['content']

    return gender, unique_name
