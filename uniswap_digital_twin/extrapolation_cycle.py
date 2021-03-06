from time import time
from datetime import datetime, timedelta
from pathlib import Path
import os
from os import listdir
from typing import List, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from Types import BacktestingData, Days, USD_per_ETH, ExogenousData
from cadCAD_tools.execution import easy_run
from cadCAD_tools.preparation import prepare_params, Param, ParamSweep
from Data import create_data
import matplotlib.pyplot as plt
from stochastic import FitParams, generate_eth_samples, generate_ratio_samples
import numpy as np
import papermill as pm
from json import dump

def retrieve_data(output_path: str,
                  date_range: Tuple[datetime, datetime]) -> None:
    """
    Download data and store it to a *.csv.xz file.
    """
    df = create_data(start_date=date_range[0], end_date=date_range[1])
    df.to_csv(output_path, compression='gzip')


def prepare(data_path: str) -> BacktestingData:
    return pd.read_csv(data_path,index_col=0)

def simulation_loss(true: BacktestingData, predicted: BacktestingData) -> None:
    loss = (((true-predicted) ** 2).sum() / len(true)) ** .5
    print("RMSE:")
    print(loss)
    
    for col in true.columns:
        plt.plot(true[col])
        plt.plot(predicted[col])
        plt.ylabel("Balance")
        plt.xlabel("Timestep")
        plt.title(col)
        plt.legend(['True', 'Predicted'])
        plt.show()
        
def stochastic_fit(input_data: object) -> FitParams:
    """
    Acquire parameters for the stochastic input signals.
    """

    params = FitParams(0.000036906289210966747, 0.014081285145600045)
    return params

def backtest_model(historical_events_data: BacktestingData) -> pd.DataFrame:
    """
    Runs the cadCAD model in backtesting model and using `backtesting_data`
    as one of the parameters.
    """

    """
    Perform historical backtesting by using the past controller state
    and token states.
    """

    # HACK
    import model as default_model

    # Set-up initial state
    initial_state = default_model.initial_state
    
    
    initial_state.update({'RAI_balance': historical_events_data.loc[0, "token_balance"]})
    initial_state.update({'ETH_balance': historical_events_data.loc[0, "eth_balance"]})

    # Set-up params
    params = default_model.parameters
    
    params.update({'uniswap_events': Param(historical_events_data, BacktestingData)})

    timesteps = len(historical_events_data) - 1

    params = prepare_params(params)


    # Run cadCAD model
    raw_sim_df = easy_run(initial_state,
                          params,
                          default_model.PSUBs[1:],
                          timesteps,
                          1,
                          drop_substeps=True,
                          assign_params=False)
    
    #Post processing
    sim_df = default_model.post_processing(raw_sim_df)
    
    # Historical data
    test_df = historical_events_data[['token_balance','eth_balance']]
    test_df.columns = ['RAI_balance', 'ETH_balance']

    simulation_loss(test_df, sim_df)

    return (sim_df, test_df, raw_sim_df)



def extrapolate_data(backtesting_data, extrapolated_signals, timesteps, initial_ratio, bt)  -> pd.DataFrame:
    # HACK
    import model as default_model

    # Set-up initial state
    initial_state = default_model.initial_state
    
    
    initial_state.update({'RAI_balance': bt["RAI_balance"].iloc[-1]})
    initial_state.update({'ETH_balance': bt["ETH_balance"].iloc[-1]})
    
    

    # Set-up params
    params = default_model.parameters
    params.update({'uniswap_events': Param(None, BacktestingData)})
    params.update({'extrapolated_signals': Param(extrapolated_signals, np.array)})
    params.update({'backtest_mode':Param(False, bool)})
    params.update({'agent_type': ParamSweep(["Arb1", "Arb2"], str)})
    

    params = prepare_params(params)


    # Run cadCAD model
    raw_sim_df = easy_run(initial_state,
                          params,
                          default_model.PSUBs,
                          timesteps,
                          1,
                          drop_substeps=True,
                          assign_params=False)
    
    #Post processing
    #sim_df = default_model.post_processing(raw_sim_df)
    return raw_sim_df

"""def extrapolate_signals(signal_params: FitParams,
                        timesteps: int,
                        initial_price: USD_per_ETH,
                        N_samples=3) -> tuple[ExogenousData, ...]:

    eth_series_list = generate_eth_samples(signal_params,
                                           timesteps,
                                           N_samples,
                                           initial_price)

    # Clean-up data for injecting on the cadCAD model
    exogenous_data_sweep = tuple(tuple({'eth_price': el}
                                       for el
                                       in eth_series)
                                 for eth_series
                                 in eth_series_list)

    return exogenous_data_sweep"""

def extrapolate_signals(signal_params: FitParams,
                        timesteps: int,
                        initial_price: USD_per_ETH,
                        N_samples=3) -> tuple[ExogenousData, ...]:

    eth_series_list = generate_ratio_samples(signal_params,
                                           timesteps,
                                           N_samples,
                                           initial_price)

    # Clean-up data for injecting on the cadCAD model
    exogenous_data_sweep = tuple(tuple({'ratio': el}
                                       for el
                                       in eth_series)
                                 for eth_series
                                 in eth_series_list)

    return exogenous_data_sweep

