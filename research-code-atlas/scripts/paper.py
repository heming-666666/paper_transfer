import re
from pathlib import Path
import shutil
import subprocess
from common import read, write, InputError


def normalize(text):
    text = re.sub(r'-\s*\n\s*', '', text)
    return re.sub(r'\s+', ' ', text.translate(str.maketrans({'“':'"','”':'"','‘':"'",'’':"'"}))).strip()


def find_quote(page_text, quote):
    return normalize(quote) in normalize(page_text)


def extract_paper(run_dir):
    run = Path(run_dir).resolve()
    request = read(run / 'request.json')
    paper = request.get('paper') or {}
    directory = run / 'paper'
    if (directory / 'status.json').exists():
        raise InputError('paper extraction already exists; reuse or create new run')
    if not paper.get('path'):
        status = {'status': 'missing', 'reason': '未提供本地论文；不自动联网下载', 'pages': 0}
        write(directory / 'status.json', status)
        return status
    path = Path(paper['path'])
    warnings = []
    if path.suffix.lower() == '.pdf':
        try:
            from pypdf import PdfReader
            document = PdfReader(str(path))
            if document.is_encrypted:
                raise InputError('encrypted PDF unsupported; provide authorized decrypted text')
            pages = [p.extract_text() or '' for p in document.pages]
            backend = 'bundled-pypdf'
        except ImportError:
            executable = shutil.which('pdftotext')
            if not executable: raise InputError('PDF text extractor unavailable; provide local MD/TXT')
            command = [executable, '-layout', '-enc', 'UTF-8', str(path), '-']
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
            if result.returncode: raise InputError('pdftotext failed: ' + result.stderr[:500])
            pages = result.stdout.split('\f')
            if pages and not pages[-1].strip(): pages.pop()
            backend = 'pdftotext'
    else:
        text = path.read_text(encoding='utf-8')
        marker = r'(?:===\s*PDF第(\d+)页\s*===|<!--\s*page\s+(\d+)\s*-->)'
        matches = list(re.finditer(marker, text, re.I))
        if matches:
            pages = []
            for index, match in enumerate(matches):
                number = int(match.group(1) or match.group(2))
                if number != index + 1: raise InputError('paper page markers must be contiguous from 1')
                pages.append(text[match.end():matches[index+1].start() if index+1<len(matches) else len(text)].strip())
        else:
            pages = [text]
            warnings.append('无分页标记，全文作为第1页；不是原PDF页码验证')
        backend = 'local-text'
    directory.mkdir(parents=True, exist_ok=True)
    full = []
    for index, text in enumerate(pages, 1):
        p = directory / 'pages' / f'page_{index:03}.txt'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        full.append(f'=== PDF第{index}页 ===\n{text}')
        if len(text.strip()) < 50: warnings.append(f'第{index}页文本少于50字符：可能扫描页，需人工核对，不自动OCR')
    (directory / 'fulltext.txt').write_text('\n\n'.join(full), encoding='utf-8')
    status = {'status': 'available', 'source': str(path), 'pages': len(pages), 'backend': backend, 'warnings': warnings}
    write(directory / 'status.json', status)
    return status
