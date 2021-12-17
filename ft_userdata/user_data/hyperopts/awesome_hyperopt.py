from datetime import datetime
from math import exp
from typing import Dict
from functools import reduce
from pandas import DataFrame

from freqtrade.optimize.hyperopt import IHyperOptLoss

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter, 
                                IStrategy, IntParameter)
# Define some constants:

# set TARGET_TRADES to suit your number concurrent trades so its realistic
# to the number of days
TARGET_TRADES = 600
# This is assumed to be expected avg profit * expected trade count.
# For example, for 0.35% avg per trade (or 0.0035 as ratio) and 1100 trades,
# self.expected_max_profit = 3.85
# Check that the reported Σ% values do not exceed this!
# Note, this is ratio. 3.85 stated above means 385Σ%.
EXPECTED_MAX_PROFIT = 3.0

# max average trade duration in minutes
# if eval ends with higher value, we consider it a failed eval
MAX_ACCEPTED_TRADE_DURATION = 300


class AwesomeHyperOpt(IHyperOptLoss):
    """
    Defines the default loss function for hyperopt
    This is intended to give you some inspiration for your own loss function.

    The Function needs to return a number (float) - which becomes smaller for better backtest
    results.
    """

    stoploss = -0.05
    timeframe = '15m'
    # Define the parameter spaces
    cooldown_lookback = IntParameter(2, 48, default=5, space="protection", optimize=True)
    stop_duration = IntParameter(12, 200, default=5, space="protection", optimize=True)
    use_stop_protection = BooleanParameter(default=True, space="protection", optimize=True)


    @property
    def protections(self):
        prot = []

        prot.append({
            "method": "CooldownPeriod",
            "stop_duration_candles": self.cooldown_lookback.value
        })
        if self.use_stop_protection.value:
            prot.append({
                "method": "StoplossGuard",
                "lookback_period_candles": 24 * 3,
                "trade_limit": 4,
                "stop_duration_candles": self.stop_duration.value,
                "only_per_pair": False
            })

        return prot
    
   # @staticmethod
   #def hyperopt_loss_function(results: DataFrame, trade_count: int,
    #                           min_date: datetime, max_date: datetime,
    #                           config: Dict, processed: Dict[str, DataFrame],
    #                           *args, **kwargs) -> float:
    #    """
    #    Objective function, returns smaller number for better results
    #    """
    #    total_profit = results['profit_ratio'].sum()
    #    trade_duration = results['trade_duration'].mean()

    #    trade_loss = 1 - 0.25 * exp(-(trade_count - TARGET_TRADES) ** 2 / 10 ** 5.8)
    #    profit_loss = max(0, 1 - total_profit / EXPECTED_MAX_PROFIT)
    #    duration_loss = 0.4 * min(trade_duration / MAX_ACCEPTED_TRADE_DURATION, 1)
    #    result = trade_loss + profit_loss + duration_loss
    #    return result
    
    def indicator_space() -> List[Dimension]:
    """
    Define your Hyperopt space for searching strategy parameters
    """
    return [
        Integer(20, 40, name='adx-value'),
        Integer(20, 40, name='rsi-value'),
        Categorical([True, False], name='adx-enabled'),
        Categorical([True, False], name='rsi-enabled'),
        Categorical(['bb_lower', 'macd_cross_signal'], name='trigger')
    ]
        
    def populate_buy_trend(dataframe: DataFrame) -> DataFrame:
            conditions = []
            # GUARDS AND TRENDS
            if 'adx-enabled' in params and params['adx-enabled']:
                conditions.append(dataframe['adx'] > params['adx-value'])
            if 'rsi-enabled' in params and params['rsi-enabled']:
                conditions.append(dataframe['rsi'] < params['rsi-value'])

            # TRIGGERS
            if 'trigger' in params:
                if params['trigger'] == 'bb_lower':
                    conditions.append(dataframe['close'] < dataframe['bb_lowerband'])
                if params['trigger'] == 'macd_cross_signal':
                    conditions.append(qtpylib.crossed_above(
                        dataframe['macd'], dataframe['macdsignal']
                    ))

            if conditions:
                dataframe.loc[
                    reduce(lambda x, y: x & y, conditions),
                    'buy'] = 1

            return dataframe

        return populate_buy_trend
    
    def sell_indicator_space() -> List[Dimension]:
         """
    Define your Hyperopt space for searching strategy parameters
    """
    return [
        Integer(20, 40, name='adx-value'),
        Integer(20, 40, name='rsi-value'),
        Categorical([True, False], name='adx-enabled'),
        Categorical([True, False], name='rsi-enabled'),
        Categorical(['bb_lower', 'macd_cross_signal'], name='trigger')
    ]
    
    def populate_sell_trend(dataframe: DataFrame) -> DataFrame:
            conditions = []
            # GUARDS AND TRENDS
            if 'adx-enabled' in params and params['adx-enabled']:
                conditions.append(dataframe['adx'] < params['adx-value'])
            if 'rsi-enabled' in params and params['rsi-enabled']:
                conditions.append(dataframe['rsi'] > params['rsi-value'])

            # TRIGGERS
            if 'trigger' in params:
                if params['trigger'] == 'bb_lower':
                    conditions.append(dataframe['close'] < dataframe['bb_lowerband'])
                if params['trigger'] == 'macd_cross_signal':
                    conditions.append(qtpylib.crossed_above(
                        dataframe['macd'], dataframe['macdsignal']
                    ))

            if conditions:
                dataframe.loc[
                    reduce(lambda x, y: x & y, conditions),
                    'sell'] = 1

            return dataframe

        return populate_buy_trend
        
