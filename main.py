# Author: Nicholas Long / Sourav Dey, modified by Amy Allen 

import datetime
import os
import random
import sys
import time
from multiprocessing import Process, freeze_support
import pdb ##AA added 

import pandas as pd
from alfalfa_client.alfalfa_client import AlfalfaClient


def pe_signal():
    k_pe = 20000
    return [random.random() * k_pe for _ in range(5)]


def dummy_flow():
    """
    :return: list, control actions
    """
    # create a number for the Supply Fan status
    return [random.random() * 0.5 for _ in range(0, 5)]


# def Controller(object):
def compute_control(y, heating_setpoint):
    """

    :param y: Temperature of zone, K
    :param heating_setpoint: Temperature Setpoint, C
    :return: dict, control input to be used for the next step {<input_name> : <input_value>}
    """
    # Controller parameters
    setpoint = 273.15 + 20
    k_p = 5
    # Compute control
    e = setpoint - y['TRooAir_y']
    value = max(k_p * e, 0)
    u = {'oveAct_u': value,
         'oveAct_activate': 1}

    return u


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
    
    u = {'oveClgSP_u': 30.0 + 273,
         'oveClgSP_activate': True} 
    return u
    
def change_setpoint(): ##AA added 11/9 
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
         
    u = {'oveClgSP_u': 22 + 273,
         'oveClgSP_activate': True} 

    return u


def main():
    alfalfa = AlfalfaClient(url='http://localhost')

    length = 90000 #25 hours 
    step = 300  # 5 minutes -- this may be hard coded in step_fmu.py
    u = initialize_control()
    heating_setpoint = 21

    #file = 'wrapped_2021.11.19.fmu' 
    file='fmus\wrapped_2021.12.07.fmu' 
    
    print(f"Uploading test case {file}")
    site = alfalfa.submit(file)

    print('Starting simulation')

    alfalfa.start(
        site,
        start_datetime=15552000, # July 1st 
        external_clock=True,
    )

    history = {
     'timestamp': [],
      'Teaser_clg_del_y': [], #add in zone temperature and cool flow 
      #'Teaser_mtg_zone_air_temp':[],
      'Teaser_office_zone_air_temp':[],
      'Teaser_mtg_zone_air_temp_v2':[], 
      'OA_DB':[], 
      }
    
     
    u2 = change_setpoint()
    alfalfa.advance([site])
    time.sleep(1.0)

    print('Stepping through time')  
    for i in range(int(length / step)): 
        if i >= 50: #to deal with time lag 
            u=change_setpoint()
        else: 
            u=initialize_control() 
        u=initialize_control() 
        alfalfa.setInputs(site, u)
        print("u")
        print(u) 
        print("i")
        print(i)
        alfalfa.advance([site])
        model_outputs = alfalfa.outputs(site)
        # print(u)
        print(model_outputs)
        sys.stdout.flush()
        current_time = i 
        history['timestamp'].append(current_time) 
 
        if i > 50: 
            history['Teaser_clg_del_y'].append(model_outputs['Teaser_clg_del_y'])
            #history['Teaser_mtg_zone_air_temp'].append(model_outputs['Teaser_mtg_zone_air_temp'])  
            history['Teaser_office_zone_air_temp'].append(model_outputs['Teaser_office_zone_air_temp'])
            history['Teaser_mtg_zone_air_temp_v2'].append(model_outputs['Teaser_mtg_zone_air_temp_v2']) 
            history['OA_DB'].append(model_outputs['Teaser_OA_DB'])
        else: 
            history['Teaser_clg_del_y'].append(0)
            #history['Teaser_mtg_zone_air_temp'].append(0)
            history['Teaser_office_zone_air_temp'].append(0) 
            history['Teaser_mtg_zone_air_temp_v2'].append(0) 
            history['OA_DB'].append(0) 
    
    #alfalfa.stop(site)

    # storage for results
    file_basename = os.path.splitext(os.path.basename(__file__))[0]
    # print(history) 
    result_dir = f'results_{file_basename}'
    os.makedirs(result_dir, exist_ok=True)
    history_df = pd.DataFrame.from_dict(history)
    # print(history_df)
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
