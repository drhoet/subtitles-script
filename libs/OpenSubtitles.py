import struct, os, xmlrpclib, base64, zlib, logging
from NoSubFoundError import NoSubFoundError

module_logger = logging.getLogger('subtitles.OpenSubtitles');

def hashFile(fileName):
	try:
		longlongformat = '<q'  # little-endian long long
		bytesize = struct.calcsize(longlongformat)

		f = open(fileName, "rb")

		filesize = os.path.getsize(fileName)
		hash = filesize

		if filesize < 65536 * 2:
			return "SizeError"

		for x in range(65536/bytesize):
			buffer = f.read(bytesize)
			(l_value,)= struct.unpack(longlongformat, buffer)
			hash += l_value
			hash = hash & 0xFFFFFFFFFFFFFFFF #to remain as 64bit number

		f.seek(max(0,filesize-65536),0)
		for x in range(65536/bytesize):
			buffer = f.read(bytesize)
			(l_value,)= struct.unpack(longlongformat, buffer)
			hash += l_value
			hash = hash & 0xFFFFFFFFFFFFFFFF

		f.close()
		returnedhash =  "%016x" % hash
		module_logger.debug('Hash for %s is %s' % (fileName, returnedhash));
		return returnedhash

	except(IOError):
		return "IOError"

class XmlRpcWrapper:
	"""Wrapper around www.opensubtitles.org xml-rpc api"""
	
	def __init__(self, lang='eng', user='', passwd=''):
		self.logger = logging.getLogger('subtitles.OpenSubtitles.XmlRpcWrapper');
		self.server = xmlrpclib.Server('http://api.opensubtitles.org/xml-rpc');
		self.lang = lang;
		self.user = user;
		self.passwd = passwd;
				
	def login(self):
		reply = self.server.LogIn(self.user, self.passwd, 'en', 'VLSub 0.9');
		if( reply['status'] != '200 OK' ):
			raise SystemError('Login failed: %s' % (reply['status']));
		self.session = reply;
		
	def logout(self):
		reply = self.server.LogOut(self.session['token']);
		if( reply['status'] != '200 OK' ):
			raise SystemError('Logout failed: %s' % (reply['status']));

	def download(self, moviehash, moviebytesize, outputFileNameNoExt):
		self.logger.debug('download hash:%s, size:%d, output:%s' % (moviehash, moviebytesize, outputFileNameNoExt));
		search = self.server.SearchSubtitles(self.session['token'], [{ 'sublanguageid': self.lang, 'moviehash': moviehash, 'moviebytesize': str(moviebytesize)}]);
		if( search['status'] != '200 OK' ):
			raise SystemError('Search failed: %s' % (search['status']));

		if(len(search['data']) > 0):
			self.logger.debug('Found %d results', (len(search['data'])));
			sortedSearch = sorted(search['data'], key=lambda k: int(k['SubDownloadsCnt']), reverse=True);
			subtitleid = sortedSearch[0]['IDSubtitleFile'];
			subtitleext = sortedSearch[0]['SubFormat'];
			
			self.logger.debug('Getting the file from the server (id:%s)', (subtitleid));
			subDownload = self.server.DownloadSubtitles(self.session['token'], [subtitleid]);
			if( subDownload['status'] != '200 OK' ):
				if( subDownload['status'] == '' ):
					raise UserWarning('Weird session issue: retry!');
				else:
					raise SystemError('Download subtitle failed: %s' % (subDownload['status']));
			subtitleGzip = subDownload['data'][0]['data'];
			subtitleStr = zlib.decompress(base64.b64decode(subtitleGzip), zlib.MAX_WBITS|16);
			
			outputFileName = outputFileNameNoExt + '.' + subtitleext
			with open(outputFileName, 'w') as f:
				f.write(subtitleStr);

			self.logger.debug('Wrote subtitle to %s', (outputFileName));
			return outputFileName
		else:
			raise NoSubFoundError();