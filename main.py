import csv
import os
import re
import string
import time
import emoji
import deepl

from deep_translator import GoogleTranslator, MyMemoryTranslator, PonsTranslator
import spacy
from PyMultiDictionary import MultiDictionary
from lingua import Language, LanguageDetectorBuilder

# Spanish parts of speech:
# -Adjectives (m/f) (singular/plural) - only get singular/m
# -Adverbs
# -Articles
# -Conjunctions
# -Interjections
# -Nouns (m/f) (singular/plural) - only get singular
# -Prepositions
# -Pronouns
# -Verbs - only get infinitive form

# Configuration Settings
DEBUG = False
SKIP_TRANSLATION = True
USE_DEEPL = True
INPUT_FILE_ALREADY_PROCESSED = True
INPUT_FILE_NAME = 'FILE_NAME.csv'
DEEPL_AUTH_KEY = 'INSERT_YOUR_KEY_HERE'

# Constants
START_TIME = time.time()
LANGUAGES_LIST = [Language.SPANISH, Language.ENGLISH, Language.FRENCH, Language.PORTUGUESE]
LANGUAGE_DETECTOR = LanguageDetectorBuilder.from_languages(*LANGUAGES_LIST).build()

class Word:
    translation = ""
    prevalence = 0.0
    def __init__(self, word, pos, gender=''):
        self.word = word
        self.pos = pos
        self.gender = gender

def debugPrintTranslations(original, translation, translator):
    if DEBUG == True:
        global START_TIME
        duration = (time.time() - START_TIME)
        print("{0}: {1} -> {2} | {3}".format(translator, original, translation, duration))
        if len(translation.split()) > 4:
            print("Too many words | Will be deleted")
        # reset time
        START_TIME = time.time()

def getDeepLTranslation(spanish_word):
    translation = ""
    try:
        translator = deepl.Translator(DEEPL_AUTH_KEY)
        result = translator.translate_text(spanish_word, source_lang='ES', target_lang='EN-US')
        translation = result.text
        return translation
    except KeyError:
        print("Word not found in DeepL. Word: {0}".format(spanish_word))
    except Exception as e:
        print("Unknown error. Word: {0}. Exception: {1}".format(spanish_word, e))

    return translation

def getMultipleTranslations(spanish_word):
    translation_list = []

    # Start time
    global START_TIME
    START_TIME = time.time()

    try:
        dictionary = MultiDictionary()
        dict = dictionary.translate('es', spanish_word)
        for d in dict:
            if d[0] == 'en':
                debugPrintTranslations(spanish_word, d[1].lower(), "MultiDictionary")
                translation_list.append(d[1].lower())
    except KeyError:
        print("Word not found in MultiDictionary. Word: {0}".format(spanish_word))
    except Exception as e:
        print("Unknown error. Word: {0}. Exception: {1}".format(spanish_word, e))

    try:
        translated = GoogleTranslator(source='es', target='en').translate(spanish_word)
        translated = (translated.strip()).lower()
        debugPrintTranslations(spanish_word, translated, "GoogleTranslator")
        if not translated in translation_list:
            translation_list.append(translated)
    except KeyError:
        print("Word not found in GoogleTranslator. Word: {0}".format(spanish_word))
    except Exception as e:
        print("Unknown error. Word: {0}. Exception: {1}".format(spanish_word, e))

    try:
        translated = MyMemoryTranslator(source='es', target='en').translate(spanish_word)
        translated = (translated.strip()).lower()
        debugPrintTranslations(spanish_word, translated, "MyMemoryTranslator")
        if not translated in translation_list:
            translation_list.append(translated)
    except KeyError:
        print("Word not found in MyMemoryTranslator. Word: {0}".format(spanish_word))
    except Exception as e:
        print("Unknown error. Word: {0}. Exception: {1}".format(spanish_word, e))

    try:
        translated = PonsTranslator(source='es', target='en').translate(spanish_word)
        translated = (translated.strip()).lower()
        debugPrintTranslations(spanish_word, translated, "PonsTranslator")
        if not translated in translation_list and len(translated.split()) < 5:
            translation_list.append(translated)
    except KeyError:
        print("Word not found in PonsTranslator. Word: {0}".format(spanish_word))
    except Exception as e:
        print("Unknown error. Word: {0}. Exception: {1}".format(spanish_word, e))

    if DEBUG == True:
        print("")

    final = ""
    for translation in translation_list:
        if spanish_word != translation:
            final = (final + translation + ", ")

    return final.rstrip(', ')


