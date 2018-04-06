#!/usr/bin/python

import logging
import nltk
import string

from optparse import OptionParser
from sklearn.feature_extraction.text import TfidfVectorizer
from Utils import Utilities

nltk.download('punkt') # if necessary...

class Similarity:
  def __init__(self, **kwargs):
    try:
      self.stemmer = nltk.stem.porter.PorterStemmer()
      self.remove_punctuation_map = dict((ord(char), None) 
                                        for char in string.punctuation)
      self.vectorizer = TfidfVectorizer(tokenizer=self.normalize, 
                                        stop_words='english')

      self.others = None
      self.base = None
      # Generating instance of strategy 
      for key, value in kwargs.iteritems():
        if "base" == key:
          self.base = value
        elif "others" == key:
          self.others = value
    except Exception as inst:
      Utilities.ParseException(inst)

  def stem_tokens(self, tokens):
    return [self.stemmer.stem(item) for item in tokens]

  def normalize(self, text):
    '''remove punctuation, lowercase, stem'''
    return self.stem_tokens(
              nltk.word_tokenize(
                  text.lower().translate(
                      self.remove_punctuation_map)))

  def cosine_sim(self, text1, text2):
    tfidf = self.vectorizer.fit_transform([text1, text2])
    return ((tfidf * tfidf.T).A)[0,1]

  def score(self, base, other):
    try:
      other = other.replace(".", " ").strip()
      complete_phrase = 1.0 if base.strip() in other else 0.0
      similarity = self.cosine_sim(base, other)
      #print "=== similarity:", similarity
      score = (complete_phrase+similarity)/2.0
      return score
    except Exception as inst:
      Utilities.ParseException(inst)

def example4(task):
  logger = Utilities.GetLogger(LOG_NAME, useFile=False)
  try:

    base = "Tron"
    others = [
    "Pain and Gain 2013 720p WEBRip x264 AC3-TRON",
    "Avengers.Age.of.Ultron.2015.1080p.3D.BluRay.Half-SBS.x264.DTS-HD.MA.7.1-RARBG",
    "Gra o Tron Sezon 1 720p.BDRip.XviD.AC3-ELiTE Lektor PL Pawulon (krzysiekvip2)",
    "Gra o Tron Sezon 2 720p.BDRip.XviD.AC3-ELiTE Lektor PL Pawulon (krzysiekvip2)",
    "TRON Legacy 2010 [English] DVDRip (XViD)",
    "Avengers.Age.of.Ultron.2015.1080p.BluRay.REMUX.AVC.DTS-HD.MA.7.1-RARBG",
    "Gra o Tron Sezon 3 720p.BDRip.XviD.AC3-ELiTE Lektor PL Pawulon (krzysiekvip2)",
    "Stronger.2017.1080p.BluRay.REMUX.AVC.DTS-HD.MA.5.1-FGT",
    "Il Trono di Spade - Game of Thrones -Stagione 1 [HDTVMux720p.Ita][Nautilus-BT] (PittaSk8)",
    "Avengers.Age.of.Ultron.2015.1080p.3D.BluRay.AVC.DTS-HD.MA.7.1-RARBG",
    "Tron.1982.Bluray.1080p.DTS-HD.x264-Grym (vonRicht)",
    "Game of Thrones - S03 Complete - 1080p x264 ENG-ITA BluRay - Il Trono Di Spade (2013) (ShivaShanti2)",
    "WII Tron Evolution Battle Grids n Space Disney Interactive Studios PAL ESPALWII ..",
    "Snitch 2013 720p HDRip AAC-TRON",
    "FAST & FURIOUS 2009 DVDRIP DALE-0-TRON(TRN)",
    "Tron.Legacy.2010.BluRay.1080p.DTS.x264-CHD (dontamil)",
    "Tron.Legacy.2010.Bluray.1080p.DTS-HD7.1.x264-Grym (vonRicht)"
    ]

    print "Base:", base
    for other in others:
      print "\t", task.score(base, other), ":", other
  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)

def example3(task):
  logger = Utilities.GetLogger(LOG_NAME, useFile=False)
  try:

    base = "Star Wars The Last Jedi"
    others = [
    "Star Wars The Last Jedi (2017) Untouched HINDI CAM MovCR com Exc",
    "Star Wars The Last Jedi 2017 FULL HDCAM ENGLiSH x264 HQMIC-DADDY (Silmarillion)",
    "Star Wars The Last Jedi 2017 FULL HDCAM ENGLiSH x264 HQMIC-DADDY (MrStark)",
    "Star Wars The Last Jedi 2017 FULL HDCAM ENGLiSH x264 HQMIC-DADDY  (MrStark)",
    "Star Wars The Last Jedi 2017 FULL HDCAM ENGLiSH x264 HQMIC-DADDY (mazemaze16)",
    "Star.Wars.The.Last.Jedi.2017.CAM.X264-BebeLeitinho (Supernova)",
    "Star.Wars.The.Last.Jedi.2017.CAM.XViD-26k (mazemaze16)",
    "Star.Wars.The.Last.Jedi.HDCAM.720p.x264.Korean.Hardcoded (Anonymous)",
    "Star Wars The Last Jedi HDCAM 720p x264 Korean Hardcoded",
    "8  Star Wars The Last Jedi 2017 TS 720.."
    ]

    print "Base:", base
    for other in others:
      print "\t", task.score(base, other), ":", other
  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)

