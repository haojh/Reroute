#hao,write on 2018.8.2


import argparse
import re 				#hao,Regular expression operations
import numpy as np
import matplotlib.pyplot as plt


parser = argparse.ArgumentParser(description="Plot Reroute experiments' results")
parser.add_argument('--k', dest='k', type=int, default=4, choices=[4, 8], help="Switch fanout number")
parser.add_argument('--duration', dest='duration', type=int, default=60, help="Duration (sec) for each iperf traffic generation")
parser.add_argument('--dir', dest='out_dir', help="Directory to store outputs")
args = parser.parse_args()


def read_file_1(file_name, delim=','):
	"""
		Read the bwmng.txt file.
	"""
	read_file = open(file_name, 'r')
	lines = read_file.xreadlines()
	lines_list = []
	for line in lines:
		line_list = line.strip().split(delim)
		#hao,['15451324.00', '15885310.00', '31336634.00', '15885310', '15451324', '10285.00', '10573.00', '20858.00', '10573', '10285', '0.00', '0.00', '0', '0']
		lines_list.append(line_list)
	read_file.close()
	#hao,lines_list is two-dimensional
	#hao,print(np.array(lines_list).shape)	---->(5376(row),16(col))

	# Remove the last second's statistics, because they are mostly not intact.
	last_second = lines_list[-1][0]
	_lines_list = lines_list[:]
	for line in _lines_list:
		if line[0] == last_second:
			lines_list.remove(line)

	return lines_list

def read_file_2(file_name):
	"""
		Read the first_packets.txt and successive_packets.txt file.
	"""
	read_file = open(file_name, 'r')
	lines = read_file.xreadlines()
	lines_list = []
	for line in lines:
		if line.startswith('rtt') or line.endswith('ms\n'):
			lines_list.append(line)
	read_file.close()
	return lines_list

# hao,2018.9.12
def read_file_3(file_name):
	'''
		read the iperf_msg.txt
		[['[', '3]', '0.0-30.0', 'sec', '3.58', 'MBytes', '1.00', 'Mbits/sec', '0.010', 'ms', '0/', '2552', '(0%)']]

	'''
	read_file = open(file_name,'r')
	lines = read_file.readlines()
	lines_list = []
	for line in lines:
		if line.startswith("["):
			line_list = line.strip().split(" ")
			for elem in line_list:
				if elem == 'ms':
					new_line = [x for x in line_list if x]
					lines_list.append(new_line)
	read_file.close()
	return lines_list

def calculate_average(value_list):
	average_value = sum(map(float, value_list)) / len(value_list)
	return average_value

