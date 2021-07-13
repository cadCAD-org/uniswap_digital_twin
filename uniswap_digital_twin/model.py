from cadCAD_tools.types import Parameter
from uniswap_digital_twin.types import ETH
from cadCAD_tools.preparation import InitialState, Param
from .types import RAI, BacktestingData, Percentage

## Initial State
genesis_states = {
    'RAI_balance': InitialState(None, RAI),
    'ETH_balance': InitialState(None, ETH)
}

## Parameters
sys_params = {
    # Mechanism parameters
    'fee_percentage': Param(0.003, Percentage),

    # Behavioural parameters
    # TODO: check if really needed
    'fix_cost': [-1], # -1 to deactivate
    'retail_precision': [3],
    'retail_tolerance': [0.0005],

    # If is None, then the model will run on Extrapolation mode
    # Else, it will run on backtesting mode
    'uniswap_events': Param(None, BacktestingData)
}

## Model Logic


def p_actionDecoder(params, substep, _3, s):


    """
    uniswap events is a pd.DataFrame
    Mapping to Uniswap-V2
    1. No transfer events
    2. Mint = Positive mint
    3. Burn = Negative mint
    4. Swap = tokenPurchase or ethPurchase
    event = {'tokenPurchase', 'ethPurchase',
             'mint', 'Transfer'}
    Columns:
        events (event)
        eth_balance (numeric)
        eth_delta (numeric)
        token_balance (numeric)
        token_delta (numeric)
        uni_delta (numeric)
        UNI_supply (numeric)
    """
    uniswap_events = params['uniswap_events']
    
    prev_timestep = s['timestep']
    if substep > 1:
        prev_timestep -= 1
        
    # skip the first two events, as they are already accounted for 
    # in the initial conditions of the system
    t = prev_timestep + 1 
    
    action = {
        'eth_sold': 0,
        'tokens_sold': 0,
        'eth_deposit': 0,
        'token_deposit': 0,
        'UNI_burn': 0, 
        'UNI_pct': 0,
        'fee': 0,
        'conv_tol': 0,
        'price_ratio': 0
    }

    #Event variables
    event = uniswap_events.iloc[t]['event']
    action['action_id'] = event

    # Swap Event
    if event in ['tokenPurchase', 'ethPurchase']:
        # action_key is either `eth_sold` or `token_sold`
        I_t, O_t, I_t1, O_t1, delta_I, delta_O, action_key = get_parameters(uniswap_events, event, s, t)
        
        # Classify actions based on trading heuristics
        # N/A case
        if params['retail_precision'] == -1:
            action[action_key] = delta_I
        # Convenience trader case
        elif classifier(delta_I, delta_O, params['retail_precision']) == "Conv":
            calculated_delta_O = int(get_output_amount(delta_I, I_t, O_t, params))
            if calculated_delta_O >= delta_O * (1-params['retail_tolerance']):
                action[action_key] = delta_I
            else:
                action[action_key] = 0
            action['price_ratio'] =  delta_O / calculated_delta_O
        # Arbitrary trader case
        else:            
            P = I_t1 / O_t1
            actual_P = I_t / O_t
            if(actual_P > P):
                I_t, O_t, I_t1, O_t1, delta_I, delta_O, action_key = get_parameters(uniswap_events, reverse_event(event), s, t)
                P = I_t1 / O_t1
                actual_P = I_t / O_t
                delta_I = get_delta_I(P, I_t, O_t, params)
                delta_O = get_output_amount(delta_I, I_t, O_t, params)
                if(unprofitable_transaction(I_t, O_t, delta_I, delta_O, action_key, params)):
                    delta_I = 0
                action[action_key] = delta_I
            else:
                delta_I = get_delta_I(P, I_t, O_t, params)
                delta_O = get_output_amount(delta_I, I_t, O_t, params)
                if(unprofitable_transaction(I_t, O_t, delta_I, delta_O, action_key, params)):
                    delta_I = 0
                action[action_key] = delta_I
    elif event == 'mint':
        delta_I = uniswap_events['eth_delta'][t]
        delta_O = uniswap_events['token_delta'][t]
        UNI_delta = uniswap_events['UNI_delta'][t]
        UNI_supply = uniswap_events['UNI_supply'][t-1]

        action['eth_deposit'] = delta_I
        action['token_deposit'] = delta_O
        action['UNI_mint'] = UNI_delta
        action['UNI_pct'] = UNI_delta / UNI_supply
    elif event == 'burn':
        delta_I = uniswap_events['eth_delta'][t]
        delta_O = uniswap_events['token_delta'][t]
        UNI_delta = uniswap_events['UNI_delta'][t]
        UNI_supply = uniswap_events['UNI_supply'][t-1]
        if UNI_delta < 0:
            action['eth_burn'] = delta_I
            action['token_burn'] = delta_O
            action['UNI_burn'] = UNI_delta
            action['UNI_pct'] = UNI_delta / UNI_supply
    del uniswap_events
    return action

## Model Structure

PSUBs = [
    {
        'policies': {
            'user_action': p_actionDecoder
        },
        'variables': {
            'RAI_balance': s_mechanismHub_RAI,
            'ETH_balance': s_mechanismHub_ETH,
        }
    }

]