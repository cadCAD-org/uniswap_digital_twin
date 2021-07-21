from math import sqrt


def get_parameters(uniswap_events, event, s, t):
    if(event == "tokenPurchase"):
        I_t = s['ETH_balance']
        O_t = s['RAI_balance']
        I_t1 = uniswap_events['eth_balance'][t]
        O_t1 = uniswap_events['token_balance'][t]
        delta_I = uniswap_events['eth_delta'][t]
        delta_O = uniswap_events['token_delta'][t]
        action_key = 'eth_sold'
    else:
        I_t = s['RAI_balance']
        O_t = s['ETH_balance']
        I_t1 = uniswap_events['token_balance'][t]
        O_t1 = uniswap_events['eth_balance'][t]
        delta_I = uniswap_events['token_delta'][t]
        delta_O = uniswap_events['eth_delta'][t]
        action_key = 'tokens_sold'
    
    return I_t, O_t, I_t1, O_t1, delta_I, delta_O, action_key

def agent_action(signal, s, params):
    #Find current ratio
    current_ratio = s['RAI_balance'] / s['ETH_balance']
    eth_res = s['ETH_balance']
    rai_res = s['RAI_balance']
    
    
    #Find the side of the trade
    if signal < current_ratio:
        action_key = "eth_sold"
    else:
        action_key = "tokens_sold"
    
    #Constant for equations
    C = rai_res * eth_res
    
    if params['agent_type'] == "Arb1":
        eth_size = 20.0
        
        #Find the maximum shift that the trade should be able to sap up all arbitrage opportunities
        max_shift = abs(rai_res / eth_res - signal)
        
        #Start with a constant choice of eth trade
        
        
        
        #Decide on sign of eth
        if action_key == "eth_sold":
            eth_delta = eth_size
        else:
            eth_delta = -eth_size
        
        #Compute the RAI delta to hold C constant
        rai_delta = C / (eth_res + eth_delta) - rai_res
        
        #Caclulate the implied shift in ratio
        implied_shift = abs((rai_res + rai_delta)/ (eth_res + eth_delta) - rai_res / eth_res)
        
        #While the trade is too large, cut trade size in half
        while implied_shift > max_shift:
            
            #Cut trade in half
            eth_delta = eth_delta/2
            rai_delta = C / (eth_res + eth_delta) - rai_res
            implied_shift = abs((rai_res + rai_delta)/ (eth_res + eth_delta) - rai_res / eth_res)
    
        if action_key == "eth_sold":
            I_t = s['ETH_balance']
            O_t = s['RAI_balance']
            I_t1 = s['ETH_balance']
            O_t1 = s['RAI_balance']
            delta_I = eth_delta
            delta_O = rai_delta
        else:
            I_t = s['RAI_balance']
            O_t = s['ETH_balance']
            I_t1 = s['RAI_balance']
            O_t1 = s['ETH_balance']
            delta_I = rai_delta
            delta_O = eth_delta
    elif params['agent_type'] == "Arb2":
        #Taken from Interacting AMM code
        #Hack for workshop, assumes linear trade-off, reality is there is curvature 
        reserve_1 = eth_res
        reserve_2 = rai_res
        amm_price = reserve_2 / reserve_1
        price_error = amm_price + signal
        optimal_value = (reserve_1 * signal - reserve_2) / price_error
        eth_size = round(abs(optimal_value) * .2, 1)
        
        
        #Decide on sign of eth
        if action_key == "eth_sold":
            eth_delta = eth_size
        else:
            eth_delta = -eth_size
        #Compute the RAI delta to hold C constant
        rai_delta = C / (eth_res + eth_delta) - rai_res
        
        if action_key == "eth_sold":
            I_t = s['ETH_balance']
            O_t = s['RAI_balance']
            I_t1 = s['ETH_balance']
            O_t1 = s['RAI_balance']
            delta_I = eth_delta
            delta_O = rai_delta
        else:
            I_t = s['RAI_balance']
            O_t = s['ETH_balance']
            I_t1 = s['RAI_balance']
            O_t1 = s['ETH_balance']
            delta_I = rai_delta
            delta_O = eth_delta
        
    else:
        assert False
    return I_t, O_t, I_t1, O_t1, delta_I, delta_O, action_key

def reverse_event(event):
    if(event == "tokenPurchase"):
        new_event = 'ethPurchase'
    else:
        new_event = 'tokenPurchase'
    return new_event

def get_output_amount(delta_I, I_t, O_t, _params):
    fee_numerator = 1-_params['fee_percentage']
    fee_denominator = 1
    delta_I_with_fee = delta_I * fee_numerator
    numerator = delta_I_with_fee * O_t                        
    denominator = (I_t * fee_denominator) + delta_I_with_fee 
    return int(numerator // denominator)                      

def get_input_amount(delta_O, I_t, O_t, _params):
    fee_numerator = 1-_params['fee_percentage']
    fee_denominator = 1
    numerator = I_t * delta_O * fee_denominator
    denominator = (O_t - delta_O) * fee_numerator
    return int(numerator // denominator) + 1

def classifier(delta_I, delta_O, retail_precision):
    if (delta_I * 10 ** retail_precision).is_integer() or (delta_O * 10 ** retail_precision).is_integer() :
      return "Conv"
    else:
      return "Arb"

def get_delta_I(P, I_t, O_t, _params):
    a = 1-_params['fee_percentage']
    b = 1

    delta_I = (
        (-(I_t*b + I_t*a)) + sqrt(
            ((I_t*b - I_t*a)**2) + (4*P*O_t*I_t*a*b)
        )
    )  / (2*a)

    return int(delta_I)

def unprofitable_transaction(I_t, O_t, delta_I, delta_O, action_key, _params):
    fix_cost = _params['fix_cost']
    if(fix_cost != -1):
      if(action_key == 'eth_sold'): # tokenPurchase
          after_P = 1 / get_output_amount(1, I_t, O_t, _params)
          profit = int(abs(delta_O*after_P) - (delta_I))
      else: # ethPurchase
          after_P = get_input_amount(1, I_t, O_t, _params) / 1
          profit = int(abs(delta_O) - int(delta_I/after_P))
      return (profit < fix_cost)
    else:
      return False