def get_throughput(throughput, traffic, app, input_file):
	"""
		csv output format:
		(Type rate)
		hao,1533022652,total,15451324.00,15885310.00,31336634.00,15885310,15451324,10285.00,10573.00,20858.00,10573,10285,0.00,0.00,0,0
		unix_timestamp;iface_name;bytes_out/s;bytes_in/s;bytes_total/s;bytes_in;bytes_out;packets_out/s;packets_in/s;packets_total/s;packets_in;packets_out;errors_out/s;errors_in/s;errors_in;errors_out\n
		(Type svg, sum, max)
		unix timestamp;iface_name;bytes_out;bytes_in;bytes_total;packets_out;packets_in;packets_total;errors_out;errors_in\n
		The bwm-ng mode used is 'rate'.

		throughput = {
						'stag1_0.5_0.3':
						{
							'realtime_bisection_bw': {'Reroute':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'realtime_throughput': {'Reroute':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'accumulated_throughput': {'Reroute':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'normalized_total_throughput': {'Reroute':x%, 'ECMP':x%, ...}
						},
						'stag2_0.5_0.3':
						{
							'realtime_bisection_bw': {'Reroute':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'realtime_throughput': {'Reroute':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'accumulated_throughput': {'Reroute':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'normalized_total_throughput': {'Reroute':x%, 'ECMP':x%, ...}
						},
						...
					}
	"""
	full_bisection_bw = 10.0 * (args.k ** 3 / 4)   # (unit: Mbit/s) #hao,160Mbit/s
	lines_list = read_file_1(input_file)
	first_second = int(lines_list[0][0])
	column_bytes_out_rate = 2   # bytes_out/s 	hao,the three column
	column_bytes_out = 6   # bytes_out
	# hao,2018.9.2
	column_packets_in = 10
	column_packets_out = 11

	if app == 'NonBlocking':
		switch = '1001'
	elif app in ['Reroute', 'ECMP']:
		switch = '3[0-9][0-9][0-9]'
	else:
		pass
	sw = re.compile(switch)

	if not throughput.has_key(traffic):
		throughput[traffic] = {}

	if not throughput[traffic].has_key('realtime_bisection_bw'):
		throughput[traffic]['realtime_bisection_bw'] = {}
	if not throughput[traffic].has_key('realtime_throughput'):
		throughput[traffic]['realtime_throughput'] = {}
	if not throughput[traffic].has_key('accumulated_throughput'):
		throughput[traffic]['accumulated_throughput'] = {}
	if not throughput[traffic].has_key('normalized_total_throughput'):
		throughput[traffic]['normalized_total_throughput'] = {}
	# hao
	if not throughput[traffic].has_key('total_send_packets'):
		throughput[traffic]['total_send_packets'] = {}
	if not throughput[traffic].has_key('total_recieve_packets'):
		throughput[traffic]['total_recieve_packets'] = {}


	if not throughput[traffic]['realtime_bisection_bw'].has_key(app):
		throughput[traffic]['realtime_bisection_bw'][app] = {}
	if not throughput[traffic]['realtime_throughput'].has_key(app):
		throughput[traffic]['realtime_throughput'][app] = {}
	if not throughput[traffic]['accumulated_throughput'].has_key(app):
		throughput[traffic]['accumulated_throughput'][app] = {}
	if not throughput[traffic]['normalized_total_throughput'].has_key(app):
		throughput[traffic]['normalized_total_throughput'][app] = 0
	# hao
	if not throughput[traffic]['total_send_packets'].has_key(app):
		throughput[traffic]['total_send_packets'][app] = 0
	if not throughput[traffic]['total_recieve_packets'].has_key(app):
		throughput[traffic]['total_recieve_packets'][app] = 0	

	for i in xrange(args.duration + 1):
		if not throughput[traffic]['realtime_bisection_bw'][app].has_key(i):
			throughput[traffic]['realtime_bisection_bw'][app][i] = 0
		if not throughput[traffic]['realtime_throughput'][app].has_key(i):
			throughput[traffic]['realtime_throughput'][app][i] = 0
		if not throughput[traffic]['accumulated_throughput'][app].has_key(i):
			throughput[traffic]['accumulated_throughput'][app][i] = 0

	for row in lines_list:
		iface_name = row[1]
		if iface_name not in ['total', 'lo', 'eth0', 'enp0s3', 'enp0s8', 'docker0']:
			if switch == '3[0-9][0-9][0-9]':
				if sw.match(iface_name):
					# print iface_name
					if int(iface_name[-1]) > args.k / 2:   # Choose down-going interfaces only.
						if (int(row[0]) - first_second) <= args.duration:   # Take the good values onlyself.hao,"int(row[0]) - first_second" is from 0 to 60
							throughput[traffic]['realtime_bisection_bw'][app][int(row[0]) - first_second] += float(row[column_bytes_out_rate]) * 8.0 / (10 ** 6)   # Mbit/s   #hao,2
							throughput[traffic]['realtime_throughput'][app][int(row[0]) - first_second] += float(row[column_bytes_out]) * 8.0 / (10 ** 6)   # Mbit 			  #hao,6

							throughput[traffic]['total_send_packets'][app] += int(row[column_packets_in])
							throughput[traffic]['total_recieve_packets'][app] += int(row[column_packets_out])

					# # #hao,2018.9.2
					# temp_sw_num = int((iface_name[3]))
					# # print temp_sw_num
					# if (temp_sw_num == 1) or (temp_sw_num == 2) or (temp_sw_num == 3) or (temp_sw_num == 4):
					# 	# print "---1---"
					# 	if int(iface_name[-1]) > args.k /2:
					# 		# print int(row[column_packets_out])
					# 		if (int(row[0]) - first_second) <= args.duration:
					# 			throughput[traffic]['total_send_packets'][app] += int(row[column_packets_in])

					# else:
					# 	# print "---2---"
					# 	if int(iface_name[-1]) > args.k / 2:
					# 		if (int(row[0]) - first_second) <= args.duration:	
					# 			throughput[traffic]['total_recieve_packets'][app] += int(row[column_packets_out])


			# Choose all the interfaces. (For NonBlocking Topo only)
			elif switch == '1001':   
				if sw.match(iface_name):
					if (int(row[0]) - first_second) <= args.duration:
						throughput[traffic]['realtime_bisection_bw'][app][int(row[0]) - first_second] += float(row[column_bytes_out_rate]) * 8.0 / (10 ** 6)   # Mbit/s
						throughput[traffic]['realtime_throughput'][app][int(row[0]) - first_second] += float(row[column_bytes_out]) * 8.0 / (10 ** 6)   # Mbit
			else:
				pass



	for i in xrange(args.duration + 1):
		for j in xrange(i+1):
			throughput[traffic]['accumulated_throughput'][app][i] += throughput[traffic]['realtime_throughput'][app][j]   # Mbit
	# print throughput[traffic]['accumulated_throughput'][app][60]

	throughput[traffic]['normalized_total_throughput'][app] = throughput[traffic]['accumulated_throughput'][app][args.duration] / (full_bisection_bw * args.duration)   # percentage

	return throughput