def parseToken(token):
    morph = str(token.morph)

    if (token.pos_ == 'VERB'):
        if ("VerbForm=Inf" in morph):
            word_obj = Word(token.text, token.pos_)
            return word_obj
    elif (token.pos_ == 'NOUN'):
        if ("Number=Sing" in morph):
            word_obj = Word(token.text, token.pos_, getGender(morph))
            return word_obj
    elif (token.pos_ == 'ADJ'):
        if ("Number=Sing" in morph and "Gender=Masc" in morph):
            word_obj = Word(token.text, token.pos_)
            return word_obj
    else:
        word_obj = Word(token.text, token.pos_)
        return word_obj

def getGender(morph):
    if "Gender=Masc" in morph:
        return "M"
    else:
        return "F"

def showProgress(count, total):
    if (count % 5000 == 0):
        print("{0}%".format(int((count / total) * 100)))

def createUniversalFilePath(relative_pathname):
    base_dir = os.path.dirname(__file__)
    return os.path.join(base_dir, relative_pathname)

def isEmoji(c):
    return emoji.is_emoji(c)

def containsSpecialCharacters(word):
    special_characters = string.punctuation
    spanish_chars = "—¿?¡!–«»"
    if any(c in special_characters for c in word):
        return True
    elif any(elem in word for elem in spanish_chars):
        return True
    else:
        return False

def hasNumbers(word):
    return any(char.isdigit() for char in word)

def hasChineseCharacter(word):
    return re.search(u'[\u4e00-\u9fff]', word)

def isVosotrosForm(word):
    vosotros_endings = ['áis', 'éis', 'asteis', 'isteis', 'abais', 'íais', 'aréis', 'eréis', 'iréis', 'aríais', 'eríais', 'iríais']
    for ending in vosotros_endings:
        if word.endswith(ending):
            return True
    return False

def isNonSpanishWord(word):
    confidence_value = LANGUAGE_DETECTOR.compute_language_confidence(word, Language.SPANISH)

    if confidence_value > 0.07:
        return False
    else:
        if DEBUG == True:
            print("Word: {0} | Confidence value: {1}".format(word, confidence_value))
        return True

def removeTheFat(word):
    if isEmoji(word):
        return ""
    elif containsSpecialCharacters(word):
        return ""
    elif hasNumbers(word):
        return ""
    elif isVosotrosForm(word):
        return ""
    elif isNonSpanishWord(word):
        return ""
    else:
        return word

#------------------------------------------------------

list_of_parsed_words = []

