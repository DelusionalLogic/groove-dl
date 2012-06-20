import urllib2, urllib
class downloadHandler():
    """downloading files"""

    def __init__(self):
        pass

    def download(self, url, outFile, data = {}, headers = {}, callBack = None):
        data = urllib.urlencode(data)
        req = urllib2.Request(url, data, headers)
        u = urllib2.urlopen(req)
        f = open(outFile, 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (outFile, file_size)

        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            f.write(buffer)
            if callBack:
                callBack(file_size_dl, file_size)
        f.close()