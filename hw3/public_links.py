"""Public URLs used by independently readable HW3 reports."""
from urllib.parse import quote
import re

REPOSITORY = 'https://github.com/Can1017/LLM-HW'
RAW = 'https://raw.githubusercontent.com/Can1017/LLM-HW/main/hw3/'
RELEASE = REPOSITORY + '/releases/tag/hw3-news-bert-v1'
MODEL_DOWNLOAD = REPOSITORY + '/releases/download/hw3-news-bert-v1/hw3-news-bert.zip'


def file_url(path, directory=False):
    return REPOSITORY + ('/tree/main/hw3/' if directory else '/blob/main/hw3/') + quote(path, safe='/')


def figure_url(path):
    return RAW + quote(path, safe='/')


def publish_links(document):
    def replace(match):
        label, target = match.groups()
        if target.startswith(('https://', 'http://')):
            return match.group(0)
        return label + '(' + (figure_url(target) if label.startswith('!') else file_url(target)) + ')'
    return re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)', replace, document)