def extrapolation_cycle(base_path: str = None,
                        historical_interval: Days = 28,
                        historical_lag: Days = 1,
                        price_samples: int = 10,
                        extrapolation_samples: int = 1,
                        extrapolation_timesteps: int = 7 * 24 * 7,
                        use_last_data=False,
                        generate_reports=True) -> object:
    """
    Perform a entire extrapolation cycle.
    """
    t1 = time()
    print("0. Retrieving Data\n---")
    runtime = datetime.utcnow()

    if base_path is None:
        working_path = Path(os.getcwd())
        data_path = working_path / 'data/runs'
    else:
        working_path = Path(base_path)
        data_path = working_path / 'data/runs'
    
    if use_last_data is False:
        date_end = runtime - timedelta(days=historical_lag)
        date_start = date_end - timedelta(days=historical_interval)
        date_range = (date_start, date_end)

        historical_data_path = data_path / f'{runtime}_retrieval.csv.gz'
        retrieve_data(str(historical_data_path),
                      date_range)
        print(f"Data written at {historical_data_path}")
    else:
        files = listdir(data_path.expanduser())
        files = sorted(
            file for file in files if 'retrieval.csv.gz' in file)
        historical_data_path = data_path / f'{files[-1]}'
        print(f"Using last data at {historical_data_path}")

    print("1. Preparing Data\n---")
    backtesting_data = prepare(str(historical_data_path))

    print("2. Backtesting Model\n---")
    backtest_results = backtest_model(backtesting_data)
    


    

    backtest_results[0].to_csv(data_path / f'{runtime}-backtesting.csv.gz',
                               compression='gzip',
                               index=False)

    backtest_results[1].to_csv(data_path / f'{runtime}-historical.csv.gz',
                               compression='gzip',
                               index=False)
    print(backtesting_data.columns)
    timestamps = (backtesting_data['timestamp'].min(), backtesting_data['timestamp'].max())

    metadata = {'createdAt': str(runtime),
                'initial_backtesting_timestamp': str(timestamps[0]),
                'final_backtesting_timestamp': str(timestamps[-1])}

    with open(data_path.expanduser() / f"{runtime}-meta.json", 'w') as fid:
        dump(metadata, fid)
        
    
    
    print("3. Fitting Stochastic Processes\n---")
    #stochastic_params = stochastic_fit(backtesting_data.exogenous_data)
    stochastic_params = stochastic_fit(None)
    
    
    
    print("4. Extrapolating Exogenous Signals\n---")
    N_t = extrapolation_timesteps
    N_price_samples = price_samples
    
    #initial_price = backtest_results[0].iloc[-1].eth_price
    initial_ratio = 6.455903839554217
    
    #extrapolated_signals = extrapolate_signals(stochastic_params,
    #                                           N_t + 10,
    #                                           initial_price,
    #                                           N_price_samples)
    
    extrapolated_signals = extrapolate_signals(stochastic_params,
                                               N_t + 10,
                                               initial_ratio,
                                               N_price_samples)

    pd.DataFrame(extrapolated_signals[0]).to_csv(data_path / f'{runtime}-signal.csv.gz',
                               compression='gzip')

    
    print("5. Extrapolating Future Data\n---")
    N_extrapolation_samples = extrapolation_samples
    extrapolation_df = extrapolate_data(backtesting_data, extrapolated_signals[0], N_t, np.exp(initial_ratio)-1, backtest_results[0])
    extrapolation_df = extrapolation_df.reset_index(drop=True)
    

    print("Test Code for Arb Traders Convergence:")
    pd.DataFrame(extrapolated_signals[0]).plot(kind='line')
    a = extrapolation_df[extrapolation_df['subset'] == 0].set_index('timestep')
    b = extrapolation_df[extrapolation_df['subset'] == 1].set_index('timestep')
    (a['RAI_balance']/a['ETH_balance']).plot(kind='line')
    (b['RAI_balance']/b['ETH_balance']).plot(kind='line')
    plt.legend(['True Ratio', 'Arb Trader 1', 'Arb Trader 2'])
    plt.ylabel("Price Ratio")
    plt.title("Extrapolated Results")
    plt.show()
    
    
    extrapolation_df.to_csv(data_path / f'{runtime}-extrapolation.csv.gz',
                            compression='gzip',
                            index=False)

    print("6. Exporting results\n---")
    if generate_reports == True:
        path = str((data_path / f'{runtime}-').expanduser())
        input_nb_path = (
            working_path / 'templates/extrapolation.ipynb').expanduser()
        output_nb_path = (
            working_path / f'reports/{runtime}-extrapolation.ipynb').expanduser()
        output_html_path = (
            working_path / f'reports/{runtime}-extrapolation.html').expanduser()
        pm.execute_notebook(
            input_nb_path,
            output_nb_path,
            parameters=dict(base_path=path)
        )
        export_cmd = f"jupyter nbconvert --to html '{output_nb_path}'"
        os.system(export_cmd)
        os.system(f"rm '{output_nb_path}'")
    
    t2 = time()
    print(f"7. Done! {t2 - t1 :.2f}s\n---")

    output = (backtest_results, extrapolation_df, stochastic_params)
    return output