def get_value_list_1(value_dict, traffic, item, app):
	"""
		Get the values from the "throughput" data structure.
	"""
	value_list = []
	for i in xrange(args.duration + 1):
		value_list.append(value_dict[traffic][item][app][i])
	return value_list

def get_average_bisection_bw(value_dict, traffics, app):
	value_list = []
	complete_list = []
	accumulated_throughput = []
	for traffic in traffics:
		# print value_dict[traffic]['accumulated_throughput'][app][args.duration]
		complete_list.append(value_dict[traffic]['accumulated_throughput'][app][args.duration] / float(args.duration))
		accumulated_throughput.append(value_dict[traffic]['accumulated_throughput'][app][args.duration])
	# print "accumulated_throughput:", accumulated_throughput

	# hao,divided traffics into four parts,as stag1_0.5.x -- stag20_0.5.x / stag1_0.6.x -- stag20_0.6.x
	# for i in xrange(4):
	# 	value_list.append(calculate_average(complete_list[(i * 20): (i * 20 + 20)]))

	# print "complete_list",complete_list
	# print "the length of complete_list:",len(complete_list)

	# hao, the range depends on the length of traffics_brief
	for i in xrange(6):
		# hao, here subtract by 4, because 4 is the number of server in iperf_peers, accroding to different iperf_peers ,the value need to change
		value_list.append(calculate_average(complete_list[i:i+1]) / 4)
	# print 'bw:',value_list
	return value_list

def get_value_list_2(value_dict, traffics, item, app):
	"""
		Get the values from the "throughput", "first_packet_delay" and "average_delay" data structure.
	"""
	value_list = []
	complete_list = []
	for traffic in traffics:
		complete_list.append(value_dict[traffic][item][app])
	# for i in xrange(4):
	# 	value_list.append(calculate_average(complete_list[(i * 20): (i * 20 + 20)]))
	for i in xrange(6):
		value_list.append(calculate_average(complete_list[i:i+1]))
	return value_list

def get_value_list_3(value_dict, traffics, items, app):
	"""
		Get the values from the "first_packet_delay" and "average_delay" data structure.
	"""
	value_list = []
	send_list = []
	receive_list = []
	for traffic in traffics:
		send_list.append(value_dict[traffic][items[0]][app])
		receive_list.append(value_dict[traffic][items[1]][app])

	# hao
	# print "send_list:",send_list
	# print "receive_list:",receive_list

	# for i in xrange(4):
	# 	value_list.append((sum(send_list[(i * 20): (i * 20 + 20)]) - sum(receive_list[(i * 20): (i * 20 + 20)])) / float(sum(send_list[(i * 20): (i * 20 + 20)])))
	for i in xrange(6):
		value_list.append((sum(send_list[i:i+1]) - sum(receive_list[i:i+1])) / float(sum(send_list[i:i+1])))
	return value_list


