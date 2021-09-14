"""
File Name: PullStreamData.py
Associated Files:
Required Python Libraries: subprocess, sys, os, datetime, tkinter
Required External Libraries (will try to pip install): pysftp, matplotlib
Author: John Lukowski(lukowskijohn@gmail.com)
Date Created: 3/18/2021

Purpose: Pull stream activity logs from a server and load them into a graph
Date Modified: 3/19/2020

Licence: This work is licensed under the Creative Commons Attribution-ShareAlike 4.0 International Licence
To view a copy of this license, visit https://creativecommons.org/licenses/by-sa/4.0/
or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.
"""

# Imports
import subprocess, sys, os, datetime, tkinter
from tkinter.simpledialog import askinteger
from tkinter.simpledialog import askfloat
from tkinter.messagebox import askquestion as question

try:
	import pysftp
except:
	print('Unmet dependency pysftp, attempting to install ...\n')
	if subprocess.call([sys.executable, '-m', 'pip', 'install', 'pysftp']):
		print('\nUnable to install pysftp, try manually installing')
		print('https://pypi.org/project/pysftp/')
		exit()
	import pysftp

try:
	import matplotlib.pyplot as plt
	import matplotlib.dates as mdates
	from matplotlib.widgets import Slider
except:
	print('Unmet dependency matplotlib, attempting to install ...\n')
	if subprocess.call([sys.executable, '-m', 'pip', 'install', 'matplotlib']):
		print('\nUnable to install matplotlib, try manually installing')
		print('https://pypi.org/project/matplotlib/')
		exit()
	import matplotlib.pyplot as plt
	import matplotlib.dates as mdates
	from matplotlib.widgets import Slider

##########################################################

# Get Date Interval
appWindow = tkinter.Tk()
appWindow.withdraw()

timeframe = askinteger('Input','Days to retreive (integer days):',parent=appWindow)
interval = int(askfloat('Input','Plot interval (double hours):',parent=appWindow)*60)

replace = True
if os.path.isfile('server1.log') and os.path.isfile('server2.log'):
	replace = 'yes' == question('Replace Logs:','Pull new log files from the server?',icon='question')

appWindow.destroy()

if timeframe is None or interval is None or timeframe <= 0 or interval <= 0:
	print('Invalid days or hours entered.')
	exit()

startDate = datetime.datetime.now()-datetime.timedelta(days=timeframe)

##########################################################

if replace:
	# Create Host Keys For SFTP Connection
	if not os.path.isfile('known_hosts'):
		print('Creating host key file')
		with open('known_hosts','w') as file:
			file.write('parkland.phxcdn.com,165.22.186.151 ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBKmycXTe6D/sadrTJnWbcKNS/xzRTQcO9EWt/va7/+0tnbpvgmzCU4XC5r//5l3fWaN8q76lUWQxdtrq4V8Ikpo=\nparkland2.phxcdn.com,192.241.128.205 ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBE/p5VGOaK56hxXB9JRKwaXq0F7n0LL4WHlYCQ+YZVXnTakIuR0ql7jGMtORjZrvGahHRoY0pG1OIbZPs8OGsKo=')

	# Retreive Server Logs Via SFTP
	cnopts = pysftp.CnOpts(knownhosts='known_hosts')

	with pysftp.Connection(host='%%% SERVER DNS OR IP HERE %%%',username='root',password='%%% PASSWORD HERE %%%',cnopts=cnopts) as sftp:
		sftp.get('/root/.pm2/logs/app-out.log')
		if os.path.isfile('server1.log'):
			os.remove('server1.log')
		os.rename('app-out.log','server1.log')
	with pysftp.Connection(host='%%% SERVER DNS OR IP HERE %%%',username='root',password='%%% PASSWORD HERE %%%',cnopts=cnopts) as sftp:
		sftp.get('/root/.pm2/logs/app-out.log')
		if os.path.isfile('server2.log'):
			os.remove('server2.log')
		os.rename('app-out.log','server2.log')

	if not os.path.isfile('server1.log') or not os.path.isfile('server2.log'):
		print('Unable to retreive log files.')
		exit()

##########################################################

# Parse Data From First Server
server1 = dict()
openStreams = dict()

with open('server1.log') as file:
	data = file.readlines()
	for line in data:
		entry = line.split()

		date = entry[0]
		month = int(date[:date.find('/')])
		date = date[date.find('/')+1:]
		day = int(date[:date.find('/')])
		date = date[date.find('/')+1:]
		year = int(date)

		time = entry[1]
		hour = int(time[:2])%24
		minute = int(time[3:5])
		second = int(time[6:])

		# Only Take Start/Stop Data From Given Timeframe
		timeStamp = datetime.datetime(year, month, day, hour, minute, second)
		if (timeStamp - startDate).total_seconds() >= 0:

			if '[rtmp publish] New stream.' in line:
				key = line[line.find('streamPath=/live/')+17:]
				key = key[:key.find(' ')]
				if 'test' not in key:
					openStreams.update({key:timeStamp})
			elif '[rtmp publish] Close stream.' in line:
				key = line[line.find('streamPath=/live/')+17:]
				key = key[:key.find(' ')]
				if key in openStreams:
					startTimeStamp = openStreams.pop(key)
					if key in server1:
						server1[key] += [(startTimeStamp,timeStamp)]
					else:
						server1.update({key:[(startTimeStamp,timeStamp)]})

