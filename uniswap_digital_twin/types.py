from typing import List
from dataclasses import dataclass
from pandas import DataFrame

Days = float
ETH = float 
RAI = float
UNI = float
Percentage = float


@dataclass
class TokenPairState():
    eth_reserve: ETH
    rai_reserve: RAI
    pool_tokens: UNI


class UniswapAction():
    pass

BacktestingData = DataFrame
