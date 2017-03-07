#!/usr/bin/python

import os
import stat
import logging
import sys
import glob
import commands
import getopt
import shutil
import re
import subprocess
import xml.dom.minidom  #add by feikuang@tcl.com
import time
import zipfile
import smtplib
import pexpect
import tempfile
import multiprocessing
from xml.dom import minidom
from optparse import OptionParser
from xml.etree import ElementTree


class Log():
	'''
	format logging
	'''
	def __init__(self,name,level,mode):
		logging.basicConfig(filename = name,
					level = level,
					filemode = mode,
					format = '[ %(levelname)s %(asctime)s fileName: %(filename)s lineNo: %(lineno)d funcName: %(funcName)s ] %(message)s')

	def setConsole(self,level=logging.WARNING):
		log = logging.getLogger()
		console = logging.StreamHandler()
		console.setLevel(level)
		log.addHandler(console)
		return log

def addNotifyInfo(strNotify, addHead = False):
	global __notifyList
	if addHead:
		__notifyList.insert(0, strNotify)
	else:
		__notifyList.append(strNotify)

def getNotifyInfo():
	global __notifyList
	return '\n==========================================================================\n\n'.join(__notifyList)


def chdir(path, log=''):
	oldDir = os.getcwd()
	os.chdir(path)
	return oldDir

def pushdir(path, log=''):
	global __dirStack
	oldDir = chdir(path, log)
	__dirStack.insert(0, oldDir)
	return oldDir

def popdir(log=''):
	global __dirStack
	oldDir = ''
	if len(__dirStack) > 0:
		oldDir = chdir(__dirStack[0], log)
		__dirStack = __dirStack[1:]
	return oldDir

class MultiRun:
	def __init__(self):
		global intToolsUtilsMultiRunErrMsgQueue
		intToolsUtilsMultiRunErrMsgQueue = multiprocessing.Queue()
		self.procList = []
		self.errMsgList = []
	def add(self, task, *argList):
		proc = multiprocessing.Process(target=task, args=argList)
		self.procList.append(proc)
	def run(self):
		retVal = 0
		global intToolsUtilsMultiRunErrMsgQueue
		global __multiRunErrMsgList
		for proc in self.procList:
			proc.start()
		isRunning = True
		while isRunning:
			isRunning = False
			time.sleep(2)
			for proc in self.procList:
				if proc.is_alive():
					isRunning = True
				else:
					if proc.exitcode != 0:
						retVal = 1
						for p in self.procList:
							if p.is_alive():
								p.terminate()
		while not intToolsUtilsMultiRunErrMsgQueue.empty():
			tmpMsg = intToolsUtilsMultiRunErrMsgQueue.get()
			self.errMsgList.append(tmpMsg)
			__multiRunErrMsgList.append(tmpMsg)
		for proc in self.procList:
			proc.join()
		return retVal
	def getErrMsgList(self):
		return self.errMsgList

def getErrMsgList():
	global __multiRunErrMsgList
	return __multiRunErrMsgList

def return_result(search_result):
	for n in range(len(search_result)):
		for attr in search_result[n][1].keys():
			for i in range(len(search_result[n][1][attr])):
				returnval=[attr,search_result[n][1][attr][i]]
				return returnval

def clone(path, server):
	chdir(path)
	docmd('rm -rf .repo .git')
	tmpstr = tempfile.mkdtemp('HAPPYBUILD', 'temp', '/tmp/')
	tmpstr = tmpstr + '/'
	chdir(tmpstr)
	docmd('git clone '+server)
	return os.getcwd()

def docmd(cmd, log='', exp={}, noprint=False):
	if len(log) == 0:
		log = getDefaultLogFile()
	logFile = __bothLog(log, 'a', noprint)
	logFile.write('docmd:'+os.getcwd()+'$ '+cmd+'\n')
	ask,answer = [],[]
	for key,val in exp.items():
		ask.append(key)
		answer.append(val)
	ask.append(pexpect.EOF)
	answer.append(None)
	proc = pexpect.spawn('/bin/bash', ['-c', cmd], timeout=None, logfile=logFile)
	proc.setecho(False)
	while True:
		index = proc.expect(ask)
		if ask[index] == pexpect.EOF:
			break
		else:
			if answer[index]:
				proc.sendline(answer[index])
			else:
				proc.sendline()
	proc.close()
	if proc.exitstatus == 0:
		logFile.close()
	else:
		logFile.write("Error: docmd:%s$ %s <Return %d>\n" % (os.getcwd(), cmd, proc.exitstatus))
		logFile.close()
		notifyStr = logFile.getNotify()
		addNotifyInfo(notifyStr)
		global intToolsUtilsMultiRunErrMsgQueue
		if intToolsUtilsMultiRunErrMsgQueue:
			intToolsUtilsMultiRunErrMsgQueue.put(notifyStr)
		sys.exit(1)

def docmd_noexit(cmd, log='', exp={}, noprint=False):
	if len(log) == 0:
		log = getDefaultLogFile()
	logFile = __bothLog(log, 'a', noprint)
	logFile.write('docmd_noexit:'+os.getcwd()+'$ '+cmd+'\n')
	ask,answer = [],[]
	for key,val in exp.items():
		ask.append(key)
		answer.append(val)
	ask.append(pexpect.EOF)
	answer.append(None)
	proc = pexpect.spawn('/bin/bash', ['-c', cmd], timeout=None, logfile=logFile)
	proc.setecho(False)
	while True:
		index = proc.expect(ask)
		if ask[index] == pexpect.EOF:
			break
		else:
			if answer[index]:
				proc.sendline(answer[index])
			else:
				proc.sendline()
	proc.close()
	if proc.exitstatus == 0:
		logFile.close()
	else:
		logFile.write("Error: docmd_noexit:%s$ %s <Return %d>\n" % (os.getcwd(), cmd, proc.exitstatus))
		logFile.close()
		notifyStr = logFile.getNotify()
		addNotifyInfo(notifyStr)
		global intToolsUtilsMultiRunErrMsgQueue
		if intToolsUtilsMultiRunErrMsgQueue:
			intToolsUtilsMultiRunErrMsgQueue.put(notifyStr)
	return proc.exitstatus

def docmd_forever(cmd, log='', exp={}, noprint=False):
	if len(log) == 0:
		log = getDefaultLogFile()
	logFile = __bothLog(log, 'a', noprint)
	logFile.write('docmd_forever:'+os.getcwd()+'$ '+cmd+'\n')
	ask,answer = [],[]
	for key,val in exp.items():
		ask.append(key)
		answer.append(val)
	ask.append(pexpect.EOF)
	answer.append(None)
	while True:
		proc = pexpect.spawn('/bin/bash', ['-c', cmd], timeout=None, logfile=logFile)
		proc.setecho(False)
		while True:
			index = proc.expect(ask)
			if ask[index] == pexpect.EOF:
				break
			else:
				if answer[index]:
					proc.sendline(answer[index])
				else:
					proc.sendline()
		proc.close()
		if proc.exitstatus == 0:
			logFile.close()
			break
		else:
			logFile.write("Error: docmd_forever:%s$ %s <Return %d>, try again\n" % (os.getcwd(), cmd, proc.exitstatus))

def usage():
	log.warn("makePerso.py [ -p <productname>][ -t <build_dir>][ -s <system_image>][ -u <userdata>][ -d <debug> ][ -m <target_theme>][ -v <perso_version>][ -z <userdata_size>][ mm ][ modulename ][ db ]")
	sys.exit(0)

def delete_string_file(delete_str,file_name):
	'''
	delete string in file
	'''
	tmp_file = open(file_name+'.tmp','w')
	del_file = open(file_name,'r')
	for line in del_file:
		if not re.search(r''+delete_str,line):
			tmp_file.write(line)
		else:
			continue
	tmp_file.close()
	del_file.close()
	os.rename(file_name+'.tmp',file_name)

def replace_string_file(old_str,new_str,file_name):
	'''
	replace string in file
	'''
	if not os.path.exists(file_name):
		log.error("ERROR: %s file no exists",file_name)
		return -1
	if old_str is None:
		log.error("ERROR: old_str is None")
		return -1
	if new_str is None:
		log.error("ERROR: new_str is None")
		return -1

	open(file_name+'.tmp','w').write(re.sub(r''+old_str,r''+new_str,open(file_name,'r').read()))
	os.rename(file_name+'.tmp',file_name)

	return 0

def findExtFile(dir_path='',ext=''):
	'''
	find match the file in path
	'''
	match_list=[]
	for root,dirs,files in os.walk(dir_path):
		if len(files)>0:
			match_list = match_list + glob.glob(root+'/*'+ext)
	return match_list

def mount_system_image(dest_raw_file,dest_path):
	'''
	mount match the file system
	'''
	log.info("")

	try:
		#mount the system image
		image_name = os.path.basename(dest_path)
		cmd = 'sudo mount -o loop ' + dest_raw_file + ' ' + dest_path
		log.info("mount img command:" + cmd)
		os.popen(cmd)
		#change file owner and group to current user
		uid_str = os.getuid()
		gid_str = os.getgid()
		cmd = 'sudo chown -hR %s:%s %s' % (uid_str,gid_str,dest_path)
		os.popen(cmd)
	except Exception,e:
		log.error("ERROR: mount filesystem except:[%s]",e)
		return -1

	#remove lost+found folder
	lost_path = dest_path + '/lost+found'
	if os.path.isdir(lost_path):
		os.rmdir(lost_path)
	log.info("mount %s image finish" % image_name)

	return 0

def umount_system_image(image_folder,default_file_name=""):
	'''
	umount match the file system
	'''
	log.info("")
	try:
		mounted = []
		image_name = os.path.basename(image_folder)
		result = os.popen('df')
		for line in result:
			if re.search(r''+image_folder,line):
				filesystem = re.split(r'\s',line)[0]
				mounted.append(filesystem)
		for device in mounted:
			cmd = 'sudo umount ' + device
			log.info("umount img command:" + cmd)
			result = os.popen(cmd)
			for line in result:
				log.debug(line)
	except Exception,e:
		log.error("ERROR: umount file %s error:[%s]",image_name,e)
		return -1

	raw_file_name = default_file_name
	if raw_file_name != "" and os.path.isfile(raw_file_name):
		os.remove(raw_file_name)
	log.info("umount %s image finish" % image_name)

	return 0


def clean_intermediates_folder(*args_clean_dir):
	'''
	clean the file in path
	'''
	log.debug("")
	if os.path.exists(TOP):
		pushdir(TOP)
	for file in args_clean_dir:
		if os.path.exists(file):
			shutil.rmtree(file)
			os.makedirs(file)
		elif not os.path.exists(file):
			os.makedirs(file)
	popdir()

def prepare_tools():

	if os.path.isdir(TOP+'/out/host'):
		shutil.rmtree(TOP+'/out/host')
	os.makedirs(TOP+'/out/host')
	shutil.copytree(SCRIPTS_DIR+'/tools/linux-x86',TOP+'/out/host/linux-x86')

	if os.path.isfile(TOP+'/out/host/linux-x86/bin/simg2img'):
		os.chmod(TOP+'/out/host/linux-x86/bin/simg2img',stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)
	if os.path.isfile(TOP+'/out/host/linux-x86/bin/mkuserimg.sh'):
		os.chmod(TOP+'/out/host/linux-x86/bin/mkuserimg.sh',stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)
	if os.path.isfile(TOP+'/out/host/linux-x86/bin/make_ext4fs'):
		os.chmod(TOP+'/out/host/linux-x86/bin/make_ext4fs',stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)
	if os.path.isfile(TOP+'/out/host/linux-x86/bin/zipalign'):
		os.chmod(TOP+'/out/host/linux-x86/bin/zipalign',stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)
	if os.path.isfile(TOP+'/out/host/linux-x86/bin/build_verity_tree'):
		os.chmod(TOP+'/out/host/linux-x86/bin/build_verity_tree',stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)
	if os.path.isfile(TOP+'/out/host/linux-x86/bin/append2simg'):
		os.chmod(TOP+'/out/host/linux-x86/bin/append2simg',stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)
	if os.path.isfile(TOP+'/out/host/linux-x86/bin/fs_config'):
		os.chmod(TOP+'/out/host/linux-x86/bin/fs_config',stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)
	if os.path.isfile(PLF_PARSE_TOOL+'/writeSdmToXML.py'):
		os.chmod(PLF_PARSE_TOOL+'/writeSdmToXML.py',stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)

	return 0

def prepare_system_folder(image_file,image_folder,product_out):
	'''mount the system image, and change file owner and group to current user, remove lost+found folder'''
	log.info("")
	origin_image = image_file	  # Y6P2D0D0BG00.zip
	dest_path = image_folder
	dest_raw_path = product_out
	dest_raw_file = image_file+'.raw'   # Y6P2D0D0BG00.zip.raw
	suffix = ''
	mygroup = ''
	if os.path.isfile(dest_raw_file):
		os.remove(dest_raw_file)

	os.makedirs(dest_path)
	log.info("now unzip %s to %s",origin_image,dest_raw_path)
	if os.path.isfile(origin_image):
		suffix = os.path.splitext(origin_image)[1]#.raw
		#if the system image is ext4 mbn file, not compressed
		if suffix == ".mbn" or suffix == ".img":
			cmd = 'simg2img ' + origin_image + ' ' + dest_raw_file
			result = os.popen(cmd)
			for line in result:
				log.info(result)
		#if the system image is compressed zip file
		elif suffix == ".zip":
			zip_file = zipfile.ZipFile(origin_image,'r')
			for file in zip_file.namelist():
				if re.search(r'raw',file):
					dest_raw_file = dest_raw_path + '/' + file
					#unzip to dest_raw_path
					zip_file = zipfile.ZipFile(origin_image)
					zip_file.extractall(dest_raw_path)
					break
				if re.search(r'mbn',file):
					#unzip to dest_raw_path
					zip_file = zipfile.ZipFile(origin_image)
					zip_file.extractall(dest_raw_path)
					dest_raw_file = dest_raw_path + '/' + file + '.raw'
					dest_mbn_file = dest_raw_path + '/' + file
					cmd = 'simg2img ' + dest_mbn_file + ' ' + dest_raw_file
					result = os.popen(cmd)
					for line in result:
						log.info(result)
					break
		else:
			#if the format of system image is not the both above, then exit
			log.info("The format of origin system image is incorrect.")
			return -1

		mount_system_image(dest_raw_file,dest_path)
		os.remove(dest_raw_file)

		image_name = os.path.basename(image_folder)
		if image_name == 'system' and SYSTEM_SIZE != '':
			system_image_size = get_build_var("BOARD_SYSTEMIMAGE_PARTITION_SIZE")
			if system_image_size and system_image_size != SYSTEM_SIZE:
				generate_system_image('system')
				if os.path.isfile(PRODUCT_OUT+'/system.img'):
					cmd = 'simg2img '+PRODUCT_OUT+'/system.img '+dest_raw_file
					os.popen(cmd)
					os.remove(PRODUCT_OUT+'/system.img')
					umount_system_image(JRD_OUT_SYSTEM)
					mount_system_image(dest_raw_file,dest_path)
					os.remove(dest_raw_file)

	else:
		log.error("ERROR: Can't find origin image file: %s. exit now ... ",image_file)
		return -1

	return 0

