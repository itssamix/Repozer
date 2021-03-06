# -*- coding: utf-8 -*-
##
##
## This file is part of Indico.
## Copyright (C) 2002 - 2013 European Organization for Nuclear Research (CERN).
##
## Indico is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 3 of the
## License, or (at your option) any later version.
##
## Indico is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Indico;if not, see <http://www.gnu.org/licenses/>.
from flask import session

import os, re, datetime, cgi, time, copy
from indico.ext.search.base.implementation import SearchEngineCallAPIAdapter, Author, SearchResult, SubContributionEntry, ContributionEntry, ConferenceEntry, SEATranslator
import indico.ext.search.repozer
import MaKaC.conference as conference
from indico.core.config import Config
from MaKaC.common.output import XSLTransformer
from MaKaC.common.logger import Logger
from MaKaC.common.contextManager import ContextManager
from MaKaC.conference import ConferenceHolder
from MaKaC.webinterface import urlHandlers
from MaKaC.common.timezoneUtils import DisplayTZ

from xml.dom import minidom
from urllib import urlencode
import urllib2
from MaKaC.plugins.base import PluginsHolder
from indico.ext.search.repozer.repozeIndexer import RepozeCatalog, RepozerMaterial
from datetime import datetime
import time
from pytz import timezone
import Utils as ut

# Ictp: without this, apache wont recognize repozer export :(
import indico.ext.search.repozer.http_api

from repozerQueryManager import RepozerQueryManager
from indico.ext.search.repozer.options import availableKeywords as keywords
from indico.ext.search.repozer.options import confCatalog, contribCatalog, matCatalog




SEA = SEATranslator("repozer")

class SearchResultRepozer(object):    
    
    def __init__(self, fid):
        self._fid = fid
        self.confId, self.sessionId, self.talkId, self.materialId = self._fid.split("|") 
        self.ch = ConferenceHolder()
            
    def isVisible(self, user):
        # Only PUBLIC documents are Indexed
        return True
#        target = self.getTarget()
#        if target:
#            return target.canView(user)
#        else:
#            Logger.get('search').warning("referenced element %s does not exist!" % self.getCompoundId())
#            return False
            
    @classmethod
    def create(cls, fid):
        if ut.getTypeFromFid(fid) == 'Conference':
            return ConferenceEntryRepozer(fid)
        if ut.getTypeFromFid(fid) == 'Contribution':
            return ContributionEntryRepozer(fid)
        if ut.getTypeFromFid(fid) == 'Material':
            return MaterialEntryRepozer(fid)



class ConferenceEntryRepozer(SearchResultRepozer):
        
    def getId(self):
        return self.confId

    def getTitle(self):
        if self.getTarget():
            return self.getTarget().getTitle()
        else:
            return ''

    def getStartDate(self, aw):
        tzUtil = DisplayTZ(aw,self.getConference())
        locTZ = tzUtil.getDisplayTZ()
        
        if self.getTarget():
            return self.getTarget().getStartDate().astimezone(timezone(locTZ))
        else:
            return None    

    def getEndDate(self, aw):
        tzUtil = DisplayTZ(aw,self.getConference())
        locTZ = tzUtil.getDisplayTZ()
        
        if self.getTarget():
            return self.getTarget().getEndDate().astimezone(timezone(locTZ))
        else:
            return None    


    def getConference(self):
        try:
            return self.ch.getById(self.confId)
        except:
            return None

    def getDescription(self):
        if self.getTarget():
            return self.getTarget().getDescription()
        else:
            return ''
    
    def getDescriptionText(self):        
        # this is to avoid partial HTML 
        return ut.getTextFromHtml(self.getDescription())
   
    def getTarget(self):
        return self.getConference()
    
    def getCompoundId(self):
        return "%s" % self.getId()
                
    def getURL(self):
        return str(urlHandlers.UHConferenceDisplay.getURL(confId=self.getId()))    



