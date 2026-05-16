from PyPDF2 import PdfWriter
from pdf_utils import merge_pdfs, split_pdf, remove_pages
import os

os.makedirs('tmp_test', exist_ok=True)
for i in range(1, 4):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with open(f'tmp_test/test{i}.pdf', 'wb') as f:
        writer.write(f)

merge_pdfs(['tmp_test/test1.pdf', 'tmp_test/test2.pdf', 'tmp_test/test3.pdf'], 'tmp_test/merged.pdf')
print('merged', os.path.exists('tmp_test/merged.pdf'))
split_pdf('tmp_test/merged.pdf', 'tmp_test/split.pdf', 1, 2)
print('split', os.path.exists('tmp_test/split.pdf'))
remove_pages('tmp_test/merged.pdf', 'tmp_test/removed.pdf', [2])
print('removed', os.path.exists('tmp_test/removed.pdf'))
