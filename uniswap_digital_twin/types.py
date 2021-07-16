from typing import List
from dataclasses import dataclass
from pandas import DataFrame
from typing import Any

Days = float
ETH = float 
RAI = float
UNI = float
Percentage = float

ETH_per_USD = float
RAI_per_USD = float
USD_per_RAI = float
ETH_per_RAI = float
USD_per_ETH = float


@dataclass
class TokenPairState():
    eth_reserve: ETH
    rai_reserve: RAI
    pool_tokens: UNI


class UniswapAction():
    pass

BacktestingData = DataFrame
ExogenousData = tuple[dict[str, Any], ...]