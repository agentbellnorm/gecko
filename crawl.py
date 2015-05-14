
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import es
import nltk
import nlstructs
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import TreebankWordTokenizer
from nltk.util import ngrams
from elasticsearch import Elasticsearch
import math
import json
from pymongo import MongoClient
import action
import stockretriever
import correlation
from email.utils import parsedate_tz
from datetime import date
stemmer = SnowballStemmer("english")
ES_HOST = {"host" : "localhost", "port" : 9200}
posindex = "gecko_pos"
negindex = "gecko_neg"
negcommand = {"create": {"_index": negindex, "_type": "gram"}}
poscommand = {"create": {"_index": posindex, "_type": "gram"}}
es = Elasticsearch(hosts = [ES_HOST])
negbulk = []
posbulk = []
sp500symbols = open('sp500.csv').read().strip('\n ').split('\n')
symbol = "YHOO"
companyName = "Yahoo"
db = action.action.getConnection();

class Word():
	def __init__(self, w):
		self.original = w.lower()
		self.stemmed = stemmer.stem(w).lower()
		self.pos_tag = nltk.pos_tag([w])[0][1]

class NewsItem():

	def __init__(self, body):
		self.words = []
		self.numPosWords = 0
		self.numNegWords = 0
		self.numWords = 0
		self.raw = body
		self.sentenceTokenize()

	def SO(self):
		bigrams = ngrams(self.toDict(), 2)
		score = 0
		classes =['JJ', 'RB', 'RBR', 'NN']
		for gram in bigrams:
			if nltk.pos_tag([gram[0]])[0][1] in classes:
				# print(nltk.pos_tag([gram[0]])[0][1])
				# print(gram)
				score += self.calc(stemmer.stem(gram[0]), stemmer.stem(gram[1]))
		return score/len(self.words)


	def calc(self, w1, w2):
		w = stemmer.stem(w1)+ " " + stemmer.stem(w2)
		q = {"query":{"match": {"gram" :{"query": w,"minimum_should_match": "2"} }}}
		phraseHitsPos = es.search(index = posindex, body = q, size = 0)['hits']['total']+0.01
		phraseHitsNeg = es.search(index = negindex, body = q, size = 0)['hits']['total']+0.01
		if(phraseHitsNeg < 2 or phraseHitsPos < 2):
			return 0
		else:
			q = {"query":{"match_all" : { } }}
			totalPos = es.search(index = posindex, body = q, size = 0)['hits']['total']
			totalNeg = es.search(index = negindex, body = q, size = 0)['hits']['total']
			SO = math.log((phraseHitsPos*totalNeg)/(phraseHitsNeg*totalPos),2)
			# print("pos: " + str(phraseHitsPos))
			# print("neg: " +str(phraseHitsNeg))
			# print(SO)
			return SO

	def sentenceTokenize(self):
		for word in TreebankWordTokenizer().tokenize(self.raw):
			word = word.strip('.,!\'";:#/&@?+()[]{}-\\\t\n1234567890')
			if word != "" and len(word) > 1:
				#print(word)
				self.words.append(Word(word))

	def toDict(self):
		a = []
		for w in self.words:
			a.append(w.stemmed)
		return a


	def toString(self):
		s = ""
		for w in self.words:
			s += w.stemmed
		s = s.strip(' ')
		return s



class Crawler():

	def getNews(self, symbol):
		url = "http://articlefeeds.nasdaq.com/nasdaq/symbols?symbol="
		req = Request(url+symbol, headers={'User-Agent': 'Mozilla/5.0'})
		data = urlopen(req).read()
		text = data.decode(encoding="ascii", errors="ignore")
		out = self.urlsfrompage(text)
		db.Article.insert(out)

	def urlsfrompage(self, tickerpage):
		objDict = []
		soup = BeautifulSoup(tickerpage)
		for item in soup.find_all('item'):
			titleRatio = self.symbolRatio(symbol, item.title.get_text())
			body = self.getbodyfromURL(item.find('feedburner:origlink').get_text())
			bodyRatio = self.symbolRatio(symbol, body)
			k = 0.2 #the weight of the title ratio vs the bodyratio
			weightedRatio = k * titleRatio + (1 - k) * bodyRatio
			
			if weightedRatio > 0.5:
				tup = parsedate_tz(item.pubdate.get_text())
				x = date(tup[0], tup[1], tup[2])
				doc = NewsItem(body)
				score = doc.SO()
				objDict.append({'body': body,
							   'symbol': symbol,
							   'date': str(x),
							   'title': item.title.get_text(),
							   'sentiment': score,
							   'seen': 'no'})
		return objDict
		
	def getbodyfromURL(self, url):
		req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
		dat = urlopen(req).read()
		text = dat.decode(encoding="ascii", errors="ignore")
		soup = BeautifulSoup(text.encode("ascii"))
		if soup.find("div", {"id": "articlebody"}) is not None:
			article = soup.find("div", {"id": "articlebody"}).encode("ascii")
			article = BeautifulSoup(article.decode("utf-8"))
			s = ""
			for item in article.find_all('div'):
				for string in item.stripped_strings:
					if string.find('@wsj.com', 0, len(string)) > 0:
						return s
					if string.find('Referenced Stocks:', 0, len(string)) > 0:
						return s
					if string.find('ArticleAd();', 0, len(string)) < 0 and string.find('makeAd', 0, len(string)) < 0:
						s += string+" "
			return s.replace('\n', ' ')

		#returns the decimal fraction of how many times a symbol is mentioned over other symbols.
	def symbolRatio(self, symb, text):
		othermentions = 1
		words = text.split(' ')
		words = self.stripList(words)
		symbolmentions = words.count(symb)
		for s in sp500symbols: 
			if(s != symb):
				othermentions += words.count(s)
		return symbolmentions/othermentions

	def stripList(self, l):
		r = []
		for w in l:
			r.append(w.strip('",:!?-'))
		return r

#print('Wed, 29 Apr 2015 17:17:31 Z'.replace('Z','+0000'))
#x = parsedate_tz('Wed, 29 Apr 2015 17:17:31 Z')
# c = Crawler()
# c.getNews(symbol)
res = list(db.Article.find({'seen':"no"}))
dates = []
scores = []
for o in res:
	dt = o['date']
	dt = dt.split('-')
	dt = date(int(dt[0]), int(dt[1]), int(dt[2])) 
	dates.append(dt)
	scores.append(o['sentiment'])
print(scores)

print(correlation.regress(scores, dates, symbol))


