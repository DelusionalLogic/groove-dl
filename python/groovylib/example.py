import groovylib

nh = groovylib.grooveshark()

s = nh.getResultsFromSearch(raw_input("Search Term: "))
i = 0
for item in s:
    i = i + 1
    print str(i) + ": " + item["ArtistName"] + " - " + item["SongName"]
    if i == 10:
        break

def reporter(downloaded, size):
    status = r"%10d  [%3.2f%%]" % (downloaded, downloaded * 100. / size)
    status = status + chr(8)*(len(status)+1)
    print status

nh.download(s, int(raw_input("Please Select: ")) - 1, reporter)