def prepare_translations():
	log.info("now creating the strings.xml from the strings.xls")
	if not os.path.isdir(JRD_CUSTOM_RES):
		os.makedirs(JRD_CUSTOM_RES)

	if os.path.isfile(STRING_RES_PATH+'/perso/string_res.ini') and os.path.isfile(JRD_WIMDATA+'/wlanguage/src/strings.xls'):
		try:
			log.debug(JRD_TOOLS_ARCT+' w -LM -I '+STRING_RES_PATH+'/perso/string_res.ini -c '+JRD_WIMDATA+'/wlanguage/src/local.config'+' -o '+JRD_CUSTOM_RES+' '+JRD_WIMDATA+'/wlanguage/src/strings.xls '+TOP)
			result = subprocess.check_output((JRD_TOOLS_ARCT,'w','-LM','-I',STRING_RES_PATH+'/perso/string_res.ini','-c',JRD_WIMDATA+'/wlanguage/src/local.config','-o',JRD_CUSTOM_RES,JRD_WIMDATA+'/wlanguage/src/strings.xls',TOP),stderr=subprocess.STDOUT)
			log.debug("result:%s",result)
		except subprocess.CalledProcessError as err:
			log.error("ERROR: %s",err)
			sys.exit(-1)
	else:
		log.error("ERROR: Can't find string.xls file.")

def prepare_res_config():
	log.info("now copy donottranslate-cldr.xml from res to $JRD_CUSTOM_RES")
	if not os.path.isdir(JRD_CUSTOM_RES):
		os.makedirs(JRD_CUSTOM_RES)

	pushdir(TOP)
	xmlList = commands.getoutput('find frameworks/base/core/res/res -name "donottranslate-cldr.xml"').split('\n')
	for cldr in xmlList:
		dirpath = os.path.dirname(cldr)
		if not os.path.isdir(JRD_CUSTOM_RES+'/'+dirpath):
			os.makedirs(JRD_CUSTOM_RES+'/'+dirpath)
		shutil.copy(cldr,JRD_CUSTOM_RES+'/'+dirpath)
	popdir()

	return 0

def prepare_timezone(product_locates):
	log.info("now copy timezone option files according to locale settings")
	timezone_xml_path = 'packages/apps/Settings/res'

	pushdir(TOP)
	for lang in product_locates:
		main_lang = lang.split('_')[0]
		if os.path.isdir(timezone_xml_path+'/xml-'+lang):
			shutil.copytree(timezone_xml_path+'/xml-'+lang,JRD_CUSTOM_RES+'/'+timezone_xml_path+'/xml-'+lang)
		elif os.path.isdir(timezone_xml_path+'/xml-'+main_lang):
			shutil.copytree(timezone_xml_path+'/xml-'+main_lang, JRD_CUSTOM_RES+'/'+timezone_xml_path+'/xml-'+main_lang)
		else:
			print "doing nothing..."
	popdir()

	return 0


def prepare_photos():
	log.info("now building the customized icons...")
	zip = zipfile.ZipFile(JRD_WIMDATA+'/wcustores/Photos/'+TARGET_PRODUCT+'/images.zip')
	zip.extractall(JRD_CUSTOM_RES)

	return 0

def override_exist_folder(dst_folder,src_folder):
	'''
	# $1 target file folder
	# $2 source file folder
	'''
	log.info("")
	target_folder = dst_folder
	if not os.path.isdir(target_folder):
		os.makedirs(target_folder)
	# Only copy files that already present at media folder before.
	file_list = os.listdir(target_folder)
	for file in file_list:
		source_file = src_folder + '/' + file
		if (not os.path.islink(target_folder+'/'+file)) and (os.path.isfile(target_folder+'/'+file)) and (os.path.isfile(source_file)):
			shutil.copy(source_file,target_folder)

	return 0

def prepare_media():
	log.info("now copy boot/shutdown animation.gif...")
	for source_file in os.listdir(JRD_WIMDATA+'/wcustores/Media/'+TARGET_PRODUCT):
		if os.path.isfile(JRD_WIMDATA+'/wcustores/Media/'+TARGET_PRODUCT+'/'+source_file):
			shutil.copy(JRD_WIMDATA+'/wcustores/Media/'+TARGET_PRODUCT+'/'+source_file,PRODUCT_OUT+'/system/media')

	return 0

def prepare_ringtone():
	log.info("now building the customized audio...")
	audio_folder = JRD_OUT_SYSTEM + '/media/audio'
	if not os.path.exists(audio_folder):
		os.makedirs(audio_folder)
	else:
		clean_intermediates_folder(audio_folder)

	#delete the origin ringtone files firstly
	pushdir(audio_folder)
	for file in os.listdir('.'):
		if os.path.isfile(file):
			os.remove(file)
		elif os.path.isdir(file):
			shutil.rmtree(file)
	popdir()

	#unzip audio.zip to target path
	log.info("unzip audios.zip to" + JRD_CUSTOM_RES)
	zip = zipfile.ZipFile(JRD_WIMDATA+'/wcustores/Audios/'+TARGET_PRODUCT+'/audios.zip')
	zip.extractall(JRD_CUSTOM_RES)
	shutil.copytree(JRD_CUSTOM_RES+'/frameworks/base/data/sounds/Alarm',audio_folder+'/alarms')
	shutil.copytree(JRD_CUSTOM_RES+'/frameworks/base/data/sounds/Notification',audio_folder+'/notifications')
	shutil.copytree(JRD_CUSTOM_RES+'/frameworks/base/data/sounds/Ringtones',audio_folder+'/ringtones')
	shutil.copytree(JRD_CUSTOM_RES+'/frameworks/base/data/sounds/Switch_On_Off',audio_folder+'/switch_on_off')
	shutil.copytree(JRD_CUSTOM_RES+'/frameworks/base/data/sounds/UI',audio_folder+'/ui')
	shutil.copytree(JRD_CUSTOM_RES+'/frameworks/base/data/sounds/CB_Ring',audio_folder+'/cb_ring')
	if os.path.isfile(TOP+'/frameworks/base/data/sounds/wifi_notification.ogg'):
		if not os.path.isdir(audio_folder+'/wifi_ring'):
			os.makedirs(audio_folder+'/wifi_ring')
		shutil.copy(TOP+'/frameworks/base/data/sounds/wifi_notification.ogg',audio_folder+'/wifi_ring/wifi_notification.ogg')

	return 0

def merge_module_plf(plf):
	log.info("Merge %s" % plf)
	plf_dir = os.path.dirname(plf)
	cmd = TOP+'/development/tcttools/mergeplf/mergeplf '+MAKE_PERSO_OR_NOT+' '+plf_dir+' '+PRODUCT_OUT+'/plf '+TARGET_PRODUCT
	try:
		os.popen(cmd)
	except Exception,e:
		log.error("ERROR: %s",e)
		sys.exit(-1)
	return 0

def remove(path):
	log.info("")
	if os.path.isdir(path):
		shutil.rmtree(path)
	else:
		os.remove(path)

def read_variable_from_Gappmakefile(target_variable=None,target_file=None):
	if target_variable is None or target_file is None:
		open("read_variable_error.log","w").write("input parameters cannot be null")
		sys.exit(-1)
	variable=target_variable
	linenum=1
	result = []
	target_obj = open(target_file,'r')
	target_no=1
	for line in target_obj:
		if target_no!=linenum:
			target_no=target_no+1
			continue
		#reserve the space in PRODUCT_MODEL value
		if re.search(r'\s*'+variable+r'.*:=.*',line):
			line=line.strip()
			line=re.sub(r'\s*',r'',line)
			if re.search(r'=',line):
				line=line.strip()
				line=re.sub(r'\s*',r'',line)
				result.append(line.split('=')[1])
	target_obj.close()
	return result

def get_standalone_name(res_dir,res_apk=None):
	print 'start process standalone_apk android.mk'
	if os.path.isfile(res_dir+'/Android.mk'):
		name=read_variable_from_Gappmakefile("LOCAL_MODULE ",res_dir+'/Android.mk')
		if len(name) > 1:
			for app_name in name:
				standlone_apk_package = commands.getoutput(MY_AAPT_TOOL+' d --values permissions '+res_dir+'/'+app_name+'*.apk | head -1').split(' ')[1]
				result = re.search(standlone_apk_package,res_apk)
				if not result is None:
					print "app_name is " ,app_name;
					return app_name
		else:
			print 'name is ' ,name
			return name[0]
	else:
		log.info("%s/Android.mk not found",res_dir)
		return ""


def customize_standalone_apk():
	pushdir(TOP)
	extra_apk_list = []
	for extraapk in open('extra_apk.lst','r').readlines():
		extra_apk_list.append(os.path.basename(extraapk).strip())
	standalone_apklist = commands.getoutput('find vendor/tctalone/TctAppPackage/ -name "*.apk"').split('\n')
	for apkitem in standalone_apklist:
		standalone_apk_package = commands.getoutput(MY_AAPT_TOOL+' d --values permissions '+apkitem+' | head -1').split(' ')[1]
		for extraapk in commands.getoutput('find '+JRD_OUT_CUSTPACK+'/app -name "*.apk"').split('\n'):
			if os.path.basename(extraapk) in extra_apk_list:
				extra_apk_package = commands.getoutput(MY_AAPT_TOOL+' d --values permissions '+extraapk+' | head -1').split(' ')[1]
				if standalone_apk_package == extra_apk_package:
					standalone_apk_path = os.path.dirname(apkitem)
					origin_apk_name = get_standalone_name(standalone_apk_path,extra_apk_package)
					print 'origin_apk_name is ',origin_apk_name
					origin_apk_path = get_custo_apk_path(standalone_apk_path)
					if os.path.isdir(origin_apk_path+'/'+origin_apk_name):
						shutil.rmtree(origin_apk_path+'/'+origin_apk_name)
						print 'customize_standalone_apk is ',origin_apk_name
					elif os.path.isfile(origin_apk_path+'/'+origin_apk_name+'.apk'):
						os.remove(origin_apk_path+'/'+origin_apk_name+'.apk')
						print 'customize_standalone_apk is ',origin_apk_name
					break
			else:
				continue
	popdir()

def check_if_3rd_apk_has_lib(apk_file):
	apk = apk_file
	apktmpfile = os.path.basename(apk_file)+'.tmp'
	apkdir = 'uncompressedlibs'
	log.info("unzip -o -d %s %s lib/*",apkdir,apk_file)
	if os.path.exists(apkdir):
		shutil.rmtree(apkdir)
		os.makedirs(apkdir)
	else:
		os.makedirs(apkdir)

	zip = zipfile.ZipFile(apk)
	for zf in zip.namelist():
		if re.search(r'^lib/.*',zf):
			log.info("%s",zf)
			zip.extract(zf,apkdir)
	# MODIFIED-BEGIN by min.liao, 2016-07-04,BUG-2459580
	zip.close()

	if not os.path.exists(apkdir+'/lib'):
		log.info("%s has no jni library to process.",apk)
	else:
		apk = os.path.basename(apk_file)
		log.info("mv %s to %s",apk_file,apk)
		(status,output) = commands.getstatusoutput('mv '+apk_file+' '+apk)
		if status != 0:
			log.error("ERROR: \n %s",output)
			log.error("ERROR: mv %s to %s fail",apk_file,apk)
			sys.exit(status)
			# MODIFIED-END by min.liao,BUG-2459580

		(status,output) = commands.getstatusoutput('zip -d '+apk+' lib/*.so')
		if status != 0:
			log.error("ERROR: \n %s",output)
			log.error("ERROR: when delete libs from: %s",apk)
			sys.exit(status)

		pushdir(apkdir)
		(status,output) = commands.getstatusoutput('zip -D -r -0 ../'+apk+' lib') # MODIFIED by min.liao, 2016-07-04,BUG-2459580
		if status != 0:
			log.error("ERROR: \n %s",output)
			log.error("ERROR: when zip libs to: %s",apk)
			sys.exit(status)
		popdir()

		(status,output) = commands.getstatusoutput('zipalign -f -p 4 '+apk+' '+apktmpfile)
		if status != 0:
			log.error("ERROR: \n %s",output)
			log.error("ERROR: when zipalign %s",apk)
			sys.exit(status)

		# MODIFIED-BEGIN by min.liao, 2016-07-04,BUG-2459580
		(status,output) = commands.getstatusoutput('df -h|grep system')
		log.info('output info:\n%s',output)

		(status,output) = commands.getstatusoutput('mv '+apktmpfile+' '+apk_file)
		if status != 0:
			log.error("ERROR: \n %s",output)
			log.error("ERROR: mv zlipalign apk:%s to %s fail",apktmpfile,apk_file)
			sys.exit(status)
		os.remove(apk)
		# MODIFIED-END by min.liao,BUG-2459580

	shutil.rmtree(apkdir)

def prepare_3rd_party_apk():
	log.info("")
	pushdir(TOP)
	log.debug('TOP=[%s]',TOP)
	#parse command from jrd_build_apps.mk and run command one by one
	with open(JRD_BUILD_PATH_COMMON+'/perso/buildres/jrd_build_apps.mk','r') as lines:
		for line in lines:
			line = re.sub(r'#.*$','',line)
			patten = re.findall(r'\(([A-Z_]*)\)',line)
			if patten and len(patten) > 0:
				for i in range(len(patten)):
					if patten[i] in globals().keys():
						line = line.replace('$('+patten[i]+')',globals()[patten[i]]).strip('\n')

			if re.search(r'mkdir',line):
				apk_path = re.split(' ',line)[3]
				if apk_path and not os.path.isdir(apk_path):
					log.debug('mkdir %s',apk_path)
					os.makedirs(apk_path)

			elif re.search(r'cp',line):
				(sp1,sp2,sp3,sp4) = line.split(' ')
				apk_cmd = sp2 + ' ' + sp3 + ' ' + sp4
				log.debug('copy apk cmd:%s',apk_cmd)
				result = os.popen(apk_cmd)
				for line in result:
					log.info(line)

	if os.path.isfile(TOP+'/extra_apk.lst'):
		customize_standalone_apk()
		os.remove(TOP+'/extra_apk.lst')

	check_folder = ['priv-app','unremoveable']
	for folder in check_folder:
		appsfolder = JRD_OUT_CUSTPACK+'/app/'+folder
		log.info('3rd apk folder:%s',appsfolder)
		for line in os.listdir(appsfolder):
			if os.path.isfile(appsfolder+'/'+line):
				log.info('Optimize apk:%s',appsfolder+'/'+line)
				check_if_3rd_apk_has_lib(appsfolder+'/'+line)
	popdir()

	return 0

