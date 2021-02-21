#!/usr/bin/env python

from __future__ import division, print_function
from nxp_imu import IMU
import time
from bmp280 import bmp280_readdata,bmp280_convert,bmp280_checktemp
from si import hum,temp
from control import func_sensor,func_return,right,addwater
 
"""
accel/mag - 0x1f
gyro - 0x21
bmp280 - 0x77
si7021 - 0x44
pi@r2d2 nxp $ sudo i2cdetect -y 1
    0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 1f
20: -- 21 -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: 40 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- 77
"""
import paho.mqtt.client as mqtt

import json
import time
receive_data = 1


client = mqtt.Client(userdata=receive_data)
 
def on_message(client, userdata, message):
 global receive_data
 receive_data = json.loads(message.payload)
   
def on_connect(client, userdata, flags, rc):
 if rc==0:
  print('connected successfully')
 client.subscribe("IC.embedded/Team_ALG/#",2)

client.on_connect = on_connect
client.on_message = on_message
 
 
client.connect("test.mosquitto.org",port=1883)

def publish_data(temp,hum,pressure,flower_pot):
  payload=json.dumps({"temp":temp,"humidity":hum,"pressure":pressure,"flowerpot":flower_pot,"last_water_hr":last_water_hr,"last_rotate_hr":last_rotate_hr})
  client.publish("IC.embedded/Team_ALG/test",payload)
  #default keep alive is 60s,thus we need at least 1 imformation change between broker and client per minutes#
  
def receive():
  global receive_data
  client.loop_start()
  time.sleep(20) #change holding-connection-state time here
  client.loop_stop()
  
   
  
# the following function is able to read all the data from the sensor,but it not use in the main
def imu():
    imu = IMU(gs=4, dps=2000, verbose=True)
    header = 67
    print('-'*header)
    print("| {:17} | {:20} | {:20} |".format("Accels [g's]", " Magnet [uT]", "Gyros [dps]"))
    print('-'*header)
    for _ in range(10):
        a, m, g = imu.get()
        print('| {:>5.2f} {:>5.2f} {:>5.2f} | {:>6.1f} {:>6.1f} {:>6.1f} | {:>6.1f} {:>6.1f} {:>6.1f} |'.format(
            a[0], a[1], a[2],
            m[0], m[1], m[2],
            g[0], g[1], g[2])
        )
        time.sleep(0.50)
    print('-'*header)
    print(' uT: micro Tesla')
    print('  g: gravity')
    print('dps: degrees per second')
    print('')

#this function convert sensor data to roll,pitch and yaw. However,yaw is not accurate enough without use of kalman filter and
# other alogorithm such as sensor fusion. stepper motor may use instead
def ahrs():
    #print('')
    imu = IMU(verbose=False)
    header = 47
    #print('-'*header)
    #print("| {:20} | {:20} |".format("Accels [g's]", "Orient(r,p,h) [deg]"))
    #print('-'*header)
    fall = False
    #for _ in range(10):
    a, m, g = imu.get()# get data from nxp-9dof fxos8700 + fxas21002
    r, p, h = imu.getOrientation(a, m) # convert sensor data to angle in roll,pitch,yaw axis
    #print the angle data
    #print('| {:>6.1f} {:>6.1f} {:>6.1f} | {:>6.1f} {:>6.1f} {:>6.1f} |'.format(a[0], a[1], a[2], r, p, h))
    time.sleep(1)

    r = abs(r)
    p = abs(p)
    #h =abs(h)

    if r>50 or p>50 :
        fall = True
    else:
        fall =False

    return fall


