# coding:utf-8
import termextract.japanese_plaintext
import termextract.mecab
import termextract.core
from pprint import pprint
import sys, getopt
import collections
import dbm
from os.path import basename
import os

def get_filepaths(directory):
    """
    This function will generate the file names in a directory
    tree by walking the tree either top-down or bottom-up. For each
    directory in the tree rooted at directory top (including top itself),
    it yields a 3-tuple (dirpath, dirnames, filenames).
    """
    file_paths = []  # List which will store all of the full filepaths.

    # Walk the tree.
    for root, directories, files in os.walk(directory):
        for filename in files:
            # Join the two strings in order to form the full filepath.
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)  # Add it to the list.

    return file_paths  # Self-explanatory.



def stroe_df_lr(data_set_path):
    df = dbm.open("df", "n")
    lr = dbm.open("lr", "n")

    input_files = get_filepaths(data_set_path)
    for file in input_files:
        frequency = get_frequency(file)
        termextract.core.store_lr(frequency, dbm=lr)
        termextract.core.store_df(frequency, dbm=df)
    lr.close
    df.close


def get_frequency(file_name):
    tagged_text = ""
    try:
        f = open(file_name, "r", encoding="shift_jis")
        tagged_text = f.read()
        f.close
    except Exception as e:
        if type(e) is UnicodeDecodeError:
            # print('An UnicodeDecodeError! ' + file_name)
            pass

    frequency = termextract.japanese_plaintext.cmp_noun_dict(tagged_text)
    return frequency


def calculate_importance(dict1, dict2):
    term_imp = termextract.core.term_importance(dict1, dict2)
    # pprint(term_imp)
    data_collection = collections.Counter(term_imp)
    for cmp_noun, value in data_collection.most_common():
        print(termextract.core.modify_agglutinative_lang(cmp_noun), sep="\t")



def get_term_LR(file_name):
    # make LR
    frequency = get_frequency(file_name)
    # pprint(frequency)
    lr = dbm.open("lr", "r")
    LR = termextract.core.score_lr(frequency,
                                   ignore_words=termextract.mecab.IGNORE_WORDS,
                                   lr_mode=1, average_rate=1, dbm=lr
                                   )
    lr.close
    # pprint(LR)

    # calculate importance
    calculate_importance(frequency, LR)


def get_term_TFIDF(file_name):

    # make TF
    frequency = get_frequency(file_name)
    # pprint(frequency)
    TF = termextract.core.frequency2tf(frequency)
    # pprint(TF)

    # make IDF
    df = dbm.open("df", "r")
    IDF = termextract.core.get_idf(frequency, dbm=df)
    df.close
    # pprint(IDF)

    # calculate importance
    calculate_importance(TF, IDF)


def main(argv):
    inputfile = ''
    inputdataset = ''

    try:
        opts, args = getopt.getopt(argv, "hi:d", ["ifile=", "dataset"])
    except getopt.GetoptError:
        print('python3 termextract_toolkit.py -i <inputfile>')
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print('python3 termextract_toolkit.py -i <inputfile> - d <inputdataset>')
            sys.exit()
        elif opt in ('-i', '--ifile'):
            inputfile = arg
            # print('Input file is ' + inputfile)
        elif opt in ('-d', '--dataset'):
            inputdataset = arg
            # print('Input dataset is ' + inputdataset)

    stroe_df_lr(inputdataset)
    get_term_TFIDF(inputfile)
    get_term_LR(inputfile)

    pass


if __name__ == '__main__':
    main(sys.argv[1:])
