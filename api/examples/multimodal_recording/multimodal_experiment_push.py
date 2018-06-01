# MUltimodal Recording

# Erik Strahl
# Matthias Kerezl

# GNU GPL License



from nicomotion import Motion
from nicomotion import Mover
import pypot.dynamixel
from time import sleep
import datetime

import logging
from nicovision import ImageRecorder
import os
from os.path import dirname, abspath
from time import sleep
import datetime
import sys
import cv2

from nicoaudio import pulse_audio_recorder

fnl="left_cam_synced_data.csv"
fnr="right_cam_synced_data.csv"
robot=None

import sqlite3
import random

from subprocess import call

#experiment definitions (Objects and number of graspings)
#definition of objects
objects =["blue ball","blue_plush ball","red_plush ball","orange_plush ball","white cube"]

#big_yellow die
#medium_yellow die
#small_yellow die
#yellow sponge
#green sponge
#blue tissues
#pink tissues
#yellow apple
#light_green apple
#heavy_green apple
#realistic_green apple
#red car
#blue car
#yellow car
#green car
#light tomato
#heavy tomato
#small_red ball
#large_red ball
#small banana
#plush banana
#heavy banana
#obergine banana
#yellow duck
#purple duck
#orange fish
#yellow seal


#action
action="push"

#definition for numbers per object
number_of_samples_per_object=10

#definition of Maximum current - This protects the hands from breaking!! Do not change this, if you do not know!
MAX_CUR_FINGER=120
MAX_CUR_THUMB=100

# Data for SQlite Access
# Experiment Data will be stored in two table database
# with samples for every sample of a grasped onject and subsample for every motor step (like for 10 degrees)

connection = sqlite3.connect("./experiment.db")
cursor = connection.cursor()
# status: 0-succesful , 1- overload, 2 - former_overload


format_str_sample = """INSERT INTO sample (sample_number,object_name , action, timecode)
    VALUES (NULL, "{object_name}", "{action}","{timecode}");"""


# Data for robot movement in high level mode
# move joints with 10 per cent of the speed and hand joints with full speed
fMS = 0.01
fMS_hand=1.0


#Pandas structures for storing joint data
import pandas as pd
columns = ["r_arm_x","r_elbow_y","head_z","isotime"]
dfl = pd.DataFrame(columns=columns)
dfr = pd.DataFrame(columns=columns)


def write_joint_data(robot,df,iso_time):
	
	#df = pd.DataFrame.append(data={"r_arm_x":[robot.getAngle("r_arm_x")],"r_elbow_y":[robot.getAngle("r_elbow_y")],"head_z":[robot.getAngle("head_z")],"isotime":[iso_time]})
	dfn = pd.DataFrame(data={"r_arm_x":[robot.getAngle("r_arm_x")],"r_elbow_y":[robot.getAngle("r_elbow_y")],"head_z":[robot.getAngle("head_z")],"isotime":[iso_time]})
	df = pd.concat([df, dfn], ignore_index=True)
	
	#df = pd.DataFrame(data={"r_arm_x":[robot.getAngle("r_arm_x")],"r_elbow_y":[robot.getAngle("r_elbow_y")],"head_z":[robot.getAngle("head_z")]})
	return(df)



class leftcam_ImageRecorder(ImageRecorder.ImageRecorder):
	
	def custom_callback(self, iso_time,frame):
		
		global dfl;
		
		#write joint data
		
		dfl=write_joint_data(robot,dfl,iso_time)
		
		#small = cv2.resize(frame, (0,0), fx=0.5, fy=0.5)
		#small=cv2.flip(small,-1)
		#return(small)
		return(frame) 

class rightcam_ImageRecorder(ImageRecorder.ImageRecorder):
	
	def custom_callback(self, iso_time,frame):
		
		global dfr;
		
		#write joint data
		
		dfr=write_joint_data(robot,dfr,iso_time)
		
		#small = cv2.resize(frame, (0,0), fx=0.5, fy=0.5)		
		#return(small)
		return(frame) 