# MODIFIED-BEGIN by yzsong, 2016-06-24,BUG-2390227
def prepare_gid_config():
	if TARGET_PRODUCT != 'idol4_bell':
		return
	log.info("now building gid config files")
	if os.path.exists(JRD_OUT_CUSTPACK+'/operator-gid'):
		cmd = 'rm -rf '+JRD_OUT_CUSTPACK+'/operator-gid/*.txt'
		os.popen(cmd)
	else:
		cmd = 'mkdir -p '+JRD_OUT_CUSTPACK+'/operator-gid'
		os.popen(cmd)

	if os.path.isfile(JRD_WIMDATA+'/wcustores/App/'+TARGET_PRODUCT+'/operator-gid/default.txt'):
		os.system("cp -r %s/wcustores/App/%s/operator-gid/*.txt %s/operator-gid" %(JRD_WIMDATA,TARGET_PRODUCT,JRD_OUT_CUSTPACK))
	else:
		cmd = 'rm -rf '+JRD_OUT_CUSTPACK+'/app/operator'
		os.popen(cmd)
		cmd = 'rm -rf '+JRD_OUT_CUSTPACK+'/operator-gid'
		os.popen(cmd)
		log.info("nothing gid config files")

# MODIFIED-END by yzsong,BUG-2390227
def prepare_usermanual():
	log.info("now building the customized user manuals...")
	override_exist_folder(JRD_OUT_CUSTPACK+'/JRD_custres/user_manual',JRD_WIMDATA+'/wcustores/UserManual')

	return 0

def override_exist_file(dst_file,src_file):
	log.info("")
	target_file = dst_file
	source_file = src_file
	if (not os.path.islink(target_file)) and os.path.isfile(target_file) and os.path.isfile(source_file):
		shutil.copy(source_file,target_file)

def prepare_apn():
	log.info("now building the apn files")
	if os.path.isfile(JRD_WIMDATA+'/wcustores/apns-conf.xml') and os.path.isfile(JRD_BUILD_PATH_DEVICE+'/perso/apns-conf-ims.xml'):
		os.system("cat %s/perso/apns-conf-ims.xml >> %s/wcustores/apns-conf.xml" % (JRD_BUILD_PATH_DEVICE, JRD_WIMDATA))
		os.system("sed -i -e '/<\/apns>/d' %s/wcustores/apns-conf.xml" % JRD_WIMDATA)
		os.system("echo '</apns>' >> %s/wcustores/apns-conf.xml" % JRD_WIMDATA)
	override_exist_file(JRD_OUT_SYSTEM+'/etc/apns-conf.xml',JRD_WIMDATA+'/wcustores/apns-conf.xml')

def prepare_appmanager():
    log.info("now building the appmanager.conf")
    if os.path.isfile(JRD_WIMDATA+'/wcustores/appmanager.conf'):
        shutil.copy(JRD_WIMDATA+'/wcustores/appmanager.conf',JRD_OUT_SYSTEM+'/etc/')


def prepare_plmn():
	log.info("now building the plmn files")
	override_exist_file(JRD_OUT_CUSTPACK+'/plmn-list.conf',JRD_WIMDATA+'/wcustores/plmn-list.conf')

#add by min.liao@tcl.com for defect:2814548 at 2016-09-22
#NOTE:if VAL do not custom the content,custo_wimdata_ng/wcustores/thermal-engine.conf is not exist, if so,
#/system/etc/thermal-engine.conf still use the default file:/device/tct/idol4/thermal-engine.conf
def prepare_thermal():
	log.info("now building the thermal files")
	override_exist_file(JRD_OUT_SYSTEM+'/etc/thermal-engine.conf',JRD_WIMDATA+'/wcustores/thermal-engine.conf')
#end by min.liao@tcl.com for defect:2814548 at 2016-09-22

def prepare_wifi():
	log.info("now building the wifi files")
	override_exist_file(JRD_OUT_SYSTEM+'/etc/wifi/wpa_supplicant.conf',TOP+'/device/tct/'+TARGET_PRODUCT+'/wpa_supplicant.conf')

def prepare_dpm():
	log.info("now building the dpm files")
	override_exist_file(JRD_OUT_SYSTEM+'etc/dpm/dpm.conf',TOP+'/device/tct/common/dpm/dpm.conf')

def prepare_btc():
	log.info("now building the btc files")
	override_exist_file(JRD_OUT_SYSTEM+'/etc/wifi/WCNSS_qcom_cfg.ini',TOP+'/device/tct/'+TARGET_PRODUCT+'/WCNSS_qcom_cfg.ini')

def prepare_nfc():
	log.info("now building the nfc files")
	override_exist_file(JRD_OUT_SYSTEM+'/etc/libnfc-brcm.conf',TOP+'/device/tct/'+TARGET_PRODUCT+'/nfc/libnfc-brcm.conf')

def clean_intermediates_files(dir_path):
	log.info("")
	pushdir(TOP)
	if os.path.isdir(dir_path):
		log.info("###"+dir_path+"###")
		for file in os.listdir(dir_path):
			if os.path.isfile(dir_path+'/'+file):
				os.remove(dir_path+'/'+file)
	else:
		log.debug(dir_path+'not exists')
	popdir()

def find_res_dir(dir_path):
	'''
	#TODO: read string_res.ini file and find out all packages that need to be overlayed
	#	  this may missing some important packages that not list in this file,
	'''
	log.info("")
	my_strings_dir = []
	my_icons_dir   = []
	my_plffile_dir = []
	if os.path.isfile(dir_path):
		file_obj = open(dir_path,'r')
		for line in file_obj:
			if re.search(r'^[^\#].*res',line):
				my_strings_dir.append(re.sub(r'\./',r'',"".join(re.findall(r'(^.*res)',line))))
		file_obj.close()
	if os.environ['TARGET_BUILD_CUSTOM_IMAGES'] == 'true':
		image_zip_file = JRD_WIMDATA + '/wcustores/Photos/' + TARGET_PRODUCT + '/images.zip'
		if os.path.exists(image_zip_file):
			zip = zipfile.ZipFile(image_zip_file,'r')
			for file_name in zip.namelist():
				if re.search(r'png|jpg',file_name):
					my_icons_dir.append(re.sub(r'res.*','res',file_name))
		else:
			log.error("ERROR: %s not found",image_zip_file)
			return -1
	for path in MY_PLF_FILE_FOLDER:
		for root,dirs,files in os.walk(path):
			if len(files)>0:
				for file in files:
					if os.path.splitext(root+'/'+''.join(file))[1] == '.plf':
						full_name = root + "/" + "".join(file)
						my_plffile_dir.append(re.sub(r'isdm.*plf','res',full_name))

	res_all = my_strings_dir + my_icons_dir + my_plffile_dir

	global MY_RES_DIR
	if not MM_MODULE_NAME:
		MY_RES_DIR = sorted(set(res_all))

	else:
		for item in set(res_all):
			if re.search(r'/'+MM_MODULE_NAME.lower()+r'/res', item.lower()):
				MY_RES_DIR.append(item)

	if len(MY_RES_DIR) <= 0:
		log.error("ERROR: not find the path %s",dir_path)
		return -1
	return 0

def prepare_launcher_workspace():
	'''
	# copy launcher workspace to out $JRD_CUSTOM_RES folder
	# TODO: the path of workspace.xml file are different for some project
	'''
	log.info("")

	pushdir(TOP)
	doc = ElementTree.parse(SCRIPTS_DIR+'/config/m8976.xml')
	for item in doc.getiterator('launcher'):
		for node in item.getchildren():
			if node.attrib['path'] in MY_RES_DIR:
				file_path = node.attrib['path']
				if not os.path.isdir(os.path.dirname(file_path)):
					log.info("Product without file_path Launcher ...")
					continue
				for subnode in node.getchildren():
					file_edir = subnode.attrib['edir']
					file_name = subnode.attrib['name']
					for root,dirs,files in os.walk(file_path):
						m = re.search(r'/'+file_edir+'-mcc[0-9]*-mnc[0-9]*', root)
						if m:
							if file_name == 'attrs.xml':
								continue
							else:
								custofile = root+'/'+file_name
						elif os.path.split(root)[1] == file_edir:
							custofile = root+'/'+file_name
						else:
							continue
						if os.path.isfile(custofile):
							if not os.path.exists(os.path.dirname(JRD_CUSTOM_RES+'/'+custofile)):
								os.makedirs(os.path.dirname(JRD_CUSTOM_RES+'/'+custofile))
							shutil.copy(custofile,JRD_CUSTOM_RES+'/'+custofile)
						elif not os.path.isfile(custofile) and subnode.attrib['perso'] == 'true':
							log.info("%s file only for perso customization not in main sw" % custofile)
						else:
							log.error("ERROR: Can't find Launcher %s file, exiting now..." % custofile)
							return -1
	popdir()

	return 0

def plf_to_xml(PLF_TARGET_XML_FOLDER,plf):
	log.info("process %s to xml..." % plf)
	XML_NAME = os.path.splitext(os.path.split(plf)[1])[0] + '.xml'
	PLF_TARGET_XML = PLF_TARGET_XML_FOLDER + '/' + XML_NAME

	if not os.path.exists(PLF_TARGET_XML_FOLDER):
		os.makedirs(PLF_TARGET_XML_FOLDER)
	try:
		ret = subprocess.check_call((PLF_PARSE_TOOL+'/writeSdmToXML.py',PLF_TARGET_XML,plf))
	except subprocess.CalledProcessError as err:
		log.error("ERROR: %s",err)
		sys.exit(-1)
	if ret != 0 and ret != 139:
		log.error("ERROR: Parse PLF files error, exiting now ... ")
		sys.exit(ret)
	else:
		pushdir(PLF_TARGET_XML_FOLDER)
		for file in os.listdir('.'):
			if (os.path.splitext(file)[1] == '.h' or os.path.splitext(file)[1] == '.log') and re.search(r'^isdm_',file):
				os.remove(file)
		popdir()

def prepare_plfs():
	log.info("now process plf to xml...")

	if os.getenv('LD_LIBRARY_PATH') is None:
		os.putenv('LD_LIBRARY_PATH',PLF_PARSE_TOOL)
	else:
		os.environ['LD_LIBRARY_PATH'] = os.environ['LD_LIBRARY_PATH'] + ':' + PLF_PARSE_TOOL

	pushdir(TOP)
	for folder in MY_PLF_FILE_FOLDER:
		if os.path.isdir(folder):
			full_files = commands.getoutput('find '+folder+' -type f -name *.plf').split('\n')
			if len(full_files) > 0 and full_files[0] != '':
				for plf in full_files:
					if os.path.isfile(plf):
						PLF_TARGET_XML_FOLDER = JRD_CUSTOM_RES + '/' + os.path.dirname(plf) + '/res/values'
						if MM_MODULE_NAME or DAILYBUILD_FLAG:
							prod_plf = PRODUCT_OUT+'/plf/'+os.path.basename(plf)
							if not os.path.isfile(prod_plf):
								merge_module_plf(plf)
							plf_to_xml(PLF_TARGET_XML_FOLDER,prod_plf)
						else:
							plf_to_xml(PLF_TARGET_XML_FOLDER,os.path.abspath(plf))
						if os.path.exists(JRD_SSV_PLF):
							full_ssv_files = commands.getoutput('find '+JRD_SSV_PLF+' -type f -name '+os.path.basename(plf)).split('\n')
							if len(full_ssv_files) > 0 and full_ssv_files[0] != '':
								for ssv_plf in full_ssv_files:
									ssv_suffix = os.path.dirname(ssv_plf).replace(JRD_SSV_PLF+'/plf','')
									PLF_TARGET_XML_FOLDER = JRD_CUSTOM_RES+'/' + os.path.dirname(plf)+'/res/values'+ssv_suffix
									plf_to_xml(PLF_TARGET_XML_FOLDER,ssv_plf)
					else:
						log.info("Cannot find plf file in folder: %s" % folder)
						continue
	if os.path.isfile(JRD_SSV_PLF+'/ssvxml/ssv_simcard.xml'):
		shutil.copy(JRD_SSV_PLF+'/ssvxml/ssv_simcard.xml', JRD_OUT_CUSTPACK)
	popdir()

	return 0

def process_sys_plf():
	'''
	generate the jrd_sys_properties.prop & jrd_build_properties.mk
	'''
	log.info("/bin/bash %s/common/perso/process_sys_plf.sh %s %s %s",JRD_BUILD_PATH,JRD_TOOLS_ARCT,JRD_PROPERTIES_PLF,JRD_CUSTOM_RES)
	if MM_MODULE_NAME or DAILYBUILD_FLAG:
		out_sys_plf = PRODUCT_OUT+'/plf/'+os.path.basename(JRD_PROPERTIES_PLF)
		if not os.path.isfile(out_sys_plf):
			merge_module_plf(JRD_PROPERTIES_PLF)
	else:
		out_sys_plf = JRD_PROPERTIES_PLF
		if not os.path.isdir(JRD_CUSTOM_RES):
			os.makedirs(JRD_CUSTOM_RES)

	try:
		result = subprocess.check_call((JRD_TOOLS_ARCT,'p',out_sys_plf,JRD_CUSTOM_RES+'/jrd_build_properties.mk',JRD_CUSTOM_RES+'/jrd_sys_properties.prop'))
		log.debug("result: %s",result)
	except subprocess.CalledProcessError as err:
		log.error("ERROR: %s",err)
		sys.exit(-1)

	return 0

def replace_properties(jrd_file,build_file):
	jrd_prop=[]
	build_prop=[]
	with open(jrd_file,'r') as jrd_obj:
		for line in jrd_obj:
			if re.search(r'^[^#]*=',line):
				line=line.strip()
				jrd_prop.append(line.split('=')[0])
			else:
				continue
	with open(build_file,'r') as build:
		for line in build:
			if re.search(r'^[^#]*=',line):
				if line.split('=')[0] in jrd_prop:
					delete_string_file(line.split('=')[0],build_file)
	open(build_file,'a').write(open(jrd_file,'r').read())

