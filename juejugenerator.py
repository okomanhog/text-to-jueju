''' 
AI Usage Disclaimer: 
- Gemini was used to map the rhyme group in python, pinyin equivalents to each final based on publicly available table
to reduce repetitive work, reference: https://gemini.google.com/share/72f39776edf1 （AI），https://zh.wikipedia.org/zh-hant/%E4%B8%AD%E8%8F%AF%E6%96%B0%E9%9F%BB (table)
- ChatGPT was used to map all jieba POS tags to the three categories named Noun, Verb, Adjective
to reduce repetitive workload and leverage its knowledge on different grammatical categories, 
reference: https://chatgpt.com/s/t_6978d8c814a88191ac5f497d28d3e0cf 
'''

import re # import regex to analyze zhuyin
import jieba # import jieba for corpus splitting
import jieba.posseg as pseg # for word formats
import dragonmapper.hanzi # for conversion to zhuyin
import tracery # to generate poems based on given words
import random # to choose rhyme group
import sys # for exiting the script on errors
from collections import Counter # for optional frequency filtering

# Chinese was used within the tracery grammar logic, as the English translation of rhyme types is either too bulky or too cryptic, consequently it was used for consistency
rules = {
    "起點": ["#詩詞格式#"], # chooses one of eight common poem formats in chinese poetry
    "詩詞格式": [ 
        "#仄起不入平韻式#", "#平起不入仄韻式#", 
        "#仄起入平韻式#", "#平起入仄韻式#",
        "#平起不入平韻式#", "#仄起不入仄韻式#", 
        "#平起入平韻式#", "#仄起入仄韻式#"
    ],
    # each poem format is defined based on pingze, for each line as the same 4 pingze patterns occur through all poem formats, 
    # depending on the poem format they sometimes rhyme and sometimes do not
    "仄起不入平韻式": ["【仄起不入平韻式 - {rhyme}】\n#仄仄平平仄_不押#\n#平平仄仄平_押#\n#平平平仄仄_不押#\n#仄仄仄平平_押#"],
    "平起不入仄韻式": ["【平起不入仄韻式 - {rhyme}】\n#平平仄仄平_不押#\n#仄仄平平仄_押#\n#仄仄仄平平_不押#\n#平平平仄仄_押#"],
    "仄起入平韻式": ["【仄起入平韻式 - {rhyme}】\n#仄仄仄平平_押#\n#平平仄仄平_押#\n#平平平仄仄_不押#\n#仄仄仄平平_押#"],
    "平起入仄韻式": ["【平起入仄韻式 - {rhyme}】\n#平平平仄仄_押#\n#仄仄平平仄_押#\n#仄仄仄平平_不押#\n#平平平仄仄_押#"],
    "平起不入平韻式": ["【平起不入平韻式 - {rhyme}】\n#平平平仄仄_不押#\n#仄仄仄平平_押#\n#仄仄平平仄_不押#\n#平平仄仄平_押#"],
    "仄起不入仄韻式": ["【仄起不入仄韻式 - {rhyme}】\n#仄仄仄平平_不押#\n#平平平仄仄_押#\n#平平仄仄平_不押#\n#仄仄平平仄_押#"],
    "平起入平韻式": ["【平起入平韻式 - {rhyme}】\n#平平仄仄平_押#\n#仄仄仄平平_押#\n#仄仄平平仄_不押#\n#平平仄仄平_押#"],
    "仄起入仄韻式": ["【仄起入仄韻式 - {rhyme}】\n#仄仄平平仄_押#\n#平平平仄仄_押#\n#平平仄仄平_不押#\n#仄仄平平仄_押#"],
    
    # subcategorize the 4 pingze format combinations into both 2-1-2 and 2-2-1 chopping for each rhymed and non rhymed lines
    "仄仄平平仄_不押": [
        "#仄仄名_任意##平動_任意##平仄名_任意#", # 2-1-2
        "#仄仄名_任意##平平形_任意##仄名_任意#"  # 2-2-1
    ],
    "仄仄平平仄_押": [
        "#仄仄名_任意##平動_任意##平仄名_{rhyme}#", 
        "#仄仄名_任意##平平形_任意##仄名_{rhyme}#"
    ],

    "平平仄仄平_不押": [
        "#平平名_任意##仄動_任意##仄平名_任意#", 
        "#平平名_任意##仄仄形_任意##平名_任意#"
    ],
    "平平仄仄平_押": [
        "#平平名_任意##仄動_任意##仄平名_{rhyme}#", 
        "#平平名_任意##仄仄形_任意##平名_{rhyme}#"
    ],

    "平平平仄仄_不押": [
        "#平平名_任意##平動_任意##仄仄名_任意#", 
        "#平平名_任意##平仄形_任意##仄名_任意#"
    ],
    "平平平仄仄_押": [
        "#平平名_任意##平動_任意##仄仄名_{rhyme}#", 
        "#平平名_任意##平仄形_任意##仄名_{rhyme}#"
    ],

    "仄仄仄平平_不押": [
        "#仄仄名_任意##仄動_任意##平平名_任意#", 
        "#仄仄名_任意##仄平形_任意##平名_任意#"
    ],
    "仄仄仄平平_押": [
        "#仄仄名_任意##仄動_任意##平平名_{rhyme}#", 
        "#仄仄名_任意##仄平形_任意##平名_{rhyme}#"
    ],
}

def save_poem_to_file(content, filename="poems.txt"):
    with open(filename, "a", encoding="utf-8") as poemcollection:
        poemcollection.write(content + "\n\n")

def get_zhuyin(word):
    return dragonmapper.hanzi.to_zhuyin(word, all_readings=False, container='[]')