class ContributionEntryRepozer(ConferenceEntryRepozer):

    def getId(self):
        return self.talkId 
                            
    def getContribution(self):
        try:
            return self.ch.getById(self.confId).getContributionById(self.talkId)
        except:
            return None
            
    def getTarget(self):
        return self.getContribution()
        
    def getURL(self):
        return str(urlHandlers.UHContributionDisplay.getURL(confId=self.confId, contribId=self.getId()))


class MaterialEntryRepozer(ConferenceEntryRepozer,RepozerMaterial):

    def __init__(self, fid=None):
        self._fid = fid
        self.confId, self.sessionId, self.talkId, self.materialId = self._fid.split("|") 
        self.ch = ConferenceHolder()
        conf = self.ch.getById(self.confId)
        self.matId, self.resId = self.materialId.split('/')
        if not(self.resId) or self.resId == 'not assigned': self.resId = '0'
        obj = None
        if self.talkId: # Material inside Talk
            if self.sessionId: # Talk inside Session
                s = conf.getSessionById(self.sessionId)
                obj = s.getContributionById(self.talkId)
            else: obj = conf.getContributionById(self.talkId)
        else: obj = conf
        self.mat = None
        if obj: self.mat = obj.getMaterialById(self.matId)        
        self.robj = None
        self.ext = ''
        if self.mat:
            self.res = self.mat.getResourceById(self.resId)
            self.robj = RepozerMaterial(self.res)
            self.ext = self.robj.ext
            
    def isVisible(self, user):
        # Only PUBLIC documents are Indexed
        return True
        
    def getMaterial(self):
        try:
            return self.robj
        except:
            return None
    
    def getTitle(self):
        if not(self.robj):
            return "- NO TITLE -"
        else:
            return self.robj.getTitle()
    
    def getDescription(self):
        return ''
                    
    def getStartDate(self, aw):
        return None

    def getEndDate(self, aw):
        return None
                
    def getTarget(self):
        return self.getMaterial()
        
    def getURL(self):
        suffix = ''
        if self.sessionId: suffix += '/session/' + self.sessionId
        if self.talkId: suffix += '/contribution/' + self.talkId
        suffix += '/material/' + self.materialId + self.ext            
        return self.ch.getById(self.confId).getURL().replace('/e/','/event/') + suffix
        
        