def read_variable_from_makefile(target_variable=None,target_file=None):
	'''
	# read in the makefile, and find out the value of the give variable
	# $1 target variable to found
	# $2 target file to search
	'''
	if target_variable is None or target_file is None:
		open("read_variable_error.log","w").write("input parameters cannot be null")
		sys.exit(-1)
	variable=target_variable
	linenum=1
	if os.path.isfile(target_file):
		target_obj = open(target_file,'r')
		for line in target_obj:
			if re.search(r''+target_variable+r'\s*:=',line):
				break
			else:
				linenum=linenum+1
		target_obj.close()

	result = []
	findit = False
	target_obj = open(target_file,'r')
	target_no=1
	for line in target_obj:
		if target_no!=linenum:
			target_no=target_no+1
			continue
		if re.search(r'^#',line):
			continue
		if re.search(r'^\s*$',line):
			continue
		#reserve the space in PRODUCT_MODEL value
		if target_variable == "PRODUCT_MODEL":
			line=line.strip()
			result.append(line.split('=')[1].strip())
			break
		if findit == False:
			if re.search(r'\s*'+variable+r'.*:=.*',line):
				findit=True
				line=line.strip()
				line=re.sub(r'\s*',r'',line)
				if line[-1] == '\\':
					line=re.sub(r'\\',r'',line)
					if re.search(r'=',line) and line.strip()[-1] != '=':
						result.append(line.split('=')[1])
				else:
					if re.search(r'=',line):
						line=line.strip()
						line=re.sub(r'\s*',r'',line)
						result.append(line.split('=')[1])
						findit=False
						break
		else:
			line=line.strip()
			line=re.sub(r'\s*',r'',line)
			if line[-1] == '\\':
				line=re.sub(r'\\',r'',line)
				line=line.strip()
				result.append(line)
			else:
				result.append(line.strip())
				findit=False
				break
	target_obj.close()

	new_result=[]
	for a in result:
		new_result.append(re.sub(r'#[^#]*',r'',a))
	if len(new_result) > 1:
		env_result = "\n".join(new_result)
	elif len(new_result) == 1:
		env_result = "".join(new_result)
	else:
		env_result = ""
	return env_result

def read_JRD_from_makefile(target_variable=None,target_file=None):
	'''
	# read in the makefile, and find out the value of the give variable
	# $1 target variable to found
	# $2 target file to search
	'''
	if target_variable is None or target_file is None:
		open("read_variable_error.log","w").write("input parameters cannot be null")
		sys.exit(-1)
	variable=target_variable
	linenum=1
	if os.path.isfile(target_file):
		target_obj = open(target_file,'r')
		for line in target_obj:
			if re.search(r''+target_variable+r'\s*:=',line):
				break
			else:
				linenum=linenum+1
		target_obj.close()

	result = []
	findit = False
	target_obj = open(target_file,'r')
	target_no=1
	for line in target_obj:
		if target_no!=linenum:
			target_no=target_no+1
			continue
		if re.search(r'^#',line):
			continue
		if re.search(r'^\s*$',line):
			continue
		#reserve the space in PRODUCT_MODEL value
		if target_variable == "PRODUCT_MODEL":
			line=line.strip()
			result.append(line.split('=')[1].strip())
			break
		if findit == False:
			if re.search(r'\s*'+variable+r'.*:=.*',line):
				findit=True
				line=line.strip()
				line=re.sub(r'\s*',r'',line)
				if line[-1] == '\\':
					line=re.sub(r'\\',r'',line)
					if re.search(r'=',line) and line.strip()[-1] != '=':
						result.append(line.split('=')[1])
				else:
					if re.search(r'=',line):
						line=line.strip()
						line=re.sub(r'\s*',r'',line)
						result.append(line.split('=')[1])
						#modify by feikuang@tcl.com for ninja
						continue
						#findit=False
						#break
		else:
			#mdify by feikuang@tcl.com for ninja
			if re.search(r'\s*'+variable+r'.*\+=.*',line):
				line=line.strip()
				line=re.sub(r'\s*',r'',line)
				if re.search(r'=',line):
						line=line.strip()
						line=re.sub(r'\s*',r'',line)
						result.append(line.split('=')[1])
						findit=True
						continue
			else:
				line=line.strip()
				line=re.sub(r'\s*',r'',line)
				if  line[-1] == '\\':
						line=re.sub(r'\\',r'',line)
						line=line.strip()
						result.append(line)
			
				else:
					result.append(line.strip())
					findit=False
					break
	target_obj.close()

	new_result=[]
	for a in result:
		new_result.append(re.sub(r'#[^#]*',r'',a))
	if len(new_result) > 1:
		env_result = "\n".join(new_result)
	elif len(new_result) == 1:
		env_result = "".join(new_result)
	else:
		env_result = ""
	return env_result

def get_build_var(var_name,path=False):
	'''
	Get the exact value of a build variable.
	'''
	log.info("")
	os.environ["CALLED_FROM_SETUP"]="true"
	os.environ["BUILD_SYSTEM"]="build/core"
	var="dumpvar-"+var_name
	try:
		pushdir(TOP)
		result = subprocess.check_output("command make --no-print-directory -f build/core/config.mk "+var,shell=True,stderr=subprocess.STDOUT)
		if path:
			result = os.path.abspath(result)
		popdir()
		return result.strip('\n')
	except subprocess.CalledProcessError as err:
		log.error("ERROR: except Exception:%s",err)
		sys.exit(-1)


def prepare_build_prop():
	log.info("Now buiding build.prop ... ")
	build_prop = JRD_OUT_SYSTEM + '/build.prop'
	jrd_build_prop_mk = JRD_CUSTOM_RES + '/jrd_build_properties.mk'

	jrd_sys_prop = JRD_CUSTOM_RES + '/jrd_sys_properties.prop'
	log.debug("build_prop:%s,jrd_build_prop_mk=%s,jrd_sys_prop=%s",build_prop,jrd_build_prop_mk,jrd_sys_prop)
	if (not os.path.exists(build_prop)) or (not os.path.exists(jrd_build_prop_mk)) or (not os.path.exists(jrd_sys_prop)):
		log.error("ERROR: can't find build.prop file, exiting now ...")
		return -1

	# replace properties from jrd_build_properties.mk, which generated by buildinfo.sh generally
	PRODUCT_MODEL        = read_variable_from_makefile("PRODUCT_MODEL",jrd_build_prop_mk)
	PRODUCT_BRAND        = read_variable_from_makefile("PRODUCT_BRAND",jrd_build_prop_mk)
	PRODUCT_MANUFACTURER = read_variable_from_makefile("PRODUCT_MANUFACTURER",jrd_build_prop_mk)
	TCT_PRODUCT_DEVICE   = read_variable_from_makefile("TCT_PRODUCT_DEVICE",jrd_build_prop_mk)
	TCT_PRODUCT_NAME     = read_variable_from_makefile("TCT_PRODUCT_NAME",jrd_build_prop_mk)
        TCT_VFD_PRODUCT_NAME = read_variable_from_makefile("TCT_VFD_PRODUCT_NAME",jrd_build_prop_mk)
	if TCT_PRODUCT_NAME == '':
		if TARGET_PRODUCT == 'idol4s_vdf':
			TCT_PRODUCT_NAME = TCT_VFD_PRODUCT_NAME
			print "TCT_PRODUCT_NAME %s" % TCT_PRODUCT_NAME
		else:
			TCT_PRODUCT_NAME = PRODUCT_MODEL.replace(' ','_')
	TCT_BUILD_NUMBER     = read_variable_from_makefile("def_tctfw_build_number",jrd_build_prop_mk)
	#TCT_PRODUCT_DEVICE   = TARGET_PRODUCT
	TARGET_DEVICE        = get_build_var("TARGET_DEVICE")
	PLATFORM_VERSION     = get_build_var("PLATFORM_VERSION")
	BUILD_ID             = get_build_var("BUILD_ID")
	BUILD_NUMBER         = get_build_var("BUILD_NUMBER")
	TARGET_BUILD_VARIANT = os.environ['TARGET_BUILD_VARIANT']
        #Add by xinxin.quan for defect-2301727 20160620
        if len(PERSO_VERSION) > 0 and TARGET_PRODUCT=="idol4_bell":
	       BUILD_NUMBER = BUILD_NUMBER[:5] + '-' + PERSO_VERSION[4:8]
        print "BUILD_NUMBER is ",BUILD_NUMBER

	fingerprint_second_part = ''
	with open(build_prop,'r') as build_obj:
		for line in build_obj:
			line = line.strip()
			if re.search(r'ro.build.fingerprint=',line):
				pos = line.find(":")
				if pos != -1:
					pos = pos + 1
					fingerprint_second_part = line[pos:]
	BUILD_FINGERPRINT = PRODUCT_BRAND+'/'+TCT_PRODUCT_NAME+'/'+TCT_PRODUCT_DEVICE+':'+fingerprint_second_part
	log.info("BUILD_FINGERPRINT = %s",BUILD_FINGERPRINT)

	key_svn = 'ro.def.software.svn'
	value_svn = ''
	try:
		jrd_prop = open(jrd_sys_prop,'r')
		jrd_properties = jrd_prop.readlines()
		jrd_prop.close()
		for readline in jrd_properties:
			if re.search(r'^'+key_svn+'=',readline.strip('\n')):
				value_svn = readline.strip().split('=')[1]
		print "value_svn: %s" % value_svn


	except Exception,e:
		print "ERROR: %s" % e
		return 1

	prop_dict = {}

	prop_dict['ro.product.model'] = PRODUCT_MODEL
	prop_dict['ro.product.name'] = TCT_PRODUCT_NAME
	prop_dict['ro.product.brand'] = PRODUCT_BRAND
	#due to the value of 'ro.product.device' can not change on fota upgrate,so we need't custom it.
	#prop_dict['ro.product.device'] = TCT_PRODUCT_DEVICE
	prop_dict['def.tctfw.build.number'] = TCT_BUILD_NUMBER
	prop_dict['ro.build.product'] = TARGET_PRODUCT
	prop_dict['ro.product.manufacturer'] = PRODUCT_MANUFACTURER
	prop_dict['ro.build.date'] = commands.getoutput('date')
	prop_dict['ro.build.date.utc'] = commands.getoutput('date +%s')
	prop_dict['ro.build.user'] = os.environ['USER']
	prop_dict['ro.build.host'] = commands.getoutput('hostname')
	prop_dict['ro.tct.product'] = TARGET_PRODUCT
	prop_dict['ro.build.fingerprint'] = BUILD_FINGERPRINT
	print "ro.build.vbd = %s" % (PRODUCT_MANUFACTURER+'/'+value_svn[:3]+'/'+value_svn[-2:])
	prop_dict['ro.build.vbd'] = PRODUCT_MANUFACTURER+'/'+value_svn[:3]+'/'+value_svn[-2:]
        #Add by xinxin.quan for defect-2301727 20160620
        prop_dict['ro.build.version.incremental'] = BUILD_NUMBER

	try:
		input_prop = open(build_prop,'r')
		properties = input_prop.readlines()
		input_prop.close()

		output_prop = open(build_prop,'w')
		for readline in properties:
			writeline = readline
			for key in prop_dict.keys():
				if re.search(r'^'+key+'=',readline.strip('\n')):
					writeline = key+'='+prop_dict[key]+'\n'
			output_prop.write(writeline)
		output_prop.close()

	except Exception,e:
		log.error("ERROR: %s",e)
		return 1

	replace_properties(jrd_sys_prop,build_prop)

	return 0

def prepare_fonts():
	log.info("now building the customized fonts...")

def prepare_theme():
	log.info("now copy the theme")
	clean_intermediates_folder(THEME_OUT_PATH+'/theme')
	if os.path.exists(THEME_OUT_PATH+'/theme'):		#call shutil.copytree.  The destination directory must not already exist.
		os.remove(THEME_OUT_PATH+'/theme')
	shutil.copytree(THEME_RESOUCE_PATH,THEME_OUT_PATH+'/theme')
#add by feikuang@tcl.com begin
def get_gapp_plf_info(gapp_plf):

	doc = xml.dom.minidom.parse(gapp_plf)      #open plf

	table_var = doc.documentElement            #<TABLE_VAR>

	vars= table_var.getElementsByTagName('VAR')  #all <VAR>

	gapp_info={}

	for var in vars:
		print "-------------------------------------------"

		# simple_var = var.getElementsByTagName('SIMPLE_VAR')

		isdm_name = var.getElementsByTagName('SDMID')[0].childNodes[0].data
		isdm_value = var.getElementsByTagName('VALUE')[0].childNodes[0].data

		print "isdm_name: %s"  %isdm_name
		print "isdm_value: %s"  %isdm_value

		gapp_name = isdm_name.split("_")[-1]
		print "gapp_name: %s" %gapp_name

		gapp_info[gapp_name]=isdm_value

	return gapp_info

def output_gapp_customized_result(gapp_info):

	selected_gapp=''
	unselected_gapp=''

	for key in gapp_info:
		if gapp_info[key] == "0":
			unselected_gapp += key + ' '

		else:
			selected_gapp += key + ' '

	selected_gapp=selected_gapp.strip(' ')
	unselected_gapp=unselected_gapp.strip(' ')

	print "selected_gapp : %s" %selected_gapp
	print "unselected_gapp : %s" %unselected_gapp

	output_result=open(JRD_WIMDATA+'/wcustores/remove_gapp.txt','w')
	output_result.write(unselected_gapp)
	output_result.close()

def prepare_gapp():
    log.info("prepare_gapp!")
    GAPP_DELETE_PACKAGES = commands.getoutput('cat '+JRD_WIMDATA+'/wcustores/remove_gapp.txt').split(' ')
    GAPP_PATH = commands.getoutput('find vendor/tctalone/TctAppPackage/ -name "*.mk"').split('\n')
    if GAPP_DELETE_PACKAGES != ['']:
        log.info("jjj")
        for gapp in GAPP_DELETE_PACKAGES:
            #gapp_name=read_variable_from_makefile("LOCAL_MODULE",GAPP_PATH+'/Android.mk')
            if os.path.isdir(JRD_OUT_SYSTEM+'/app/'+gapp):
                gapp_dirname=JRD_OUT_SYSTEM+'/app/'+gapp
                shutil.rmtree(gapp_dirname)
                log.info("remove system/app/"+gapp)
            elif os.path.isdir(JRD_OUT_SYSTEM+'/priv-app/'+gapp):
                gapp_dirname=JRD_OUT_SYSTEM+'/priv-app/'+gapp
                shutil.rmtree(gapp_dirname)
                log.info("remove system/priv-app/"+gapp)
            else:
                log.info("can't find gapp",gapp)
                continue
            if os.path.isfile(JRD_OUT_SYSTEM+'/vendor/overlay/'+gapp+'-overlay.apk'):
                os.remove(JRD_OUT_SYSTEM+'/vendor/overlay/'+gapp+'-overlay.apk')
                log.info("remove system/vendor/overlay/"+gapp+'-overlay.apk')
                log.info("xxxx")
#add by feikuang@tcl.com end