def get_pingze(current_zhuyin):
    syllables = current_zhuyin.split()
    pingze = ""
    for s in syllables:
        if re.search(r'[ˇˋ˙]', s): # based on the tone symbols used in dragonmapper's zhuyin, the pingze for each word is being extracted
            pingze = pingze + '仄'
        else:
            pingze = pingze + '平'
    return pingze
    
def get_rhyme_group(current_zhuyin):
    last_syllable = current_zhuyin.split()[-1]
    clean_syllable = re.sub(r'[ˊˇˋ˙]', '', last_syllable)
    
    if re.fullmatch(r'[ㄓㄔㄕㄖㄗㄘㄙ]', clean_syllable):
        return "五支"
    
    if re.search(r'(ㄨㄥ|ㄩㄥ)$', clean_syllable):
        return "十八東"
        
    final = clean_syllable[-1]
    
    mapping = {
        'ㄚ': "一麻",  # a, ia, ua
        'ㄛ': "二波",  # o, uo
        'ㄜ': "三歌",  # e
        'ㄝ': "四皆",  # ie, üe
        'ㄦ': "六兒",  # er
        'ㄧ': "七齊",  # i
        'ㄟ': "八微",  # ei, ui
        'ㄞ': "九開",  # ai, uai
        'ㄨ': "十模",  # u
        'ㄩ': "十一魚", # ü
        'ㄡ': "十二侯", # ou, iu 
        'ㄠ': "十三豪", # ao, iao
        'ㄢ': "十四寒", # an, ian, uan, üan
        'ㄣ': "十五痕", # en, in, un, ün
        'ㄤ': "十六唐", # ang, iang, uang
        'ㄥ': "十七庚", # eng, ing (weng)
    }

    return mapping.get(final, "未知")
    
# as jieba subdivides the grammatical formats into very detailed formats, I simplified them roughly into noun, verb and adjective - it is meant rather as a basic structure thus I did not want to fine grammatical formats
def get_grammatical_format(word):
    words = pseg.cut(word)
    w, flag = next(words)
    if flag.startswith(('n', 'r', 't', 's', 'm', 'q', 'i')):
        return "名"
    elif flag.startswith(('v', 'p', 'c')):
        return "動"
    elif flag.startswith(('a', 'd', 'z', 'f', 'b', 'u', 'e', 'y', 'o')):
        return "形"
    else:
        return "名"

# 

print("Welcome to Verse Alchemist!")
print("1. Use the existing file")
print("2. Input your own text")
choice = input("Please enter 1 or 2: ").strip()

raw_text = ""

if choice == '1':
    # you can edit the filepath here to whatever you like to try, there are also other option in the repository folder
    file_path = 'wordbases/不同意罷免雜志 - Anti Recall Magazine.txt' 
    try:
        with open(file_path, encoding='utf-8') as f:
            raw_text = f.read()
        print(f"\nSuccessfully loaded text from '{file_path}'. Analyzing...")
    except FileNotFoundError:
        print(f"\nError: File '{file_path}' not found. Please make sure it is in the same directory.")
        sys.exit()
elif choice == '2':
    raw_text = input("\nPlease paste or type your Chinese text here (please ensure it is all in one line to prevent command line limitations):\n")
    print("\nAnalyzing text...")
else:
    print("\nInvalid choice. Please restart the script.")
    sys.exit()

if not raw_text.strip():
    print("The provided text is empty. Please restart the script.")
    sys.exit()

min_frequency = 1 # optional variable to filter words by frequency
repetition_filter = True # optional variable to prevent word repetition, they will be filtered afterwards

all_words = [w for w in jieba.cut(raw_text) if re.fullmatch(r'[\u4e00-\u9fa5]+', w) and len(w) in [1, 2]]
word_count = Counter(all_words)

# applying minimum frequency for final list
words = [w for w, count in word_count.items() if count >= min_frequency]
unique_word_count = len(words)

dictionary = {}
available_rhyme_groups = set()

for word in words:
    current_zhuyin = get_zhuyin(word)
    pingze = get_pingze(current_zhuyin)
    rhyme_group = get_rhyme_group(current_zhuyin)
    
    if rhyme_group != "未知":
        available_rhyme_groups.add(rhyme_group)

    grammar_format = get_grammatical_format(word)
    
    dictionary_name = f"{pingze}{grammar_format}_任意"
    dictionary_name_rhyme = f"{pingze}{grammar_format}_{rhyme_group}"
    
    dictionary.setdefault(dictionary_name, []).append(word)
    dictionary.setdefault(dictionary_name_rhyme, []).append(word)

rhymegroups = list(available_rhyme_groups)

if not rhymegroups:
    print("No valid rhyme groups found in text. Ensure that your text/database is in Chinese.")
    sys.exit()
    
print(f"\nGenerating 5 poems based on a total of {unique_word_count} unique words (frequency >= {min_frequency}):\n")
print("-" * 40)

for i in range(5):
    attempt = 0
    max_attempts = 100 # increased limit to prevent infinite loops but give Tracery a fair chance
    
    while attempt < max_attempts:
        attempt += 1
        
        rhymegroup = random.choice(rhymegroups)
        current_rules = {
            key: [rule.format(rhyme=rhymegroup) for rule in val_list]
            for key, val_list in rules.items()
        }
        
        current_rules.update(dictionary) 
        grammar = tracery.Grammar(current_rules)
        poem = grammar.flatten("#起點#")
        
        if "((" in poem or "))" in poem: 
            continue

        if repetition_filter:
            poem_content = re.sub(r'【.*?】', '', poem) 
            chars = [character for character in poem_content if '\u4e00' <= character <= '\u9fa5']
            if len(chars) != len(set(chars)): 
                continue

        print(poem)
        print("-" * 40)
        save_poem_to_file(poem)
        break 

print("\nDone! Poems have been saved to 'poems.txt'.")