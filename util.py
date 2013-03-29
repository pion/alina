from alina.conf import get_stop_words, replace
from alina.porter_stemmer import PorterStemmer
from alina.publisher import CsvPublisher, JsonPublisher, WordCounter
from alina.reader import FacebookPostsReaderIterator, FileReaderIterator, json_read
import inflect
import re

STEMMER = PorterStemmer()
INFLECT = inflect.engine()

def _to_str(data):
    ret = {}
    for key, value in data.items():
        ret[_encode(key)] = _encode(value)
    return ret
        
def _encode(value):
    return unicode.encode(value, 'utf-8')    

def collect_facebook_posts(name, token, last_post_date = None, page_size = 25):    
    fbk_reader = FacebookPostsReaderIterator(name, token, 
                                         last_post_date, limit = page_size)

    json_pub = JsonPublisher("data/" + name + ".txt", "data/meta_" + name + ".txt")
    collect(fbk_reader, json_pub)

def same(elem):
    return elem

def no_filter(elem):
    return True

def collect(reader, publisher, convert_function = same, filter_function = no_filter):
    try:
        publisher.prepare()
        for page in reader:
            for elem in page:
                if filter_function(elem):
                    publisher.publish(convert_function(elem))
    finally:        
        publisher.close()

def convert_fbk_json_to_simple_json(json_obj):
    message = ''
    if json_obj.has_key('message'):
        message = json_obj['message']
    
    return {'name' : json_obj['from']['name'], 
            'message' : message, 
            'created_time' : json_obj['created_time']}

def convert_json_to_csv(json_obj):
    message = ''
    if json_obj.has_key('message'):
        message = json_obj['message']
        
    return ",".join([json_obj['from']['name'], message, json_obj['created_time']])

def between(date1, date2):
    def _between(elem):
        if elem.has_key('created_time'):
            c_time = elem['created_time'][:10]
            return c_time >= date1 and c_time <= date2
        return False
    return _between

def before(date1):
    def _before(elem):
        if elem.has_key('created_time'):
            c_time = elem['created_time'][:10]
            return c_time <= date1
        return False
    return _before    

def after(date1):
    def _after(elem):
        if elem.has_key('created_time'):
            c_time = elem['created_time'][:10]
            return c_time >= date1
        return False
    return _after

def clean_string(word):
    return clean(word, lambda(w): INFLECT.singular_noun(w) or w)

def clean_as_list(word, fun = same):
    # 0 clear any URL
    word = re.sub(r"\.", '', word)
    word = re.sub(r"http://\w+(/\w*)?", '', word)
    
    # 1 make the replacements
    text = replace(word)
    # 2 get only the words
    
    # 3 lower
    words = map(lower, re.findall(r"\w+\'?\w+", text))
    
    # 4 remove stop words
    
    # 5 apply the fun
    return [fun(w) for w in words if w not in get_stop_words()]

def clean(word, fun = same):
    return " ".join(clean_as_list(word, fun))

def lower(word):
    return word.lower()

def clean_stem(word):
    return clean(word, lambda(w): STEMMER.stem2(word))

def convert_json_to_clean_csv(json_obj):
    message = ''
    if json_obj.has_key('message'):
        message = json_obj['message']
        
    return ",".join([json_obj['from']['name'], clean_string(message), json_obj['created_time']])

def convert_json_to_word_list(json_obj):
    message = ''
    if json_obj.has_key('message'):
        message = json_obj['message']
    return clean_as_list(message)
	
def collect_posts_and_count_words(persons, token, since = None, until = None):
	if since is None:
		if until is None:
			filter_fun = no_filter
		else:
			filter_fun = before(until)
	else:
		if until is None:
			filter_fun = after(since)
		else:
			filter_fun = between(since, until)
			
	for person in persons:
		w = WordCounter()
		collect_facebook_posts(person, token)
		collect(FileReaderIterator("data/" + person + ".txt", json_read), 
				w, 
				convert_function = convert_json_to_word_list,
				filter_function = filter_fun)

		w.dump("data/word_count" + person + ".txt")