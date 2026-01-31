import streamlit as st # for streamlit interface
import re  # regex to analyze zhuyin
import jieba  # import jieba for corpus splitting
import jieba.posseg as pseg  # for word formats
import dragonmapper.hanzi  # for conversion to zhuyin
import tracery  # to generate poems based on given words
import random  # to choose rhyme group
from collections import Counter  # for optional frequency filtering
import gettext

lang_choice = st.sidebar.selectbox("Language / 語言", ["繁體中文", "English"]) # adds multilingual support
lang_code = 'zh_TW' if lang_choice == "繁體中文" else 'en' # traditional chinese acts as a default considering the main target group

_ = gettext.translation('messages', localedir='locales', languages=[lang_code]).gettext

st.set_page_config(page_title=_("點字成詩 - Verse Alchemist"), layout="centered")

rules = {
    "origin": ["#poemformats#"],  # chooses one of eight common poem formats in chinese poetry
    "poemformats": [
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
    "仄起不入仄韻式": ["【仄起不入仄韻式 - {rhyme}】\n#仄仄仄平平_不押#\n#平平平仄仄_押#\n#平平仄仄平_不押#\n#平平仄仄平_押#"],
    "平起入平韻式": ["【平起入平韻式 - {rhyme}】\n#平平仄仄平_押#\n#仄仄仄平平_押#\n#仄仄平平仄_不押#\n#平平仄仄平_押#"],
    "仄起入仄韻式": ["【仄起入仄韻式 - {rhyme}】\n#仄仄平平仄_押#\n#平平平仄仄_押#\n#平平仄仄平_不押#\n#仄仄平平仄_押#"],

    # subcategorize the 4 pingze format combinations into both 2-1-2 and 2-2-1 chopping for each rhymed and non rhymed lines
    "仄仄平平仄_不押": [
        "#仄仄n_any##平v_any##平仄n_any#",  # 2-1-2
        "#仄仄n_any##平平a_any##仄n_any#"  # 2-2-1
    ],
    "仄仄平平仄_押": [
        "#仄仄n_any##平v_any##平仄n_{rhyme}#",
        "#仄仄n_any##平平a_any##仄n_{rhyme}#"
    ],

    "平平仄仄平_不押": [
        "#平平n_any##仄v_any##仄平n_any#",
        "#平平n_any##仄仄a_any##平n_any#"
    ],
    "平平仄仄平_押": [
        "#平平n_any##仄v_any##仄平n_{rhyme}#",
        "#平平n_any##仄仄a_any##平n_{rhyme}#"
    ],

    "平平平仄仄_不押": [
        "#平平n_any##平v_any##仄仄n_any#",
        "#平平n_any##平仄a_any##仄n_any#"
    ],
    "平平平仄仄_押": [
        "#平平n_any##平v_any##仄仄n_{rhyme}#",
        "#平平n_any##平仄a_any##仄n_{rhyme}#"
    ],

    "仄仄仄平平_不押": [
        "#仄仄n_any##仄v_any##平平n_any#",
        "#仄仄n_any##仄平a_any##平n_any#"
    ],
    "仄仄仄平平_押": [
        "#仄仄n_any##仄v_any##平平n_{rhyme}#",
        "#仄仄n_any##仄平a_any##平n_{rhyme}#"
    ],
}

def get_zhuyin(word):
    return dragonmapper.hanzi.to_zhuyin(word, all_readings=False, container='[]')  # readings could be useful to account for double rhyme schemes (one word fitting in multiple schemes due to multiple readings) but kept out for now to keep it simple


def get_pingze(current_zhuyin):
    syllables = current_zhuyin.split()
    pingze = ""
    for s in syllables:
        if re.search(r'[ˇˋ˙]', s):
            pingze = pingze + '仄'
        else:
            # no mark (1st tone) or ˊ (2nd tone) will be assigned 平
            pingze = pingze + '平'
    return pingze


def get_rhyme_group(current_zhuyin):
    last_syllable = current_zhuyin.split()[-1]  # only the last syllable of a word is taking into account
    clean_syllable = re.sub(r'[ˊˇˋ˙]', '', last_syllable)  # removes tone to solely

    if re.fullmatch(r'[ㄓㄔㄕㄖㄗㄘㄙ]', clean_syllable):  # accounts for words with no finals like 自 being ㄗ only
        return "五支"

    if re.search(r'(ㄨㄥ|ㄩㄥ)$', clean_syllable):  # as ㄥ can be the final for both 17th and 18th rhyme group, we assign category 18 first using the specific combinations - the only case where we cannot go with the final only
        return "十八東"

    final = clean_syllable[-1]  # only considers the final sound of each character

    mapping = {  # maps characters based on the final sound only, instead of mapping all 409 pinyin combinations
        'ㄚ': "一麻",  # a, ia, ua
        'ㄛ': "二波",  # o, uo
        'ㄜ': "三歌",  # e
        'ㄝ': "四皆",  # ie, üe
        'ㄦ': "六兒",  # er
        'ㄧ': "七齊",  # i
        'ㄟ': "八微",  # ei, ui
        'ㄞ': "九開",  # ai, uai
        'ㄨ': "十模",  # u
        'ㄩ': "十一魚",  # ü
        'ㄡ': "十二侯",  # ou, iu
        'ㄠ': "十三豪",  # ao, iao
        'ㄢ': "十四寒",  # an, ian, uan, üan
        'ㄣ': "十五痕",  # en, in, un, ün
        'ㄤ': "十六唐",  # ang, iang, uang
        'ㄥ': "十七庚",  # eng, ing (weng)
    }

    return mapping.get(final, "Unknown")


def get_grammatical_format(word):
    words = pseg.cut(word)
    w, flag = next(words)
    if (
            flag.startswith('n') or
            flag.startswith('r') or
            flag.startswith('t') or
            flag.startswith('s') or
            flag.startswith('m') or
            flag.startswith('q') or
            flag.startswith('i')
    ):
        return "n"  # noun (and other grammatical forms that could be used in that place)

    elif (
            flag.startswith('v') or
            flag.startswith('p') or
            flag.startswith('c')
    ):
        return "v"  # verb (and other grammatical forms that could be used in that place)

    elif (
            flag.startswith('a') or
            flag.startswith('d') or
            flag.startswith('z') or
            flag.startswith('f') or
            flag.startswith('b') or
            flag.startswith('u') or
            flag.startswith('e') or
            flag.startswith('y') or
            flag.startswith('o')
    ):
        return "a"  # adjective (and other grammatical forms that could be used in that place)
    else:
        return "Noun"  # if the word group is none of these we just assume it to be a noun, to avoid words to be lost (these words account for only a very small amount of words, as can be tested by replacing Noun with None here)

@st.cache_data # cache data so the same text does not get re-analyzed with every interaction
def analyze_wordbase(text, min_frequency=1):
    dictionary = {}
    
    all_words = [w for w in jieba.cut(text) if re.fullmatch(r'[\u4e00-\u9fa5]+', w) and len(w) in [1, 2]]
    word_count = Counter(all_words)
    
    words = [w for w, count in word_count.items() if count >= min_frequency] # applying optional minimum frequency for final list
    unique_word_count = len(words)
    
    available_rhyme_groups = set()

    for word in words:
        # gets all necessary parameters for poem generator
        current_zhuyin = get_zhuyin(word) # zhuyin phonetics used for pingze and rhyme group later on
        pingze = get_pingze(current_zhuyin) # pingze for tone rules e.g "平仄"
        rhyme_group = get_rhyme_group(current_zhuyin) # rhyme group for rhyming e.g "十七庚"
        
        if rhyme_group != "Unknown":
            available_rhyme_groups.add(rhyme_group)

        grammar_format = get_grammatical_format(word) # i changed the name to grammar_format as format seems to be a python function as well
        
        # assigns the name for the two dictionaries, this word belongs in (one is the general list, one for the specific rhyme group)
        dictionary_name = f"{pingze}{grammar_format}_any"
        dictionary_name_rhyme = f"{pingze}{grammar_format}_{rhyme_group}"
        
        # adds the word to these two dictionaries inside the grammar rules or creates the dictionary if it not yet exists
        dictionary.setdefault(dictionary_name, []).append(word)
        dictionary.setdefault(dictionary_name_rhyme, []).append(word)

    rhymegroups = list(available_rhyme_groups)
    
    return dictionary, rhymegroups, unique_word_count

def generate_poem(dictionary, rules, rhymegroups, user_rhyme_choice, repetition_filter, num_poems):
    generated_poems = []
    
    for i in range(num_poems):
        attempt = 0
        max_attempts = 10 # limit attempts to prevent infinite loops if dictionary is too small
        
        while attempt < max_attempts:
            attempt += 1
            
            # rewrites rules based on chosen rhyme group
            if user_rhyme_choice == "Random":
                rhymegroup = random.choice(rhymegroups) # chooses one rhyme type used across the poem
            else:
                rhymegroup = user_rhyme_choice
                
            current_rules = { # replaces rhyme variable with the actual rhymegroup for this poem
                key: [rule.format(rhyme=rhymegroup) for rule in val_list]
                for key, val_list in rules.items() # goes through every val_list (content of each rule) in every key (e.g. origin, poemformats etc.) to replace rhyme with rhymegroup
            }
            
            current_rules.update(dictionary) # adds the dictionary to the rules 
            
            grammar = tracery.Grammar(current_rules)
            
            poem = grammar.flatten("#origin#")
            
            if "((" in poem or "))" in poem: # if found, a word category didn't exist. regenerate.
                continue

            if repetition_filter:
                poem_content = re.sub(r'【.*?】', '', poem) # removes title etc.
                poem_words = [w for w in jieba.cut(poem_content) if w.strip()] 
                if len(poem_words) != len(set(poem_words)): # if unique count != total count, there are duplicates. regenerate.
                    continue
            
            generated_poems.append(poem)
            break # Successfully generated valid poem, exit while loop
            
    return generated_poems

# streamlit logic
st.title(_("Verse Alchemist"))
st.header(_("Turn any Text into Jueju Poems"))

user_input = st.text_area(_("Enter your Chinese text (100 - 10000 characters)"), height=200)

st.write(_("**Or**"))

wordbase_option = st.selectbox(
    _("Choose Wordbase"),
    (_("唐詩三百首 - Three Hundred Tang Poems"), _("不同意罷免留言 - Anti Recall Comments"))
)

raw_text = ""

if user_input:
    if 100 <= len(user_input) <= 10000:
        raw_text = user_input
    else:
        st.warning(_("Please ensure text is between 100 and 10000 characters."))
else:
    file_path = f'wordbases/{wordbase_option}.txt'
    try:
        raw_text = open(file_path, encoding='utf-8').read()
    except FileNotFoundError:
        st.error(_("File '{file_path}' not found. Please check the 'wordbases' folder in your repository.").format(file_path=file_path))

if raw_text:
    with st.spinner(_("Analyzing wordbase...")):
        min_freq = 1 # fixed based on original code defaults
        dictionary_data, available_rhyme_groups, unique_count = analyze_wordbase(raw_text, min_freq)
    
    if not available_rhyme_groups:
        st.error(_("No valid rhyme groups found in text. Ensure that your database is in Chinese."))
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            rhyme_options = [_("Random")] + sorted(available_rhyme_groups)
            rhyme_choice = st.selectbox(_("Choose Rhyme Group (Optional)"), rhyme_options)
        
        with col2:
            num_poems = st.slider(_("Number of Poems"), 1, 10, 5)

        allow_repetition = st.checkbox(_("Allow Character Repetitions"), value=False)
        repetition_filter = not allow_repetition 

        if st.button(_("Generate Poem")):
            poems = generate_poem(
                dictionary_data, 
                rules, 
                available_rhyme_groups, 
                rhyme_choice, 
                repetition_filter, 
                num_poems
            )
            
            if not poems:
                st.warning(_("Could not generate valid poems with current constraints. Try allowing repetition, changing rhyme group or use a bigger Wordbase)."))
            elif len(poems) < num_poems:
                st.warning(_("Could not generate as many poems as requested with current constraints. Try allowing character repetition, changing rhyme group or use a bigger wordbase for more resutls)."))
                st.markdown(_("### Generated Poems"))
                for p in poems:
                    st.code(p, language='text')
            else:
                st.markdown(_("### Generated Poems"))
                for p in poems:
                    st.code(p, language='text')

with st.expander(_("AI Usage Disclaimer")):
    st.info(_('''
- Gemini was used to map the rhyme group in python, pinyin equivalents to each final based on publicly available table
to reduce repetitive work, reference: https://gemini.google.com/share/72f39776edf1 (AI），https://zh.wikipedia.org/zh-hant/%E4%B8%AD%E8%8F%AF%E6%96%B0%E9%9F%BB (table)
- ChatGPT was used to map all jieba POS tags to the three categories named Noun, Verb, Adjective
to reduce repetitive workload and leverage its knowledge on different grammatical categories, 
reference: https://chatgpt.com/s/t_6978d8c814a88191ac5f497d28d3e0cf
- Gemini was used to turn the existing python code into a streamlit application for demo purposes based on
given requirements, reference: https://gemini.google.com/share/dd1a4ec00677
'''))
