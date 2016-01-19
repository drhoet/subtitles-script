import os, sys, logging, shutil
from libs import OpenSubtitles
from libs.NoSubFoundError import NoSubFoundError

VIDEO_EXT = ['.avi', '.mp4', '.mkv', '.rmvb', '.mpg'];
SUB_EXT = ['.sub', '.srt', '.txt'];
NOT_FOUND_EXT = '.nosubsfound';

module_logger = logging.getLogger('subtitles');
module_logger.setLevel(logging.DEBUG);

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
module_logger.addHandler(ch)

def main(argv):
	if(len(argv) != 1):
		print("Usage: SubtitleDownloader <filename>");
		return
	input = argv[0];
	
	downloader = OpenSubtitles.XmlRpcWrapper();
	downloader.login();
	
	if( os.path.isfile(input) ):
		downloadSubForFile(downloader, input);
	elif( os.path.isdir(input) ):
		downloadSubRecursively(downloader, input);
	
	downloader.logout();
	
def downloadSubRecursively(downloader, rootdir):
	for root, subFolders, files in os.walk(rootdir):
		subFolders.sort();
		for filename in files:
			absFilename = os.path.join(root, filename);
			base, ext = os.path.splitext(absFilename);
			if( isVideoExt(ext) ):
				if( subtitleAlreadyExists(base) ):
					module_logger.info('Skipping %s as a subtitle is already there' % absFilename);
				elif( subtitleAlreadyNotFound(base) ):
					module_logger.warn('Skipping %s as no subtitle was found before' % absFilename);
				else:
					try:
						downloadSubForFile(downloader, absFilename);
					except UserWarning:
						module_logger.warn('Botched session. Recreating and trying again.');
						downloader.logout();
						downloader.login();
						downloadSubForFile(downloader, absFilename);
	
def downloadSubForFile(downloader, filename):
	module_logger.info('Handling %s', (filename));
	hash = OpenSubtitles.hashFile(filename);
	size = os.path.getsize(filename);
	
	outputFileNameNoExt, _ = os.path.splitext(filename);
	
	try:
		outputFileName = downloader.download(hash, size, outputFileNameNoExt);
		copyFileAttributes(filename, outputFileName);
	except NoSubFoundError:
		module_logger.warn('No subtitle found for file');
		outputFileName = outputFileNameNoExt + NOT_FOUND_EXT;
		os.mknod(outputFileName);
		copyFileAttributes(filename, outputFileName);
	except ValueError as exc:
		module_logger.warn('Couldn\'t download subtitle: %s' % exc);
	
	module_logger.info('Done.');

def isVideoExt(ext):
	return ext in VIDEO_EXT;

def subtitleAlreadyExists(baseFileName):
	for ext in SUB_EXT:
		if (os.path.isfile( baseFileName + ext ) ):
			return True;
	return False;

def subtitleAlreadyNotFound(baseFileName):
	return os.path.isfile( baseFileName + NOT_FOUND_EXT );

def copyFileAttributes(src, dst):
	fileStat = os.stat(src);
	os.chown(dst, fileStat.st_uid, fileStat.st_gid);
	shutil.copymode(src, dst);
	
if __name__ == "__main__":
	main(sys.argv[1:])