def prepare_overlay_res():
	log.info("")
	if DEBUG_ONLY == "":
		prepare_translations()
		prepare_res_config()

	env_image_value = os.environ['TARGET_BUILD_CUSTOM_IMAGES']
	if env_image_value :
		log.info("TARGET_BUILD_CUSTOM_IMAGES=[%s]",env_image_value)
		prepare_photos()

	if not MM_MODULE_NAME:
		prepare_media()
		prepare_gid_config() # MODIFIED by yzsong, 2016-06-24,BUG-2390227
		prepare_ringtone()
		prepare_usermanual()
		prepare_apn()
		prepare_plmn()
		prepare_appmanager()
		prepare_thermal()
		prepare_wifi()
		prepare_dpm()
		prepare_btc()
		prepare_nfc()
	ret = find_res_dir(STRING_RES_PATH + '/perso/string_res.ini')
        #add by feikuang@tcl.com begin
        pushdir(TOP)
        TEMPMY_RES_DIRS=' '.join(MY_RES_DIR)
        log.info("/bin/bash %s/copyOriginResource.sh %s %s %s %s",SCRIPTS_DIR,JRD_WIMDATA,TEMPMY_RES_DIRS,TOP,JRD_CUSTOM_RES)
        subprocess.check_call(('/bin/bash',SCRIPTS_DIR+'/copyOriginResource.sh',JRD_WIMDATA,TEMPMY_RES_DIRS,TOP,JRD_CUSTOM_RES))
        popdir()
        #add by feikuang@tcl.com end
	if ret != 0:
		log.error("ERROR: find re in path failed")
		sys.exit(ret)
	if MM_MODULE_NAME:
		print '#', MM_MODULE_NAME
		check_module()
	ret = prepare_launcher_workspace()
	if ret != 0:
		log.error("ERROR: prepare launcher failed")
		sys.exit(ret)
	ret = prepare_plfs()
	if ret != 0:
		log.error("ERROR: process plf to xml failed")
		sys.exit(ret)

	if not MM_MODULE_NAME:
		ret = prepare_build_prop()
		if ret != 0:
			log.error("ERROR: buiding build.prop failed")
			sys.exit(ret)

	return 0

def check_module():
	module_name = []
	for path in MY_RES_DIR:
		path_split = path.split(os.sep)
		for index in xrange(len(path_split)):
			if re.search(r'res|res_ext', path_split[index]):
				module_name.append(path_split[index-1].lower())
				break
	print module_name
	if MM_MODULE_NAME.lower() in module_name:
		return module_name
	else:
		log.error('ERROR: not match the module name : [%s]' % MM_MODULE_NAME)
		sys.exit(-1)

def prepare_audio_param():
	log.info("copy audio params")
	if not os.path.exists(JRD_OUT_SYSTEM+'/etc/acdbdata/MTP'):
		os.makedirs(JRD_OUT_SYSTEM+'/etc/acdbdata/MTP/')
	shutil.copy(JRD_PROPERTIES_AUDIO+'/Bluetooth_cal.acdb',JRD_OUT_SYSTEM+'/etc/acdbdata/MTP/MTP_Bluetooth_cal.acdb')
	shutil.copy(JRD_PROPERTIES_AUDIO+'/General_cal.acdb',JRD_OUT_SYSTEM+'/etc/acdbdata/MTP/MTP_General_cal.acdb')
	shutil.copy(JRD_PROPERTIES_AUDIO+'/Global_cal.acdb',JRD_OUT_SYSTEM+'/etc/acdbdata/MTP/MTP_Global_cal.acdb')
	shutil.copy(JRD_PROPERTIES_AUDIO+'/Handset_cal.acdb',JRD_OUT_SYSTEM+'/etc/acdbdata/MTP/MTP_Handset_cal.acdb')
	shutil.copy(JRD_PROPERTIES_AUDIO+'/Hdmi_cal.acdb',JRD_OUT_SYSTEM+'/etc/acdbdata/MTP/MTP_Hdmi_cal.acdb')
	shutil.copy(JRD_PROPERTIES_AUDIO+'/Headset_cal.acdb',JRD_OUT_SYSTEM+'/etc/acdbdata/MTP/MTP_Headset_cal.acdb')
	shutil.copy(JRD_PROPERTIES_AUDIO+'/Speaker_cal.acdb',JRD_OUT_SYSTEM+'/etc/acdbdata/MTP/MTP_Speaker_cal.acdb')

	shutil.copy(JRD_PROPERTIES_AUDIO_SmartPA+'/seltech_stereo.ini',JRD_OUT_SYSTEM+'/etc/tfa9897/seltech_stereo.ini')
	shutil.copy(JRD_PROPERTIES_AUDIO_SmartPA+'/seltech_stereo.cnt',JRD_OUT_SYSTEM+'/etc/tfa9897/seltech_stereo.cnt')
	shutil.copy(JRD_PROPERTIES_AUDIO_SmartPA+'/seltech_top.ini',JRD_OUT_SYSTEM+'/etc/tfa9897/seltech_top.ini')
	shutil.copy(JRD_PROPERTIES_AUDIO_SmartPA+'/seltech_top.cnt',JRD_OUT_SYSTEM+'/etc/tfa9897/seltech_top.cnt')
	shutil.copy(JRD_PROPERTIES_AUDIO_SmartPA+'/seltech_bottom.ini',JRD_OUT_SYSTEM+'/etc/tfa9897/seltech_bottom.ini')
	shutil.copy(JRD_PROPERTIES_AUDIO_SmartPA+'/seltech_bottom.cnt',JRD_OUT_SYSTEM+'/etc/tfa9897/seltech_bottom.cnt')

	return 0

def get_product_aapt_config(file_path):
	log.info("")
	default_aapt_config="normal,xhdpi,xxhdpi,hdpi,mdpi,ldpi,nodpi,anydpi,large"
	if os.path.isfile(file_path):
		language_list=read_variable_from_makefile("PRODUCT_LOCALES",file_path)
		return language_list.replace('\n',',')+','+default_aapt_config
	else:
		return "Can't find jrd_build_properties.mk, exiting now ... "

def read_package_from_manifest(manifest_file):
	if os.path.isfile(manifest_file):
		do = minidom.parse(manifest_file)
		root = do.documentElement
		if root.getAttribute('package') != "com.jrdcom.setupwizard.overlay":
			attrib = root.getAttribute('package').replace('.overlay','')
		else:
			attrib = root.getAttribute('package')
		log.info("attrib:[%s]",attrib)
		return attrib

def get_package_name(top,jdr_dir_path,res_dir_path):
	log.info("")
	if os.path.isdir(jdr_dir_path+'/'+res_dir_path):
		if os.path.isfile(top+'/'+res_dir_path+'/'+'AndroidManifest.xml'):
			return read_package_from_manifest(top+'/'+res_dir_path+'/'+'AndroidManifest.xml')
		else:
			apklist=[]
			if os.path.exists(top+'/'+res_dir_path):
				apklist = findExtFile(top+'/'+res_dir_path,'.apk')

			if len(apklist) == 1:
				result = commands.getoutput(MY_AAPT_TOOL+' d --values permissions '+apklist[0]+' | head -n 1')
				log.info("result:[%s]",result)
				if len(result) != 0:
					return result.split(':')[1].strip(' ')

			elif len(apklist) < 1:
				log.warning("WARNNING:NO APK exist.")
				return ""
			else:
				log.error("ERROR: [%s/%s]Duplicated APK exist.",top,res_dir_path)
				sys.exit(-1)
	else:
		return ""

def get_coreApp_attr(top,jdr_dir_path,res_dir_path):
	log.info("")
	coreApp = ''
	if os.path.isdir(jdr_dir_path+'/'+res_dir_path):
		if os.path.isfile(top+'/'+res_dir_path+'/AndroidManifest.xml'):
			xmlDoc = ElementTree.parse(top+'/'+res_dir_path+'/AndroidManifest.xml')
			if 'coreApp' in xmlDoc.getroot().attrib.keys():
				coreApp = xmlDoc.getroot().attrib['coreApp']
	return coreApp

def get_local_package_name(res_dir):
	log.info("")
	if os.path.isfile(res_dir+'/Android.mk'):
		name = read_variable_from_makefile("LOCAL_PACKAGE_NAME",res_dir+'/Android.mk')
		# if more than one package name found, remove override package
		log.debug("[%s]",name)
		if name == "" or re.search(r'TctAppPackage',res_dir):
			name=read_variable_from_makefile("LOCAL_MODULE",res_dir+'/Android.mk')
			return name
		elif len(re.split(r'\s',name)) > 1:
			override=read_variable_from_makefile("LOCAL_OVERRIDES_PACKAGES",res_dir+'/Android.mk')
			if override != "" and re.search(r''+override,name):
				return re.sub(r''+override,r'',name)
			else:
				return ""
		else:
			return name
	else:
		log.info("%s/Android.mk not found",res_dir)
		return ""

def eval_variable(variable_path):
	'''
	command make --no-print-directory -f build/core/config.mk dumpvar-variable_path
	'''
	if not re.search(r'\$',variable_path):
		return variable_path
	var = ''
	if re.search(r'/',variable_path):
		dir_list = variable_path.split('/')
		dir_count = len(dir_list)
		tmp_count = 0
		for a in dir_list:
			tmp_count = tmp_count + 1
			if a == "":
				if tmp_count == 1:
					var = var + '/'
				else:
					continue
			elif a[0] == '$':
				var = var + get_build_var(a[1:])
				if tmp_count == dir_count:
					break
				else:
					var = var + '/'
			else:
				var = var + a
				if tmp_count == dir_count:
					break
				else:
					var = var + '/'

	return var

def get_custo_apk_path(top_res):
	is_privileged_module = ''
	my_module_path = ''
	log.debug("%s/Android.mk",top_res)
	if os.path.isfile(top_res+'/'+'Android.mk'):
		is_privileged_module = read_variable_from_makefile("LOCAL_PRIVILEGED_MODULE",top_res+'/'+'Android.mk')
		my_module_path = read_variable_from_makefile("LOCAL_MODULE_PATH",top_res+'/'+'Android.mk')
		if my_module_path != "":
			my_module_path = "".join(re.findall(r'\$[A-Z_]*[-/a-z]*',re.sub(r'[()]',r'',my_module_path)))
			log.debug("my_module_path:[%s]",my_module_path)
			patten = re.findall(r'([A-Z_]*)',my_module_path)
			if patten and len(patten) > 0:
				for i in range(len(patten)):
					if patten[i] in globals().keys():
						my_module_path = my_module_path.replace('$'+patten[i],globals()[patten[i]])
			log.debug("my_module_path:[%s]",my_module_path)
			if (not re.search(r'system/framework',my_module_path)) and (not re.search(r'system/app',my_module_path)) and (not re.search(r'system/priv-app',my_module_path)) and (not re.search(r'system/custpack/app',my_module_path)):
				my_module_path = ""
		else:
			my_module_path = ""

	if is_privileged_module == "true":
		return JRD_OUT_SYSTEM+'/priv-app'
	else:
		if (not my_module_path is None) and (os.path.exists(my_module_path)):
			return my_module_path
		else:
			return JRD_OUT_SYSTEM+'/app'

def generate_androidmanifest_xml(pack_path,tmp_path,coreAppAttr):
	log.info("Generate AndroidManifest.xml...")
	if pack_path !="" and os.path.exists(tmp_path):
		if coreAppAttr:
			content = '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
	package="'''+pack_path+'''.overlay" coreApp="true">
	<uses-sdk android:minSdkVersion="23" android:targetSdkVersion="23" />
	<overlay android:targetPackage="'''+pack_path+'''" android:priority="16"/>
</manifest>'''
		else:
			content = '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
	package="'''+pack_path+'''.overlay">
	<uses-sdk android:minSdkVersion="23" android:targetSdkVersion="23" />
	<overlay android:targetPackage="'''+pack_path+'''" android:priority="16"/>
</manifest>'''

		open(tmp_path+'/AndroidManifest.xml','a').write(content)

def get_extra_resource(first_string,attrib_name,package_xml):
	if attrib_name=="" or (not os.path.exists(package_xml)):
		sys.exit(-1)
	xmlDoc = ElementTree.parse(package_xml)
	path_res = ""
	for node in xmlDoc.getiterator('package'):
		if node.get('name') == attrib_name:
			for subnode in node.getchildren():
				if os.path.exists(JRD_CUSTOM_RES+'/'+subnode.attrib['path']):
					path_res = path_res + first_string + subnode.attrib['path']

	return path_res