class RepozerBaseSEA:
    _id = "repozer"

    def __init__(self, **params):
        self._userLoggedIn = params.get("userLoggedIn", False)
        self._target = params.get("target", None)
        self._page = params.get("page", 1)
        self._noQuery = False
        # this is used also as query limit. default was 25. 
        # WARNING: paging needs to be implemented
        self._pagination = 250

        if self._userLoggedIn:
            self._sessionHash = '%s_%s' % (session.sid, session.user.getId())
        else:
            self._sessionHash = 'PUBLIC'

        self._searchCategories = False
        


    def isSearchTypeOnlyPublic(self):
        #return self.getVarFromPluginStorage("type") != "private"
        return True

    
    @SEA.translate ('f',[],'p')
    def translateFieldAuthor(self, field):
        if field == "author":
            return "author:"
        else:
            return ""

    @SEA.translate ('p', 'text', 'p')
    def translatePhrase(self, phrase):
        return phrase

    @SEA.translate(['startDate', 'endDate'],'date', 'p')
    def translateDates(self, startDate, endDate):
        if startDate != '':
            startDate = time.strftime("%Y-%m-%d", time.strptime(startDate, "%d/%m/%Y"))
        if endDate != '':
            endDate = (datetime.datetime.strptime(endDate, "%d/%m/%Y") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        if startDate != '' and endDate != '':
            return '"%s"->"%s"' % (startDate, endDate)
        elif startDate != '':
            return '"%s"->"2100"' % (startDate)
        elif endDate != '':
            return '"1950"->"%s"' % (endDate)
        else:
            return ""

    @SEA.translate ('f',[],'f')
    def translateField(self, field):
        if field == "author":
            return ""
        else:
            return field

    @SEA.translate ('startRecord',[],'jrec')
    def translateStartRecord(self, startRecord):
        return startRecord

    @SEA.translate ('numRecords',[],'rg')
    def translateNumRecords(self, numRecords):
        return numRecords

    @SEA.translate ('collections','text','collections')
    def translateCollections(self, collections):
        return collections
        
    @SEA.translate ('wildcards','text','wildcards')
    def translateWildcards(self, wildcards):
        return wildcards
        
    @SEA.translate ('sortField',[],'sortField')
    def translateSortField(self, sortField):
        return sortField

    @SEA.translate ('sortOrder',[],'sortOrder')
    def translateSortOrder(self, sortOrder):
        return sortOrder

    @SEA.translate ('category', 'text', 'category')
    def translateCategory(self, phrase):
        return phrase
    
    @SEA.translate ('keywords', 'text', 'keywords')
    def translateKeywords(self, keywords):
        return keywords  
        
    @SEA.translate ('limit', 'text', 'limit')
    def translateKeywords(self, limit):
        return limit  
                

class RepozerSEA(RepozerBaseSEA, SearchEngineCallAPIAdapter):
    """
        Search engine adapter for Repoze.
    """
    _implementationPackage = indico.ext.search.repozer

    def __init__(self, **params):
        RepozerBaseSEA.__init__(self, **params)

    def _processElem(self, fid):
        if fid:
            return SearchResultRepozer.create(fid)


    def preProcess(self, results):
        result = []
        for res in results:
            pp = self._processElem(res)
            if pp: result.append(pp)
        return result


    def _loadBatchOfRecords(self, user, number, start):

        record = start

        # by default, we should have several pages of results
        shortResult = False

        # if we're searching the private repository,
        # always request twice the number of items per page
        # (in order to account for invisible records)
        if self._userLoggedIn:
            numRequest = number * 2
        else:
            # ask always for an extra one, in order
            # to know if we reached the end
            numRequest = number+1

        results, fResults = [], []

        while (len(fResults) < number):

            Logger.get("search").debug("asking %s->%s from server" % (start, numRequest))

            
            (numHits, r) = self.obtainRecords(startRecord=start,
                                                   numRecords=numRequest,
                                                   collections=self._filteredParams['collections'],
                                                   startDate = self._filteredParams['startDate'],
                                                   endDate = self._filteredParams['endDate'],
                                                   category = self._filteredParams['category'],
                                                   keywords = self._filteredParams['keywords'],
                                                   p = self._filteredParams['p'],
                                                   f = self._filteredParams['f'],
                                                   wildcards = self._filteredParams['wildcards'],
                                                   sortField = self._filteredParams['sortField'],
                                                   sortOrder = self._filteredParams['sortOrder'],
                                                   limit = self._filteredParams['limit']
                                                   )
                                                   
            results.extend(r)
            
            # filter
            allResultsFiltered = False
            for r in results:
                if len(fResults) == number or len(fResults) == numHits:
                    break
                if r.isVisible(user):
                    fResults.append(r)
                record += 1
            else:
                allResultsFiltered = len(fResults) > 0


            if record > numHits or numHits <= number or len(results) <= number or (allResultsFiltered and len(fResults) <= number):
                shortResult = True
                break

            Logger.get("search").debug("fResults (%s)" % len(fResults))

            start += numRequest

        Logger.get("search").debug("%s %s %s" % (len(fResults), numHits, number))
        
        return (fResults, numHits, shortResult, record)


    def obtainRecords(self,**kwargs):
        """
            The main processing cycle. Translates the search request parameters
            from the web interface to those of the target search engine.

            @param kwargs: Input parameters

        """
        
        Logger.get('search.SEA').debug('Translating parameters...')
        #finalArgs = self.translateParameters(kwargs)
        finalArgs = kwargs

        Logger.get('search.SEA').debug('Fetching results...')
        (numPreResults, preResults) = self._fetchResultsFromServer(finalArgs )

        Logger.get('search.SEA').debug('Preprocessing results...')

        results = self.preProcess(preResults)

        Logger.get('search').debug('Done!')

        return (numPreResults, results)



    def _fetchResultsFromServer(self, parameters):

        # add dictonary keys for RepozerQueryManager        
        if parameters.has_key('p'):
            parameters['text'] = parameters['p']
        if parameters.has_key('sortField'):
            parameters['sort_field'] = parameters['sortField']
        if parameters.has_key('startDate') and parameters['startDate']:
            parameters['start_date'] = time.strftime("%Y/%m/%d", time.strptime(parameters['startDate'], "%d/%m/%Y"))
        if parameters.has_key('endDate')and parameters['endDate']:
            parameters['end_date'] = time.strftime("%Y/%m/%d", time.strptime(parameters['endDate'], "%d/%m/%Y"))
        if parameters.has_key('sortOrder'):
            if parameters['sortOrder'] != 'a':
                parameters['desc'] = 1     
        if parameters.has_key('f'):
            parameters['where'] = parameters['f']
        if parameters.has_key('numRecords'):
            parameters['limit'] = parameters['numRecords']

        # do not convert to Conference objects
        parameters['onlyFids'] = True
        
        # remove val = ''
        p = {}
        for par in parameters.keys():
            if parameters[par] != '':
                p[par] = parameters[par]
                         
        rqm = RepozerQueryManager(p)
        numdocs, results = rqm.getResults()      
                             
        return (numdocs, results)


    def _getResults(self, number):

        params = copy.copy(self._filteredParams)
        params['target'] = self._target.getId()

        queryHash = self._getQueryHash(params)

        Logger.get('search').debug('Hashing %s to %s' % (params, queryHash))

        # ATTENTION: _getStartingRecord will set self._page to 1,
        # if there's a cache miss
        start, cachedObj = self._getStartingRecord(queryHash, self._page)

        # get the access wrapper, so we can check user access privileges
        user = ContextManager.get("currentRH", None).getAW()

        results, numHits, shortResult, record = self._loadBatchOfRecords(user, number, start)

        self._cacheNextStartingRecord(queryHash, self._page, record, cachedObj)

        return (numHits, shortResult, record, results)

    def process(self, filteredParams):

        self._filteredParams = filteredParams
        phrase = self._filteredParams.get('p', '')
        if phrase.strip() == '':
            self._noQuery = True

        params = copy.copy(self._filteredParams)
        
        nEvtRec, nContRec = 0, 0
        numEvtHits, numContHits = 0, 0
        eventResults, contribResults = [], []
        
        numEvtHits, evtShortResult, nEvtRec, eventResults = self._getResults(self._pagination)
        params['evtShortResult'] = evtShortResult

        params['p'] = cgi.escape(phrase, quote=True)
        params['f'] = cgi.escape(filteredParams.get('f', ''), quote=True)

        params['eventResults'] = eventResults
        params['contribResults'] = contribResults
                
        categories = {}

        for cat in conference.CategoryManager().getList():
            catparent = cat.getOwner()
            if catparent and catparent.getCategory().getId() == '0':
                categories[cat.getId()] = cat.name

        #keywords = []
#         for conf in conference.ConferenceHolder().getValuesToList():
#             for keyword in conf.getKeywords().split('\n'):
#                 if not(keyword in keywords) and not(keyword.startswith('smr')) and not(keyword.startswith('expparts')) and not(keyword.startswith('siscode')) and keyword != '':
#                     keywords.append(keyword)
                    
        # To get a faster response, comment the above lines and use a static keywords definitions.
        #keywords.sort()
        
        params['categories'] = categories
        params['avakeywords'] = keywords

        params['nEventResult'] = nEvtRec
        params['nContribResult'] = nContRec

        params['numHits'] = numEvtHits + numContHits
        params['page'] = self._page

        params['targetObj'] = self._target

        params['searchingPublicWarning'] = self.isSearchTypeOnlyPublic() and not self._userLoggedIn
        params['accessWrapper'] = ContextManager().get("currentRH", None).getAW()

        return params
