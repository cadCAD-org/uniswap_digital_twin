from time import time
from datetime import datetime, timedelta
from pathlib import Path
import os
from os import listdir
from typing import List, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from Types import BacktestingData, Days
from cadCAD_tools.execution import easy_run
from cadCAD_tools.preparation import prepare_params
from Data import create_data


def retrieve_data(output_path: str,
                  date_range: Tuple[datetime, datetime]) -> None:
    """
    Download data and store it to a *.csv.xz file.
    """
    df = create_data()
    df.to_csv(output_path, compression='gzip')


def prepare(data_path: str) -> BacktestingData:
    return pd.read_csv(data_path)


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
    initial_state.update('RAI_balance', historical_events_data.RAI_balance.iloc[0])
    initial_state.update('ETH_balance', historical_events_data.RAI_balance.iloc[0])

    # Set-up params
    params = default_model.parameters
    params.update('uniswap_events', historical_events_data)

    timesteps = len(historical_events_data.heights) - 1

    params = prepare_params(params)

    # Run cadCAD model
    raw_sim_df = easy_run(initial_state,
                          params,
                          default_model.timestep_block,
                          timesteps,
                          1,
                          drop_substeps=True,
                          assign_params=False)


    # TODO
    # Sim_df and test_df should only have RAI_balance and ETH_balance
    # Need refactor
    # sim_df = default_model.post_processing(raw_sim_df)

    # Historical data
    test_df = pd.DataFrame.from_dict(
        backtesting_data.pid_states, orient='index')

    # Need to refactor: https://github.com/BlockScience/reflexer-digital-twin/blob/master/rai_digital_twin/backtesting.py
    loss = simulation_loss(sim_df, test_df)
    print(f"Backtesting loss: {loss :.2%}")

    return (sim_df, test_df, raw_sim_df)

def extrapolation_cycle(base_path: str = None,
                        historical_interval: Days = 28,
                        historical_lag: Days = 0,
                        price_samples: int = 10,
                        extrapolation_samples: int = 1,
                        extrapolation_timesteps: int = 7 * 24,
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


    """

    backtest_results[0].to_csv(data_path / f'{runtime}-backtesting.csv.gz',
                               compression='gzip',
                               index=False)

    backtest_results[1].to_csv(data_path / f'{runtime}-historical.csv.gz',
                               compression='gzip',
                               index=False)

    timestamps = sorted([el['timestamp']
                         for (timestep, el)
                         in backtesting_data.exogenous_data.items()])

    metadata = {'createdAt': str(runtime),
                'initial_backtesting_timestamp': str(timestamps[0]),
                'final_backtesting_timestamp': str(timestamps[-1])}

    with open(data_path.expanduser() / f"{runtime}-meta.json", 'w') as fid:
        dump(metadata, fid)

    print("3. Fitting Stochastic Processes\n---")
    stochastic_params = stochastic_fit(backtesting_data.exogenous_data)

    print("4. Extrapolating Exogenous Signals\n---")
    N_t = extrapolation_timesteps
    N_price_samples = price_samples
    initial_price = backtest_results[0].iloc[-1].eth_price
    extrapolated_signals = extrapolate_signals(stochastic_params,
                                               N_t + 10,
                                               initial_price,
                                               N_price_samples)

    print("5. Extrapolating Future Data\n---")
    N_extrapolation_samples = extrapolation_samples
    extrapolation_df = extrapolate_data(extrapolated_signals,
                                        backtest_results,
                                        governance_events,
                                        N_t,
                                        N_extrapolation_samples)

    extrapolation_df.to_csv(data_path / f'{runtime}-extrapolation.csv.gz',
                            compression='gzip',
                            index=False)

    print("6. Exporting results\n---")
    if generate_reports == True:
        path = str((data_path / f'{runtime}-').expanduser())
        input_nb_path = (
            working_path / 'rai_digital_twin/templates/extrapolation.ipynb').expanduser()
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
    """