def generate_overlay_packages():
	log.info("")
	# parse string_res.ini, to find out all packages that need generate overlay apk
	# TODO: string_res.ini only include packages need to be translated, but still there is some pacages use google default translation.

	my_apk_path = TARGET_OUT_VENDOR_OVERLAY
	my_package_name = ""
	my_apk_file_name = ""
	my_apk_certificate = ""
	main_apk_path = ""
	if not MM_MODULE_NAME:
		clean_intermediates_folder(TARGET_OUT_VENDOR_OVERLAY)

	if not os.path.exists(my_apk_path):
		os.makedirs(my_apk_path)

	PRODUCT_LOCALES      = read_variable_from_makefile("PRODUCT_LOCALES",JRD_CUSTOM_RES+'/jrd_build_properties.mk').split('\n')
	PRODUCT_AAPT_CONFIG  = get_product_aapt_config(JRD_CUSTOM_RES+'/jrd_build_properties.mk')

	prepare_timezone(PRODUCT_LOCALES)

	if os.path.isfile("missing_package.log"):
		os.remove("missing_package.log")

	pushdir(TOP)

	print 'MY_RES_DIR:', MY_RES_DIR
	for res in MY_RES_DIR:
		extra_res=""
		res = os.path.dirname(res)
		log.info("Start to process ---- "+res+" ----")
		if not MM_MODULE_NAME:
			my_apk_file_name=get_local_package_name(TOP+'/'+res)
		else:
			my_apk_file_name=get_mm_package_name()

		main_apk_path=get_custo_apk_path(TOP+'/'+res)
		log.info("[main_apk_path]:%s [my_apk_file_name]:%s" % (main_apk_path, my_apk_file_name))
		if ((not DAILYBUILD_FLAG) and (not MM_MODULE_NAME)):
			if (not os.path.exists(main_apk_path+'/'+my_apk_file_name+'/'+my_apk_file_name+'.apk')) and (not os.path.exists(main_apk_path+'/'+my_apk_file_name+'.apk')):
				open("ungene_package.log","a").write("main_apk_path: "+main_apk_path+"\napkfile_name: "+my_apk_file_name+"\n")
				continue
		my_package_name = get_package_name(TOP,JRD_CUSTOM_RES,res)
		log.info("my_package_name=[%s]",my_package_name)

		coreAppAttr = get_coreApp_attr(TOP,JRD_CUSTOM_RES,res)
		log.info("coreAppAttr=[%s]",coreAppAttr)

		if (my_package_name != "") and (my_apk_file_name != "") and (my_apk_file_name not in JRD_DELETED_PACKAGES):
			my_tmp_path = JRD_CUSTOM_RES+'/'+res
			if not os.path.exists(my_tmp_path):
				os.makedirs(my_tmp_path)
			generate_androidmanifest_xml(my_package_name,my_tmp_path,coreAppAttr)
			log.debug("my_apk_file_name=[%s],JRD_CUSTOM_RES=[%s],JRD_BUILD_PATH_DEVICE=[%s]",my_apk_file_name,JRD_CUSTOM_RES,JRD_BUILD_PATH_DEVICE)
			if re.search(r'<package name="'+my_apk_file_name+r'">',open(PACKAGE_LIST_PATH+'/package_list.xml','r').read()):
				try:
					extra_res = get_extra_resource(' -S '+JRD_CUSTOM_RES+'/',my_apk_file_name,PACKAGE_LIST_PATH+"/package_list.xml")
					log.info("extra_res=[%s]",extra_res)
					if extra_res != "":
						extra_res="--auto-add-overlay "+extra_res
				except subprocess.CalledProcessError as err:
					log.error("ERROR: except Exception:%s",err)
					sys.exit(-1)
			else:
				extra_res = ""

			if os.path.isdir(JRD_CUSTOM_RES+'/'+res+'/assets'):
				MY_ASSET_OPT="-A "+JRD_CUSTOM_RES+"/"+res+"/assets"
			else:
				MY_ASSET_OPT=""
				log.info("MY_ASSET_OPT is null")

			if not os.path.exists(JRD_CUSTOM_RES+'/'+res+'/res'):
				os.makedirs(JRD_CUSTOM_RES+'/'+res+'/res')

			if os.path.isfile(JRD_CUSTOM_RES+'/'+res+'/AndroidManifest.xml'):
				try:
					result = subprocess.check_output(MY_AAPT_TOOL+' p -f -I '+MY_ANDROID_JAR_TOOL+' -S '+JRD_CUSTOM_RES+'/'+res+'/res '+extra_res+
						' -M '+JRD_CUSTOM_RES+'/'+res+'/AndroidManifest.xml'+' -c '+PRODUCT_AAPT_CONFIG+' -F '+my_tmp_path+'/'+my_apk_file_name+'-overlay.apk'+MY_ASSET_OPT,shell=True,stderr=subprocess.STDOUT)
					log.info("result=[%s]",result)
				except subprocess.CalledProcessError as err:
					log.error("%s p -f -I %s -S %s/%s/res %s -M %s/%s/AndroidManifest.xml -c %s -F %s/%s-overlay.apk%s",MY_AAPT_TOOL,MY_ANDROID_JAR_TOOL,JRD_CUSTOM_RES,res,extra_res,JRD_CUSTOM_RES,res,PRODUCT_AAPT_CONFIG,my_tmp_path,my_apk_file_name,MY_ASSET_OPT)
					log.error("ERROR: except Exception:%s",err)
					sys.exit(-1)

				if not os.path.exists(my_tmp_path+'/'+my_apk_file_name+'-overlay.apk'):
					open("overlay-failed.log","a").write(my_tmp_path+'/'+my_apk_file_name+'-overlay.apk'+" generate failed")

				#TODO: It's ok to use releasekey for all overlay apk
				my_apk_certificate="releasekey"

				#Try use jdk6 jarsigner to sign overlay apk, which is much faster then by using signapk.jar!
				if os.path.exists("/opt/java/jdk1.6.0_45"):
					try:
						log.info("pwd:%s %s/android.testkey" % (os.getcwd(), SCRIPTS_DIR))

						sign_cmd = '/opt/java/jdk1.6.0_45/bin/jarsigner -sigfile CERT -verbose' \
								+' -digestalg SHA1 -sigalg MD5withRSA' \
								+' -keystore '+SCRIPTS_DIR+'/android.testkey' \
								+' -storepass TCL_1010' \
								+' -signedjar '+my_tmp_path+'/'+my_apk_file_name+'-overlay-signed.apk' \
								+' '+my_tmp_path+'/'+my_apk_file_name+'-overlay.apk' \
								+' android-testkey-key'
						os.popen(sign_cmd)
						log.info("Now generate %s/%s-overlay-signed.apk...",my_tmp_path,my_apk_file_name)

						zipalign_cmd = 'zipalign -f -v 4' \
								+' '+my_tmp_path+'/'+my_apk_file_name+'-overlay-signed.apk' \
								+' '+my_apk_path+'/'+my_apk_file_name+'-overlay.apk'
						os.popen(zipalign_cmd)
					except Exception,e:
						log.error("/opt/jdk1.6.0_45/bin/jarsigner -sigfile CERT -verbose -digestalg SHA1 -sigalg MD5withRSA -keystore %s/android.testkey -storepass TCL_1010 -signedjar %s/%s-overlay-signed.apk %s/%s-overlay.apk android-testkey-key",SCRIPTS_DIR,
							my_tmp_path,my_apk_file_name,my_tmp_path,my_apk_file_name)
						log.error("ERROR: except Exception:%s",e)
						sys.exit(-1)
				elif my_apk_certificate != "":
					if not os.path.isfile(TOP+"/build/target/product/security_releasekey/"+my_apk_certificate+".x509.pem"):
						shutil.copy(TOP+"/build/target/product/security_releasekey/testkey.x509.pem", TOP+"/build/target/product/security_releasekey/"+my_apk_certificate+".x509.pem")
					if not os.path.isfile(TOP+"/build/target/product/security_releasekey/"+my_apk_certificate+".pk8"):
						shutil.copy(TOP+"/build/target/product/security_releasekey/testkey.pk8", TOP+"/build/target/product/security_releasekey/"+my_apk_certificate+".pk8")
					try:
						subprocess.check_call(("java","-Xmx128m","-jar",TOP+"/out/host/linux-x86/framework/signapk.jar",
									TOP+"/build/target/product/security_releasekey/"+my_apk_certificate+".x509.pem",
									TOP+"/build/target/product/security_releasekey/"+my_apk_certificate+".pk8",
									my_tmp_path+'/'+my_apk_file_name+"-overlay.apk",
									my_apk_path+'/'+my_apk_file_name+"-overlay.apk"))
					except subprocess.CalledProcessError as err:
						log.error("java -Xmx128m -jar %s/out/host/linux-x86/framework/signapk.jar %s/build/target/product/security_releasekey/%s.x509.pem %s/build/target/product/security_releasekey/%s.pk8 %s/%s-overlay.apk %s/%s-overlay.apk",
							TOP,TOP,my_apk_certificate,TOP,my_apk_certificate,my_tmp_path,my_apk_file_name,my_apk_path,my_apk_file_name)
						log.error("ERROR: except Exception:%s",err)
						sys.exit(-1)
					if not os.path.exists(my_apk_path+'/'+my_apk_file_name+'-overlay.apk'):
						open("sign-failed.log","a").write(my_apk_path+'/'+my_apk_file_name+'-overlay.apk sign failed')
					else:
						try:
							log.info('zipalign -c 4 %s/%s-overlay.apk' % (my_apk_path, my_apk_file_name))
							result = subprocess.check_call(("zipalign","-c","4",my_apk_path+'/'+my_apk_file_name+"-overlay.apk"))
						except subprocess.CalledProcessError as err:
							log.error("zipalign -c 4 %s/%s-overlay.apk",my_apk_path,my_apk_file_name)
							log.error("ERROR: except Exception:%s",err)
							sys.exit(-1)
						try:
							if result != 0:
								result = subprocess.check_call(("zipalign","-f","4",my_apk_path+'/'+my_apk_file_name+"-overlay.apk",my_apk_path+'/'+my_apk_file_name+"-overlay.apk_aligned"))
						except subprocess.CalledProcessError as err:
							log.error("zipalign -c 4 %s/%s-overlay.apk %s/%s-overlay.apk_aligned",my_apk_path,my_apk_file_name,my_apk_path,my_apk_file_name)
							log.error("ERROR: except Exception:%s",err)
						if result != 0 and os.path.exists(my_apk_path+'/'+my_apk_file_name+"-overlay.apk_aligned"):
							os.remove(my_apk_path+'/'+my_apk_file_name+'-overlay.apk')
							os.rename(my_apk_path+'/'+my_apk_file_name+'-overlay.apk_aligned',my_apk_path+'/'+my_apk_file_name+'-overlay.apk')
		else:
			miss_log = open('missing_package.log','a')
			miss_log.write(res+'/res')
			if not my_package_name is None:
				miss_log.write('package_name: '+my_package_name)
			if not my_apk_file_name is None:
				miss_log.write('apkfile_name: '+my_apk_file_name)
			miss_log.close()
	#if os.path.exists(JRD_OUT_SYSTEM+'/vendor/overlay/'+'GmsSetupWizardOverlay-overlay.apk'):
	#	os.remove(JRD_OUT_SYSTEM+'/vendor/overlay/'+'GmsSetupWizardOverlay-overlay.apk')
	popdir()
	return 0
#add by feikuang@tcl.com begin
def prepre_extra_apk():
    if os.path.isdir(JRD_WIMDATA+'/wcustores/App/'+TARGET_PRODUCT+'/PrivApp/ThirdParty'):
	    if os.listdir(JRD_WIMDATA+'/wcustores/App/'+TARGET_PRODUCT+'/PrivApp/ThirdParty'):
        	    apk_list_priv = commands.getoutput('find '+JRD_WIMDATA+'/wcustores/App/'+TARGET_PRODUCT+'/PrivApp/ -name "*.apk"' ).split('\n')
        	    print "apk_list_priv",apk_list_priv
        	    if apk_list_priv != ['']:
        		    for apkitem in apk_list_priv:
                		    apk_name=os.path.basename(apkitem)
                		    apk_folo_pri=apk_name.split('.apk')[0]
                		    if os.path.isdir(JRD_OUT_SYSTEM+'/priv-app/'+apk_folo_pri):
                        		    apk_dirname_pri=JRD_OUT_SYSTEM+'/priv-app/'+apk_folo_pri
                        		    shutil.rmtree(apk_dirname_pri)
                		    elif os.path.isfile(JRD_OUT_SYSTEM+'/priv-app/'+apk_name):
                        		    os.remove(apk_name)
                		    else:
                        		    log.info("WARNING:CANNOT find %s in /system/app",apk_name)
    if os.path.isdir(JRD_WIMDATA+'/wcustores/App/'+TARGET_PRODUCT+'/Unremoveable/ThirdParty'):
	    if os.listdir(JRD_WIMDATA+'/wcustores/App/'+TARGET_PRODUCT+'/Unremoveable/ThirdParty'):
        	    apk_list_unre = commands.getoutput('find '+JRD_WIMDATA+'/wcustores/App/'+TARGET_PRODUCT+'/Unremoveable/ -name "*.apk"' ).split('\n')
        	    print "apk_list_unre",apk_list_unre
        	    if apk_list_unre != ['']:
        		    for apkitem in apk_list_unre:
                		    apk_name=os.path.basename(apkitem)
                		    apk_folo_unre=apk_name.split('.apk')[0]
                		    if os.path.isdir(JRD_OUT_SYSTEM+'/app/'+apk_folo_unre):
                        		    apk_dirname_unre=JRD_OUT_SYSTEM+'/app/'+apk_folo_unre
                        		    shutil.rmtree(apk_dirname_unre)
                		    if os.path.isfile(JRD_OUT_SYSTEM+'/app/'+apk_name):
                        		    os.remove(apk_name)
                		    else:
                        		    log.info("WARNING:CANNOT find %s in /system/priv",apk_name)
#add by feikuang@tcl.com end
def change_system_ver():

	log.info("")
	if os.path.exists(JRD_OUT_SYSTEM+'/system.ver'):
		os.remove(JRD_OUT_SYSTEM+'/system.ver')
	open(JRD_OUT_SYSTEM+'/system.ver','w').write(PERSO_VERSION)

	return 0


def release_key():
	log.info("/bin/bash %s/checkapk_perso.sh %s",SCRIPTS_DIR,TARGET_PRODUCT)
	try:
		pushdir(TOP)
		log.info("pwd:%s" % os.getcwd())
		subprocess.check_call(('/bin/bash',SCRIPTS_DIR+'/checkapk_perso.sh',JRD_OUT_CUSTPACK,TOP))
		log.info("/bin/bash %s/releasekey.sh TCL_1010 %s",SCRIPTS_DIR,TARGET_PRODUCT)
		subprocess.check_call(('/bin/bash',SCRIPTS_DIR+'/releasekey.sh',"TCL_1010",TARGET_PRODUCT))
		popdir()
	except subprocess.CalledProcessError as err:
		log.error("ERROR: %s",err)
		sys.exit(-1)

def generate_splash_image():
	log.info("Generate a splash.img from the picture")
	log.debug("%s/logo_gen/multi_logo_gen.py %s/splash.img %s/device/tct/%s/logo.png %s/device/tct/%s/Dload_logo.png %s/device/tct/%s/Low_power_logo.png %s/device/tct/%s/Charger_boot_logo.png",JRD_TOOLS,PRODUCT_OUT,TOP,TARGET_PRODUCT,TOP,TARGET_PRODUCT,TOP,TARGET_PRODUCT,TOP,TARGET_PRODUCT)
	cmd = 'python '+JRD_TOOLS+'/logo_gen/multi_logo_gen.py '+PRODUCT_OUT+'/splash.img '+TOP+'/device/tct/'+TARGET_PRODUCT+'/logo.png '+TOP+'/device/tct/'+TARGET_PRODUCT+'/Dload_logo.png '+TOP+'/device/tct/'+TARGET_PRODUCT+'/Low_power_logo.png '+TOP+'/device/tct/'+TARGET_PRODUCT+'/Charger_boot_logo.png'
	(status,output) = commands.getstatusoutput(cmd)
	if status != 0:
		log.error("ERROR: \n%s",output)
		log.error("ERROR: %s/splash.img generate failed" % PRODUCT_OUT)
		sys.exit(status)

