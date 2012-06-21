import urllib2
import json
import string
import hashlib
import uuid
import os
import cookielib
import gzip
import StringIO
import random
import re
import math
import time
import downloadHandler
from urlgrabber.keepalive import HTTPHandler

class grooveshark:
    '''Handles all the network stuff'''

    downloader = downloadHandler.downloadHandler()

    URL = "https://grooveshark.com"
    USERAGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:12.0) Gecko/20100101 Firefox/12.0"
    COOKIEFILE = "groovy.cookie"

    jsQueue = {}
    jsQueue["client"] = "jsqueue"
    jsQueue["clientRevision"] = "20120312.08"
    jsQueue["secret"] = "circlesAndSquares"
    jsQueue["headers"] = {
                         "User-Agent":USERAGENT,
                         "Host":"grooveshark.com",
                         "Accept-Encoding":"gzip, deflate",
                         "Content-Type":"application/json",
                         "Accept-Language":"da,en-us;q=0.7,en;q=0.3"
                         }

    htmlshark = {}
    htmlshark["client"] = "htmlshark"
    htmlshark["clientRevision"] = "20120312"
    htmlshark["secret"] = "reallyHotSauce"
    htmlshark["headers"] = {
                         "User-Agent":USERAGENT,
                         "Host":"grooveshark.com",
                         "Accept-Encoding":"gzip, deflate",
                         "Content-Type":"application/json",
                         "Accept-Language":"da,en-us;q=0.7,en;q=0.3"
                         }

    #Setting the static header (Country, session and uuid)
    h = {}
    h["country"] = {}
    h["country"]["CC1"] = 72057594037927940
    h["country"]["CC2"] = 0
    h["country"]["CC3"] = 0
    h["country"]["CC4"] = 0
    h["country"]["ID"] = 57
    h["country"]["IPR"] = 0
    h["privacy"] = 0
    h["uuid"] = str.upper(str(uuid.uuid4()))

    token = None
    session = None
    userTrackingID = None
    queueID = None
    cj = None
    tokenExpires = None

    def __init__(self):
        self.installHandlers()
        self.getSession()
        self.doCrossdomainRequest()
        self.getToken()
        self.getCountry()
        self.generateQueueID()

    def installHandlers(self):
        global cj
        #Install support for KeepAlive and HTTP/1.1, via urlgrabber (older versions) 
        keepalive_handler = HTTPHandler()
        opener = urllib2.build_opener(keepalive_handler)
        urllib2.install_opener(opener)

        #Install cookielib for easy cookie management
        self.cj = cookielib.LWPCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        urllib2.install_opener(opener)

        #Proxy stuff, used for testing, might be added at a later date
        #proxy = urllib2.ProxyHandler({"https":"119.252.160.34:8000"})
        #opener = urllib2.build_opener(proxy)
        #urllib2.install_opener(opener)

    def parseMainPage(self, html):
        global userTrackingID
        matchObj = re.search(r'"userTrackingID":[^}]*', html, re.I|re.M)
        if matchObj:
            matchObj = re.search(r"[0123456789]+", matchObj.group(), re.I|re.M)
            if matchObj:
                self.userTrackingID = matchObj.group()
                return
        raise SyntaxError("TrackingID not found")

    def readSession(self):
        for cookie in self.cj:
            if cookie.name == "PHPSESSID":
                session = cookie.value
                return session
        return

    def doCrossdomainRequest(self):
        req = urllib2.Request(self.URL + "/crossdomain.xml?20120312.08")
        page = urllib2.urlopen(req)
        page.read()

    def getSession(self):
        global session

        if os.path.isfile(self.COOKIEFILE):
            self.cj.load(self.COOKIEFILE)
        req = urllib2.Request(self.URL)
        page = urllib2.urlopen(req)
        self.parseMainPage(page.read())
        self.session = self.readSession()
        self.cj.save(self.COOKIEFILE)

    def getCountry(self):
        p = {}
        p["header"] = {}
        p["header"]["session"] = self.session
        p["header"]["client"] = self.jsQueue["client"]
        p["header"]["clientRevision"] = self.jsQueue["clientRevision"]
        p["header"]["token"] = self.generateToken("getCountry", self.jsQueue["secret"])
        p["header"]["privacy"] = self.h["privacy"]
        p["header"]["uuid"] = self.h["uuid"]
        p["method"] = "getCountry"
        p["parameters"] = {}
        page = urllib2.urlopen(self.createRequest(p, self.jsQueue))
        self.h["country"] = json.JSONDecoder().decode(gzip.GzipFile(fileobj=(StringIO.StringIO(page.read()))).read())["result"]


    def createHeader(self, data, client, method = None):
        data["header"] = self.h
        data["header"]["session"] = self.session
        data["header"]["client"] = client["client"]
        data["header"]["clientRevision"] = client["clientRevision"]
        if method:
            data["header"]["token"] = self.generateToken(method, client["secret"])
            data["method"] = method
        return data

    def createRequest(self, data, client):
        return urllib2.Request(self.URL + "/more.php?" + data["method"], json.JSONEncoder().encode(data), client["headers"])

    def generateQueueID(self):
        global queueID
        part1 = self.userTrackingID + str(math.floor(time.time()))
        part2 = str(math.floor(random.random() * 500))
        while len(part2)<3:
            part2 = "0" + part2
        self.queueID = part1 + part2

    def generateToken(self, methodName, secret):
        if (self.tokenExpires and self.tokenExpires > time.time()):
            rnd = (''.join(random.choice(string.hexdigits) for x in range(6))).lower()
            return rnd + hashlib.sha1('%s:%s:%s:%s' % (methodName, self.token, secret, rnd)).hexdigest()
        else:
            self.getToken()
            return self.generateToken(methodName, secret)

    def getToken(self):
        global token, tokenExpires
        p = {}
        p["parameters"] = {}
        p["parameters"]["secretKey"] = hashlib.md5(self.session).hexdigest()
        p["method"] = "getCommunicationToken"
        p = self.createHeader(p, self.htmlshark)
        page = urllib2.urlopen(self.createRequest(p, self.htmlshark))
        result = json.JSONDecoder().decode(gzip.GzipFile(fileobj=(StringIO.StringIO(page.read()))).read())["result"]
        if result:
            self.tokenExpires = time.time() + (60 * 25)
            self.token = result
        else:
            raise KeyError("Couldn't get token")

    def getResultsFromSearch(self, query, what="Songs"):
        p = {}
        p["parameters"] = {}
        p["parameters"]["type"] = what
        p["parameters"]["query"] = query
        p = self.createHeader(p, self.htmlshark, "getResultsFromSearch")
        page = urllib2.urlopen(self.createRequest(p, self.htmlshark))
        j = json.JSONDecoder().decode(gzip.GzipFile(fileobj=(StringIO.StringIO(page.read()))).read())
        try:
            return j["result"]["result"]["Songs"]
        except:
            return j["result"]["result"]

    def getStreamKeyFromSongIDEx(self, id):
        p = {}
        p["parameters"] = {}
        p["parameters"]["type"] = 0
        p["parameters"]["mobile"] = False
        p["parameters"]["prefetch"] = False
        p["parameters"]["songID"] = id
        p["parameters"]["country"] = self.h["country"]
        p = self.createHeader(p, self.jsQueue, "getStreamKeyFromSongIDEx")
        page = urllib2.urlopen(self.createRequest(p, self.jsQueue))
        return json.JSONDecoder().decode(gzip.GzipFile(fileobj=(StringIO.StringIO(page.read()))).read())["result"]

    def addSongsToQueue(self, songObj, source = "user"):    
        queueObj = {}
        queueObj["songID"] = songObj["SongID"]
        queueObj["artistID"] = songObj["ArtistID"]
        queueObj["source"] = source
        queueObj["songQueueSongID"] = 1
    
        p = {}
        p["parameters"] = {}
        p["parameters"]["songIDsArtistIDs"] = []
        p["parameters"]["songIDsArtistIDs"].append(queueObj)
        p["parameters"]["songQueueID"] = self.queueID
        p = self.createHeader(p, self.jsQueue, "addSongsToQueue")
        page = urllib2.urlopen(self.createRequest(p, self.jsQueue))
        return json.JSONDecoder().decode(gzip.GzipFile(fileobj=(StringIO.StringIO(page.read()))).read())["result"]

    def removeSongsFromQueue(self, userRemoved = True):
        p = {}
        p["parameters"] = {}
        p["parameters"]["songQueueID"] = self.queueID
        p["parameters"]["userRemoved"] = True
        p["parameters"]["songQueueSongIDs"]=[1]
        p = self.createHeader(p, self.jsQueue, "removeSongsFromQueue")
        page = urllib2.urlopen(self.createRequest(p, self.jsQueue))
        return json.JSONDecoder().decode(gzip.GzipFile(fileobj=(StringIO.StringIO(page.read()))).read())["result"]

    def markSongDownloadedEx(self, streamServer, songID, streamKey):
        p = {}
        p["parameters"] = {}
        p["parameters"]["streamServerID"] = streamServer
        p["parameters"]["songID"] = songID
        p["parameters"]["streamKey"] = streamKey
        p = self.createHeader(p, self.jsQueue, "markSongDownloadedEx")
        page = urllib2.urlopen(self.createRequest(p, self.jsQueue))
        return json.JSONDecoder().decode(gzip.GzipFile(fileobj=(StringIO.StringIO(page.read()))).read())["result"]

    def markSongQueueSongPlayed(self, streamServerID, streamKey, songID):
        p = {}
        p["parameters"] = {}
        p["parameters"]["streamServerID"] = streamServerID
        p["parameters"]["streamKey"] = streamKey
        p["parameters"]["songQueueSongID"] = 1
        p["parameters"]["songQueueID"] = self.queueID
        p["parameters"]["songID"] = songID
        p = self.createHeader(p, self.jsQueue, "markSongQueueSongPlayed")
        page = urllib2.urlopen(self.createRequest(p, self.jsQueue))
        return json.JSONDecoder().decode(gzip.GzipFile(fileobj=(StringIO.StringIO(page.read()))).read())["result"]

    def download(self, search, choice, callBack = None):
        try:
            songid = int(choice)
        except:
            raise SyntaxError("Failed to convert choice to int")

        
        self.addSongsToQueue(search[songid]) #Add the song to the queue
        
        stream = self.getStreamKeyFromSongIDEx(search[songid]["SongID"]) #Get the StreamKey for the selected song
        if stream == None:
            raise Exception("StreamKey not found")

        #markTimer = threading.Timer(30 + random.randint(0,5), self.markStreamKeyOver30Seconds, [search[choice]["SongID"], str(self.queueID), stream["ip"], stream["streamKey"]])
        #markTimer.start()
        data = {"streamKey":stream["streamKey"]}
        headers = {"Accept-Encoding":"gzip, deflate", "Host":stream["ip"], "User-Agent":self.USERAGENT}
        try:
            

            self.markSongDownloadedEx(stream["ip"], search[songid]["SongID"], stream["streamKey"])

            self.downloader.download(("http://%s/stream.php" % (stream["ip"])), ("%s - %s.mp3" % (search[songid]["ArtistName"], search[songid]["SongName"])), data, headers, callBack)
            
            self.markSongQueueSongPlayed(stream["ip"], stream["streamKey"], search[songid]["SongID"])

            self.removeSongsFromQueue()

        except KeyboardInterrupt:

            os.remove('%s - %s.mp3' % (search[songid]["ArtistName"], search[songid]["SongName"]))

            self.markSongDownloadedEx(stream["ip"], search[songid]["SongID"], stream["streamKey"])