def get_sampled_numbers_for_object(object_name):

    sql="SELECT * FROM sample where object_name='" + object_name + " and action ='"+action+"';"
    cursor.execute(sql)
    result = cursor.fetchall()
    return len(result)

def get_needed_numbers_for_object(object_name):

    num = number_of_samples_per_object - get_sampled_numbers_for_object(object_name)
    return (num)

def get_needed_overall_numbers():
    sum=0
    for o in objects:
        sum+=get_needed_numbers_for_object(o)
    return(sum)

def print_progress():
    for o in objects:
        print " For " + o + " - samples needed: " + str(get_needed_numbers_for_object(o))
        " - samples finished: " + str(get_sampled_numbers_for_object(o))


#Print out was is still needed
print "\n\nWe still need the following samples:"

print_progress()

if get_needed_overall_numbers()>0:
    print "\n\nOverall there are still " +str(get_needed_overall_numbers()) + " samples needed.\n\n"
else:
    print "\n\nAll samples recorded. Thank you. If you needed more, adapt the number_of_samples_per_object parameter on the programm.\n\n"
    exit(0)


# Instructions for the experimenter. Brig the robot in Initial position
print "\n Please put the robot in position. Right arm on the table. Left arm hanging down. Give RETURN after finished.\n"
raw_input()

#Put the left arm in defined position
robot = Motion.Motion("../../../json/nico_humanoid_legged_with_hands_mod.json",vrep=False)
mover_path = "../../../../moves_and_positions/"
mov = Mover.Mover(robot, stiff_off=False)


#set the robot to be compliant
robot.disableTorqueAll()

robot.openHand('RHand', fractionMaxSpeed=fMS_hand)

robot.enableForceControl("r_wrist_z", 50)
robot.enableForceControl("r_wrist_x", 50)

robot.enableForceControl("r_indexfingers_x", 50)
robot.enableForceControl("r_thumb_x", 50)

# enable torque of left arm joints
robot.enableForceControl("head_z", 20)
robot.enableForceControl("head_y", 20)

robot.enableForceControl("r_shoulder_z", 20)
robot.enableForceControl("r_shoulder_y", 20)
robot.enableForceControl("r_arm_x", 20)
robot.enableForceControl("r_elbow_y", 20)


# Instructions for the experimenter. Brig the robot in Initial position
print "\n OK. The robot is positioned. We will start the experiment now.\n\n"

pulse_device=pulse_audio_recorder.get_pulse_device()
	
res_x=1920
res_y=1080
framerate=30
amount_of_cams=2
logging.getLogger().setLevel(logging.INFO)
	
		
try:
	os.mkdir(dirname(abspath(__file__))+'/'+action)
except OSError:
	pass


while ( get_needed_overall_numbers() > 0 ):
	
	#Select an object
	o=random.choice(objects)
	while (get_needed_numbers_for_object(o)<1):
		o = random.choice(objects)

	print "Randomly chosen object : " + o + "\n"

	print "\n\n Please put the " + o + " on the robot fingers. Then press RETURN."
	raw_input()

	#!!!!Write Sample data in database
	sql_command = format_str_sample.format(object_name=o, action=action, timecode= datetime.datetime.now().isoformat())
	#print "\n " +sql_command
	cursor.execute(sql_command)
	sample_number=cursor.lastrowid
	
	str_sample_number=str(sample_number)

	try:
		os.mkdir(dirname(abspath(__file__))+'/'+action+'/camera1')
	except OSError:
		pass

	try:
		os.mkdir(dirname(abspath(__file__))+'/'+action+'/camera1')
	except OSError:
		pass


        #step over 8 movement steps
        for n in range(8):

            mov.move_file_position(mover_path + "lift_arm_experiment_pos_"+n+".csv",
                                   subsetfname=mover_path + "subset_right_arm.csv",
                                   move_speed=0.05)

            sleep(1)




        connection.commit()
    connection.close()
    print "\n\n Great! I got all samples together! Finishing experiment.\n"
    print_progress()

    robot=none

#set the robot to be compliant