def get_delay(delay, traffic, keys, app, input_file):
	"""
		first_packet_delay = {
								'stag1_0.5_0.3':
								{
									'average_first_packet_round_trip_delay': {'Reroute':x, 'ECMP':x, ...},
									'first_packet_loss_rate': {'Reroute':x%, 'ECMP':x%, ...}
								},
								'stag2_0.5_0.3':
								{
									'average_first_packet_round_trip_delay': {'Reroute':x, 'ECMP':x, ...},
									'first_packet_loss_rate': {'Reroute':x%, 'ECMP':x%, ...}
								},
								...
							}

		average_delay = {
							'stag1_0.5_0.3':
							{
								'average_round_trip_delay': {'Reroute':x, 'ECMP':x, ...},
								'packet_loss_rate': {'Reroute':x%, 'ECMP':x%, ...},
								'mean_deviation_of_round_trip_delay': {'Reroute':x%, 'ECMP':x%, ...},
							},
							'stag2_0.5_0.3':
							{
								'average_round_trip_delay': {'Reroute':x, 'ECMP':x, ...},
								'packet_loss_rate': {'Reroute':x%, 'ECMP':x%, ...},
								'mean_deviation_of_round_trip_delay': {'Reroute':x%, 'ECMP':x%, ...},
							},
							...
						}
	"""
	if not delay.has_key(traffic):
		delay[traffic] = {}

	for i in range(len(keys)):
		if not delay[traffic].has_key(keys[i]):
			delay[traffic][keys[i]] = {}

	for i in range(len(keys)):
		if not delay[traffic][keys[i]].has_key(app):
			delay[traffic][keys[i]][app] = 0

	lines_list = read_file_2(input_file)
	average_delay_list = []
	if len(keys) == 3:
		for line in lines_list:
			if line.startswith('rtt'):
				average_delay_list.append(float(line.split('/')[4]))
				# hao,['rtt min', 'avg', 'max', 'mdev = 0.5291', '0.5292', '0.5293', '0.000 ms']
			else:
				delay[traffic]['first_packet_total_send'][app] += int(line.split(' ')[0])
				delay[traffic]['first_packet_total_receive'][app] += int(line.split(' ')[3])
		# print "traffic:", traffic
		# print "app:", app
		delay[traffic][keys[0]][app] = calculate_average(average_delay_list)
	elif len(keys) == 4:
		mean_deviation_list = []
		for line in lines_list:
			if line.startswith('rtt'):
				'''
				hao
				600 packets transmitted, 600 received, 0% packet loss, time 60038ms
				rtt min/avg/max/mdev = 0.015/0.057/4.929/0.204 ms
				'''
				average_delay_list.append(float(line.split('/')[4]))
				mean_deviation_list.append(float((line.split('/')[6]).split(' ')[0]))
			else:
				delay[traffic]['total_send'][app] += int(line.split(' ')[0])
				delay[traffic]['total_receive'][app] += int(line.split(' ')[3])
		print "average_delay_list:",len(average_delay_list)
		delay[traffic][keys[0]][app] = calculate_average(average_delay_list)
		delay[traffic][keys[1]][app] = calculate_average(mean_deviation_list)

	return delay

# hao,2018.9.12
# hao, from iperf_msg file get latency message
def get_delay_1(delay, traffic, keys, app, input_file):
	'''
		line = [['[', '3]', '0.0-30.0', 'sec', '3.58', 'MBytes', '1.00', 'Mbits/sec', '0.010', 'ms', '0/', '2552', '(0%)']]
	'''
	# print "------1------"
	if not delay.has_key(traffic):
		delay[traffic] = {}
	# print "------2------"
	for i in range(len(keys)):
		if not delay[traffic].has_key(keys[i]):
			delay[traffic][keys[i]] = {}
	# print "------3------"
	for i in range(len(keys)):
		if not delay[traffic][keys[i]].has_key(app):
			delay[traffic][keys[i]][app] = 0
	# print "------4------"
	lines_list = read_file_3(input_file)
	# print "------5------"
	average_delay_list = []
	packet_loss_rate_list = []
	for line in lines_list:
		average_delay_list.append(float(line[8]))
		p1 = line[len(line)-1]
		# print p1
		p2 = p1[1:len(p1)-2]
		# print p2
		packet_loss_rate_list.append(float(p2) / 100)
	# print "average_delay_list:",average_delay_list
	# print "packet_loss_rate_list:",packet_loss_rate_list
	delay[traffic][keys[0]][app] = calculate_average(average_delay_list)
	delay[traffic][keys[1]][app] = calculate_average(packet_loss_rate_list)
	print delay
	print ""
	return delay



