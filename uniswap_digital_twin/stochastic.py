from typing import Iterable
import pandas as pd
import numpy as np
from dataclasses import dataclass
from scipy.stats import gamma
import pymc3 as pm
from Types import USD_per_ETH

@dataclass
class FitParams():
    shape: float
    scale: float
    
def kalman_filter(observations: list[float],
                  initialValue: float,
                  truthValues: np.ndarray = None) -> np.ndarray:
    '''
    Description:
    Function to create a Kalman Filter for smoothing currency timestamps in order to search for the
    intrinisic value.
    Parameters:
    observations: Array of observations, i.e. predicted secondary market prices.
    initialValue: Initial Starting value of filter
    truthValues: Array of truth values, i.e. GPS location or secondary market prices. Or can be left
    blank if none exist
    plot: If True, plot the observations, truth values and kalman filter.
    paramExport: If True, the parameters xhat,P,xhatminus,Pminus,K are returned to use in training.
    Example:
    xhat,P,xhatminus,Pminus,K = kalman_filter(observations=train.Close.values[0:-1],
                                              initialValue=train.Close.values[-1],paramExport=True)
    '''
    # intial parameters
    n_iter = len(observations)
    sz = (n_iter,)  # size of array
    if isinstance(truthValues, np.ndarray):
        x = truthValues  # truth value
    z = observations  # observations (normal about x, sigma=0.1)

    Q = 1e-5  # process variance

    # allocate space for arrays
    xhat = np.zeros(sz)      # a posteri estimate of x
    P = np.zeros(sz)         # a posteri error estimate
    xhatminus = np.zeros(sz)  # a priori estimate of x
    Pminus = np.zeros(sz)    # a priori error estimate
    K = np.zeros(sz)         # gain or blending factor

    R = 0.1**2  # estimate of measurement variance, change to see effect

    # intial guesses
    xhat[0] = initialValue
    P[0] = 1.0

    for k in range(1, n_iter):
        # time update
        xhatminus[k] = xhat[k-1]
        Pminus[k] = P[k-1]+Q

        # measurement update
        K[k] = Pminus[k]/(Pminus[k]+R)
        xhat[k] = xhatminus[k]+K[k]*(z[k]-xhatminus[k])
        P[k] = (1-K[k])*Pminus[k]
    return xhat
    
    
def generate_eth_samples(fit_params: FitParams,
                         timesteps: int,
                         samples: int,
                         initial_value: USD_per_ETH = None) -> Iterable[np.ndarray]:
    for run in range(0, samples):
        np.random.seed(seed=run)

        buffer_for_transcients = 100
        X = np.random.gamma(fit_params.shape,
                            fit_params.scale,
                            timesteps + buffer_for_transcients)

        # train kalman
        xhat = kalman_filter(observations=X[0:-1],
                             initialValue=X[-1])

        xhat = xhat[buffer_for_transcients:]
        
        # Align predictions with the initial value
        if initial_value is None:
            pass
        else:
            xhat += (initial_value - xhat[0])

        yield xhat
        
        
def generate_ratio_samples(fit_params: FitParams,
                         timesteps: int,
                         samples: int,
                         initial_value: USD_per_ETH = None) -> Iterable[np.ndarray]:
    for run in range(0, samples):
        np.random.seed(seed=run)
        mu, std = fit_params.shape, fit_params.scale
        deltas = np.random.normal(mu, std, timesteps)
        ratios = np.exp(initial_value + deltas.cumsum()) - 1
        yield ratios