if __name__ == "__main__":
    last_time = time.localtime()
    last_hour = last_time.tm_hour
    last_min = last_time.tm_min
    last_day = last_time.tm_mday
    last_day2 = last_time.tm_mday # use for water
    last_hour2 = last_time.tm_hour # use for humidity
    last_hour3 = last_time.tm_hour # hour record used for rotation
    last_hour4 = last_time.tm_hour # use for water
    move_time =1 #setting time sleep for the motor
    max_num = 2  # record maximum number of backward
    counter =0 #record number of backward movement
    stabilizer = True  # use to delay movement of motor to avoid problems cause by humidity
    time_delay_humidity = 2 # 2 minutes wait for humidity
    time_for_return = 1 # setting time for return to its initial position,e.g. 1 is an hour
    check_for_return = False
    current_rotate_position =0
    each_hr_for_rotation = 2  # record : rotation every n hours
    rotate_time =1 # set motor time for 90 degree rotation
    manual_return =False #
    manual_backward = False
    manual_rotate = False
    manual_message =None
    each_hr_for_water = 8
    Temp_threshold =35
    Humid_threshold =80
    Pressure_threshold = 1005.7
    water_time =2


    try:
     while True:
        client.loop_start()
        flower = ahrs()
        data = bmp280_readdata()
        p = bmp280_convert(data)
        t = bmp280_checktemp(data)
        te = temp()
        hu = hum()
        print("fall:", flower, "pressure:", p, "temperature:", t, "humidity:", hu)
        received = receive_data


        try:
            manual_message = received["Action"]
            if manual_message == "manual_rotate":
                right(rotate_time)
                current_rotate_position = current_rotate_position + 1
                # set back to zero when 360 degree
                if current_rotate_position == 4:
                    current_rotate_position = 0

            if manual_message=="manual_backward":
                stabilizer, counter = func_sensor(40, 0, 0, counter, max_num, move_time, stabilizer,current_rotate_position,rotate_time,Temp_threshold,Pressure_threshold,Humid_threshold)

            if manual_message=="manual_return":
                counter = func_return(counter, move_time)

            if manual_message == "water":
                addwater(water_time)
                last_hour4 = last_time.tm_hour


        except:
            pass

        try:
          move_time = received["motor_time"]
          max_num = received["max_num"]

          Temp_threshold = received["Temp_threshold"]
          Pressure_threshold = received["Pressure_threshold"]
          Humid_threshold = received["Humid_threshold"]

          rotate_time = received["rotate_time"]
          each_hr_for_rotation =received["each_hr_for_rotation"]

          water_time = received["water_time"]
          each_hr_for_water=received["each_hr_for_water"]



          print("move_time:",move_time,"rotate_time",rotate_time,"water_time",water_time,"max_num",max_num,"Temp_threshold:",Temp_threshold,"Pressure_threshold",Pressure_threshold,"Humid_threshold",Humid_threshold)
          print("each_hr_for_water",each_hr_for_water,"each_hr_for_rotation",each_hr_for_rotation)
        except:
            pass

        try:
          #code for auto motor motion
          #muliti copy of time to avoid intercetion time error after changing parameter by phone
          stabilizer, counter = func_sensor(t,hu,p,counter,max_num,move_time,stabilizer,current_rotate_position,rotate_time,Temp_threshold,Pressure_threshold,Humid_threshold)
          current_time =time.localtime()
          current_min = current_time.tm_min
          current_hour2 = current_time.tm_hour #use for humidity delay
          current_hour = current_time.tm_hour # use for rotation
          current_day = current_time.tm_mday
          current_day2 = current_time.tm_mday #for water
          current_hour3 = current_time.tm_hour # use for rotate
          current_hour4 = current_time.tm_hour # use for water

          # if  time_delay reach threshold, then unlock the humidity sensor
          if current_hour2 == last_hour2:
              if current_min - last_min >= time_delay_humidity:
                  stabilizer = True
                  last_min = current_min
              else:
                  pass


          else:
              hour_difference =current_hour2 - last_hour2
              min_difference = current_min+hour_difference*60-last_min
              if min_difference >= time_delay_humidity:

                  last_hour2 =current_hour2
                  last_min = current_min
                  stabilizer = True




          # rotate every few hours
          if current_hour3 - last_hour3 >= each_hr_for_rotation:
              right(rotate_time)
              current_rotate_position = current_rotate_position +1
              last_hour3 = current_hour3
              # set back to zero when 360 degree
              if current_rotate_position == 4:
                  current_rotate_position = 0



          # every few hours after move backward, it return back to inital position

          if current_day ==last_day:
            if current_hour - last_hour >= time_for_return:
                 counter = func_return(counter,move_time)
                 last_hour =current_hour
          else:
              # across day
              hour_difference2 = current_hour+ 24 - last_hour
              if hour_difference2 >= time_for_return:
                counter = func_return(counter, move_time,current_rotate_position,rotate_time)
                last_day =current_day
                last_hour = current_hour



        #code for water
          if current_day2 == last_day2:
              if current_hour4 - last_hour4 >= each_hr_for_water:
                  addwater(water_time)
                  last_hour4 = current_hour4

          else:
              # across day
              hour_difference3 = current_hour4 + 24 - last_hour4
              if hour_difference3 >= each_hr_for_water:
                  addwater(water_time)
                  last_day2 = current_day2
                  last_hour4 = current_hour4



        except:
            pass
        last_water_hr = last_hour4
        last_rotate_hr = last_hour3
        publish_data(te, hu, p, flower,last_water_hr,last_rotate_hr)

        client.loop_stop()
    except Exception as e:
          print(e)
    except KeyboardInterrupt:
          pass

    #print('Done ...'