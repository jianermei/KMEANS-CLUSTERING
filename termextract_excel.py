# coding: utf-8
import os
import commands
from os.path import join
import xlrd


HOME = os.path.expanduser("~")
DATASET_PATH = u'reviewdata'
TOPN = 30


def get_terms(method, files):
    termCommand = 'python3 termextract_toolkit.py -m analysis ' + ' -t ' + method + ' -i ' + "\"" + files + "\""
    resp = commands.getoutput('%s' % (termCommand))
    # print('resp:---' + resp + '---')
    terms = resp.split('\n')
    return terms[0:TOPN]


def prepare_termextract():
    mode = 'store'
    dataset = join(HOME, DATASET_PATH)
    termCommand = 'python3 termextract_toolkit.py' + ' -m ' + mode + ' -d ' + dataset
    resp = commands.getoutput('%s' % (termCommand))
    print('resp:---' + resp + '---')
    pass


def read_excel(ifile_name, mode='all', sheet_num=0, clo_num=1, row_num=1):
    book = xlrd.open_workbook(ifile_name)
    # for name in book.sheet_names():
    #     print name
    sheet = book.sheet_by_index(sheet_num-1)  # start from 0

    cells = []
    if mode == 'all':
        for col in range(sheet.ncols):
            # print '----------------------------'
            for row in range(sheet.nrows):
                cell = sheet.cell(row, col).value
                # print cell
                cells.append(cell)
    elif mode == 'col_fix':
        col = clo_num
        for row in range(sheet.nrows):
            cell = sheet.cell(row, col).value
            # print cell
            cells.append(cell)
    elif mode == 'row_fix':
        row = row_num
        for col in range(sheet.ncols):
            cell = sheet.cell(row, col).value
            # print cell
            cells.append(cell)

    ofile_name = ifile_name.split('.')[0] + '.txt'
    dataset = join(HOME, DATASET_PATH)
    ofile = open(dataset + '/' + ofile_name, 'w')
    for item in cells:
        ofile.write("%s\n" % item.encode('utf-8'))

    print('save [' + ofile_name + '] in ' + dataset)
    ofile.close()

    pass


read_excel(u'SWDR0_レビュー摘録まとめ.xlsx', mode='col_fix', sheet_num=1, clo_num=6)
# prepare_termextract()
# get_terms('tfidf', '/home/huang/reviewdata/review.txt')