def example2(task):
  logger = Utilities.GetLogger(LOG_NAME, useFile=False)
  try:
    base = "Star Wars Episode 8"
    others = [
    "Star Wars Episode III - Revenge of the Sith 2005 BluRay 1080p DTS LoNeWolf (bobnjeff)",
    "Star Wars Episode II - Attack of the Clones 2002 BluRay 1080p DTS LoNeWolf (bobnjeff)",
    "(Fan Edit) Star Wars Episode VII: The Force Awakens - Restructured V2 1080p (kirkafur)",
    "Star Wars: Episode V - The Empire Strikes Back (1980) 1080p BrRip x264 - YIFY",
    "Star Wars Episode VII The Force Awakens 2015 1080p BluRay x264 DTS-JYK",
    "Star Wars: Episode II - Attack of the Clones (2002) 1080p BrRip x264 - YIFY",
    "Star Wars: Episode VI - Return of the Jedi (1983) 1080p BrRip x264 - YIFY",
    "Star Wars: Episode VII - The Force Awakens (2015) 1080p BluRay - 6CH - 2 5GB - S..",
    "Star Wars Episode II Attack Of The Clones 2002 MULTI UHD 4K x264 (SaM)",
    "Star.Wars.Episode.VII.The.Force.Awakens.2015.1080p.BluRay.REMUX. (Anonymous)"
    ]

    print "Base:", base
    for other in others:
      print "\t", task.score(base, other), ":", other
  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)

def example1(task):
  logger = Utilities.GetLogger(LOG_NAME, useFile=False)
  try:
    base = "Blade Runner 2049"
    others = [
    "Blade Runner 2049 2017 NEW HD-TS X264 HQ-CPG (xxxlavalxxx)",
    "Blade Runner 2049.1080p.WEB-DL.H264.AC3-EVO (mazemaze16)",
    "Blade Runner 2049 2017 NEW HD-TS X264 HQ-CPG (makintos13)",
    "Blade Runner 2049 2017 1080p WEBRip 6CH AAC x264 - EiE (samcode4u)",
    "Blade Runner 2049 2017 FULL CAM x264 - THESTiG (makintos13)",
    "Blade Runner 2049 2017 1080p WEB-DL DD5.1 x264-PSYPHER (ViVeKRaNa)",
    "Blade Runner 2049 720p WEB-DL H264 AC3-EVO[EtHD]",
    "Blade Runner 2049 (2017) 1080p WEB-DL 6CH 2.7GB - MkvCage (MkvCage)",
    "Blade Runner 2049 2017 1080p WEB-DL DD5 1 H264-FGT",
    "Blade Runner 2049 1080p WEB-DL X264 6CH HQ-CPG",
    "Blade Runner 2049 1080p WEB-DL H264 AC3-EVO[EtHD]",
    "Blade Runner 2049 2017 iTA ENG MD-AC3 WEBDL 1080p x264-BG mkv",
    "Blade Runner 2049 2017 1080p WEB-DL x265 HEVC 6CH-MRN (MRNTUT)"
    ]

    print "Base:", base
    for other in others:
      print "\t", task.score(base, other), ":", other
  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)

LOG_NAME = 'Similarity'
def call_task():
  ''' Command line method for running sniffer service'''
  try:
    
    logger = Utilities.GetLogger(LOG_NAME, useFile=False)
    logger.debug('Calling task from command line')
    args = {}
    #base, others = example1()
    #args.update({'base': base})
    #args.update({'others': others})

    taskAction = Similarity(**args)
    example1(taskAction)
    example2(taskAction)
    example3(taskAction)
    example4(taskAction)

  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)

if __name__ == '__main__':
  logger = Utilities.GetLogger(LOG_NAME, useFile=False)
  
  myFormat = '%(asctime)s|%(name)30s|%(message)s'
  logging.basicConfig(format=myFormat, level=logging.DEBUG)
  logger        = Utilities.GetLogger(LOG_NAME, useFile=False)
  logger.debug('Logger created.')
  
  #usage = "usage: %prog option1=string option2=bool"
  #parser = OptionParser(usage=usage)
  #parser.add_option('--text1',
                      #action="append",
                      #default=None,
                      #help='Write here something helpful')
  #parser.add_option("--opt2", 
                      #action="store_true", 
                      #default=False,
                      #help='Write here something helpful')
    
  #(options, args) = parser.parse_args()
  
  #if options.opt1 is None:
    #parser.error("Missing required option: --opt1='string'")
    #sys.exit()
    
  call_task()