def plot_results():
	"""
		Plot the results:
		1. Plot average bisection bandwidth
		2. Plot normalized total throughput
		3. Plot average first-packet round-trip delay of delay-sensitive traffic
		4. Plot first-packet loss rate of delay-sensitive traffic
		5. Plot average packet round-trip delay of delay-sensitive traffic
		6. Plot packet loss rate of delay-sensitive-traffic
		7. Plot mean deviation of round-trip delay of delay-sensitive traffic

		throughput = {
						'stag1_0.5_0.3':
						{
							'realtime_bisection_bw': {'Reroute':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'realtime_throughput': {'Reroute':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'accumulated_throughput': {'Reroute':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'normalized_total_throughput': {'Reroute':x%, 'ECMP':x%, ...}
						},
						'stag2_0.5_0.3':
						{
							'realtime_bisection_bw': {'Reroute':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'realtime_throughput': {'Reroute':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'accumulated_throughput': {'Reroute':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
							'normalized_total_throughput': {'Reroute':x%, 'ECMP':x%, ...}
						},
						...
					}

		first_packet_delay = {
								'stag1_0.5_0.3':
								{
									'average_first_packet_round_trip_delay': {'Reroute':x, 'ECMP':x, ...},
									'first_packet_loss_rate': {'Reroute':x%, 'ECMP':x%, ...}
								},
								'stag1_0.5_0.3':
								{
									'average_first_packet_round_trip_delay': {'Reroute':x, 'ECMP':x, ...},
									'first_packet_loss_rate': {'Reroute':x%, 'ECMP':x%, ...}
								},
								...
							}

		average_delay = {
							'stag1_0.5_0.3':
							{
								'average_round_trip_delay': {'Reroute':x, 'ECMP':x, ...},
								'packet_loss_rate': {'Reroute':x%, 'ECMP':x%, ...},
								'mean_deviation_of_round_trip_delay': {'Reroute':x%, 'ECMP':x%, ...},
							},
							'stag1_0.5_0.3':
							{
								'average_round_trip_delay': {'Reroute':x, 'ECMP':x, ...},
								'packet_loss_rate': {'Reroute':x%, 'ECMP':x%, ...},
								'mean_deviation_of_round_trip_delay': {'Reroute':x%, 'ECMP':x%, ...},
							},
							...
						}
	"""
	full_bisection_bw = 10.0 * (args.k ** 3 / 4)   # (unit: Mbit/s)
	utmost_throughput = full_bisection_bw * args.duration
	# _traffics = "stag1_0.5_0.3 stag2_0.5_0.3 stag1_0.6_0.2 stag2_0.6_0.2 stag1_0.7_0.2 stag2_0.7_0.2 stag1_0.8_0.1 stag2_0.8_0.1"
	#_traffics = "stag1_0.5_0.3 stag2_0.5_0.3 stag3_0.5_0.3 stag4_0.5_0.3 stag5_0.5_0.3 stag6_0.5_0.3 stag7_0.5_0.3 stag8_0.5_0.3 stag9_0.5_0.3 stag10_0.5_0.3 stag11_0.5_0.3 stag12_0.5_0.3 stag13_0.5_0.3 stag14_0.5_0.3 stag15_0.5_0.3 stag16_0.5_0.3 stag17_0.5_0.3 stag18_0.5_0.3 stag19_0.5_0.3 stag20_0.5_0.3 stag1_0.6_0.2 stag2_0.6_0.2 stag3_0.6_0.2 stag4_0.6_0.2 stag5_0.6_0.2 stag6_0.6_0.2 stag7_0.6_0.2 stag8_0.6_0.2 stag9_0.6_0.2 stag10_0.6_0.2 stag11_0.6_0.2 stag12_0.6_0.2 stag13_0.6_0.2 stag14_0.6_0.2 stag15_0.6_0.2 stag16_0.6_0.2 stag17_0.6_0.2 stag18_0.6_0.2 stag19_0.6_0.2 stag20_0.6_0.2 stag1_0.7_0.2 stag2_0.7_0.2 stag3_0.7_0.2 stag4_0.7_0.2 stag5_0.7_0.2 stag6_0.7_0.2 stag7_0.7_0.2 stag8_0.7_0.2 stag9_0.7_0.2 stag10_0.7_0.2 stag11_0.7_0.2 stag12_0.7_0.2 stag13_0.7_0.2 stag14_0.7_0.2 stag15_0.7_0.2 stag16_0.7_0.2 stag17_0.7_0.2 stag18_0.7_0.2 stag19_0.7_0.2 stag20_0.7_0.2 stag1_0.8_0.1 stag2_0.8_0.1 stag3_0.8_0.1 stag4_0.8_0.1 stag5_0.8_0.1 stag6_0.8_0.1 stag7_0.8_0.1 stag8_0.8_0.1 stag9_0.8_0.1 stag10_0.8_0.1 stag11_0.8_0.1 stag12_0.8_0.1 stag13_0.8_0.1 stag14_0.8_0.1 stag15_0.8_0.1 stag16_0.8_0.1 stag17_0.8_0.1 stag18_0.8_0.1 stag19_0.8_0.1 stag20_0.8_0.1"
	#hao,output2
	# _traffics = "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50"
	#hao,output1
	# _traffics = "01 02 03 04 05 06 07 08 09 10 31 32 33 34 35 36 37 38 39 40 11 12 13 14 15 16 17 18 19 20 41 42 43 44 45 46 47 48 49 50 21 22 23 24 25 26 27 28 29 30"
	#hao,output3
	# _traffics = "10M 15M 20M 25M 30M 35M 40M 45M 50M 55M 60M 65M 70M 75M"

	_traffics = "1M 2M 3M 4M 5M 6M"
	traffics = _traffics.split(' ')
	# print traffics
	# traffics_brief = ['10M', '15M','20M','25M','30M','35M','40M','45M','50M','55M','60M','65M','70M','75M']
	traffics_brief = ['1M', '2M','3M','4M','5M','6M']
	apps = ['Reroute', 'ECMP']
	# apps = ['Reroute']

	throughput = {}
	first_packet_delay = {}
	average_delay = {}
	# i = 0 
	for traffic in traffics:
		# i += 1
		# print i
		print "traffic:",traffic
		for app in apps:
			print "app:",app
			bwmng_file = args.out_dir + './output18/%s/%s/bwmng.txt' % (traffic,app)
			throughput = get_throughput(throughput, traffic, app, bwmng_file)
			# keys1 = ['average_first_packet_round_trip_delay', 'first_packet_total_send', 'first_packet_total_receive']
			# keys2 = ['average_round_trip_delay', 'mean_deviation_of_round_trip_delay', 'total_send', 'total_receive']
			# first_packet_file = args.out_dir + './output2/%s/%s/first_packets.txt' % (traffic,app)
			# first_packet_delay = get_delay(first_packet_delay, traffic, keys1, app, first_packet_file)
			# successive_packets_file = args.out_dir + './output3/%s/%s/successive_packets.txt' %(traffic, app)
			# average_delay = get_delay(average_delay, traffic, keys2, app, successive_packets_file)

			# hao,2018.9.12
			key3 = ["average_round_trip_delay", "packet_loss_rate"]
			iperf_msg_file = args.out_dir + './output18/%s/%s/iperf_msg.txt' %(traffic, app)
			average_delay = get_delay_1(average_delay, traffic, key3, app, iperf_msg_file)


	# 1. Plot average throughput.
	fig, ax = plt.subplots()
	fig.set_size_inches(10, 5)
	num_groups = len(traffics_brief)
	num_bar = len(apps)
	Reroute_value_list = get_average_bisection_bw(throughput, traffics, 'Reroute')
	ECMP_value_list = get_average_bisection_bw(throughput, traffics, 'ECMP')
	# Hedera_value_list = get_average_bisection_bw(throughput, traffics, 'Hedera')
	#hao,index = [0.15  1.15  2.15  3.15]
	index = np.arange(num_groups) + 0.15
	# bar_width = 0.15
	#hao
	bar_width = 0.1
	opacity = 1     #hao,transparent
	ax.bar(index + 0 * bar_width, Reroute_value_list, bar_width, alpha=opacity, color='#315E9B', label='Reroute')
	ax.bar(index + 1 * bar_width, ECMP_value_list, bar_width, alpha=opacity, color='#FB8025', label='ECMP')
	# for i, v in zip(index + 0 * bar_width, Reroute_value_list):
	# 	print i,v
	# 	ax.text(i, v + .25, str(int(v)), color='blue', fontweight='bold')
	
	# for i, v in zip(index + 1 * bar_width, ECMP_value_list):
	# 	ax.text(i , v + .25, str(int(v)), color='#315E9B', fontweight='bold')


	# plt.bar(index + 2 * bar_width, Hedera_value_list, bar_width, alpha=opacity, color='#21A27A', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics_brief, fontsize='large')
	plt.ylabel('Average Throughput\n(Mbps)', fontsize='x-large')
	# plt.ylim(0, full_bisection_bw)
	# plt.yticks(np.linspace(0, full_bisection_bw, 11), fontsize='large')
	plt.yticks(np.arange(0, 10, 1))
	plt.legend(loc='upper left', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.tight_layout()
	plt.savefig(args.out_dir + '/1.average_throughput.png')



	# 5. Plot average packet round-trip delay of delay-sensitive traffic.
	# hao , use iperf latency message to calculate latency
	item = 'average_round_trip_delay'
	fig = plt.figure()
	fig.set_size_inches(10, 5)
	num_groups = len(traffics_brief)
	num_bar = len(apps)
	Reroute_value_list = get_value_list_2(average_delay, traffics, item, 'Reroute')
	# Hedera_value_list = get_value_list_2(average_delay, traffics, item, 'Hedera')
	ECMP_value_list = get_value_list_2(average_delay, traffics, item, 'ECMP')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.1
	opacity = 1
	plt.bar(index + 1 * bar_width, Reroute_value_list, bar_width, alpha=opacity, color='#315E9B', label='Reroute')
	plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, alpha=opacity, color='#FB8025', label='ECMP')
	# plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, alpha=opacity, color='#21A27A', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics_brief, fontsize='large')
	plt.ylabel('Average Packet Round-trip Delay(ms)', fontsize='large')
	plt.yticks(fontsize='large')
	plt.legend(loc='upper left', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.tight_layout()
	plt.savefig(args.out_dir + '/5.average_round_trip_delay.png')


	# 6. Plot packet loss rate of delay-sensitive traffic.
	# hao, use bwm-ng message to calculate packet loss rate
	# items = ['total_send', 'total_receive']
	items = ['total_send_packets', 'total_recieve_packets']
	# items = ['total_recieve_packets', 'total_send_packets']
	fig = plt.figure()
	fig.set_size_inches(10, 5)
	num_groups = len(traffics_brief)
	num_bar = len(apps)
	Reroute_value_list = get_value_list_3(throughput, traffics, items, 'Reroute')
	# print "packet loss rate of Reroute_value_list:",Reroute_value_list
	# Hedera_value_list = get_value_list_3(average_delay, traffics, items, 'Hedera')
	ECMP_value_list = get_value_list_3(throughput, traffics, items, 'ECMP')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.1
	plt.bar(index + 1 * bar_width, Reroute_value_list, bar_width, color='#315E9B', label='Reroute')
	plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, color='#FB8025', label='ECMP')
	# plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, color='#21A27A', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics_brief, fontsize='large')
	plt.ylabel('Packet Loss Rate', fontsize='large')
	plt.yticks(fontsize='large')
	plt.legend(loc='upper left', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.tight_layout()
	plt.savefig(args.out_dir + '/6.packet_loss_rate_method1.png')


	# 7. Plot packet loss rate of delay-sensitive traffic.
	# hao, use iperf's packet loss rate message to calculate packet loss rate 
	item = 'packet_loss_rate'
	fig = plt.figure()
	fig.set_size_inches(10, 5)
	num_groups = len(traffics_brief)
	num_bar = len(apps)
	Reroute_value_list = get_value_list_2(average_delay, traffics, item, 'Reroute')
	# print "packet loss rate of Reroute_value_list:",Reroute_value_list
	# Hedera_value_list = get_value_list_3(average_delay, traffics, items, 'Hedera')
	ECMP_value_list = get_value_list_2(average_delay, traffics, item, 'ECMP')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.1
	plt.bar(index + 1 * bar_width, Reroute_value_list, bar_width, color='#315E9B', label='Reroute')
	plt.bar(index + 2 * bar_width, ECMP_value_list, bar_width, color='#FB8025', label='ECMP')
	# plt.bar(index + 3 * bar_width, Hedera_value_list, bar_width, color='#21A27A', label='Hedera')
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics_brief, fontsize='large')
	plt.ylabel('Packet Loss Rate 2', fontsize='large')
	plt.yticks(fontsize='large')
	plt.legend(loc='upper left', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.tight_layout()
	plt.savefig(args.out_dir + '/7.packet_loss_rate_method2.png')



if __name__ == '__main__':
	plot_results()