def generate_system_image(image_name):
	log.info("Now start to generate %s image ... " % image_name)

	pushdir(TOP)

	image_info = {}
	build_prop = JRD_OUT_SYSTEM + '/build.prop'
	internal_product = get_build_var("INTERNAL_PRODUCT")

	if image_name == 'system':

		if SYSTEM_SIZE == '':
			image_info['partition_size'] = get_build_var("BOARD_SYSTEMIMAGE_PARTITION_SIZE")
		else:
			image_info['partition_size'] = SYSTEM_SIZE

		image_info['mount_point'] = 'system'

		verity_partition = get_build_var("PRODUCTS."+internal_product+".PRODUCT_SYSTEM_VERITY_PARTITION")
		if verity_partition != '':
			image_info['verity_block_device'] = verity_partition

		if os.path.isfile(TARGET_ROOT_OUT+'/file_contexts.bin'):
			(status, output) = commands.getstatusoutput('find '+TARGET_OUT+' | while read -r line; do if [ -d "$line" ]; then line="$line/"; fi; echo $line | grep -o "system/.*"; done | fs_config -C -D '+TARGET_OUT+' -S '+TARGET_ROOT_OUT+'/file_contexts.bin > '+PRODUCT_OUT+'/filesystem_config.txt')
		if status != 0:
			log.error("ERROR: \n%s",output)
			log.error("ERROR: build filesystem_config.txt falied")
			sys.exit(status)

		if os.path.isfile(PRODUCT_OUT+'/filesystem_config.txt'):
			image_info['fs_config'] = PRODUCT_OUT+'/filesystem_config.txt'

		image_info['block_list'] = PRODUCT_OUT+'/system.map'

	elif image_name == 'userdata':

		if USERDATA_SIZE == '':
			image_info['partition_size'] = get_build_var("BOARD_USERDATAIMAGE_PARTITION_SIZE")
		else:
			image_info['partition_size'] = USERDATA_SIZE

		image_info['mount_point'] = 'data'

	else:
		log.error("ERROR: [%s] image generation is not supported at present",image_name)
		sys.exit(-1)

	if os.path.isfile(TARGET_ROOT_OUT+'/file_contexts.bin'):
		image_info['selinux_fc'] = TARGET_ROOT_OUT+'/file_contexts.bin'

	if get_build_var("TARGET_USERIMAGES_USE_EXT2") == "true":
		image_info['fs_type'] = 'ext2'
	elif get_build_var("TARGET_USERIMAGES_USE_EXT3") == "true":
		image_info['fs_type'] = 'ext3'
	elif get_build_var("TARGET_USERIMAGES_USE_EXT4") == "true":
		image_info['fs_type'] = 'ext4'
	else:
		log.error("ERROR: fs type error")
		sys.exit(-1)

	image_info['verity_signer_cmd'] = get_build_var("VERITY_SIGNER")

	image_info['verity_key'] = get_build_var("PRODUCTS."+internal_product+".PRODUCT_VERITY_SIGNING_KEY")

	if get_build_var("TARGET_USERIMAGES_SPARSE_EXT_DISABLED") != 'true':
		image_info['extfs_sparse_flag'] = '-s'

	image_info['skip_fsck'] = 'true'

	image_info['verity'] = get_build_var("PRODUCTS."+internal_product+".PRODUCT_SUPPORTS_VERITY")

	m = re.search(r'ro.build.date.utc\s*=\s*([0-9]*)',open(build_prop).read())
	if m:
		timestamp = m.group(1)
		if len(timestamp) > 0:
			image_info['timestamp'] = timestamp
	else:
		log.error("ERROR: no ro.build.date.utc in %s", build_prop)
		sys.exit(1)


	sys.path.append(TOP+'/build/tools/releasetools')
	import build_image

	if not build_image.BuildImage(PRODUCT_OUT+'/'+image_info['mount_point'], image_info, PRODUCT_OUT+'/'+image_name+'.img'):
		log.error("ERROR: failed to build %s from %s", PRODUCT_OUT+'/'+image_name+'.img', PRODUCT_OUT+'/'+image_info['mount_point'])
		sys.exit(1)
#	if image_name == 'system':
#		spinfo = PRODUCT_OUT+'/'+image_name +'.ext4.info' ## should be system.ext4.info
#		if not build_image.GetSparseInfo(PRODUCT_OUT+'/'+image_name+'.img', spinfo):
#			log.error("ERROR: failed to get ext4 info of %s/%s.img",PRODUCT_OUT,image_name)
#			sys.exit(1)

	popdir()

	return 0

def generate_tarball():
	log.info("Generate study.tar from the nv param management")
	pushdir(TOP)
	if os.path.exists(TARBALL_OUT_DIR):
		shutil.rmtree(TARBALL_OUT_DIR)
	os.makedirs(TARBALL_OUT_DIR)

	TARGET_BUILD_MMITEST = os.environ['TARGET_BUILD_MMITEST']

	if DAILYBUILD_FLAG:
		if not os.path.isfile(PRODUCT_OUT+'/plf/isdm_nv_control.plf'):
			merge_module_plf(JRD_NV_CONTROL_PLF)
	else:
		if not os.path.isdir(PRODUCT_OUT+'/plf'):
			os.makedirs(PRODUCT_OUT+'/plf')
		shutil.copy(JRD_NV_CONTROL_PLF,PRODUCT_OUT+'/plf/isdm_nv_control.plf')
		shutil.copy(JRD_PROPERTIES_PLF,PRODUCT_OUT+'/plf/isdm_sys_properties.plf')

	cmd = 'python '+AUTO_SCRIPTS_DIR+'/maketar.py '+TARGET_PRODUCT+' '+TARGET_BUILD_MMITEST+' '+PRODUCT_OUT+'/plf/isdm_nv_control.plf amss_8996/contents.xml '+TARBALL_OUT_DIR

	(status,output) = commands.getstatusoutput(cmd)
	if status != 0:
		log.error('ERROR: \n%s',output)
		log.error('ERROR: generate_tarball failed')
		sys.exit(-1)
	log.info("generate_tarball finished")
	popdir()
	return 0

def prepare_device_config_xml():
	"# Prepare device configration xmls, like, NFC/COMPASS, etc."
	log.info("")
	feature_sdmid  = ''
	feature_name   = ''
	feature_file   = ''
	feature_enable = ''
	build_prop = JRD_OUT_SYSTEM + '/build.prop'

	doc = ElementTree.parse(SCRIPTS_DIR+'/config/l8916.xml')
	for item in doc.getiterator('feature'):
		for myfeature in item.getchildren():
			feature_sdmid  = myfeature.attrib['sdmid']
			feature_name   = myfeature.attrib['feature']
			feature_file   = myfeature.attrib['xmlfile']
			output = commands.getoutput('cat '+build_prop+' | grep '+feature_sdmid).split('\n')
			if len(output) > 1:
				log.error("ERROR: duplicate SDM id in build.prop")
				sys.exit(1)
			if not output[0] == '':
				feature_enable = output[0].split('=')[1]
				if feature_enable=='false':
					delete_string_file(feature_sdmid,PRODUCT_OUT+'/'+feature_file)

	return 0

def read_variable_from_xml(attrib,xml_file):
	'''
	read in the makefile, and find out the value of the give variable\
	variable : target variable to found
	xml_path : target file to search
	'''
	if attrib =="" and (not os.path.exists(xml_file)):
		log.error("ERROR: paraments failed")
		sys.exit(-1)
	do = minidom.parse(xml_file)
	root = do.documentElement
	nodes = root.getElementsByTagName('bool')
	for node in nodes:
		if node.getAttribute('name') == attrib:
			value = node.childNodes[0].nodeValue
			return value

def prepare_GMS_apk():
	log.info("now process GMS apk...")
	if os.path.isfile("remove_GMS_apks.log"):
		os.remove("remove_GMS_apks.log")

	ALL_APK_FILES=read_variable_from_makefile("ZZ_THIRTY_APP",JRD_WIMDATA_WCUSTORES_PRODUCT+'/App/Unremoveable/all_GMS_app.mk').split('\n')
	PERSO_NEED_GMS=read_variable_from_makefile("ZZ_THIRTY_APP",JRD_WIMDATA_WCUSTORES_PRODUCT+'/App/Unremoveable/zz_thirty_app.mk').split('\n')
	for sourceapk in ALL_APK_FILES:
		filename=sourceapk
		found=False
		for destapk in PERSO_NEED_GMS:
			destfilename=destapk
			log.info("destfilename=%s",destfilename)
			if filename == destfilename:
				found=True
				log.info("%s is need",filename)
				break
		if found == False:
			log.info("%s is not found in zz_thirty_app.mk, please remove it")
			foldername=filename.split('.')[0]
			if foldername is None:
				log.info("do nothing")

			if os.path.exists(JRD_OUT_SYSTEM+'/app/'+foldername):
				shutil.rmtree(JRD_OUT_SYSTEM+'/app/'+foldername)
				open("remove_GMS_apks.log","a").write("apkfile_name: "+JRD_OUT_SYSTEM+"/app/"+foldername+"/"+filename)
			elif os.path.exists(JRD_OUT_SYSTEM+'/priv-app/'+foldername):
				shutil.rmtree(JRD_OUT_SYSTEM+'/priv-app/'+foldername)
				open("remove_GMS_apks.log","a").write("apkfile_name: "+JRD_OUT_SYSTEM+"/priv-app/"+foldername+"/"+filename)
			else:
				log.info("do nothing")

def remove_extra_apk():
	log.info("")
	global JRD_DELETED_PACKAGES
	JRD_DELETED_PACKAGES = read_JRD_from_makefile("JRD_PRODUCT_PACKAGES",JRD_CUSTOM_RES+'/jrd_build_properties.mk').split('\n')

	if os.path.isfile(JRD_WIMDATA+'/wcustores/gms_apk_unselected.txt'):
		GMS_DELETED_PACKAGES = commands.getoutput('cat '+JRD_WIMDATA+'/wcustores/gms_apk_unselected.txt').split(' ')
		JRD_DELETED_PACKAGES.extend(GMS_DELETED_PACKAGES)
	if os.path.isfile(JRD_WIMDATA+'/wcustores/gms_apk_removeable.txt'):
		GMS_REMOVEABLE_PACKAGES = commands.getoutput('cat '+JRD_WIMDATA+'/wcustores/gms_apk_removeable.txt').split(' ')
		JRD_DELETED_PACKAGES.extend(GMS_REMOVEABLE_PACKAGES)

	for apk in JRD_DELETED_PACKAGES:
		if os.path.isdir(JRD_OUT_SYSTEM+'/app/'+apk):
			apk_dirname=JRD_OUT_SYSTEM+'/app/'+apk
			apk_fullpath=JRD_OUT_SYSTEM+'/app/'+apk+'/'+apk+'.apk'
		elif os.path.isdir(JRD_OUT_SYSTEM+'/priv-app/'+apk):
			apk_dirname=JRD_OUT_SYSTEM+'/priv-app/'+apk
			apk_fullpath=JRD_OUT_SYSTEM+'/priv-app/'+apk+'/'+apk+'.apk'
		elif os.path.isfile(JRD_OUT_SYSTEM+'/app/'+apk+'.apk'):
			apk_dirname=JRD_OUT_SYSTEM+'/app/'+apk+'.apk'
			apk_fullpath=JRD_OUT_SYSTEM+'/app/'+apk+'.apk'
		elif os.path.isfile(JRD_OUT_SYSTEM+'/priv-app/'+apk+'.apk'):
			apk_dirname=JRD_OUT_SYSTEM+'/priv-app/'+apk+'.apk'
			apk_fullpath=JRD_OUT_SYSTEM+'/priv-app/'+apk+'.apk'
		else:
			log.warning("WARNING:CANNOT find %s in /system",apk)
			apk_dirname=""
			apk_fullpath=""
			continue
		if apk_dirname and os.path.isfile(apk_fullpath):
			if locals().has_key('GMS_REMOVEABLE_PACKAGES') and (apk in GMS_REMOVEABLE_PACKAGES) and (apk not in GMS_DELETED_PACKAGES):
				cmd = 'mkdir -p ' +  JRD_OUT_CUSTPACK + '/app/removeable'
				os.popen(cmd)
				cmd = 'cp -r '+ apk_dirname + ' ' +  JRD_OUT_CUSTPACK + '/app/removeable'
				result = os.popen(cmd)
				for line in result:
					open('remove_apks.log','a').write("apkfile_name: %s change path to removeable\n" % apk_fullpath)
				shutil.rmtree(apk_dirname)
				#open('remove_apks.log','a').write("apkfile_name: %s change path to removeable" % apk_fullpath)
			else:
				shutil.rmtree(apk_dirname)
				open('remove_apks.log','a').write("apkfile_name: %s\n" % apk_fullpath)
		else:
			log.info("do nothing")

	return 0

def prepare_selinux_tag(root_image,path):
	'''
	'''
	log.info("")
	origin_root_image=root_image
	dest_path=path
	if os.path.isfile(origin_root_image):
		os.makedirs(dest_path)
		pushdir(dest_path)
		log.info('gunzip -c %s | cpio -i',origin_root_image)
		cmd = 'gunzip -c '+origin_root_image+' | cpio -i'
		ret = os.popen(cmd)
		popdir()

	return 0

def get_mm_package_name():
	return MM_MODULE_NAME

def clean_build_logs(clean_files):
	if len(clean_files) > 0:
		for file in clean_files:
			if os.path.isfile(file):
				os.remove(file)

def check_apk_debugable(apk_name):
	SEARCH_RESULT = commands.getoutput('%s/out/host/linux-x86/bin/aapt l -v -a -M AndroidManifest.xml %s|grep android:Debuggable\(0x0101000f\)=\(type\ 0x12\)0xffffffff' % (TOP, apk_name))
	if SEARCH_RESULT:
		global DEBUG_APKS
		DEBUG_APKS.append(apk_name)

def check_apk_signature(apk_name):
	SEARCH_RESULT = commands.getoutput('jarsigner -certs -verbose -verify %s' % (apk_name))
	TEST_KEY = 'CN=Android, OU=Android, O=Android'
	if (not TEST_KEY) and (TEST_KEY in SEARCH_RESULT):
		global TESTKEY_APKS
		TESTKEY_APKS.append(apk_name)

def check_whitespace():
	log.info("Check filename contains whitespace in system image ... ")

	pushdir(PRODUCT_OUT)
	whitespace_file = commands.getoutput('find system -type f | grep " "')
	if not whitespace_file == '':
		log.error("ERROR: file contains whitespace character")
		sys.exit(1)
	popdir()

	return 0

def collect_build_info():

	pushdir(TOP)
	log.info('pwd:%s' % os.getcwd())

	if os.path.isfile('results.xml'):
		os.remove('results.xml')

	log.info("/bin/bash %s/tools/check_perso.sh -t %s -p %s",SCRIPTS_DIR,TOP,TARGET_PRODUCT)
	os.popen(SCRIPTS_DIR+"/tools/check_perso.sh -t "+TOP+" -p "+TARGET_PRODUCT)

	if os.path.isfile('results.xml'):
		log.info("python %s/tools/insert_build_info.py results.xml",SCRIPTS_DIR)
		(status,output) = commands.getstatusoutput("python "+SCRIPTS_DIR+"/tools/insert_build_info.py results.xml")
		if status != 0:
			log.warning("WARNING: \n%s",output)
			log.warning("WARNING:collect Software info failed")
	popdir()

	return 0

def prepare_tct_meta():
	if (os.path.exists(JRD_OUT_SYSTEM+'/build.prop')) and (os.path.exists(JRD_OUT_SYSTEM+'/system.ver')) and (os.path.exists(PRODUCT_OUT+'/system.map')):
		JRD_OUT_TCT_META = PRODUCT_OUT+'/tct_fota_meta_perso'
		JRD_OUT_TCT_META_ZIP = PRODUCT_OUT+'/tct_fota_meta_perso.zip'
		if not os.path.isdir(JRD_OUT_TCT_META):
			os.makedirs(JRD_OUT_TCT_META)
		shutil.copy(JRD_OUT_SYSTEM+'/build.prop',JRD_OUT_TCT_META)
		shutil.copy(JRD_OUT_SYSTEM+'/system.ver',JRD_OUT_TCT_META)
		#shutil.copy(PRODUCT_OUT+'/system.ext4.info',JRD_OUT_TCT_META)
		shutil.copy(PRODUCT_OUT+'/system.map',JRD_OUT_TCT_META)
		os.system('zip -rjq %s %s' % (JRD_OUT_TCT_META_ZIP,JRD_OUT_TCT_META))
	return 0