if INPUT_FILE_ALREADY_PROCESSED == True:
    # Step 0: Words Already Processed and Parsed
    print("Step 0: Words Already Processed and Parsed")

    input_file_name = createUniversalFilePath(INPUT_FILE_NAME)
    file_read_lines = open(input_file_name)
    total_records = float(len(file_read_lines.readlines()))
    count = 1
    in_memory_dictionary = []
    with open(input_file_name, mode='r', encoding='utf8') as file:
        reader = csv.reader(file)
        for row in reader:
            translation_list = []

            deepl_translations = row[3]
            if deepl_translations == "":
                pass
            elif ',' in deepl_translations:
                for trans in deepl_translations.split(','):
                    translation_list.append(trans.strip())
            else:
                translation_list.append(deepl_translations.strip())

            google_translations = row[4]
            if google_translations == "":
                pass
            elif ',' in google_translations:
                for trans in google_translations.split(','):
                    translation_list.append(trans.strip())
            else:
                translation_list.append(google_translations.strip())

            third_party_translations = row[5]
            if third_party_translations == "":
                pass
            elif ',' in third_party_translations:
                for trans in third_party_translations.split(','):
                    translation_list.append(trans.strip())
            else:
                translation_list.append(third_party_translations.strip())

            manual_translations = row[6]
            if manual_translations == "":
                pass
            elif ',' in manual_translations:
                for trans in manual_translations.split(','):
                    translation_list.append(trans.strip())
            else:
                translation_list.append(manual_translations.strip())

            translation_list = list(set(translation_list))

            final_translation = ", ".join(translation_list)
            if final_translation.endswith(', '):
                final_translation = final_translation[:-2]

            word_obj = Word(row[0], row[2], row[1]) # word, pos, gender
            word_obj.translation = final_translation
            word_obj.prevalence = round(((total_records - count) / total_records), 2)
            #print(word_obj.prevalence)
            count += 1
            list_of_parsed_words.append(word_obj)

    list_of_parsed_words.sort(key=lambda x: x.word)

else:
    # Step 1: Linguistic Processing
    print("Step 1: Linguistic Processing")

    # Create in-memory dictionary
    print("Creating in-memory dictionary...")
    input_file_name = createUniversalFilePath(INPUT_FILE_NAME)

    file_read_lines = open(input_file_name)
    total = len(file_read_lines.readlines())

    in_memory_dictionary = []
    with open(input_file_name, mode='r', encoding='utf8') as file:
        count = 0
        for row in file:
            word = row.split(',')[0]
            word = removeTheFat(word)
            count += 1
            showProgress(count, total)
            if word != "":
                in_memory_dictionary.append(word)

    if DEBUG == True:
        in_memory_dictionary = ["bueno", "gato", "como", "de", "a", "Harry", "Potter", "comer"]

    # Tokenize each word
    # only keep verbs in infinitive form
    # only keep nouns that are singular
    # only keep adjectives that are masculine and singular
    print("Tokenizing words...")
    list_of_parsed_words_unfiltered = []
    nlp = spacy.load("es_core_news_md")
    count = 0
    total = len(in_memory_dictionary)
    for word in in_memory_dictionary:
        word_data = nlp(word)
        for token in word_data:
            list_of_parsed_words_unfiltered.append(parseToken(token))
            count += 1
            showProgress(count, total)

    # Remove "NoneType" from list
    list_of_parsed_words = list(filter(lambda item: item is not None, list_of_parsed_words_unfiltered))

if not SKIP_TRANSLATION:
    # Step 2: Translation
    print("Step 2: Translation")

    # Get translation for each word
    print("Fetching translations...")
    count = 0
    total = len(list_of_parsed_words)
    for wordObj in list_of_parsed_words:
        if USE_DEEPL:
            wordObj.translation = getDeepLTranslation(wordObj.word)
        else:
            wordObj.translation = getMultipleTranslations(wordObj.word)
        count += 1
        showProgress(count, total)

# Part 3: Saving to CSV File
print("Part 3: Saving to CSV File")

# Save to csv file
print("Saving to CSV file...")
result_file_exists = os.path.isfile(createUniversalFilePath('result.csv'))
if result_file_exists:
    os.remove(createUniversalFilePath('result.csv'))
result_file = open(createUniversalFilePath('result.csv'), 'a+', encoding="utf8", newline='')
result_file_writer = csv.writer(result_file)

header = ['Spanish Word', 'Translation', 'Prevalence', 'Gender', 'Part-of-Speech']
result_file_writer.writerow(header)

count = 0
total = len(list_of_parsed_words)
for wordObj in list_of_parsed_words:
    row = [wordObj.word, wordObj.translation, wordObj.prevalence, wordObj.gender, wordObj.pos]
    result_file_writer.writerow(row)
    count += 1
    showProgress(count, total)

result_file.flush()
result_file.close()

# --------------------------------------------------

