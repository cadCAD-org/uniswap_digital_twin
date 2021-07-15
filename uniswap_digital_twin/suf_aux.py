from policy_aux import get_output_amount


# RAI functions

def mint_RAI(_params, substep, sH, s, _input):
    token_reserve = s['RAI_balance']
    return ('RAI_balance', token_reserve + _input['token_deposit'])


def removeLiquidity_RAI(_params, substep, sH, s, _input):
    token_reserve = s['RAI_balance']
    return ('RAI_balance', token_reserve + _input['token_burn'])


def ethToToken_RAI(_params, substep, sH, s, _input):
    delta_I = int(_input['eth_sold']) #amount of ETH being sold by the user
    I_t = s['ETH_balance']
    O_t = s['RAI_balance']
    if delta_I == 0:
        return ('RAI_balance', O_t)
    else:
        delta_O = get_output_amount(delta_I, I_t, O_t, _params)
        return ('RAI_balance', O_t - delta_O)


def tokenToEth_RAI(_params, substep, sH, s, _input):
    delta_I = _input['tokens_sold'] #amount of tokens being sold by the user
    I_t = s['RAI_balance']
    return ('RAI_balance', I_t + delta_I)


# ETH functions

def mint_ETH(_params, substep, sH, s, _input):
    eth_reserve = s['ETH_balance']
    return ('ETH_balance', eth_reserve + _input['eth_deposit'])


def removeLiquidity_ETH(_params, substep, sH, s, _input):
    eth_reserve = s['ETH_balance']
    return ('ETH_balance', eth_reserve + _input['eth_burn'])


def ethToToken_ETH(_params, substep, history, s, _input):
    delta_I = _input['eth_sold'] #amount of ETH being sold by the user
    I_t = s['ETH_balance']
    return ('ETH_balance', I_t + delta_I)


def tokenToEth_ETH(_params, substep, sH, s, _input):
    delta_I = _input['tokens_sold'] #amount of tokens being sold by the user
    O_t = s['ETH_balance']
    I_t = s['RAI_balance']
    if delta_I == 0:
        return ('ETH_balance', O_t)
    else:
        delta_O = get_output_amount(delta_I, I_t, O_t, _params)
        return ('ETH_balance', O_t - delta_O)
    

# UNI functions

def mint_UNI(_params, substep, sH, s, _input):
    total_liquidity = s['UNI_supply']
    return ('UNI_supply', total_liquidity + _input['UNI_mint'])


def removeLiquidity_UNI(_params, substep, sH, s, _input):
    total_liquidity = s['UNI_supply']
    return ('UNI_supply', total_liquidity + _input['UNI_burn'])