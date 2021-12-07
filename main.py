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
    
    u = {'oveClgSP_u': 20.0 + 273,
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

    file = 'wrapped_2021.11.19.fmu' 
    
    print(f"Uploading test case {file}")
    site = alfalfa.submit(file)

    print('Starting simulation')

    alfalfa.start(
        site,
        start_datetime=15552000,
        external_clock=True,
    )

    history = {
        'elapsed_seconds': [],
        'datetime': [],
        'Teaser_clg_del_y': [], #add in zone temperature and cool flow 
        'Teaser_office_zone_air_temp':[],
        'Teaser_mtg_zone_air_temp_v2':[], 
    }
     
    u2 = change_setpoint()
    alfalfa.advance([site])
    time.sleep(1.0)

    print('Stepping through time')  
    for i in range(int(length / step)): 
        u=initialize_control() 
        alfalfa.setInputs(site, u)

        alfalfa.advance([site])

        model_outputs = alfalfa.outputs(site)

        current_time = alfalfa.get_sim_time(site)
        history['elapsed_seconds'].append(current_time) 
        history['datetime'].append(datetime.datetime.fromtimestamp(int(float(current_time)))) # From Jan 1, 1970, which is probably not the correct year
        history['Teaser_clg_del_y'].append(model_outputs['Teaser_clg_del_y'])
        history['Teaser_office_zone_air_temp'].append(model_outputs['Teaser_office_zone_air_temp'])
        history['Teaser_mtg_zone_air_temp_v2'].append(model_outputs['Teaser_mtg_zone_air_temp_v2']) 
    
    alfalfa.stop(site)

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