if __name__ == '__main__':
	#log level : ERROR > WARNING > INFO > DEBUG
	LOG = Log(os.path.basename(sys.argv[0]).split('.')[0]+'.log',logging.DEBUG,'w')
	log = LOG.setConsole(level=logging.WARNING)
	TARGET_PRODUCT = ''
	TOP = ''
	ORIGIN_SYSTEM_IMAGE = ''
	SYSTEM_SIZE = ''
	ORIGIN_USERDATA_IMAGE = ''
	USERDATA_SIZE = ''
	TARGET_THEME = ''
	PERSO_VERSION = ''
	DEBUG_ONLY = ''
	MY_RES_DIR = []
	DEBUG_APKS = []
	TESTKEY_APKS = []

	__notifyList = []
	__dirStack = []
	__multiRunErrMsgList = []
	intToolsUtilsMultiRunErrMsgQueue = None

	#get option arguments
	MM_MODULE_NAME = ''
	DAILYBUILD_FLAG = False
	NO_MOUNT_FLAG = False
	OFFICIALBUILD_FLAG = True
	MAKE_PERSO_OR_NOT = '1'

	if (not TARGET_PRODUCT ) and ('TARGET_PRODUCT' in os.environ):
		TARGET_PRODUCT = os.environ['TARGET_PRODUCT']

	if len(sys.argv[1:]) <= 16:
		msg_usage = "makePerso.py [ -p <productname>][ -t <build_dir>][ -s <system_image>] [ -y <system_size> ] [ -u <userdata>] [ -z <userdata_size>] [ -d <debug> ][ -m <target_theme> ][ -v <perso_version> ] [ mm ][ modulename ][ db ]"
		opt_parser = OptionParser(msg_usage)
		opt_parser.add_option("-p","--productname",action = "store",type = "string",dest = "TARGET_PRODUCT")
		opt_parser.add_option("-t","--build_dir",action = "store",type = "string",dest = "TOP")
		opt_parser.add_option("-s","--system_image",action = "store",type = "string",dest = "ORIGIN_SYSTEM_IMAGE")
		opt_parser.add_option("-y","--system_size",action = "store",type = "string",dest = "SYSTEM_SIZE")
		opt_parser.add_option("-u","--userdata_image",action = "store",type = "string",dest = "ORIGIN_USERDATA_IMAGE")
		opt_parser.add_option("-z","--userdata_size",action = "store",type = "string",dest = "USERDATA_SIZE")
		opt_parser.add_option("-m","--target_theme",action = "store",type = "string",dest = "TARGET_THEME")
		opt_parser.add_option("-v","--perso_version",action = "store",type = "string",dest = "PERSO_VERSION")
		opt_parser.add_option("-d","--debug_only",action = "store",type = "string",dest = "DEBUG_ONLY")
		options, args = opt_parser.parse_args()

		if options.TOP:
			TOP = options.TOP
		else:
			log.warn('-t must setting')
			usage()

		if options.TARGET_PRODUCT:
			TARGET_PRODUCT = options.TARGET_PRODUCT
		if options.ORIGIN_SYSTEM_IMAGE:
			ORIGIN_SYSTEM_IMAGE = options.ORIGIN_SYSTEM_IMAGE
		if options.SYSTEM_SIZE:
			SYSTEM_SIZE = options.SYSTEM_SIZE
		if options.ORIGIN_USERDATA_IMAGE:
			ORIGIN_USERDATA_IMAGE = options.ORIGIN_USERDATA_IMAGE
		if options.USERDATA_SIZE:
			USERDATA_SIZE = options.USERDATA_SIZE
		if options.TARGET_THEME:
			TARGET_THEME = options.TARGET_THEME
		if options.PERSO_VERSION:
			PERSO_VERSION = options.PERSO_VERSION
		if options.DEBUG_ONLY:
			DEBUG_ONLY = options.DEBUG_ONLY

		if 'mm' in args:
			for i in xrange(len(args)):
				if args[i] == 'mm':
					MM_MODULE_NAME =args[i+1]
					OFFICIALBUILD_FLAG = False
					print MM_MODULE_NAME
		if 'db' in args:
			DAILYBUILD_FLAG = True
			print DAILYBUILD_FLAG

		if MM_MODULE_NAME and DAILYBUILD_FLAG:
			print 'choose one in or db'
			sys.exit(0)

		if MM_MODULE_NAME or DAILYBUILD_FLAG or DEBUG_ONLY:
			NO_MOUNT_FLAG = True
			MAKE_PERSO_OR_NOT = '0'

	else:
		usage()

	if TARGET_PRODUCT is None:
		log.warning("Please specify target product.")
		usage()

	if TOP is None:
		log.warning("Please specify TOP folder.")
		usage()
	else:
		TOP = os.path.abspath(TOP)
		log.debug('TOP=[%s]',TOP)
		os.chdir(TOP)

	if OFFICIALBUILD_FLAG or MM_MODULE_NAME:
		if ORIGIN_SYSTEM_IMAGE is None :
			log.warning("Please specify where to find ORIGIN_SYSTEM_IMAGE.")
			usage()
		else:
			while True:
				if os.path.islink(ORIGIN_SYSTEM_IMAGE):
					ORIGIN_SYSTEM_IMAGE=os.readlink(ORIGIN_SYSTEM_IMAGE)
				else:
					break
			log.info("ORIGIN_SYSTEM_IMAGE="+ORIGIN_SYSTEM_IMAGE)

		if PERSO_VERSION is None:
			log.warning("Please specify PERSO version.")
			usage()
		else:
			log.info("PERSO_VERSION="+PERSO_VERSION)

		JRD_DELETED_PACKAGES = ''
		image_dir = os.path.abspath(os.path.dirname(ORIGIN_SYSTEM_IMAGE))
		if image_dir != "":
			ORIGIN_ROOT_IMAGE=image_dir+'/ramdisk.img'
		else:
			log.error("ERROR: ORIGIN_ROOT_IMAGE not find")
			sys.exit(-1)

	SCRIPTS_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
	if os.path.exists(SCRIPTS_DIR+'/out'):
		shutil.rmtree(SCRIPTS_DIR + '/out')

	#indicate the fold of wimdata in the source code
	JRD_WIMDATA = get_build_var('JRD_WIMDATA',True)
	JRD_WIMDATA_WCUSTORES_PRODUCT = JRD_WIMDATA + '/wcustores/' + TARGET_PRODUCT
	#indicate the path of the jrd tools
	JRD_TOOLS      = get_build_var('JRD_TOOLS',True)
	JRD_TOOLS_ARCT = get_build_var('JRD_TOOLS_ARCT',True)
	#indicate the main path for the build system of jrdcom
	JRD_BUILD_PATH = get_build_var('JRD_BUILD_PATH',True)
	#indicate the main path for the build system of a certain project
	JRD_BUILD_PATH_DEVICE = get_build_var('JRD_BUILD_PATH_DEVICE',True)
	JRD_BUILD_PATH_COMMON = get_build_var('JRD_BUILD_PATH_COMMON',True)
	#indicate the path of the system properties plf
	JRD_PROPERTIES_PLF = get_build_var('JRD_PROPERTIES_PLF',True)
	JRD_NV_CONTROL_PLF = get_build_var('JRD_NV_CONTROL_PLF',True)

	if os.path.isfile(JRD_BUILD_PATH_DEVICE+'/perso/string_res.ini'):
		STRING_RES_PATH = JRD_BUILD_PATH_DEVICE
	else:
		STRING_RES_PATH = JRD_BUILD_PATH_COMMON
	if os.path.isfile(JRD_BUILD_PATH_DEVICE+'/perso/package_list.xml'):
		PACKAGE_LIST_PATH = JRD_BUILD_PATH_DEVICE + '/perso'
	else:
		PACKAGE_LIST_PATH = SCRIPTS_DIR

	#the audio param path
	JRD_PROPERTIES_AUDIO = TOP+'/vendor/qcom/proprietary/mm-audio/audcal/family-b/acdbdata/8916/'+TARGET_PRODUCT
	JRD_PROPERTIES_AUDIO_SmartPA = TOP+'/hardware/qcom/audio/tfa9897/settings'

	JRD_SSV_PLF = JRD_WIMDATA+'/wprocedures/'+TARGET_PRODUCT
	PLF_PARSE_TOOL = TOP + '/device/tct/common/perso/tools/prd2xml'

	#indicate the jrd custom resource path in /out
	JRD_CUSTOM_RES = get_build_var('JRD_CUSTOM_RES',True)
	if MM_MODULE_NAME:
		JRD_CUSTOM_RES = JRD_CUSTOM_RES+'mm'
		clean_intermediates_folder(JRD_CUSTOM_RES)
	elif DAILYBUILD_FLAG:
		JRD_CUSTOM_RES = JRD_CUSTOM_RES+'db'
		clean_intermediates_folder(JRD_CUSTOM_RES)

	#indicate the customization out path
	PRODUCT_OUT        = get_build_var('PRODUCT_OUT',True)
	TARGET_ROOT_OUT    = get_build_var('TARGET_ROOT_OUT',True)
	JRD_OUT_CUSTPACK   = get_build_var('JRD_OUT_CUSTPACK',True)
	JRD_OUT_SYSTEM     = get_build_var('TARGET_OUT',True)
	JRD_OUT_USERDATA   = PRODUCT_OUT+'/data'
	TARBALL_OUT_DIR    = PRODUCT_OUT+'/tarball'

	if TARGET_THEME != '':
		THEME_RESOUCE_PATH = JRD_WIMDATA_WCUSTORES_PRODUCT+'/theme/output_zip/'+TARGET_THEME
		THEME_OUT_PATH     = JRD_OUT_SYSTEM

	#indicate the path of overlay apk
	TARGET_OUT_VENDOR_OVERLAY = PRODUCT_OUT+'/system/vendor/overlay'
	MY_ANDROID_JAR_TOOL       = TOP+'/prebuilts/sdk/current/android.jar'
	MY_AAPT_TOOL              = TOP+'/prebuilts/sdk/tools/linux/bin/aapt'
	#the path of gen tarball scripts
	AUTO_SCRIPTS_DIR = TOP+'/vendor/tct/source/qcn/auto_make_tar'

	TARGET_OUT                = get_build_var('TARGET_OUT',True)
	TARGET_OUT_ETC            = get_build_var('TARGET_OUT_ETC',True)
	TARGET_OUT_APP_PATH       = get_build_var('TARGET_OUT_APP_PATH',True)
	TARGET_OUT_PRIV_APP_PATH  = get_build_var('TARGET_OUT_PRIV_APP_PATH',True)
	TARGET_OUT_JAVA_LIBRARIES = get_build_var('TARGET_OUT_JAVA_LIBRARIES',True)
	TARGET_OUT_VENDOR_APPS    = get_build_var('TARGET_OUT_VENDOR_APPS',True)


	#plf file search path
	MY_PLF_FILE_FOLDER=['frameworks/base/core',
		'frameworks/base/packages',
		'packages/apps',
		'packages/providers',
		'packages/services',
		'packages/inputmethods',
		'vendor/qcom/proprietary/telephony-apps',
		'vendor/tct/source/apps',
		'vendor/tct/source/frameworks',
		'vendor/tctalone/apps',
		'vendor/tctalone/TctAppPackage']

	if DAILYBUILD_FLAG:
		if (not os.path.exists('%s/system.img' % PRODUCT_OUT)) and (not os.path.exists('%s/system/build.prop' % PRODUCT_OUT)):
			log.error('ERROR: you must first compile main version!!!')
			sys.exit(0)
	if DEBUG_ONLY == '' and OFFICIALBUILD_FLAG:
		if not DAILYBUILD_FLAG:
			ret = umount_system_image(JRD_OUT_USERDATA)
			if ret != 0:
				log.error("umount file userdata failed")
				sys.exit(ret)
			ret = umount_system_image(JRD_OUT_SYSTEM)
			if ret != 0:
				log.error("ERROR: umount file system failed")
				sys.exit(ret)

		if (not MM_MODULE_NAME) and (not DAILYBUILD_FLAG):
			clean_intermediates_folder(TOP + '/out')
			log.info("clean out dir!")
			prepare_tools()

		clean_files = (
		"remove_apks.log",
		"missing_package.log",
		"ungene_package.log",
		"overlay-failed.log",
		"sign-failed.log",
		"read_variable_error.log"
		"results.xml"
		)
		clean_build_logs(clean_files)
	if not NO_MOUNT_FLAG:
		if os.path.isfile(ORIGIN_ROOT_IMAGE):
			prepare_selinux_tag(ORIGIN_ROOT_IMAGE,TARGET_ROOT_OUT)

		if ORIGIN_USERDATA_IMAGE != '':
			ret = prepare_system_folder(ORIGIN_USERDATA_IMAGE,JRD_OUT_USERDATA,PRODUCT_OUT)
			if ret != 0:
				log.error("ERROR: mount userdata image failed")
				sys.exit(ret)

		ret = prepare_system_folder(ORIGIN_SYSTEM_IMAGE,JRD_OUT_SYSTEM,PRODUCT_OUT)
		if ret != 0:
			log.error("ERROR: mount system image failed")
			sys.exit(ret)
	if not MM_MODULE_NAME:
		if ORIGIN_USERDATA_IMAGE != '':
			generate_system_image('userdata')
			ret = umount_system_image(JRD_OUT_USERDATA)
			if ret != 0:
				log.error("ERROR: umount userdata image failed")
				sys.exit(ret)

		process_sys_plf()
		#prepare_audio_param()
		remove_extra_apk()
	prepare_overlay_res()
	ret = generate_overlay_packages()
	if ret != 0:
		log.error("ERROR: generate overlay package failed")
		sys.exit(ret)
	if not MM_MODULE_NAME:
	    prepre_extra_apk()

	if TARGET_PRODUCT == 'simba6_na':
        	ret=get_gapp_plf_info(TOP + '/device/tct/common/perso/plf/app_control/isdm_gapp_makefile.plf')
        	output_gapp_customized_result(ret)
        	prepare_gapp()

	if OFFICIALBUILD_FLAG:
		change_system_ver()

		if (not (PERSO_VERSION[4:6] == "ZZ")) and (not DAILYBUILD_FLAG):
			prepare_3rd_party_apk()
		if not MM_MODULE_NAME:
			release_key()
			prepare_device_config_xml()

		generate_system_image('system')
		generate_tarball()
		generate_splash_image()
		check_whitespace()
		prepare_tct_meta()

		product_info = TOP+'/manifests/sheet/'+TARGET_PRODUCT+'.csv'
		if (os.path.exists(product_info)) and (len(PERSO_VERSION) == 12):
			MAIN_VERSION  = PERSO_VERSION[1:4] + PERSO_VERSION[6:7]
			DAILY_VERSION = PERSO_VERSION[7:8]
			if re.search(r''+MAIN_VERSION,open(product_info).read()) and (DAILY_VERSION == '0'):
				collect_build_info()
	if not NO_MOUNT_FLAG:
		ret = umount_system_image(JRD_OUT_SYSTEM)
		if ret != 0:
			log.error("ERROR: umount file system failed")
			sys.exit(ret)
