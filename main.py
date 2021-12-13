# Author: Nicholas Long / Sourav Dey, modified by Amy Allen 

import datetime
import os
import random
import sys
import time
from multiprocessing import Process, freeze_support
from decimal import Decimal 

import pandas as pd
from alfalfa_client.alfalfa_client import AlfalfaClient
seconds_day = 86400 
sec_hour = 3600 


# def Controller(object):


def initialize_control():
    '''Initialize the control input u.

    Parameters
    ----------
    None

    Returns
    -------
    u : dict
        Defines the control input to be used for the next step.
        {<input_name> : <input_value>}

    '''
    
    u = {'oveClgSP_u': 23 + 273,
         'oveClgSP_activate': True,
         'oveClgSP_v2_u': 23 + 273,
         'oveClgSP_v2_activate': True} 
    return u
    
def change_setpoint(): 
    '''change the control input u.

    Parameters
    ----------
    None

    Returns
    -------
    u : dict
        Defines the control input to be used for the next step.
        {<input_name> : <input_value>}

    '''
         
    u = {'oveClgSP_u': 27 + 273,
         'oveClgSP_activate': True,
         'oveClgSP_v2_u': 27 + 273,
         'oveClgSP_v2_activate': True} 

    return u


def main():
    alfalfa = AlfalfaClient(url='http://localhost')

    length = 604800 #168 hours 
    step = 300  # 5 minutes -- this may be hard coded in step_fmu.py
    u = initialize_control()
    heating_setpoint = 21

    file='wrapped_2021.12.09_bldg2.fmu'
    
    print(f"Uploading test case {file}")
    site = alfalfa.submit(file)

    print('Starting simulation')
    
    start_time=13824000

    alfalfa.start(
        site,
        start_datetime=start_time, 
        external_clock=True,
    )
    print(alfalfa.status(site)) 
    
    time.sleep(10.0)
    print(alfalfa.status(site)) 
    history = {
        'elapsed_seconds': [],
        'hour':[], 
        'Teaser_mtg_zone_air_temp_v2':[], 
        'Teaser_office_zone_air_temp':[], 
        'Teaser_clg_del_y':[], 
        'chiller_power_draw_y':[],
        'Teaser_clg_SP_air':[], 
        'Teaser_clg_SP_air_bldg2':[], 
        'OA_DB':[]
    }
     
    u2 = change_setpoint()
    print("alfalfa advancing") 
    alfalfa.advance([site])
    current_time = alfalfa.get_sim_time(site) 
    

    print('Stepping through time')  

    while Decimal(current_time) <= (start_time + length): 
        current_time = alfalfa.get_sim_time(site) 
        model_outputs = alfalfa.outputs(site)
        sec_into_day = Decimal(current_time) % seconds_day 
        hour = sec_into_day/sec_hour
        history['hour'].append(hour) 
        u=initialize_control() 
        datetime_obj=pd.to_datetime(int(float(current_time)), unit='s', origin=pd.Timestamp('2017-01-01'))
        dow=datetime_obj.weekday()
        if hour >=15 and hour <=17 and dow<5: #going in to DR condition on weekday afternoons 
            alfalfa.setInputs(site, u2) #Increase cooling setpoint
            print("dr condition") 
        else:
            alfalfa.setInputs(site, u) #Keep base case setpoint 
        alfalfa.advance([site])
        model_outputs = alfalfa.outputs(site)
        current_time = alfalfa.get_sim_time(site)
        datetime=pd.to_datetime(int(float(current_time))) 
        history['elapsed_seconds'].append(current_time) 
        #history['datetime'].append(datetime.datetime.fromtimestamp(int(float(current_time)))) # From Jan 1, 1970, which is probably not the correct year
        history['Teaser_mtg_zone_air_temp_v2'].append(model_outputs['Teaser_mtg_zone_air_temp_v2']) 
        history['Teaser_office_zone_air_temp'].append(model_outputs['Teaser_office_zone_air_temp']) 
        history['Teaser_clg_del_y'].append(model_outputs['Teaser_clg_del_y']) 
        history['chiller_power_draw_y'].append(model_outputs['chiller_power_draw_y']) 
        history['Teaser_clg_SP_air'].append(model_outputs['Teaser_clg_SP_air'])
        history['Teaser_clg_SP_air_bldg2'].append(model_outputs['Teaser_clg_SP_air_bldg2']) 
        history['OA_DB'].append(model_outputs['Teaser_OA_DB'])

    alfalfa.stop(site)

    # storage for results
    file_basename = os.path.splitext(os.path.basename(__file__))[0]
    result_dir = f'results_{file_basename}'
    os.makedirs(result_dir, exist_ok=True)
    history_df = pd.DataFrame.from_dict(history)
    history_df.to_csv(f'{result_dir}/{file_basename}.csv')


# In windows you must include this to allow alfalfa client to multiprocess
if __name__ == '__main__':
    if os.name == 'nt':
        freeze_support()
        p = Process(target=main)
        p.start()
    else:
        # Running the debugger doesn't work on mac with freeze_support()
        main()