# Plot Data From First Server
fig, ax = plt.subplots()

lastTime = startDate
largest = 0
firstTime = datetime.datetime.now()
smallest = (datetime.datetime.now() - startDate).total_seconds()

for key in server1.keys():
	first = server1[key][0][0]
	last = server1[key][-1][1]
	firstElapsed = (first-startDate).total_seconds()
	lastElapsed = (last-startDate).total_seconds()
	if firstElapsed < smallest:
		smallest = firstElapsed
		firstTime = first
	if lastElapsed > largest:
		largest = lastElapsed
		lastTime = last

yPos = 0

for key in server1.keys():
	yPos += 10
	timeStamps = server1[key]
	ax.broken_barh([((stamp[0]-firstTime).total_seconds()/60, (stamp[1]-stamp[0]).total_seconds()/60) for stamp in timeStamps], (yPos-4,8))

ax.set_xlim(0,(lastTime-firstTime).total_seconds()/60+interval)
ax.set_xticks([i for i in range(0,int((lastTime-firstTime).total_seconds()/60)+interval,interval)])
ax.set_xticklabels([firstTime + datetime.timedelta(minutes=i) for i in range(0,int((lastTime-firstTime).total_seconds()/60)+interval,interval)])
ax.set_ylim(0,yPos+10)
ax.set_yticks([i for i in range(10,yPos+10,10)])
ax.set_yticklabels(server1.keys())
ax.grid(True)
ax.set_xlabel('Stream Active')
ax.set_ylabel('Stream Key')
ax.title.set_text('Server: %%% SERVER DNS OR IP HERE %%%')
plt.gcf().autofmt_xdate()

##########################################################

# Parse Data From Second Server
server2 = dict()
openStreams = dict()

with open('server2.log') as file:
	data = file.readlines()
	for line in data:
		entry = line.split()

		date = entry[0]
		month = int(date[:date.find('/')])
		date = date[date.find('/')+1:]
		day = int(date[:date.find('/')])
		date = date[date.find('/')+1:]
		year = int(date)

		time = entry[1]
		hour = int(time[:2])%24
		minute = int(time[3:5])
		second = int(time[6:])

		# Only Take Start/Stop Data From Given Timeframe
		timeStamp = datetime.datetime(year, month, day, hour, minute, second)
		if (timeStamp - startDate).total_seconds() >= 0:

			if '[rtmp publish] New stream.' in line:
				key = line[line.find('streamPath=/live/')+17:]
				key = key[:key.find(' ')]
				if 'test' not in key:
					openStreams.update({key:timeStamp})
			elif '[rtmp publish] Close stream.' in line:
				key = line[line.find('streamPath=/live/')+17:]
				key = key[:key.find(' ')]
				if key in openStreams:
					startTimeStamp = openStreams.pop(key)
					if key in server2:
						server2[key] += [(startTimeStamp,timeStamp)]
					else:
						server2.update({key:[(startTimeStamp,timeStamp)]})

# Plot Data From Second Server
fig1, ax1 = plt.subplots()

lastTime = startDate
largest = 0
firstTime = datetime.datetime.now()
smallest = (datetime.datetime.now() - startDate).total_seconds()

for key in server2.keys():
	first = server2[key][0][0]
	last = server2[key][-1][1]
	firstElapsed = (first-startDate).total_seconds()
	lastElapsed = (last-startDate).total_seconds()
	if firstElapsed < smallest:
		smallest = firstElapsed
		firstTime = first
	if lastElapsed > largest:
		largest = lastElapsed
		lastTime = last

yPos = 0

for key in server2.keys():
	yPos += 10
	timeStamps = server2[key]
	ax1.broken_barh([((stamp[0]-firstTime).total_seconds()/60, (stamp[1]-stamp[0]).total_seconds()/60) for stamp in timeStamps], (yPos-4,8))

ax1.set_xlim(0,(lastTime-firstTime).total_seconds()/60+interval)
ax1.set_xticks([i for i in range(0,int((lastTime-firstTime).total_seconds()/60)+interval,interval)])
ax1.set_xticklabels([firstTime + datetime.timedelta(minutes=i) for i in range(0,int((lastTime-firstTime).total_seconds()/60)+interval,interval)])
ax1.set_ylim(0,yPos+10)
ax1.set_yticks([i for i in range(10,yPos+10,10)])
ax1.set_yticklabels(server2.keys())
ax1.grid(True)
ax1.set_xlabel('Stream Active')
ax1.set_ylabel('Stream Key')
ax1.title.set_text('Server: %%% SERVER DNS OR IP HERE %%%')

plt.gcf().autofmt_xdate()
plt.show()
